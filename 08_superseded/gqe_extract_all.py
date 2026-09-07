"""
GQE BRSR EXTRACTOR — companies 1 to 100, single run
===================================================
Run this in VS Code. It reads every PDF in one folder, extracts the 8 ESG
fields from the BRSR section, and writes:
  - extraction_results.csv   (all extracted numbers, one row per company-year)
  - extraction_report.txt    (which companies/fields succeeded vs need manual check)
  - updates GQE_OPS_Data_Tracker.xlsx  (if present in the same folder)

WHY THIS WORKS: it uses `pdftotext -layout` (via the `pdftotext` binary from
poppler) which preserves the table columns in Indian BRSR reports, then reads
the two number columns (current FY, previous FY) off each labelled row.

────────────────────────────────────────────────────────────────────────────
ONE-TIME SETUP (do this first, see instructions I gave you in chat)
────────────────────────────────────────────────────────────────────────────
1. Install poppler so the `pdftotext` command exists:
     - Windows: download poppler, add its /bin folder to PATH
     - Mac:     brew install poppler
     - Linux:   sudo apt install poppler-utils
2. pip install openpyxl pandas
3. Put ALL your PDFs in ONE folder. Any filename with the company name + year
   works, e.g.  "sun pharma 2023.pdf", "tata_steel_2024.pdf",
   "1785131128199_ongc_2024.pdf". The script strips prefixes automatically.
4. Set PDF_FOLDER below to that folder. Set EXCEL_PATH to your tracker.
5. Press Run.
────────────────────────────────────────────────────────────────────────────
"""

import os, re, glob, subprocess, csv
from pathlib import Path

# ─── EDIT THESE THREE PATHS ───────────────────────────────────────────────────
PDF_FOLDER = r"C:\Users\ASUS\Desktop\me\Dissertation\pdfs"
EXCEL_PATH = r"C:\Users\ASUS\Desktop\me\Dissertation\GQE_OPS_Data_Tracker.xlsx"
OUT_FOLDER = r"C:\Users\ASUS\Desktop\me\Dissertation"
# ─────────────────────────────────────────────────────────────────────────────

