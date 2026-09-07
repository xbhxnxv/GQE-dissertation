"""
BRSR Data Extractor for GQE Dissertation
=========================================
Run this in PyCharm. Point PDF_FOLDER at your folder of annual reports.
It will extract all 5 ESG metrics and update your Excel tracker automatically.

SETUP:
    pip install pdfplumber openpyxl pandas

FOLDER STRUCTURE EXPECTED:
    Your PDFs should be named like:
    tcs_2023.pdf, tcs_2024.pdf, infosys_2023.pdf etc.
    OR any name containing the company keyword and year.

USAGE:
    1. Set PDF_FOLDER to where your PDFs are saved
    2. Set EXCEL_PATH to your GQE_OPS_Data_Tracker.xlsx location
    3. Run the script
    4. Results saved to extraction_results.csv and the Excel tracker
"""

import pdfplumber
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import os
import re
import glob
import json
from pathlib import Path

# ─── CONFIGURE THESE ──────────────────────────────────────────────────────────
PDF_FOLDER  = r"C:\Users\ASUS\Desktop\me\Dissertation\pdfs"   # folder with all your PDFs
EXCEL_PATH  = r"C:\Users\ASUS\Desktop\me\Dissertation\GQE_OPS_Data_Tracker.xlsx"
OUTPUT_CSV  = r"C:\Users\ASUS\Desktop\me\Dissertation\extraction_results.csv"
# ─────────────────────────────────────────────────────────────────────────────

