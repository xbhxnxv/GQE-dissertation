"""
Maps dataset PDF filenames -> (company name, fiscal_year), using the
NIFTY-100-ish company_master.csv from the wider dissertation project for
canonical names where available, and a manual alias table for filename
quirks (misspellings, abbreviations, non-standard year formats).
"""
import re

# normalized filename base (year/extension stripped) -> canonical company name
ALIASES = {
    "abb": "ABB India",
    "acc": "ACC Ltd",
    "adani enterprise": "Adani Enterprises",
    "adani green": "Adani Green Energy",
    "adani ports": "Adani Ports",
    "airtel": "Bharti Airtel",
    "alkem": "Alkem Laboratories",
    "ambuja": "Ambuja Cements",
    "angel one": "Angel One",
    "apollo hospital": "Apollo Hospitals",
    "apollo tyre": "Apollo Tyres",
    "ashok leyland": "Ashok Leyland",
    "asianpaints": "Asian Paints",
    "aurobindo": "Aurobindo Pharma",
    "axis bank": "Axis Bank",
    "bajaj auto": "Bajaj Auto",
    "bajaj finance": "Bajaj Finance",
    "bajaj finserv": "Bajaj Finserv",
    "bank of baroda": "Bank of Baroda",
    "bharat petroleum": "Bharat Petroleum",
    "biocon": "Biocon",
    "bosch": "Bosch India",
    "britannia": "Britannia Industries",
    "bse": "BSE Ltd",
    "cdsl": "Central Depository Services",
    "cholamandalam": "Cholamandalam Finance",
    "cipla": "Cipla",
    "coal india": "Coal India",
    "coforge": "Coforge",
    "colgate": "Colgate-Palmolive India",
    "cummins": "Cummins India",
    "dabur": "Dabur India",
    "divis": "Divi's Laboratories",
    "dr.reddy": "Dr Reddy's Laboratories",
    "eicher": "Eicher Motors",
    "emami": "Emami Ltd",
    "escorts": "Escorts Kubota",
    "federal bank": "Federal Bank",
    "godrej consumer": "Godrej Consumer Products",
    "graism": "Grasim Industries",  # misspelling of grasim
    "grasim": "Grasim Industries",
    "havells": "Havells India",
    "hcl": "HCL Technologies",
    "hdfc": "HDFC Bank",
    "hdfc life": "HDFC Life Insurance",
    "hero motocorp": "Hero MotoCorp",
    "hindalco": "Hindalco Industries",
    "hindustan unilever": "Hindustan Unilever",
    "icici": "ICICI Bank",
    "icici lombard": "ICICI Lombard General Insurance",
    "idfc": "IDFC First Bank",
    "indus tower": "Indus Towers",
    "induslnd": "IndusInd Bank",  # misspelling of indusind
    "infosys": "Infosys",
    "ioc": "Indian Oil Corporation",
    "ioc brsr": "Indian Oil Corporation",
    "itc": "ITC Ltd",
    "jindal steel": "Jindal Steel & Power",
    "jsw steel": "JSW Steel",
    "kotak bank": "Kotak Mahindra Bank",
    "l&t": "Larsen & Toubro",
    "l&t tech": "L&T Technology Services",
    "lic life insurance": "Life Insurance Corporation",
    "ltimindtree": "LTIMindtree",
    "lupin": "Lupin",
    "mahindra": "Mahindra & Mahindra",
    "marico": "Marico",
    "maruti suzuki": "Maruti Suzuki",
    "mphasis": "Mphasis",
    "muthoot finance": "Muthoot Finance",
    "nalco": "National Aluminium Company",
    "nestle": "Nestle India",
    "nmdc": "NMDC Ltd",
    "ntpc": "NTPC Ltd",
    "ongc": "Oil & Natural Gas Corporation",
    "oracle": "Oracle Financial Services",
    "paytm": "Paytm (One 97 Communications)",
    "persistent": "Persistent Systems",
    "pidilite": "Pidilite Industries",
    "pnb": "Punjab National Bank",
    "policy bazaar": "PB Fintech (PolicyBazaar)",
    "powergrid": "Power Grid Corporation",
    "reliance": "Reliance Industries",
    "sail": "Steel Authority of India",
    "sbi": "State Bank of India",
    "sbi life": "SBI Life Insurance",
    "shree cement": "Shree Cement",
    "shriram": "Shriram Finance",
    "siemen": "Siemens India",
    "sun pharma": "Sun Pharmaceutical",
    "tata consumers": "Tata Consumer Products",
    "tata power": "Tata Power",
    "tata steel": "Tata Steel",
    "tcs": "Tata Consultancy Services",
    "tech mahindra": "Tech Mahindra",
    "titan": "Titan Company",
    "torrent": "Torrent Pharmaceuticals",
    "tvs motors": "TVS Motor Company",
    "ultratech cement": "UltraTech Cement",
    "vendanta": "Vedanta Ltd",  # misspelling of vedanta
    "vedanta": "Vedanta Ltd",
    "vodafone idea": "Vodafone Idea",
    "wipro": "Wipro",
}

YEAR_RANGE_RE = re.compile(r"(20\d{2})\s*-\s*(\d{2})")
YEAR_SINGLE_RE = re.compile(r"(20\d{2})")


def normalize_base(stem: str) -> str:
    """Strip year tokens/extraneous words from a filename stem, lowercase it."""
    s = stem.lower().strip()
    s = re.sub(r"\bbrsr\b", "brsr", s)  # keep brsr token for ioc-brsr case
    s = re.sub(r"20\d{2}\s*-\s*\d{2}", "", s)  # strip "2022-23" style ranges
    s = re.sub(r"20\d{2}", "", s)  # strip bare 4-digit years
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_fiscal_year(stem: str):
    """Return 'FY2022-23', 'FY2023-24', or None (incl. for bare 2022 / unparseable)."""
    m = YEAR_RANGE_RE.search(stem)
    if m:
        start = m.group(1)
        if start == "2022":
            return "FY2022-23"
        if start == "2023":
            return "FY2023-24"
        return None

    nums = YEAR_SINGLE_RE.findall(stem)
    if not nums:
        return None
    year = nums[-1]
    if year == "2023":
        return "FY2022-23"
    if year == "2024":
        return "FY2023-24"
    return None  # 2022 or anything else -> skip


def match_company(stem: str):
    """Return canonical company name for a filename stem, or None if unmatched."""
    base = normalize_base(stem)
    base = re.sub(r"\bbrsr\b", "", base).strip()
    base = re.sub(r"\s+", " ", base)
    if base in ALIASES:
        return ALIASES[base]
    # try without "ioc brsr" style suffix already stripped above; also try
    # collapsing double spaces / punctuation variants
    compact = base.replace(".", "").replace("&", "and")
    for key, val in ALIASES.items():
        key_compact = key.replace(".", "").replace("&", "and")
        if compact == key_compact:
            return val
    return None
