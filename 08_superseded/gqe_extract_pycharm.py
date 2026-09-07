"""
GQE BRSR EXTRACTOR  —  PyCharm edition
======================================
Reads every BRSR/annual-report PDF in one folder and extracts 8 ESG fields
into a CSV you can paste into your tracker.

KEY DIFFERENCE FROM THE EARLIER SCRIPT
--------------------------------------
This version does NOT need the external `pdftotext` program. It uses the
pure-Python library `pdfplumber`, so `pip install` alone is enough — nothing
to add to your system PATH. That makes it far easier to run in PyCharm.

It also writes, next to each number, the RAW TABLE LINE it came from, in a
second file `extraction_evidence.txt`. That way you can eyeball any suspicious
value against the exact text it was read from, instead of trusting it blindly.

=======================  HOW TO RUN IN PYCHARM  =======================
1.  File > New Project  (or open your dissertation folder as a project).
2.  Put THIS file and all your PDFs somewhere you can find them.
3.  Open PyCharm's Terminal tab (bottom of the window) and run:
        pip install pdfplumber openpyxl pandas
4.  Edit the three paths in the CONFIG block below.
5.  Right-click the file in PyCharm > Run 'gqe_extract_pycharm'.
6.  When it finishes, open:
        extraction_results.csv    <- the numbers
        extraction_evidence.txt   <- the source line for every number
        extraction_report.txt     <- which companies came out OK / PARTIAL / FAIL
=======================================================================

IMPORTANT: treat the CSV as a DRAFT. Open extraction_evidence.txt and sanity-
check anything that looks off (e.g. a Scope-1 in the millions for a bank).
Send me the CSV afterwards and I'll clean the gaps and fix wrong rows.
"""

import os, re, glob, csv
from pathlib import Path

# ============================  CONFIG  ================================
PDF_FOLDER = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
OUT_FOLDER = r"C:\Users\ASUS\Desktop\me\Dissertation"
EXCEL_PATH = r"C:\Users\ASUS\Desktop\me\Dissertation\GQE_OPS_Data_Tracker.xlsx"
ONLY_YEARS = ("FY 2022-23", "FY 2023-24")   # the two mandatory BRSR years
# =====================================================================

try:
    import pdfplumber
except ImportError:
    raise SystemExit("Please run:  pip install pdfplumber openpyxl pandas")

COMPANY_MAP = {
    "tech mahindra":("Tech Mahindra","TECHM.NS","IT"),
    "hdfc life":("HDFC Life","HDFCLIFE.NS","Insurance"),
    "sbi life":("SBI Life","SBILIFE.NS","Insurance"),
    "icici lombard":("ICICI Lombard","ICICIGI.NS","Insurance"),
    "lic life insurance":("LIC","LICI.NS","Insurance"),
    "bajaj finserv":("Bajaj Finserv","BAJAJFINSV.NS","FinServ"),
    "bajaj finance":("Bajaj Finance","BAJFINANCE.NS","FinServ"),
    "bajaj auto":("Bajaj Auto","BAJAJ-AUTO.NS","Auto"),
    "apl apollo":("APL Apollo","APLAPOLLO.NS","Metals"),
    "apollo hospital":("Apollo Hospitals","APOLLOHOSP.NS","Pharma"),
    "apollo tyre":("__SKIP__","",""),
    "tata steel":("Tata Steel","TATASTEEL.NS","Metals"),
    "tata power":("Tata Power","TATAPOWER.NS","Energy"),
    "tata consumer":("Tata Consumer","TATACONSUM.NS","FMCG"),
    "tata consumers":("Tata Consumer","TATACONSUM.NS","FMCG"),
    "adani green":("Adani Green","ADANIGREEN.NS","Energy"),
    "adani ports":("Adani Ports","ADANIPORTS.NS","Infra"),
    "adani enterprise":("Adani Enterprises","ADANIENT.NS","Energy"),
    "ultratech cement":("UltraTech Cement","ULTRACEMCO.NS","Infra"),
    "ultratech":("UltraTech Cement","ULTRACEMCO.NS","Infra"),
    "l&t tech":("LTTS","LTTS.NS","Infra"),
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
    "coal india":("Coal India","COALINDIA.NS","Energy"),
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
    "hdfc":("HDFC Bank","HDFCBANK.NS","Banking"),
    "icici":("ICICI Bank","ICICIBANK.NS","Banking"),
    "kotak bank":("Kotak Mahindra Bank","KOTAKBANK.NS","Banking"),
    "axis bank":("Axis Bank","AXISBANK.NS","Banking"),
    "federal bank":("Federal Bank","FEDERALBNK.NS","Banking"),
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
    "siemen":("Siemens India","SIEMENS.NS","Infra"),
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
}