# Company name → ticker mapping
COMPANY_MAP = {
    # ══ ORDER MATTERS: specific keys must come before shorter/general ones ══

    # ── Multi-word / conflict-prone keys FIRST ────────────────────────────
    'tech_mahindra':   ('Tech Mahindra',       'TECHM.NS',      'IT'),
    'techmahindra':    ('Tech Mahindra',       'TECHM.NS',      'IT'),
    'hdfc_life':       ('HDFC Life',           'HDFCLIFE.NS',   'Insurance'),
    'hdfclife':        ('HDFC Life',           'HDFCLIFE.NS',   'Insurance'),
    'sbi_life':        ('SBI Life',            'SBILIFE.NS',    'Insurance'),
    'sbilife':         ('SBI Life',            'SBILIFE.NS',    'Insurance'),
    'icici_lombard':   ('ICICI Lombard',       'ICICIGI.NS',    'Insurance'),
    'icicilombard':    ('ICICI Lombard',       'ICICIGI.NS',    'Insurance'),
    'lombard':         ('ICICI Lombard',       'ICICIGI.NS',    'Insurance'),
    'bajaj_finserv':   ('Bajaj Finserv',       'BAJAJFINSV.NS', 'FinServ'),
    'bajajfinserv':    ('Bajaj Finserv',       'BAJAJFINSV.NS', 'FinServ'),
    'bajaj_finance':   ('Bajaj Finance',       'BAJFINANCE.NS', 'FinServ'),
    'bajajfinance':    ('Bajaj Finance',       'BAJFINANCE.NS', 'FinServ'),
    'bajaj_auto':      ('Bajaj Auto',          'BAJAJ-AUTO.NS', 'Auto'),
    'bajajauto':       ('Bajaj Auto',          'BAJAJ-AUTO.NS', 'Auto'),
    'apl_apollo':      ('APL Apollo',          'APLAPOLLO.NS',  'Metals'),
    'aplapollo':       ('APL Apollo',          'APLAPOLLO.NS',  'Metals'),
    'tata_steel':      ('Tata Steel',          'TATASTEEL.NS',  'Metals'),
    'tatasteel':       ('Tata Steel',          'TATASTEEL.NS',  'Metals'),
    'tata_power':      ('Tata Power',          'TATAPOWER.NS',  'Energy'),
    'tatapower':       ('Tata Power',          'TATAPOWER.NS',  'Energy'),
    'tata_consumer':   ('Tata Consumer',       'TATACONSUM.NS', 'FMCG'),
    'tataconsumer':    ('Tata Consumer',       'TATACONSUM.NS', 'FMCG'),
    'adani_green':     ('Adani Green',         'ADANIGREEN.NS', 'Energy'),
    'adanigreen':      ('Adani Green',         'ADANIGREEN.NS', 'Energy'),
    'adani_ports':     ('Adani Ports',         'ADANIPORTS.NS', 'Infra'),
    'adaniports':      ('Adani Ports',         'ADANIPORTS.NS', 'Infra'),
    'adani_ent':       ('Adani Enterprises',   'ADANIENT.NS',   'Energy'),
    'adanient':        ('Adani Enterprises',   'ADANIENT.NS',   'Energy'),
    'adani_enterprises':('Adani Enterprises',  'ADANIENT.NS',   'Energy'),
    'ultratech':       ('UltraTech Cement',    'ULTRACEMCO.NS', 'Infra'),
    'ltts':            ('LTTS',                'LTTS.NS',       'Infra'),
    'l_t_technology':  ('LTTS',                'LTTS.NS',       'Infra'),
    'ltimindtree':     ('LTIMindtree',         'LTIM.NS',       'IT'),
    'ltim':            ('LTIMindtree',         'LTIM.NS',       'IT'),
    'mindtree':        ('LTIMindtree',         'LTIM.NS',       'IT'),
    'indus_tower':     ('Indus Towers',        'INDUSTOWER.NS', 'Telecom'),
    'industower':      ('Indus Towers',        'INDUSTOWER.NS', 'Telecom'),
    'indus_towers':    ('Indus Towers',        'INDUSTOWER.NS', 'Telecom'),
    'policybazaar':    ('PolicyBazaar',        'POLICYBZR.NS',  'FinTech'),
    'policybzr':       ('PolicyBazaar',        'POLICYBZR.NS',  'FinTech'),
    'pb_fintech':      ('PolicyBazaar',        'POLICYBZR.NS',  'FinTech'),
    'biocon':          ('Biocon',              'BIOCON.NS',     'Pharma'),
    'shree_cement':    ('Shree Cement',        'SHREECEM.NS',   'Infra'),
    'shreecement':     ('Shree Cement',        'SHREECEM.NS',   'Infra'),
    'jindal_steel':    ('Jindal Steel',        'JINDALSTEL.NS', 'Metals'),
    'jindalsteel':     ('Jindal Steel',        'JINDALSTEL.NS', 'Metals'),
    'jindal':          ('Jindal Steel',        'JINDALSTEL.NS', 'Metals'),
    'bank_of_baroda':  ('Bank of Baroda',      'BANKBARODA.NS', 'Banking'),
    'bankofbaroda':    ('Bank of Baroda',      'BANKBARODA.NS', 'Banking'),
    'baroda':          ('Bank of Baroda',      'BANKBARODA.NS', 'Banking'),
    'bob':             ('Bank of Baroda',      'BANKBARODA.NS', 'Banking'),
    'ashok_leyland':   ('Ashok Leyland',       'ASHOKLEY.NS',   'Auto'),
    'ashokleyland':    ('Ashok Leyland',       'ASHOKLEY.NS',   'Auto'),
    'ashokley':        ('Ashok Leyland',       'ASHOKLEY.NS',   'Auto'),
    'hindustan_unilever':('Hindustan Unilever','HINDUNILVR.NS', 'FMCG'),
    'unilever':        ('Hindustan Unilever',  'HINDUNILVR.NS', 'FMCG'),
    'hul':             ('Hindustan Unilever',  'HINDUNILVR.NS', 'FMCG'),
    'asian_paints':    ('Asian Paints',        'ASIANPAINT.NS', 'Consumer'),
    'asianpaints':     ('Asian Paints',        'ASIANPAINT.NS', 'Consumer'),
    'asianpaint':      ('Asian Paints',        'ASIANPAINT.NS', 'Consumer'),
    'hero_motocorp':   ('Hero MotoCorp',       'HEROMOTOCO.NS', 'Auto'),
    'heromotocorp':    ('Hero MotoCorp',       'HEROMOTOCO.NS', 'Auto'),
    'hero':            ('Hero MotoCorp',       'HEROMOTOCO.NS', 'Auto'),
    'godrej_consumer': ('Godrej Consumer',     'GODREJCP.NS',   'FMCG'),
    'godrej':          ('Godrej Consumer',     'GODREJCP.NS',   'FMCG'),
    'dr_reddy':        ("Dr Reddy's",          'DRREDDY.NS',    'Pharma'),
    'drreddy':         ("Dr Reddy's",          'DRREDDY.NS',    'Pharma'),
    'sun_pharma':      ('Sun Pharma',          'SUNPHARMA.NS',  'Pharma'),
    'sunpharma':       ('Sun Pharma',          'SUNPHARMA.NS',  'Pharma'),
    'coal_india':      ('Coal India',          'COALINDIA.NS',  'Energy'),
    'coalindia':       ('Coal India',          'COALINDIA.NS',  'Energy'),
    'power_grid':      ('Power Grid',          'POWERGRID.NS',  'Energy'),
    'powergrid':       ('Power Grid',          'POWERGRID.NS',  'Energy'),
    'angel_one':       ('Angel One',           'ANGELONE.NS',   'FinTech'),
    'angelone':        ('Angel One',           'ANGELONE.NS',   'FinTech'),
    'oracle_financial':('Oracle Financial',    'OFSS.NS',       'IT'),
    'oracle':          ('Oracle Financial',    'OFSS.NS',       'IT'),
    'ofss':            ('Oracle Financial',    'OFSS.NS',       'IT'),
    'vodafone_idea':   ('Vodafone Idea',       'IDEA.NS',       'Telecom'),
    'vodafone':        ('Vodafone Idea',       'IDEA.NS',       'Telecom'),
    'bharti_airtel':   ('Bharti Airtel',       'BHARTIARTL.NS', 'Telecom'),
    'airtel':          ('Bharti Airtel',       'BHARTIARTL.NS', 'Telecom'),
    'bharti':          ('Bharti Airtel',       'BHARTIARTL.NS', 'Telecom'),
    'national_alum':   ('NALCO',               'NATIONALUM.NS', 'Metals'),
    'nationalum':      ('NALCO',               'NATIONALUM.NS', 'Metals'),
    'nalco':           ('NALCO',               'NATIONALUM.NS', 'Metals'),
    'cholamandalam':   ('Cholamandalam',       'CHOLAFIN.NS',   'FinServ'),
    'chola':           ('Cholamandalam',       'CHOLAFIN.NS',   'FinServ'),
    'indian_oil':      ('IOC',                 'IOC.NS',        'Energy'),
    'indianoil':       ('IOC',                 'IOC.NS',        'Energy'),
    'bharat_petroleum':('BPCL',                'BPCL.NS',       'Energy'),
    'punjab_national': ('PNB',                 'PNB.NS',        'Banking'),
    'hdfc_bank':       ('HDFC Bank',           'HDFCBANK.NS',   'Banking'),
    'hdfcbank':        ('HDFC Bank',           'HDFCBANK.NS',   'Banking'),
    'icici_bank':      ('ICICI Bank',          'ICICIBANK.NS',  'Banking'),
    'icicibank':       ('ICICI Bank',          'ICICIBANK.NS',  'Banking'),
    'kotak_bank':      ('Kotak Mahindra Bank', 'KOTAKBANK.NS',  'Banking'),
    'kotakbank':       ('Kotak Mahindra Bank', 'KOTAKBANK.NS',  'Banking'),
    'kotak':           ('Kotak Mahindra Bank', 'KOTAKBANK.NS',  'Banking'),
    'axis_bank':       ('Axis Bank',           'AXISBANK.NS',   'Banking'),
    'axisbank':        ('Axis Bank',           'AXISBANK.NS',   'Banking'),
    'axis':            ('Axis Bank',           'AXISBANK.NS',   'Banking'),
    'federal_bank':    ('Federal Bank',        'FEDERALBNK.NS', 'Banking'),
    'federalbank':     ('Federal Bank',        'FEDERALBNK.NS', 'Banking'),
    'federal':         ('Federal Bank',        'FEDERALBNK.NS', 'Banking'),
    'idfc_first':      ('IDFC First Bank',     'IDFCFIRSTB.NS', 'Banking'),
    'idfcfirst':       ('IDFC First Bank',     'IDFCFIRSTB.NS', 'Banking'),
    'idfc':            ('IDFC First Bank',     'IDFCFIRSTB.NS', 'Banking'),
    'indusind':        ('IndusInd Bank',       'INDUSINDBK.NS', 'Banking'),
    'induslnd':        ('IndusInd Bank',       'INDUSINDBK.NS', 'Banking'),
    'tata_consultancy':('TCS',                 'TCS.NS',        'IT'),
    'infosys':         ('Infosys',             'INFY.NS',       'IT'),
    'reliance':        ('Reliance Industries', 'RELIANCE.NS',   'Energy'),
    'mahindra':        ('Mahindra & Mahindra', 'M&M.NS',        'Auto'),
    'aurobindo':       ('Aurobindo Pharma',    'AUROPHARMA.NS', 'Pharma'),
    'torrent':         ('Torrent Pharma',      'TORNTPHARM.NS', 'Pharma'),
    'apollo':          ('Apollo Hospitals',    'APOLLOHOSP.NS', 'Pharma'),
    'muthoot':         ('Muthoot Finance',     'MUTHOOTFIN.NS', 'FinServ'),
    'shriram':         ('Shriram Finance',     'SHRIRAMFIN.NS', 'FinServ'),
    'persistent':      ('Persistent Systems',  'PERSISTENT.NS', 'IT'),
    'mphasis':         ('Mphasis',             'MPHASIS.NS',    'IT'),
    'coforge':         ('Coforge',             'COFORGE.NS',    'IT'),
    'britannia':       ('Britannia',           'BRITANNIA.NS',  'FMCG'),
    'dabur':           ('Dabur',               'DABUR.NS',      'FMCG'),
    'marico':          ('Marico',              'MARICO.NS',     'FMCG'),
    'colgate':         ('Colgate India',       'COLPAL.NS',     'FMCG'),
    'colpal':          ('Colgate India',       'COLPAL.NS',     'FMCG'),
    'emami':           ('Emami',               'EMAMILTD.NS',   'FMCG'),
    'nestle':          ('Nestle India',        'NESTLEIND.NS',  'FMCG'),
    'cipla':           ('Cipla',               'CIPLA.NS',      'Pharma'),
    'divis':           ("Divi's Labs",         'DIVISLAB.NS',   'Pharma'),
    'divi':            ("Divi's Labs",         'DIVISLAB.NS',   'Pharma'),
    'lupin':           ('Lupin',               'LUPIN.NS',      'Pharma'),
    'alkem':           ('Alkem Labs',          'ALKEM.NS',      'Pharma'),
    'jsw_steel':       ('JSW Steel',           'JSWSTEEL.NS',   'Metals'),
    'jswsteel':        ('JSW Steel',           'JSWSTEEL.NS',   'Metals'),
    'jsw':             ('JSW Steel',           'JSWSTEEL.NS',   'Metals'),
    'hindalco':        ('Hindalco',            'HINDALCO.NS',   'Metals'),
    'vedanta':         ('Vedanta',             'VEDL.NS',       'Metals'),
    'vedl':            ('Vedanta',             'VEDL.NS',       'Metals'),
    'sail':            ('SAIL',                'SAIL.NS',       'Metals'),
    'nmdc':            ('NMDC',                'NMDC.NS',       'Metals'),
    'grasim':          ('Grasim',              'GRASIM.NS',     'Infra'),
    'ambuja':          ('Ambuja Cements',      'AMBUJACEM.NS',  'Infra'),
    'siemens':         ('Siemens India',       'SIEMENS.NS',    'Infra'),
    'cummins':         ('Cummins India',       'CUMMINSIND.NS', 'Infra'),
    'maruti':          ('Maruti Suzuki',       'MARUTI.NS',     'Auto'),
    'eicher':          ('Eicher Motors',       'EICHERMOT.NS',  'Auto'),
    'escorts':         ('Escorts Kubota',      'ESCORTS.NS',    'Auto'),
    'bosch':           ('Bosch India',         'BOSCHLTD.NS',   'Auto'),
    'titan':           ('Titan',               'TITAN.NS',      'Consumer'),
    'pidilite':        ('Pidilite',            'PIDILITIND.NS', 'Consumer'),
    'havells':         ('Havells',             'HAVELLS.NS',    'Consumer'),
    'paytm':           ('Paytm',               'PAYTM.NS',      'FinTech'),
    'cdsl':            ('CDSL',                'CDSL.NS',       'FinTech'),
    'wipro':           ('Wipro',               'WIPRO.NS',      'IT'),
    'maruti_suzuki':   ('Maruti Suzuki',       'MARUTI.NS',     'Auto'),
    'apollo_hospitals':('Apollo Hospitals',    'APOLLOHOSP.NS', 'Pharma'),
    'tvs':             ('TVS Motor',           'TVSMOTORS.NS',  'Auto'),
    'ntpc':            ('NTPC',                'NTPC.NS',       'Energy'),
    'ongc':            ('ONGC',                'ONGC.NS',       'Energy'),
    'bpcl':            ('BPCL',                'BPCL.NS',       'Energy'),
    'hcl':             ('HCL Technologies',    'HCLTECH.NS',    'IT'),
    'tcs':             ('TCS',                 'TCS.NS',        'IT'),
    'itc':             ('ITC',                 'ITC.NS',        'FMCG'),
    'sbi':             ('SBI',                 'SBIN.NS',       'Banking'),
    'pnb':             ('PNB',                 'PNB.NS',        'Banking'),
    'lici':            ('LIC',                 'LICI.NS',       'Insurance'),
    'lic':             ('LIC',                 'LICI.NS',       'Insurance'),
    'bse':             ('BSE Ltd',             'BSE.NS',        'FinTech'),
    'ioc':             ('IOC',                 'IOC.NS',        'Energy'),
    'abb':             ('ABB India',           'ABB.NS',        'Infra'),
    'acc':             ('ACC',                 'ACC.NS',        'Infra'),
    'idea':            ('Vodafone Idea',       'IDEA.NS',       'Telecom'),
    # ── L&T LAST: 'lt' is a substring of many names ───────────────────────
    'larsen':          ('Larsen & Toubro',     'LT.NS',         'Infra'),
    'l_t':             ('Larsen & Toubro',     'LT.NS',         'Infra'),
    'l&t':             ('Larsen & Toubro',     'LT.NS',         'Infra'),
    'lt':              ('Larsen & Toubro',     'LT.NS',         'Infra'),
}


