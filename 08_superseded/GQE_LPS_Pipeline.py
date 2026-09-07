
# ===== CODE CELL 1 =====
!pip install -q pdfplumber transformers torch pysentiment2 openpyxl pandas
print("Libraries installed. If prompted to restart, do so and re-run this cell.")

# ===== CODE CELL 2 =====
from google.colab import drive
drive.mount('/content/drive')

# ---- CONFIGURE THESE IF NEEDED ----
# Your GQE project folder ID (from the Drive URL):
DRIVE_FOLDER_ID = "1i4XZDktzWR4H1R9ncPlOFTI22fCBC5--"
# Where your PDFs live. If you synced the folder to "My Drive", set the path:
PDF_FOLDER = "/content/drive/MyDrive/GQE"   # <-- adjust if your folder name differs
OUTPUT_FOLDER = "/content/drive/MyDrive/GQE"  # where LPS_scores.csv will be saved

import os
if not os.path.isdir(PDF_FOLDER):
    print("WARNING: PDF_FOLDER not found. Listing My Drive so you can find the right name:")
    for name in sorted(os.listdir("/content/drive/MyDrive"))[:50]:
        print("  ", name)
else:
    pdfs = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdfs)} PDF files in {PDF_FOLDER}")

# ===== CODE CELL 3 =====
import pdfplumber, re, difflib, json, os

# The 100 companies (canonical name -> ticker)
COMPANIES = {
"Reliance Industries": "RELIANCE",
"TCS": "TCS",
"Infosys": "INFY",
"HDFC Bank": "HDFCBANK",
"Wipro": "WIPRO",
"ITC": "ITC",
"HCL Technologies": "HCLTECH",
"ICICI Bank": "ICICIBANK",
"Asian Paints": "ASIANPAINT",
"Larsen & Toubro": "LT",
"Mahindra & Mahindra": "M&M",
"Hindustan Unilever": "HINDUNILVR",
"Bajaj Finance": "BAJFINANCE",
"Nestle India": "NESTLEIND",
"Bharti Airtel": "BHARTIARTL",
"Kotak Mahindra Bank": "KOTAKBANK",
"Axis Bank": "AXISBANK",
"IDFC First Bank": "IDFCFIRSTB",
"Federal Bank": "FEDERALBNK",
"Bank of Baroda": "BANKBARODA",
"IndusInd Bank": "INDUSINDBK",
"SBI": "SBIN",
"Vedanta Limited": "VEDL",
"Hindalco Industries": "HINDALCO",
"UltraTech Cement": "ULTRACEMCO",
"Shree Cement": "SHREECEM",
"Grasim Industries": "GRASIM",
"BPCL": "BPCL",
"Indian Oil Corporation": "IOC",
"ABB India": "ABB",
"ACC": "ACC",
"Adani Enterprises": "ADANIENT",
"Adani Green": "ADANIGREEN",
"Adani Ports": "ADANIPORTS",
"Alkem Labs": "ALKEM",
"Ambuja Cements": "AMBUJACEM",
"Angel One": "ANGELONE",
"Apollo Hospitals": "APOLLOHOSP",
"Ashok Leyland": "ASHOKLEY",
"Aurobindo Pharma": "AUROPHARMA",
"BSE Ltd": "BSE",
"Bajaj Auto": "BAJAJ-AUTO",
"Bajaj Finserv": "BAJAJFINSV",
"Biocon": "BIOCON",
"Bosch India": "BOSCHLTD",
"Britannia": "BRITANNIA",
"CDSL": "CDSL",
"Cholamandalam": "CHOLAFIN",
"Cipla": "CIPLA",
"Coal India": "COALINDIA",
"Coforge": "COFORGE",
"Colgate India": "COLPAL",
"Cummins India": "CUMMINSIND",
"Dabur": "DABUR",
"Divi's Labs": "DIVISLAB",
"Dr Reddy's": "DRREDDY",
"Eicher Motors": "EICHERMOT",
"Emami": "EMAMILTD",
"Escorts Kubota": "ESCORTS",
"Godrej Consumer": "GODREJCP",
"HDFC Life": "HDFCLIFE",
"Havells": "HAVELLS",
"Hero MotoCorp": "HEROMOTOCO",
"ICICI Lombard": "ICICIGI",
"Indus Towers": "INDUSTOWER",
"JSW Steel": "JSWSTEEL",
"Jindal Steel": "JINDALSTEL",
"LIC": "LICI",
"LTIMindtree": "LTIM",
"LTTS": "LTTS",
"Lupin": "LUPIN",
"Marico": "MARICO",
"Maruti Suzuki": "MARUTI",
"Mphasis": "MPHASIS",
"Muthoot Finance": "MUTHOOTFIN",
"NALCO": "NATIONALUM",
"NMDC": "NMDC",
"NTPC": "NTPC",
"ONGC": "ONGC",
"Oracle Financial": "OFSS",
"PNB": "PNB",
"Paytm": "PAYTM",
"Persistent Systems": "PERSISTENT",
"Pidilite": "PIDILITIND",
"PolicyBazaar": "POLICYBZR",
"Power Grid": "POWERGRID",
"SAIL": "SAIL",
"SBI Life": "SBILIFE",
"Shriram Finance": "SHRIRAMFIN",
"Siemens India": "SIEMENS",
"Sun Pharma": "SUNPHARMA",
"TVS Motor": "TVSMOTORS",
"Tata Consumer": "TATACONSUM",
"Tata Power": "TATAPOWER",
"Tata Steel": "TATASTEEL",
"Tech Mahindra": "TECHM",
"Titan": "TITAN",
"Torrent Pharma": "TORNTPHARM",
"Vodafone Idea": "IDEA",
"Tata Motors": "TATAMOTORS"
}

