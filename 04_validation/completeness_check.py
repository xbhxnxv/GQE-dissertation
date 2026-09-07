"""
TASK 3 - completeness check.

Confirms every company in the dataset has BOTH FY2022-23 and FY2023-24 rows in
LPS_scores.csv. Read-only; writes nothing.
"""
import os
import csv

from company_mapping import match_company, parse_fiscal_year, ALIASES

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
SCORES_CSV = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_scores.csv"
YEARS = ("FY2022-23", "FY2023-24")


def expected_companies():
    """Canonical company names the dataset actually covers."""
    names = set()
    for f in os.listdir(DATASET_DIR):
        if not f.lower().endswith(".pdf"):
            continue
        c = match_company(os.path.splitext(f)[0])
        if c:
            names.add(c)
    return names


def report():
    companies = expected_companies()
    with open(SCORES_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    have = {(r["company"], r["year"]) for r in rows}

    lines = []
    a = lines.append
    a(f"Distinct companies represented in dataset : {len(companies)}")
    a(f"Rows present in LPS_scores.csv            : {len(rows)}")
    a(f"Expected if every company had both years  : {len(companies) * 2}")
    a("")

    missing = []
    for c in sorted(companies):
        for y in YEARS:
            if (c, y) not in have:
                missing.append((c, y))

    if missing:
        a(f"MISSING company-years ({len(missing)}):")
        for c, y in missing:
            # was there even a source file for it?
            src = [f for f in os.listdir(DATASET_DIR)
                   if f.lower().endswith(".pdf")
                   and match_company(os.path.splitext(f)[0]) == c
                   and parse_fiscal_year(os.path.splitext(f)[0]) == y]
            why = f"source file(s) present: {src}" if src else "NO source PDF in dataset"
            a(f"   {c:<34} {y:<10} {why}")
    else:
        a("No missing company-years - every company has both FY2022-23 and FY2023-24.")
    a("")

    # companies with only one year
    one_year = [c for c in sorted(companies)
                if sum((c, y) in have for y in YEARS) == 1]
    if one_year:
        a(f"Companies with only ONE year scored ({len(one_year)}):")
        for c in one_year:
            got = [y for y in YEARS if (c, y) in have]
            a(f"   {c:<34} has {got}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