def identify_company(filename):
    """Identify company and year from filename"""
    fn = Path(filename).stem.lower()
    # Extract year
    year_match = re.search(r'(202[0-9])', fn)
    year = int(year_match.group(1)) if year_match else None
    fy = f"FY {year-1}-{str(year)[2:]}" if year else None

    # Match company
    fn_clean = re.sub(r'^\d+_', '', fn)                       # strip leading upload IDs
    fn_clean = re.sub(r'_?202[0-9]_?', '', fn_clean).strip('_').strip()

    # 1. Exact match wins outright
    if fn_clean in COMPANY_MAP:
        info = COMPANY_MAP[fn_clean]
        return info[0], info[1], info[2], fy

    # 2. Otherwise the LONGEST key found inside the filename wins
    #    (prevents 'lt' hijacking 'ultratech', 'sbi' hijacking 'sbi_life', etc.)
    best_key, best_info = None, None
    for key, info in COMPANY_MAP.items():
        if key in fn_clean and (best_key is None or len(key) > len(best_key)):
            best_key, best_info = key, info
    if best_info:
        return best_info[0], best_info[1], best_info[2], fy
    return None, None, None, fy


def extract_number(text, patterns, min_val=0, max_val=1e9):
    """Extract first valid number matching any pattern"""
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            try:
                # Clean number string
                clean = re.sub(r'[,\s]', '', str(m))
                val = float(clean)
                if min_val <= val <= max_val:
                    return val
            except:
                continue
    return None