# Known filename aliases (misspellings / short forms in your Drive)
ALIASES = {
    'vendanta':'Vedanta','vedanta':'Vedanta','siemen':'Siemens India',
    'ltimindtree':'LTIMindtree','ltts':'LTTS','m&m':'Mahindra & Mahindra',
    'mahindra':'Mahindra & Mahindra','lt':'Larsen & Toubro','l&t':'Larsen & Toubro',
    'bajaj auto':'Bajaj Auto','bajaj finance':'Bajaj Finance','bajaj finserv':'Bajaj Finserv',
    'hdfc':'HDFC Bank','hdfc bank':'HDFC Bank','hdfc life':'HDFC Life',
    'icici':'ICICI Bank','icici bank':'ICICI Bank','icici lombard':'ICICI Lombard',
    'tata motors':'Tata Motors','tata steel':'Tata Steel','tata power':'Tata Power',
    'tata consumer':'Tata Consumer','sbi':'SBI','sbi life':'SBI Life',
    'ioc':'Indian Oil Corporation','indian oil':'Indian Oil Corporation',
    'ongc':'ONGC','bpcl':'BPCL','sail':'SAIL','nalco':'NALCO','nmdc':'NMDC',
    'ultratech':'UltraTech Cement','ultratech cement':'UltraTech Cement',
    'shree cement':'Shree Cement','grasim':'Grasim','graism':'Grasim','hindalco':'Hindalco','vedl':'Vedanta',
    'bharat petroleum':'BPCL','bharatpetroleum':'BPCL',
}

canon_names = list(COMPANIES.keys())
canon_lower = {c.lower():c for c in canon_names}

def match_company(fname):
    stem = re.sub(r'\.pdf$','',fname, flags=re.I).strip().lower()
    # strip trailing year
    m = re.search(r'(19|20)\d{2}', stem)
    year = m.group(0) if m else None
    name_part = re.sub(r'(19|20)\d{2}','',stem).strip(' -_')
    # alias?
    if name_part in ALIASES: return ALIASES[name_part], year
    if name_part in canon_lower: return canon_lower[name_part], year
    # fuzzy
    hit = difflib.get_close_matches(name_part, [c.lower() for c in canon_names], n=1, cutoff=0.6)
    if hit: return canon_lower[hit[0]], year
    # token overlap fallback
    toks = set(name_part.split())
    best=None; bestscore=0
    for c in canon_names:
        ov = len(toks & set(c.lower().split()))
        if ov>bestscore: bestscore=ov; best=c
    return (best, year) if bestscore>0 else (None, year)

def year_to_fy(y):
    if y is None: return None
    y=int(y)
    return f"FY{y-1}-{str(y)[2:]}"  # 2023 -> FY2022-23-ish label