# company keyword -> (Display Name, NSE ticker, Sector)
# Order matters: multi-word / conflict-prone keys are checked first via longest-match.
COMPANY_MAP = {
    "tech mahindra":("Tech Mahindra","TECHM.NS","IT"),
    "tech_mahindra":("Tech Mahindra","TECHM.NS","IT"),
    "hdfc life":("HDFC Life","HDFCLIFE.NS","Insurance"),
    "hdfc_life":("HDFC Life","HDFCLIFE.NS","Insurance"),
    "sbi life":("SBI Life","SBILIFE.NS","Insurance"),
    "sbi_life":("SBI Life","SBILIFE.NS","Insurance"),
    "icici lombard":("ICICI Lombard","ICICIGI.NS","Insurance"),
    "icici_lombard":("ICICI Lombard","ICICIGI.NS","Insurance"),
    "lic life insurance":("LIC","LICI.NS","Insurance"),
    "bajaj finserv":("Bajaj Finserv","BAJAJFINSV.NS","FinServ"),
    "bajaj_finserv":("Bajaj Finserv","BAJAJFINSV.NS","FinServ"),
    "bajaj finance":("Bajaj Finance","BAJFINANCE.NS","FinServ"),
    "bajaj_finance":("Bajaj Finance","BAJFINANCE.NS","FinServ"),
    "bajaj auto":("Bajaj Auto","BAJAJ-AUTO.NS","Auto"),
    "bajaj_auto":("Bajaj Auto","BAJAJ-AUTO.NS","Auto"),
    "apl apollo":("APL Apollo","APLAPOLLO.NS","Metals"),
    "apollo hospital":("Apollo Hospitals","APOLLOHOSP.NS","Pharma"),
    "apollo tyre":("__SKIP__","","") ,  # not in NIFTY sample; ignore
    "tata steel":("Tata Steel","TATASTEEL.NS","Metals"),
    "tata_steel":("Tata Steel","TATASTEEL.NS","Metals"),
    "tata power":("Tata Power","TATAPOWER.NS","Energy"),
    "tata_power":("Tata Power","TATAPOWER.NS","Energy"),
    "tata consumer":("Tata Consumer","TATACONSUM.NS","FMCG"),
    "tata consumers":("Tata Consumer","TATACONSUM.NS","FMCG"),
    "adani green":("Adani Green","ADANIGREEN.NS","Energy"),
    "adani ports":("Adani Ports","ADANIPORTS.NS","Infra"),
    "adani enterprise":("Adani Enterprises","ADANIENT.NS","Energy"),
    "ultratech cement":("UltraTech Cement","ULTRACEMCO.NS","Infra"),
    "ultratech":("UltraTech Cement","ULTRACEMCO.NS","Infra"),
    "l&t tech":("LTTS","LTTS.NS","Infra"),
    "l&t_tech":("LTTS","LTTS.NS","Infra"),
    "ltts":("LTTS","LTTS.NS","Infra"),
    "ltimindtree":("LTIMindtree","LTIM.NS","IT"),
    "indus tower":("Indus Towers","INDUSTOWER.NS","Telecom"),
    "policy bazaar":("PolicyBazaar","POLICYBZR.NS","FinTech"),
    "shree cement":("Shree Cement","SHREECEM.NS","Infra"),
    "jindal steel":("Jindal Steel","JINDALSTEL.NS","Metals"),
    "bank of baroda":("Bank of Baroda","BANKBARODA.NS","Banking"),
    "ashok leyland":("Ashok Leyland","ASHOKLEY.NS","Auto"),
    "hindustan unilever":("Hindustan Unilever","HINDUNILVR.NS","FMCG"),
    "asian paints":("Asian Paints","ASIANPAINT.NS","Consumer"),
    "asianpaints":("Asian Paints","ASIANPAINT.NS","Consumer"),
    "hero motocorp":("Hero MotoCorp","HEROMOTOCO.NS","Auto"),
    "godrej consumer":("Godrej Consumer","GODREJCP.NS","FMCG"),
    "dr.reddy":("Dr Reddy's","DRREDDY.NS","Pharma"),
    "dr reddy":("Dr Reddy's","DRREDDY.NS","Pharma"),
    "sun pharma":("Sun Pharma","SUNPHARMA.NS","Pharma"),
    "sun_pharma":("Sun Pharma","SUNPHARMA.NS","Pharma"),
    "coal india":("Coal India","COALINDIA.NS","Energy"),
    "coal_india":("Coal India","COALINDIA.NS","Energy"),
    "power grid":("Power Grid","POWERGRID.NS","Energy"),
    "powergrid":("Power Grid","POWERGRID.NS","Energy"),
    "angel one":("Angel One","ANGELONE.NS","FinTech"),
    "oracle":("Oracle Financial","OFSS.NS","IT"),
    "vodafone idea":("Vodafone Idea","IDEA.NS","Telecom"),
    "vodafone":("Vodafone Idea","IDEA.NS","Telecom"),
    "bharti airtel":("Bharti Airtel","BHARTIARTL.NS","Telecom"),
    "airtel":("Bharti Airtel","BHARTIARTL.NS","Telecom"),
    "nalco":("NALCO","NATIONALUM.NS","Metals"),
    "cholamandalam":("Cholamandalam","CHOLAFIN.NS","FinServ"),
    "bharat petroleum":("BPCL","BPCL.NS","Energy"),
    "muthoot finance":("Muthoot Finance","MUTHOOTFIN.NS","FinServ"),
    "tech_mahindra":("Tech Mahindra","TECHM.NS","IT"),
    "hdfc":("HDFC Bank","HDFCBANK.NS","Banking"),
    "icici":("ICICI Bank","ICICIBANK.NS","Banking"),
    "kotak bank":("Kotak Mahindra Bank","KOTAKBANK.NS","Banking"),
    "kotak_bank":("Kotak Mahindra Bank","KOTAKBANK.NS","Banking"),
    "axis bank":("Axis Bank","AXISBANK.NS","Banking"),
    "axis_bank":("Axis Bank","AXISBANK.NS","Banking"),
    "federal bank":("Federal Bank","FEDERALBNK.NS","Banking"),
    "federal_bank":("Federal Bank","FEDERALBNK.NS","Banking"),
    "idfc":("IDFC First Bank","IDFCFIRSTB.NS","Banking"),
    "induslnd":("IndusInd Bank","INDUSINDBK.NS","Banking"),
    "indusind":("IndusInd Bank","INDUSINDBK.NS","Banking"),
    "reliance":("Reliance Industries","RELIANCE.NS","Energy"),
    "mahindra":("Mahindra & Mahindra","M&M.NS","Auto"),
    "aurobindo":("Aurobindo Pharma","AUROPHARMA.NS","Pharma"),
    "torrent":("Torrent Pharma","TORNTPHARM.NS","Pharma"),
    "persistent":("Persistent Systems","PERSISTENT.NS","IT"),
    "mphasis":("Mphasis","MPHASIS.NS","IT"),
    "coforge":("Coforge","COFORGE.NS","IT"),
    "britannia":("Britannia","BRITANNIA.NS","FMCG"),
    "dabur":("Dabur","DABUR.NS","FMCG"),
    "marico":("Marico","MARICO.NS","FMCG"),
    "colgate":("Colgate India","COLPAL.NS","FMCG"),
    "emami":("Emami","EMAMILTD.NS","FMCG"),
    "nestle":("Nestle India","NESTLEIND.NS","FMCG"),
    "cipla":("Cipla","CIPLA.NS","Pharma"),
    "divis":("Divi's Labs","DIVISLAB.NS","Pharma"),
    "lupin":("Lupin","LUPIN.NS","Pharma"),
    "alkem":("Alkem Labs","ALKEM.NS","Pharma"),
    "biocon":("Biocon","BIOCON.NS","Pharma"),
    "jsw steel":("JSW Steel","JSWSTEEL.NS","Metals"),
    "hindalco":("Hindalco","HINDALCO.NS","Metals"),
    "vendanta":("Vedanta","VEDL.NS","Metals"),
    "vedanta":("Vedanta","VEDL.NS","Metals"),
    "sail":("SAIL","SAIL.NS","Metals"),
    "nmdc":("NMDC","NMDC.NS","Metals"),
    "grasim":("Grasim","GRASIM.NS","Infra"),
    "graism":("Grasim","GRASIM.NS","Infra"),
    "ambuja":("Ambuja Cements","AMBUJACEM.NS","Infra"),
    "acc":("ACC","ACC.NS","Infra"),
    "shree_cement":("Shree Cement","SHREECEM.NS","Infra"),
    "siemen":("Siemens India","SIEMENS.NS","Infra"),
    "siemens":("Siemens India","SIEMENS.NS","Infra"),
    "cummins":("Cummins India","CUMMINSIND.NS","Infra"),
    "abb":("ABB India","ABB.NS","Infra"),
    "maruti suzuki":("Maruti Suzuki","MARUTI.NS","Auto"),
    "maruti":("Maruti Suzuki","MARUTI.NS","Auto"),
    "eicher":("Eicher Motors","EICHERMOT.NS","Auto"),
    "escorts":("Escorts Kubota","ESCORTS.NS","Auto"),
    "bosch":("Bosch India","BOSCHLTD.NS","Auto"),
    "tvs motors":("TVS Motor","TVSMOTORS.NS","Auto"),
    "tvs":("TVS Motor","TVSMOTORS.NS","Auto"),
    "titan":("Titan","TITAN.NS","Consumer"),
    "pidilite":("Pidilite","PIDILITIND.NS","Consumer"),
    "havells":("Havells","HAVELLS.NS","Consumer"),
    "paytm":("Paytm","PAYTM.NS","FinTech"),
    "cdsl":("CDSL","CDSL.NS","FinTech"),
    "wipro":("Wipro","WIPRO.NS","IT"),
    "tcs":("TCS","TCS.NS","IT"),
    "infosys":("Infosys","INFY.NS","IT"),
    "itc":("ITC","ITC.NS","FMCG"),
    "hcl":("HCL Technologies","HCLTECH.NS","IT"),
    "ntpc":("NTPC","NTPC.NS","Energy"),
    "ongc":("ONGC","ONGC.NS","Energy"),
    "ioc":("IOC","IOC.NS","Energy"),
    "sbi":("SBI","SBIN.NS","Banking"),
    "pnb":("PNB","PNB.NS","Banking"),
    "bse":("BSE Ltd","BSE.NS","FinTech"),
    "shriram":("Shriram Finance","SHRIRAMFIN.NS","FinServ"),
    "l&t":("Larsen & Toubro","LT.NS","Infra"),
    "l_t":("Larsen & Toubro","LT.NS","Infra"),
}