def find_page_with_keywords(pdf, keywords, max_pages=None):
    """Find page containing all specified keywords"""
    pages = pdf.pages[:max_pages] if max_pages else pdf.pages
    for i, page in enumerate(pages):
        text = page.extract_text() or ""
        tl = text.lower()
        if all(k.lower() in tl for k in keywords):
            return i, text
    return None, None


def extract_brsr_data(pdf_path):
    """Main extraction function — returns dict of ESG metrics"""
    result = {
        'scope1_tco2e': None,
        'scope12_tco2e': None,
        'total_energy_mgj': None,
        'renewable_energy_mgj': None,
        'renewable_pct': None,
        'women_directors_pct': None,
        'women_employees_pct': None,
        'controversies': 0,
        'extraction_notes': []
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:

            # ── SCOPE 1 & 2 ───────────────────────────────────────────
            idx, text = find_page_with_keywords(pdf, ['scope 1', 'tco2'])
            if text is None:
                idx, text = find_page_with_keywords(pdf, ['scope 1', 'emission'])

            if text:
                # Try to get Scope 1
                sc1 = extract_number(text,
                    [r'scope 1[^0-9]{1,60}?([\d,]+\.?\d*)\s*(?:tco2|mt|metric)',
                     r'total scope 1[^0-9]{1,60}?([\d,]+\.?\d*)'],
                    min_val=100, max_val=10_000_000)
                if sc1: result['scope1_tco2e'] = sc1

                # Try to get total Scope 1+2
                sc12 = extract_number(text,
                    [r'scope 1 and scope 2[^0-9]{1,80}?([\d,]+\.?\d*)',
                     r'total scope 1 and 2[^0-9]{1,80}?([\d,]+\.?\d*)',
                     r'scope 1\+2[^0-9]{1,40}?([\d,]+\.?\d*)'],
                    min_val=100, max_val=100_000_000)
                if sc12: result['scope12_tco2e'] = sc12

                # Try combined mention
                combined = extract_number(text,
                    [r'scope 1 and 2 emissions[^:]{0,20}:\s*([\d,]+\.?\d*)',
                     r'scope 1\+2 emissions[^:]{0,20}:\s*([\d,]+\.?\d*)'],
                    min_val=100, max_val=100_000_000)
                if combined and not result['scope12_tco2e']:
                    result['scope12_tco2e'] = combined

            # ── ENERGY ───────────────────────────────────────────────
            idx2, text2 = find_page_with_keywords(pdf, ['total energy', 'gj'])
            if text2 is None:
                idx2, text2 = find_page_with_keywords(pdf, ['total energy', 'gigajoule'])
            if text2 is None:
                idx2, text2 = find_page_with_keywords(pdf, ['energy consumption', 'gwh'])

            if text2:
                # Total energy in GJ
                total_e = extract_number(text2,
                    [r'total energy consumption[^0-9]{1,50}([\d,]+\.?\d*)',
                     r'total energy consumed[^0-9]{1,50}([\d,]+\.?\d*)'],
                    min_val=100, max_val=100_000_000)
                if total_e:
                    # Convert to Million GJ if in GJ
                    result['total_energy_mgj'] = total_e / 1_000_000 if total_e > 10000 else total_e

                # Renewable energy
                renew_e = extract_number(text2,
                    [r'from renewable sources[^0-9]{1,100}total[^0-9]{1,50}([\d,]+\.?\d*)',
                     r'renewable[^0-9]{1,60}total[^0-9]{1,50}([\d,]+\.?\d*)',
                     r'total.*?renewable[^0-9]{1,50}([\d,]+\.?\d*)'],
                    min_val=0, max_val=100_000_000)
                if renew_e and result['total_energy_mgj']:
                    result['renewable_energy_mgj'] = renew_e / 1_000_000 if renew_e > 10000 else renew_e
                    if result['total_energy_mgj'] > 0:
                        result['renewable_pct'] = result['renewable_energy_mgj'] / result['total_energy_mgj']

            # ── WOMEN DIRECTORS ───────────────────────────────────────
            for search_text in ['women director', 'no. of women', '% women']:
                idx3, text3 = find_page_with_keywords(pdf, [search_text])
                if text3:
                    # Look for percentage
                    wd_pct = extract_number(text3,
                        [r'women[^0-9]{1,30}(\d+\.?\d*)\s*%',
                         r'(\d+\.?\d*)\s*%[^0-9]{1,30}women',
                         r'no\. of women directors[^0-9]{1,30}(\d+)'],
                        min_val=0, max_val=100)
                    if wd_pct:
                        result['women_directors_pct'] = wd_pct / 100 if wd_pct > 1 else wd_pct
                        break

                    # Look for count X of Y
                    count_match = re.search(r'(\d+)\s+women?\s+director', text3, re.IGNORECASE)
                    total_match = re.search(r'total\s+(?:of\s+)?(\d+)\s+director', text3, re.IGNORECASE)
                    if count_match and total_match:
                        count = int(count_match.group(1))
                        total = int(total_match.group(1))
                        if total > 0:
                            result['women_directors_pct'] = round(count / total, 3)
                            break

            # ── WOMEN EMPLOYEES ───────────────────────────────────────
            idx4, text4 = find_page_with_keywords(pdf, ['women', 'employee'])
            if text4:
                we_pct = extract_number(text4,
                    [r'women\s+employees?[^0-9]{1,30}(\d+\.?\d*)\s*%',
                     r'(\d+\.?\d*)\s*%[^0-9]{1,20}female\s+employee',
                     r'female[^0-9]{1,20}(\d+\.?\d*)\s*%'],
                    min_val=0, max_val=100)
                if we_pct:
                    result['women_employees_pct'] = we_pct / 100 if we_pct > 1 else we_pct

            # ── CONTROVERSIES ─────────────────────────────────────────
            # Search for penalty/fine mentions in BRSR Principle 1
            idx5, text5 = find_page_with_keywords(pdf, ['penalty', 'principle 1'])
            if text5 is None:
                idx5, text5 = find_page_with_keywords(pdf, ['penalty', 'fine', 'compliance'])
            if text5:
                text5l = text5.lower()
                controv = 0
                if any(k in text5l for k in ['penalty imposed', 'fine imposed', 'penalty paid',
                                              'regulatory penalty', 'sebi order', 'rbi penalty']):
                    controv = 1
                if any(k in text5l for k in ['no penalty', 'nil penalty', 'no fine', 'no instances']):
                    controv = 0
                result['controversies'] = controv

    except Exception as e:
        result['extraction_notes'].append(f"Error: {str(e)}")

    return result


def process_all_pdfs(pdf_folder, excel_path, output_csv):
    """Process all PDFs in folder and update Excel tracker"""
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files in {pdf_folder}")
    print("="*60)

    results = []
    for pdf_path in sorted(pdf_files):
        filename = os.path.basename(pdf_path)
        company, ticker, sector, fy = identify_company(filename)

        if not company or not fy:
            print(f"SKIP: {filename} — could not identify company/year")
            continue

        # Only process FY 2022-23 and FY 2023-24
        if fy not in ["FY 2022-23", "FY 2023-24"]:
            print(f"SKIP: {filename} — year {fy} not needed")
            continue

        print(f"\nProcessing: {company} {fy}")
        print(f"  File: {filename}")

        data = extract_brsr_data(pdf_path)

        row = {
            'company': company,
            'sector': sector,
            'ticker': ticker,
            'year': fy,
            'scope1_tco2e': data['scope1_tco2e'],
            'scope12_tco2e': data['scope12_tco2e'],
            'total_energy_mgj': data['total_energy_mgj'],
            'renewable_energy_mgj': data['renewable_energy_mgj'],
            'renewable_pct': data['renewable_pct'],
            'women_directors_pct': data['women_directors_pct'],
            'women_employees_pct': data['women_employees_pct'],
            'controversies': data['controversies'],
        }

        # Print what was found
        found = {k:v for k,v in row.items() if v is not None and k not in ['company','sector','ticker','year']}
        print(f"  Extracted {len(found)}/8 fields: {list(found.keys())}")
        results.append(row)

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"\n\nResults saved to: {output_csv}")
    print(f"Total extracted: {len(df)} company-year records")
    print(f"Companies: {df['company'].nunique() if len(df) else 0}")

    # Update Excel tracker
    if os.path.exists(excel_path) and len(df) > 0:
        print(f"\nUpdating Excel tracker: {excel_path}")
        update_excel(df, excel_path)
        print("Excel tracker updated successfully!")
    else:
        print("\nExcel tracker not found or no data to add.")

    return df


