"""
Builds the manual re-download list: company-years whose source PDF contains no
BRSR form at all, plus any BRSR/sustainability URL found inside that PDF.

Read-only. Writes BRSR_redownload_list.txt.
"""
import os
import re
import csv

import fitz

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
SCORES_CSV = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_scores.csv"
OUT_TXT = r"C:\Users\ASUS\Desktop\me\Dissertation\BRSR_redownload_list.txt"

ESS_RE = re.compile(r"essential indicators|leadership indicators", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s\)\]\},;\"'<>]+", re.I)
# URLs likely to point at a standalone BRSR / sustainability / ESG report
RELEVANT_URL = re.compile(
    r"brsr|business[-_]?respons|sustainab|esg|responsibility|annual[-_]?report|investor",
    re.I,
)


def scan(pdf_path):
    """Return (ess_page_count, sorted list of candidate BRSR URLs)."""
    urls = set()
    ess = 0
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                t = page.get_text() or ""
                if ESS_RE.search(t):
                    ess += 1
                for m in URL_RE.finditer(t):
                    u = m.group(0).rstrip(".,;:")
                    if RELEVANT_URL.search(u):
                        urls.add(u)
                # links stored as PDF annotations rather than visible text
                try:
                    for link in page.get_links():
                        u = link.get("uri")
                        if u and RELEVANT_URL.search(u):
                            urls.add(u.rstrip(".,;:"))
                except Exception:
                    pass
    except Exception as e:
        return None, [f"<could not read PDF: {e}>"]
    return ess, sorted(urls)


def main():
    with open(SCORES_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    missing = []
    for r in rows:
        try:
            ess = int(r.get("ess_pages") or 0)
        except ValueError:
            ess = 0
        if ess == 0:
            missing.append(r)

    out = []
    w = out.append
    w("=" * 78)
    w("BRSR RE-DOWNLOAD LIST")
    w("Company-years whose supplied PDF contains NO BRSR form")
    w("(zero pages with 'Essential Indicators' / 'Leadership Indicators').")
    w("These cannot be fixed in code - the standalone BRSR must be fetched.")
    w("=" * 78)
    w("")
    w(f"Rows needing a replacement file: {len(missing)}")
    w("")

    for r in sorted(missing, key=lambda x: (x["company"], x["year"])):
        src = r.get("source_file", "")
        path = os.path.join(DATASET_DIR, src)
        ess, urls = scan(path) if os.path.exists(path) else (None, ["<file not found>"])
        w("-" * 78)
        w(f"COMPANY : {r['company']}")
        w(f"YEAR    : {r['year']}")
        w(f"FILE    : {src}")
        w(f"PAGES   : {r.get('brsr_pages','?')} extracted, "
          f"{r.get('principles_found','?')}/9 principles, ess_pages={ess}")
        if urls:
            w("URLS FOUND IN PDF (candidate sources for the standalone BRSR):")
            for u in urls[:12]:
                w(f"    {u}")
            if len(urls) > 12:
                w(f"    ... and {len(urls) - 12} more")
        else:
            w("URLS FOUND IN PDF: none matching BRSR/sustainability/investor patterns")
        w("")

    w("=" * 78)
    w("SUGGESTED SOURCES IF NO URL IS LISTED ABOVE:")
    w("  - NSE:  nseindia.com -> company page -> Financial Results / Annual Reports")
    w("  - BSE:  bseindia.com -> Corp Filings -> Business Responsibility Report")
    w("  - The company's own Investor Relations / Sustainability page")
    w("  BRSR is filed separately from the Annual Report by many companies, which")
    w("  is why the Annual Report PDF alone does not contain it.")
    w("=" * 78)

    text = "\n".join(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nWritten to {OUT_TXT}")


if __name__ == "__main__":
    main()