def identify(filename):
    fn = Path(filename).stem.lower()
    ym = re.search(r"(202[0-9])", fn)
    year = int(ym.group(1)) if ym else None
    fy = f"FY {year-1}-{str(year)[2:]}" if year else None
    clean = re.sub(r"^\d+[_ ]", "", fn)
    clean = re.sub(r"[_ ]?202[0-9](-\d+)?[_ ]?", " ", clean).strip()
    if clean in COMPANY_MAP:
        n,t,s = COMPANY_MAP[clean]; return n,t,s,fy
    best=None
    for k in COMPANY_MAP:
        if k in clean and (best is None or len(k)>len(best)):
            best=k
    if best:
        n,t,s = COMPANY_MAP[best]; return n,t,s,fy
    return None,None,None,fy

def page_text(page):
    # layout=True keeps table columns aligned, like pdftotext -layout
    try:
        return page.extract_text(layout=True) or ""
    except Exception:
        return page.extract_text() or ""

def nums(line):
    out=[]
    for t in re.findall(r"[\d][\d,]*\.?\d*", line):
        try: out.append(float(t.replace(",","")))
        except: pass
    return out

def find_line(fulltext, patterns):
    for pat in patterns:
        m = re.search(pat, fulltext, re.IGNORECASE)
        if m:
            line = fulltext[m.start():].split("\n",1)[0]
            return line
    return None

def extract(path, evidence):
    fields = dict(scope1=None,scope12=None,energy_mgj=None,renew_mgj=None,
                  renew_pct=None,wom_dir=None,wom_emp=None,controv=0)
    text=""
    try:
        with pdfplumber.open(path) as pdf:
            # only scan pages that mention BRSR keywords (keeps it fast)
            for pg in pdf.pages:
                t = page_text(pg)
                tl=t.lower()
                if any(k in tl for k in ("scope 1","scope 2","energy consumption",
                                         "renewable sources","women director",
                                         "female employee","penalty")):
                    text += "\n"+t
    except Exception as e:
        evidence.append(f"    !! could not open: {e}")
        return fields

    def grab(label_pats, lo, hi, scale=None, key=None):
        line = find_line(text, label_pats)
        if not line: return None
        for v in nums(line):
            if lo<=v<=hi:
                evidence.append(f"    {key}: {v}   <-- \"{line.strip()[:90]}\"")
                return v/scale if scale else v
        return None

    s1 = grab([r"Total Scope 1 emissions"], 10, 5e7, key="scope1")
    s2 = grab([r"Total Scope 2 emissions"], 10, 1e8, key="scope2")
    if s1 is not None: fields["scope1"]=s1
    if s1 is not None and s2 is not None: fields["scope12"]=s1+s2

    e = grab([r"Total energy consumption \(A\+B\+C\)",
              r"Total energy consumed \(A\+B\+C\)"], 1000, 1e11, scale=1_000_000, key="energy_MGJ")
    if e is not None: fields["energy_mgj"]=round(e,4)

    rn = grab([r"renewable sources \(A\+B\+C\)"], 100, 1e11, scale=1_000_000, key="renew_MGJ")
    if rn is not None: fields["renew_mgj"]=round(rn,4)

    rp = grab([r"Percentage of total energy from renewable"], 0, 100, key="renew_pct")
    if rp is not None: fields["renew_pct"]=round(rp/100,4)
    elif fields["renew_mgj"] and fields["energy_mgj"]:
        fields["renew_pct"]=round(fields["renew_mgj"]/fields["energy_mgj"],4)

    m = re.search(r"(\d+\.?\d*)\s*%[^%\n]{0,40}(women|female)[^%\n]{0,20}(director|board)", text, re.I)
    if m:
        v=float(m.group(1))
        if 0<v<=100:
            fields["wom_dir"]=round(v/100,4)
            evidence.append(f"    wom_dir: {v}%   <-- \"{m.group(0)[:80]}\"")

    m = re.search(r"female employees[^%\n]{0,40}?(\d+\.?\d*)\s*%", text, re.I) \
        or re.search(r"(\d+\.?\d*)\s*%[^%\n]{0,20}(women|female)\s+(employee|workforce)", text, re.I)
    if m:
        v=float(m.group(1))
        if 0<v<=100:
            fields["wom_emp"]=round(v/100,4)
            evidence.append(f"    wom_emp: {v}%   <-- \"{m.group(0)[:80]}\"")

    low=text.lower()
    if any(k in low for k in ("penalty imposed","fine imposed","penalty paid","monetary penalty")) \
       and not any(k in low for k in ("no penalty","nil","not applicable","no fine","no monetary")):
        fields["controv"]=1
    return fields