def identify(filename):
    fn = Path(filename).stem.lower()
    ym = re.search(r"(202[0-9])", fn)
    year = int(ym.group(1)) if ym else None
    fy = f"FY {year-1}-{str(year)[2:]}" if year else None
    clean = re.sub(r"^\d+[_ ]", "", fn)
    clean = re.sub(r"[_ ]?202[0-9](-\d+)?[_ ]?", " ", clean).strip()
    # exact
    if clean in COMPANY_MAP:
        n,t,s = COMPANY_MAP[clean]; return n,t,s,fy
    # longest key contained in filename
    best=None
    for k in COMPANY_MAP:
        if k in clean and (best is None or len(k)>len(best)):
            best=k
    if best:
        n,t,s = COMPANY_MAP[best]; return n,t,s,fy
    return None,None,None,fy

def pdftext(path):
    """Return layout-preserved text using poppler's pdftotext."""
    try:
        out = subprocess.run(["pdftotext","-layout",path,"-"],
                             capture_output=True, timeout=120)
        return out.stdout.decode("utf-8","ignore")
    except Exception as e:
        print(f"    pdftotext failed: {e}")
        return ""

def nums_on_line(line):
    """Return list of numeric tokens on a line, as floats."""
    toks = re.findall(r"[\d][\d,]*\.?\d*", line)
    vals=[]
    for t in toks:
        try: vals.append(float(t.replace(",","")))
        except: pass
    return vals

