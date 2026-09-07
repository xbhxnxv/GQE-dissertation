"""
Fetches standalone BRSR PDFs from the NSE archive for company-years whose
supplied annual-report PDF lacked the BRSR form.

Downloads to a staging dir and validates each file (must contain real BRSR
form content) BEFORE it is placed into the dataset folder.
"""
import os
import sys
import json
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_brsr import extract_brsr_section

STAGE = r"C:\Users\ASUS\AppData\Local\Temp\claude\C--Users-ASUS-Desktop-me-claude\bb4467f7-15c3-4a7d-94b9-101e0a3c5973\scratchpad\brsr_stage"
DATASET = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
LISTING = "https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiyreports"
API = "https://www.nseindia.com/api/corporate-bussiness-sustainabilitiy"

# (nse_symbol, dataset_filename_stem, fy_from, fy_to)
# filename stem must survive company_mapping.match_company (it strips "brsr")
TARGETS = [
    ("APOLLOHOSP", "apollo hospital brsr 2023", 2022, 2023),
    ("AXISBANK",   "axis bank brsr 2024",       2023, 2024),
    ("BSE",        "bse brsr 2023",             2022, 2023),
    ("BSE",        "bse brsr 2024",             2023, 2024),
    ("BANKBARODA", "bank of baroda brsr 2024",  2023, 2024),
    ("GODREJCP",   "godrej consumer brsr 2023", 2022, 2023),
    ("ICICIGI",    "icici lombard brsr 2023",   2022, 2023),
    ("ICICIGI",    "icici lombard brsr 2024",   2023, 2024),
    ("IDFCFIRSTB", "idfc brsr 2023",            2022, 2023),
    ("IDFCFIRSTB", "idfc brsr 2024",            2023, 2024),
    ("MPHASIS",    "mphasis brsr 2024",         2023, 2024),
    ("OFSS",       "oracle brsr 2023",          2022, 2023),
    ("OFSS",       "oracle brsr 2024",          2023, 2024),
    ("CDSL",       "cdsl brsr 2023",            2022, 2023),
    ("CDSL",       "cdsl brsr 2024",            2023, 2024),
    ("COALINDIA",  "coal india brsr 2024",      2023, 2024),
    ("LTIM",       "ltimindtree brsr 2024",     2023, 2024),
    ("SBIN",       "SBI brsr 2023",             2022, 2023),
    ("HDFCLIFE",   "hdfc life brsr 2023",       2022, 2023),
    ("HDFCLIFE",   "hdfc life brsr 2024",       2023, 2024),
]


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    s.get("https://www.nseindia.com", timeout=40)
    s.get(LISTING, timeout=40, headers={"Referer": "https://www.nseindia.com"})
    return s


def fetch_listing(s, symbol):
    # Without an explicit date range the API returns ONLY the latest filing,
    # which is the current FY -- the historical BRSRs we need are invisible.
    params = {"index": "equities", "symbol": symbol,
              "from_date": "01-04-2022", "to_date": "31-12-2024"}
    r = s.get(API, params=params, timeout=60,
              headers={"Referer": LISTING, "X-Requested-With": "XMLHttpRequest",
                       "Accept": "*/*"})
    r.raise_for_status()
    try:
        return r.json().get("data", [])
    except json.JSONDecodeError:
        return []


def main():
    os.makedirs(STAGE, exist_ok=True)
    s = make_session()
    results = []

    by_symbol = {}
    for sym, stem, fy_from, fy_to in TARGETS:
        by_symbol.setdefault(sym, []).append((stem, fy_from, fy_to))

    for sym, wants in by_symbol.items():
        try:
            data = fetch_listing(s, sym)
        except Exception as e:
            for stem, a, b in wants:
                results.append((stem, "LISTING_FAIL", str(e)[:60]))
            continue
        if not data:
            for stem, a, b in wants:
                results.append((stem, "NO_DATA", "empty listing"))
            continue

        for stem, fy_from, fy_to in wants:
            match = None
            for row in data:
                if row.get("fyFrom") == fy_from and row.get("fyTo") == fy_to:
                    match = row
                    break
            if match is None:
                avail = sorted({(r.get("fyFrom"), r.get("fyTo")) for r in data})
                results.append((stem, "NO_FY", f"have {avail}"))
                continue

            url = match.get("attachmentFile")
            # NSE sometimes records the filing but stores the literal string
            # ".../null" as the attachment -- no PDF was actually lodged.
            if not url or url.rstrip("/").endswith("null"):
                results.append((stem, "NO_ATTACHMENT", "NSE has no PDF for this FY"))
                continue

            dest = os.path.join(STAGE, stem + ".pdf")
            try:
                rr = s.get(url, timeout=180, headers={"Referer": LISTING})
                rr.raise_for_status()
                with open(dest, "wb") as f:
                    f.write(rr.content)
            except Exception as e:
                results.append((stem, "DL_FAIL", str(e)[:60]))
                continue

            # validate before it is allowed anywhere near the dataset
            try:
                res = extract_brsr_section(dest)
                ess = res.get("ess_pages", 0)
                npr = len(res["principles_found"])
                words = len(res["text"].split())
                if ess > 0 and npr >= 8:
                    results.append((stem, "PASS",
                                    f"ess={ess} principles={npr}/9 words={words}"))
                else:
                    results.append((stem, "REJECT",
                                    f"ess={ess} principles={npr}/9 words={words}"))
            except Exception as e:
                results.append((stem, "PARSE_FAIL", str(e)[:60]))
            time.sleep(1.0)

    print(f"{'file':<30} {'status':<12} detail")
    print("-" * 78)
    for stem, status, detail in sorted(results):
        print(f"{stem:<30} {status:<12} {detail}")

    passed = [r for r in results if r[1] == "PASS"]
    print(f"\n{len(passed)}/{len(TARGETS)} passed validation (staged, NOT yet copied to dataset)")
    print(f"Staging dir: {STAGE}")


if __name__ == "__main__":
    main()