def update_excel(df, excel_path):
    """Append extracted data to existing Excel tracker"""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb["OPS Data Tracker"]

    GREEN="27500A"; GREEN_L="EAF3DE"; AMBER="633806"; AMBER_L="FAEEDA"
    SEC_COLORS = {"Energy":"FFF8E6","IT":"E8F5E9","Banking":"E3F2FD","FinServ":"EDE7F6",
                  "FMCG":"FBE9E7","Pharma":"E0F7FA","Auto":"F3E5F5","Metals":"EFEBE9",
                  "Infra":"F9FBE7","Consumer":"FCE4EC","Telecom":"E8EAF6","Digital":"E8EAF6"}

    def tf(h): return PatternFill("solid", fgColor=h)
    def fn(bold=False,color="1A1A1A",size=9): return Font(name="Arial",bold=bold,color=color,size=size)
    def ca(): return Alignment(horizontal="center",vertical="center",wrap_text=True)
    def la(): return Alignment(horizontal="left",vertical="center",wrap_text=True)
    def bd():
        s=Side(style="thin",color="B4B2A9"); return Border(left=s,right=s,top=s,bottom=s)

    # Get existing company-years to avoid duplicates
    existing = set()
    last_row = 5
    for row in ws.iter_rows(min_row=6, max_row=ws.max_row):
        if row[0].value:
            existing.add(f"{row[0].value}_{row[3].value}")
            last_row = row[0].row

    fmt = {5:'#,##0',6:'#,##0',7:'0.000',8:'0.000',9:'0.0%',10:'0.0%',11:'0.0%',12:'0'}
    added = 0

    for _, row_data in df.iterrows():
        key = f"{row_data['company']}_{row_data['year']}"
        if key in existing:
            print(f"  SKIP duplicate: {key}")
            continue

        r = last_row + 1 + added
        sec = str(row_data.get('sector',''))
        shade = SEC_COLORS.get(sec, "FFFFFF")

        vals = [row_data['company'], sec, row_data['ticker'], row_data['year']]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col)
            c.value = val; c.fill=tf(shade)
            c.font=fn(size=9)
            c.alignment=la() if col<=2 else ca()
            c.border=bd()

        data_vals = [
            row_data.get('scope1_tco2e'),
            row_data.get('scope12_tco2e'),
            row_data.get('total_energy_mgj'),
            row_data.get('renewable_energy_mgj'),
            row_data.get('renewable_pct'),
            row_data.get('women_directors_pct'),
            row_data.get('women_employees_pct'),
            row_data.get('controversies'),
        ]

        for col_i, (val, f) in enumerate(zip(data_vals, fmt.values()), 5):
            c = ws.cell(row=r, column=col_i)
            c.border=bd(); c.font=fn(size=9); c.alignment=ca()
            c.number_format=f
            if val is None or (isinstance(val, float) and pd.isna(val)):
                c.value=""; c.fill=tf("FFF9C4")
            else:
                c.value=round(float(val),6) if isinstance(val,float) else val
                c.fill=tf(shade)

        # OPS formula
        m=ws.cell(row=r,column=13)
        m.value=f"=IFERROR(ROUND(COUNTA(E{r}:L{r})/8,2),0)"
        m.font=fn(bold=True,color="0C447C",size=9)
        m.fill=tf("E6F1FB"); m.number_format='0%'
        m.alignment=ca(); m.border=bd()

        # Completeness
        n=ws.cell(row=r,column=14)
        n.value=f'=COUNTA(E{r}:L{r})&"/8 fields"'
        n.font=fn(size=9); n.alignment=ca(); n.border=bd()

        # Status
        filled=sum(1 for v in data_vals if v is not None)
        o=ws.cell(row=r,column=15)
        if filled>=6: o.value="✓ Complete"; o.font=fn(bold=True,color=GREEN,size=9); o.fill=tf(GREEN_L)
        elif filled>=3: o.value="◑ Partial"; o.font=fn(bold=True,color=AMBER,size=9); o.fill=tf(AMBER_L)
        else: o.value="⬜ Needs Data"; o.font=fn(color=AMBER,size=9); o.fill=tf(AMBER_L)
        o.alignment=ca(); o.border=bd()
        ws.row_dimensions[r].height=16
        added += 1

    wb.save(excel_path)
    print(f"  Added {added} new rows to Excel tracker")


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("BRSR Data Extractor — GQE Dissertation")
    print("="*60)
    print(f"PDF Folder: {PDF_FOLDER}")
    print(f"Excel:      {EXCEL_PATH}")
    print(f"Output CSV: {OUTPUT_CSV}")

    if not os.path.exists(PDF_FOLDER):
        print(f"\nERROR: PDF folder not found: {PDF_FOLDER}")
        print("Please update PDF_FOLDER at the top of the script.")
    else:
        df = process_all_pdfs(PDF_FOLDER, EXCEL_PATH, OUTPUT_CSV)
        print("\n" + "="*60)
        print("DONE. Check extraction_results.csv for all extracted data.")
        print("="*60)