def first_num_after(text, label_patterns, lo=0, hi=1e12):
    """Find a line matching any label, return its first plausible number."""
    for pat in label_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line = text[m.start(): m.start()+400].split("\n")[0]
            for v in nums_on_line(line[len(pat):] if line.lower().startswith(pat.lower()) else line):
                if lo <= v <= hi:
                    return v
    return None

def extract(path):
    txt = pdftext(path)
    r = dict(scope1=None, scope12=None, energy_mgj=None, renew_mgj=None,
             renew_pct=None, wom_dir=None, wom_emp=None, controv=0, note="")
    if not txt:
        r["note"]="no text (image PDF?)"; return r

    sc1 = first_num_after(txt, [r"Total Scope 1 emissions"], 10, 5e7)
    sc2 = first_num_after(txt, [r"Total Scope 2 emissions"], 10, 1e8)
    if sc1 is not None: r["scope1"]=sc1
    if sc1 is not None and sc2 is not None: r["scope12"]=sc1+sc2

    te = first_num_after(txt, [r"Total energy consumption \(A\+B\+C\)",
                                r"Total energy consumed \(A\+B\+C\)"], 1000, 1e11)
    if te is not None: r["energy_mgj"]=round(te/1_000_000,4)

    re_ = first_num_after(txt, [r"Total energy consumed from renewable sources \(A\+B\+C\)",
                                 r"renewable sources \(A\+B\+C\)"], 100, 1e11)
    if re_ is not None: r["renew_mgj"]=round(re_/1_000_000,4)

    rp = first_num_after(txt, [r"Percentage of total energy from renewable"], 0, 100)
    if rp is not None: r["renew_pct"]=round(rp/100,4)
    elif r["renew_mgj"] and r["energy_mgj"]:
        r["renew_pct"]=round(r["renew_mgj"]/r["energy_mgj"],4)

    # women directors: look for "X women director" or a % near board diversity
    for m in re.finditer(r"(\d+\.?\d*)\s*%[^%\n]{0,40}(women|female)[^%\n]{0,20}(director|board)",
                         txt, re.IGNORECASE):
        try:
            v=float(m.group(1))
            if 0<v<=100: r["wom_dir"]=round(v/100,4); break
        except: pass

    # women employees %
    m = re.search(r"female employees[^%\n]{0,40}?(\d+\.?\d*)\s*%", txt, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d+\.?\d*)\s*%[^%\n]{0,20}(women|female)\s+(employee|workforce)",
                      txt, re.IGNORECASE)
    if m:
        try:
            v=float(m.group(1))
            if 0<v<=100: r["wom_emp"]=round(v/100,4)
        except: pass

    low=txt.lower()
    if any(k in low for k in ["penalty imposed","fine imposed","penalty paid","monetary penalty"]):
        if not any(k in low for k in ["no penalty","nil","not applicable","no fine","no monetary"]):
            r["controv"]=1
    return r

