"""GQE unified BRSR extractor - runs server-side on downloaded PDFs."""
import pdfplumber, re, json, sys, os

def num(s):
    if s is None: return None
    s = str(s).replace(',', '').replace('%','').strip()
    if s in ('','-','–','—','NA','N/A','Nil','nil'): return None
    try: return float(s)
    except: return None

def find_pages(pdf, keys, need=1):
    out=[]
    for i,p in enumerate(pdf.pages):
        t=(p.extract_text() or "").lower()
        if sum(1 for k in keys if k in t) >= need:
            out.append((i,p.extract_text() or ""))
    return out

def first_num_after(text, pattern, lo=0, hi=1e12):
    """Find pattern then grab first plausible number on that line."""
    for line in text.split('\n'):
        m = re.search(pattern, line, re.I)
        if m:
            tail = line[m.end():]          # only look AFTER the label
            tail = re.sub(r'tco2\s*e|tco2|co2e|co2|gj/mt|mwh|gj|kl|mt\b|unit', ' ', tail, flags=re.I)
            for tok in re.findall(r'[\d][\d,]*\.?\d*', tail):
                v = num(tok)
                if v is not None and lo <= v <= hi:
                    return v
    return None

def extract(path):
    r = dict(scope1_tco2e=None, scope2_tco2e=None, scope12_tco2e=None,
             total_energy_gj=None, renewable_energy_gj=None, renewable_pct=None,
             women_directors_pct=None, women_employees_pct=None,
             controversies=0, notes=[])
    try:
        pdf = pdfplumber.open(path)
    except Exception as e:
        r['notes'].append(f"open_fail:{e}"); return r

    # ---- EMISSIONS ----
    for i,t in find_pages(pdf, ['scope 1','tco2e'], need=2):
        s1 = first_num_after(t, r'total scope 1 emission', 1, 5e8)
        s2 = first_num_after(t, r'total scope 2 emission', 1, 5e8)
        if s1: r['scope1_tco2e']=s1
        if s2: r['scope2_tco2e']=s2
        if r['scope1_tco2e'] and r['scope2_tco2e']:
            r['scope12_tco2e']=r['scope1_tco2e']+r['scope2_tco2e']; break
    if r['scope12_tco2e'] is None:
        for i,t in find_pages(pdf, ['scope 1 and scope 2'], need=1):
            v=first_num_after(t, r'total scope 1 and scope 2 emission', 1, 5e8)
            if v: r['scope12_tco2e']=v; break

    # ---- ENERGY ----
    for i,t in find_pages(pdf, ['total energy consum'], need=1):
        te = first_num_after(t, r'total energy consum', 100, 5e9)
        if te:
            r['total_energy_gj']=te
            ren = (first_num_after(t, r'total energy consumed from renewable', 0, 5e9)
                   or first_num_after(t, r'from renewable sources', 0, 5e9))
            if ren is not None:
                r['renewable_energy_gj']=ren
                if te>0: r['renewable_pct']=round(ren/te,4)
            break

    # ---- WOMEN DIRECTORS ----
    for i,t in find_pages(pdf, ['women','director'], need=2):
        for line in t.split('\n'):
            if re.search(r'women', line, re.I) and re.search(r'director|board', line, re.I):
                pct = re.findall(r'(\d+\.?\d*)\s*%', line)
                if pct:
                    v=num(pct[-1])
                    if v is not None and 0<=v<=100: r['women_directors_pct']=round(v/100,4); break
        if r['women_directors_pct'] is not None: break

    # ---- WOMEN EMPLOYEES ----
    for i,t in find_pages(pdf, ['women','employee'], need=2):
        for line in t.split('\n'):
            if re.search(r'women|female', line, re.I) and re.search(r'employee|workforce', line, re.I):
                pct = re.findall(r'(\d+\.?\d*)\s*%', line)
                if pct:
                    v=num(pct[-1])
                    if v is not None and 0<v<=100: r['women_employees_pct']=round(v/100,4); break
        if r['women_employees_pct'] is not None: break

    # ---- CONTROVERSIES (BRSR Principle 1 penalties) ----
    for i,t in find_pages(pdf, ['penalt'], need=1):
        tl=t.lower()
        if any(k in tl for k in ['penalty imposed','fine imposed','penalty paid','settlement amount paid']):
            if not any(k in tl for k in ['nil','no penalt','not applicable','none']):
                r['controversies']=1; break
    pdf.close()
    return r

if __name__=='__main__':
    out={}
    for f in sorted(os.listdir('pdfs')):
        if f.endswith('.pdf'):
            out[f]=extract(os.path.join('pdfs',f))
            print(f, json.dumps({k:v for k,v in out[f].items() if k!='notes'}))
    json.dump(out, open('out/results.json','w'), indent=1)
