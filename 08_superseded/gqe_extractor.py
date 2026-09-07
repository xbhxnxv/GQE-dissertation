import pdfplumber, re, json, sys, os

def num(s):
    s=str(s).replace(',','').strip()
    try: return float(s)
    except: return None

def clean(line):
    return re.sub(r'tco2\s*e|tco2|co2e|co2|gj/mt|mwh|gj|kl|\bmt\b|unit', ' ', line, flags=re.I)

def grab(line, pat, lo, hi):
    m=re.search(pat,line,re.I)
    if not m: return None
    for tok in re.findall(r'[\d][\d,]*\.?\d*', clean(line[m.end():])):
        v=num(tok)
        if v is not None and lo<=v<=hi: return v
    return None

def extract(path):
    r=dict(scope1=None,scope2=None,scope12=None,energy_gj=None,renew_gj=None,
           renew_pct=None,wdir=None,wemp=None,controv=0)
    pdf=pdfplumber.open(path)
    for p in pdf.pages:
        t=p.extract_text() or ""
        tl=t.lower()
        if 'scope 1' not in tl and 'energy consum' not in tl and 'women' not in tl and 'penalt' not in tl:
            continue
        for line in t.split('\n'):
            if r['scope1'] is None:
                v=grab(line,r'total scope 1 emission',1,5e8)
                if v: r['scope1']=v
            if r['scope2'] is None:
                v=grab(line,r'total scope 2 emission',1,5e8)
                if v: r['scope2']=v
            if r['energy_gj'] is None:
                v=grab(line,r'total energy consum(ption|ed)?\s*\(?a\+b\+c\)?|total energy consum',100,5e9)
                if v: r['energy_gj']=v
            if r['renew_gj'] is None:
                v=grab(line,r'total energy consumed from renewable',0,5e9)
                if v: r['renew_gj']=v
            if r['wdir'] is None and re.search(r'women',line,re.I) and re.search(r'director|board',line,re.I):
                pct=re.findall(r'(\d+\.?\d*)\s*%',line)
                if pct:
                    v=num(pct[-1])
                    if v is not None and 0<=v<=100: r['wdir']=round(v/100,4)
            if r['wemp'] is None and re.search(r'women|female',line,re.I) and re.search(r'employee|workforce',line,re.I):
                pct=re.findall(r'(\d+\.?\d*)\s*%',line)
                if pct:
                    v=num(pct[-1])
                    if v is not None and 0<v<=100: r['wemp']=round(v/100,4)
        if 'penalt' in tl and any(k in tl for k in ['penalty imposed','fine imposed','penalty paid']):
            if not any(k in tl for k in ['nil','no penalt','not applicable']): r['controv']=1
    pdf.close()
    if r['scope1'] and r['scope2']: r['scope12']=r['scope1']+r['scope2']
    if r['energy_gj'] and r['renew_gj']: r['renew_pct']=round(r['renew_gj']/r['energy_gj'],4)
    return r

if __name__=='__main__':
    f=sys.argv[1]
    print(os.path.basename(f), json.dumps(extract(f)))