def main():
    pdfs = sorted(glob.glob(os.path.join(PDF_FOLDER,"*.pdf")))
    print(f"Found {len(pdfs)} PDFs in {PDF_FOLDER}\n")
    rows=[]; report=[]
    for p in pdfs:
        name,tick,sec,fy = identify(os.path.basename(p))
        if not name or name=="__SKIP__":
            report.append(f"SKIP  {os.path.basename(p)}  (unrecognised or not in sample)")
            continue
        if fy not in ("FY 2022-23","FY 2023-24"):
            continue  # only the two mandatory BRSR years
        print(f"Processing {name} {fy} ...")
        d = extract(p)
        filled = sum(1 for k in ("scope1","scope12","energy_mgj","renew_mgj",
                                 "renew_pct","wom_dir","wom_emp") if d[k] is not None)
        status = "OK" if filled>=6 else ("PARTIAL" if filled>=3 else "FAIL")
        report.append(f"{status:7} {name:24} {fy}  {filled}/8 fields  {d['note']}")
        rows.append(dict(company=name,sector=sec,ticker=tick,year=fy,
                         scope1_tco2e=d["scope1"], scope12_tco2e=d["scope12"],
                         total_energy_mgj=d["energy_mgj"], renewable_mgj=d["renew_mgj"],
                         renewable_pct=d["renew_pct"], women_dir_pct=d["wom_dir"],
                         women_emp_pct=d["wom_emp"], controversies=d["controv"]))

    # write CSV
    csv_path=os.path.join(OUT_FOLDER,"extraction_results.csv")
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()) if rows else [])
        if rows: w.writeheader(); w.writerows(rows)
    print(f"\nWrote {csv_path}  ({len(rows)} rows)")

    # write report
    rep_path=os.path.join(OUT_FOLDER,"extraction_report.txt")
    with open(rep_path,"w",encoding="utf-8") as f:
        ok=sum(1 for l in report if l.startswith("OK"))
        part=sum(1 for l in report if l.startswith("PARTIAL"))
        fail=sum(1 for l in report if l.startswith("FAIL"))
        f.write(f"GQE EXTRACTION REPORT\nOK={ok}  PARTIAL={part}  FAIL={fail}\n"+"="*60+"\n")
        f.write("\n".join(report))
    print(f"Wrote {rep_path}")
    print("\nSummary:", f"OK={ok}  PARTIAL={part}  FAIL={fail}")

    # optional: update the Excel tracker
    try:
        import openpyxl
        if os.path.exists(EXCEL_PATH) and rows:
            wb=openpyxl.load_workbook(EXCEL_PATH); ws=wb["OPS Data Tracker"]
            existing=set()
            last=5
            for row in ws.iter_rows(min_row=6):
                if row[0].value:
                    existing.add(f"{row[0].value}_{row[3].value}"); last=row[0].row
            added=0
            for rd in rows:
                key=f"{rd['company']}_{rd['year']}"
                if key in existing: continue
                r=last+1+added
                order=[rd['company'],rd['sector'],rd['ticker'],rd['year'],
                       rd['scope1_tco2e'],rd['scope12_tco2e'],rd['total_energy_mgj'],
                       rd['renewable_mgj'],rd['renewable_pct'],rd['women_dir_pct'],
                       rd['women_emp_pct'],rd['controversies']]
                for c,val in enumerate(order,1):
                    ws.cell(row=r,column=c).value = "" if val is None else val
                added+=1
            wb.save(EXCEL_PATH)
            print(f"Updated tracker: added {added} new rows to {EXCEL_PATH}")
    except Exception as e:
        print(f"(Excel update skipped: {e})  — the CSV is still complete.")

if __name__=="__main__":
    main()