def extract_brsr_section(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        texts=[(p.extract_text() or "") for p in pdf.pages]
    n=len(texts)
    markers=[f'principle {i}' for i in range(1,10)]+['section a','section b','section c',
             'essential indicators','business responsibility','sustainability report']
    insec=[any(m in t.lower() for m in markers) for t in texts]
    best=(0,0); i=0
    while i<n:
        if insec[i]:
            j=i; gap=0
            while j<n and (insec[j] or gap<3):
                gap = 0 if insec[j] else gap+1
                j+=1
            if j-i>best[1]: best=(i,j-i)
            i=j
        else: i+=1
    s,ln=best
    return "\n".join(texts[s:s+ln]), (s+1, s+ln, ln, n)

# Run extraction over all PDFs (FY2022-23 and FY2023-24 only)
os.makedirs('/content/corpus', exist_ok=True)
corpus=[]; skipped=[]
pdfs=sorted([f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')])
for k,fname in enumerate(pdfs,1):
    company,year = match_company(fname)
    if year not in ('2023','2024'):   # keep only the two study years
        continue
    if company is None:
        skipped.append((fname,'no company match')); continue
    fy = 'FY 2022-23' if year=='2023' else 'FY 2023-24'
    try:
        text,(sp,ep,pages,total) = extract_brsr_section(os.path.join(PDF_FOLDER,fname))
        wc=len(text.split())
        if wc < 500:
            skipped.append((fname,f'BRSR too short ({wc}w) — pages {sp}-{ep}')); 
        key=f"{company}__{fy}".replace(' ','_').replace('/','_')
        open(f'/content/corpus/{key}.txt','w').write(text)
        corpus.append(dict(company=company,fy=fy,file=fname,words=wc,brsr_pages=pages,total_pages=total))
        print(f"[{k}/{len(pdfs)}] {company} {fy}: BRSR p{sp}-{ep} ({pages}p, {wc:,}w)")
    except Exception as e:
        skipped.append((fname,str(e)[:80]))

import pandas as pd
manifest=pd.DataFrame(corpus)
manifest.to_csv('/content/corpus_manifest.csv',index=False)
print(f"\nExtracted {len(corpus)} company-years. Skipped {len(skipped)}.")
if skipped:
    print("Skipped files (check these):")
    for f,why in skipped: print(f"   {f}: {why}")

# ===== CODE CELL 4 =====
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print("Device:", device)

# --- FinBERT (primary): labels = positive / negative / neutral ---
finbert_tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
finbert = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").to(device).eval()
FINBERT_LABELS = ['positive','negative','neutral']  # ProsusAI/finbert order

# --- ClimateBERT (comparator): labels = risk / neutral / opportunity ---
try:
    cb_name = "climatebert/distilroberta-base-climate-sentiment"
    climatebert_tok = AutoTokenizer.from_pretrained(cb_name)
    climatebert = AutoModelForSequenceClassification.from_pretrained(cb_name).to(device).eval()
    CB_LABELS = list(climatebert.config.id2label.values())
    print("ClimateBERT labels:", CB_LABELS)
    HAVE_CB = True
except Exception as e:
    print("ClimateBERT unavailable, will skip:", str(e)[:100])
    HAVE_CB = False

print("Models ready.")

# ===== CODE CELL 5 =====
import glob, os
import pandas as pd

def chunk_words(text, size=300):
    w=text.split()
    return [" ".join(w[i:i+size]) for i in range(0,len(w),size)] or [""]

@torch.no_grad()
def score_model(text, tok, model, labels, pos_label, neg_label):
    chunks=chunk_words(text)
    diffs=[]
    for i in range(0,len(chunks),16):   # batch
        batch=chunks[i:i+16]
        enc=tok(batch, return_tensors='pt', truncation=True, max_length=512, padding=True).to(device)
        probs=torch.softmax(model(**enc).logits, dim=-1).cpu().numpy()
        pi=labels.index(pos_label); ni=labels.index(neg_label)
        diffs.extend((probs[:,pi]-probs[:,ni]).tolist())
    return float(np.mean(diffs)) if diffs else 0.0

rows=[]
files=sorted(glob.glob('/content/corpus/*.txt'))
for k,path in enumerate(files,1):
    key=os.path.basename(path)[:-4]
    company,fy = key.rsplit('__',1)
    company=company.replace('_',' '); fy=fy.replace('_',' ')
    text=open(path).read()
    lps_fin = score_model(text, finbert_tok, finbert, FINBERT_LABELS, 'positive','negative')
    lps_cb = None
    if HAVE_CB:
        # map opportunity->positive, risk->negative
        pos = 'opportunity' if 'opportunity' in CB_LABELS else CB_LABELS[-1]
        neg = 'risk' if 'risk' in CB_LABELS else CB_LABELS[0]
        lps_cb = score_model(text, climatebert_tok, climatebert, CB_LABELS, pos, neg)
    rows.append(dict(company=company, year=fy, LPS_finbert=round(lps_fin,4),
                     LPS_climatebert=round(lps_cb,4) if lps_cb is not None else None))
    print(f"[{k}/{len(files)}] {company} {fy}: FinBERT={lps_fin:+.3f}" + (f"  ClimateBERT={lps_cb:+.3f}" if lps_cb is not None else ""))

lps_df=pd.DataFrame(rows)
print("\nFinBERT + ClimateBERT scoring complete.")

# ===== CODE CELL 6 =====
import pysentiment2 as ps
lm = ps.LM()

lm_rows=[]
for path in sorted(glob.glob('/content/corpus/*.txt')):
    key=os.path.basename(path)[:-4]
    company,fy=key.rsplit('__',1); company=company.replace('_',' '); fy=fy.replace('_',' ')
    text=open(path).read()
    tokens=lm.tokenize(text); sc=lm.get_score(tokens)
    pos,neg=sc['Positive'],sc['Negative']
    lps_lm=(pos-neg)/(pos+neg) if (pos+neg)>0 else 0.0
    lm_rows.append(dict(company=company, year=fy, LPS_lm=round(lps_lm,4),
                        lm_pos=pos, lm_neg=neg))
lm_df=pd.DataFrame(lm_rows)
print("Loughran-McDonald baseline complete.")

# ===== CODE CELL 7 =====
final = lps_df.merge(lm_df, on=['company','year'], how='outer')
final = final.sort_values(['company','year']).reset_index(drop=True)

out_path = os.path.join(OUTPUT_FOLDER, 'LPS_scores.csv')
final.to_csv(out_path, index=False)
print(f"Saved {len(final)} rows to {out_path}\n")
print(final.to_string(index=False))
