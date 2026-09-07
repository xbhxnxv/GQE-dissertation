import os
from collections import defaultdict
from company_mapping import match_company, parse_fiscal_year

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"

files = [f for f in os.listdir(DATASET_DIR) if f.lower().endswith(".pdf")]
print(f"Total PDFs: {len(files)}")

groups = defaultdict(list)
unmatched = []
skipped_year = []

for f in files:
    stem = os.path.splitext(f)[0]
    company = match_company(stem)
    fy = parse_fiscal_year(stem)
    if company is None:
        unmatched.append(f)
        continue
    if fy is None:
        skipped_year.append(f)
        continue
    groups[(company, fy)].append(f)

print(f"\nUnmatched company ({len(unmatched)}):")
for f in unmatched:
    print(" ", f)

print(f"\nSkipped (no valid FY22-23/23-24 year) ({len(skipped_year)}):")
for f in skipped_year:
    print(" ", f)

dupes = {k: v for k, v in groups.items() if len(v) > 1}
print(f"\nDuplicate (company, year) groups ({len(dupes)}):")
for k, v in dupes.items():
    print(" ", k, "->", v)

print(f"\nTotal distinct (company, year) targets: {len(groups)}")
companies = sorted(set(c for c, y in groups.keys()))
print(f"Total distinct companies: {len(companies)}")