def main():
    # search the folder AND any subfolders for .pdf files
    pdfs = sorted(glob.glob(os.path.join(PDF_FOLDER,"**","*.pdf"), recursive=True))
    print(f"Found {len(pdfs)} PDFs in {PDF_FOLDER}\n")
    if not pdfs:
        print("No PDFs found. Check that PDF_FOLDER points at the folder that")
        print("actually contains your .pdf files. Current setting:")
        print("   ", PDF_FOLDER)
        return
    rows=[]; report=[]; evidence_all=[]
    for p in pdfs:
        name,tick,sec,fy = identify(os.path.basename(p))
        if not name or name=="__SKIP__":
            report.append(f"SKIP    {os.path.basename(p)}"); continue
        if fy not in ONLY_YEARS:
            continue
        print(f"  {name} {fy} ...")
        ev=[f"{name} {fy}  ({os.path.basename(p)})"]
        d = extract(p, ev)
        evidence_all += ev + [""]
        filled=sum(1 for k in ("scope1","scope12","energy_mgj","renew_mgj",
                               "renew_pct","wom_dir","wom_emp") if d[k] is not None)
        tag="OK" if filled>=6 else ("PARTIAL" if filled>=3 else "FAIL")
        report.append(f"{tag:7} {name:24} {fy}  {filled}/8")
        rows.append(dict(company=name,sector=sec,ticker=tick,year=fy,
                         scope1_tco2e=d["scope1"],scope12_tco2e=d["scope12"],
                         total_energy_mgj=d["energy_mgj"],renewable_mgj=d["renew_mgj"],
                         renewable_pct=d["renew_pct"],women_dir_pct=d["wom_dir"],
                         women_emp_pct=d["wom_emp"],controversies=d["controv"]))

    if rows:
        with open(os.path.join(OUT_FOLDER,"extraction_results.csv"),"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT_FOLDER,"extraction_evidence.txt"),"w",encoding="utf-8") as f:
        f.write("\n".join(evidence_all))
    ok=sum(l.startswith("OK") for l in report)
    pa=sum(l.startswith("PARTIAL") for l in report)
    fa=sum(l.startswith("FAIL") for l in report)
    with open(os.path.join(OUT_FOLDER,"extraction_report.txt"),"w",encoding="utf-8") as f:
        f.write(f"OK={ok} PARTIAL={pa} FAIL={fa}\n"+"="*50+"\n"+"\n".join(report))

    print(f"\nDONE.  OK={ok}  PARTIAL={pa}  FAIL={fa}")
    print("Files written to:", OUT_FOLDER)
    print("  extraction_results.csv   (numbers)")
    print("  extraction_evidence.txt  (source line for every number - CHECK THIS)")
    print("  extraction_report.txt    (per-company status)")

if __name__=="__main__":
    main()
