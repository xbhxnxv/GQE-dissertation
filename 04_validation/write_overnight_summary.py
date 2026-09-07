"""
TASK 4 - writes overnight_summary.txt.

Report only. Reads LPS_scores.csv and the recovery log; changes nothing.
"""
import os
import csv

from completeness_check import report as completeness_report

SCORES_CSV = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_scores.csv"
OUT = r"C:\Users\ASUS\Desktop\me\Dissertation\overnight_summary.txt"

# The 16 company-years targeted for recovery, and what happened to each.
# 'why' is filled in for failures only.
RECOVERY = [
    ("Reliance Industries",             "FY2022-23", "RECOVERED", "ril.com standalone BRSR"),
    ("Reliance Industries",             "FY2023-24", "RECOVERED", "ril.com standalone BRSR"),
    ("Indian Oil Corporation",          "FY2022-23", "RECOVERED", "iocl.com standalone BRSR"),
    ("Indian Oil Corporation",          "FY2023-24", "RECOVERED", "iocl.com standalone BRSR"),
    ("ICICI Lombard General Insurance", "FY2023-24", "RECOVERED", "NSE archive"),
    ("Apollo Hospitals",                "FY2022-23", "RECOVERED", "NSE archive"),
    ("Axis Bank",                       "FY2023-24", "RECOVERED", "NSE archive"),
    ("Bank of Baroda",                  "FY2023-24", "RECOVERED", "NSE archive"),
    ("BSE Ltd",                         "FY2022-23", "RECOVERED", "NSE archive"),
    ("IDFC First Bank",                 "FY2022-23", "RECOVERED", "NSE archive"),
    ("IDFC First Bank",                 "FY2023-24", "RECOVERED", "NSE archive"),
    ("Mphasis",                         "FY2023-24", "RECOVERED", "NSE archive"),
    ("Oracle Financial Services",       "FY2023-24", "RECOVERED", "NSE archive"),
    ("ICICI Lombard General Insurance", "FY2022-23", "FAILED",
     "icicilombard.com CDN returns Access Denied to automated requests; "
     "NSE has the filing but attachmentFile is null (no PDF lodged)"),
    ("Godrej Consumer Products",        "FY2022-23", "FAILED",
     "NSE has the filing but attachmentFile is null (no PDF lodged)"),
    ("Oracle Financial Services",       "FY2022-23", "FAILED",
     "NSE has the filing but attachmentFile is null (no PDF lodged)"),
]

# Additional company-years recovered beyond the original 16, found during
# verification (duplicate source files / never produced a row at all).
EXTRA = [
    ("BSE Ltd",                    "FY2023-24", "NSE archive - never had a row before"),
    ("Central Depository Services", "FY2022-23", "NSE archive - never had a row before"),
    ("Central Depository Services", "FY2023-24", "NSE archive - never had a row before"),
    ("Coal India",                 "FY2023-24", "NSE archive - never had a row before"),
    ("LTIMindtree",                "FY2023-24", "NSE archive - never had a row before"),
    ("HDFC Life Insurance",        "FY2022-23", "was scored on HDFC Bank's PDF (identical file)"),
    ("HDFC Life Insurance",        "FY2023-24", "was scored on HDFC Bank's PDF (identical file)"),
]

EXTRA_FAILED = [
    ("State Bank of India", "FY2022-23",
     "existing row is a 4-page / 1,794-word truncation; NSE attachmentFile is "
     "null for FY2022-23 so no replacement PDF could be fetched"),
    ("Nestle India", "FY2022-23",
     "no source PDF in dataset and none on NSE. NSE holds only FY2023-24 and "
     "FY2024-25 for NESTLEIND. Nestle India historically used a December "
     "year-end and transitioned to a March year-end, so no filing maps onto "
     "FY2022-23 the way it does for the other 99 companies. This looks like a "
     "structural absence rather than a missed download - worth stating as such "
     "rather than chasing"),
]


def main():
    with open(SCORES_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    idx = {(r["company"], r["year"]): r for r in rows}

    def geti(r, k):
        try:
            return int(r.get(k) or 0)
        except ValueError:
            return 0

    def is_solid(r):
        return (geti(r, "ess_pages") >= 5 and geti(r, "principles_found") >= 8
                and geti(r, "brsr_pages") >= 8)

    solid = [r for r in rows if is_solid(r)]
    failed = [r for r in rows if geti(r, "ess_pages") == 0]
    partial = [r for r in rows if not is_solid(r) and geti(r, "ess_pages") > 0]

    o = []
    a = o.append
    a("=" * 78)
    a("OVERNIGHT SUMMARY - BRSR CORPUS RECOVERY AND VERIFICATION")
    a("Report only. No GDS, no regressions, no models were run.")
    a("LPS_scores.csv contains scored rows only; all backups left intact.")
    a("=" * 78)
    a("")

    a("-" * 78)
    a("1. RECOVERY OF THE 16 TARGETED COMPANY-YEARS")
    a("-" * 78)
    ok = [x for x in RECOVERY if x[2] == "RECOVERED"]
    bad = [x for x in RECOVERY if x[2] == "FAILED"]
    a(f"  Recovered and scored : {len(ok)}/16")
    a(f"  Failed               : {len(bad)}/16")
    a("")
    a("  RECOVERED:")
    for c, y, _, src in ok:
        r = idx.get((c, y))
        if r:
            a(f"    {c:<32} {y:<10} ess_pages={geti(r,'ess_pages'):<3} "
              f"principles={geti(r,'principles_found')}/9 pages={geti(r,'brsr_pages'):<3} "
              f"words={geti(r,'word_count'):<6} [{src}]")
        else:
            a(f"    {c:<32} {y:<10} (recovered but NO ROW IN CSV - investigate) [{src}]")
    a("")
    a("  FAILED:")
    for c, y, _, why in bad:
        a(f"    {c:<32} {y:<10}")
        a(f"        reason: {why}")
    a("")
    a("  NOTE on the 3 failures: all are FY2022-23, the first mandatory BRSR year.")
    a("  NSE holds a filing record for each but stores the literal string 'null'")
    a("  as the attachment, i.e. no PDF was lodged through that route. An XBRL")
    a("  file DOES exist for each. It was deliberately NOT used: its text nodes")
    a("  are largely schema identifiers (e.g. 'DetailsOfBusinessActivities...")
    a("  Domain1') rather than prose, and its composition differs systematically")
    a("  from the PDF-derived text used for every other row, so scoring it would")
    a("  not be comparable. Recovering these needs a manual browser download or a")
    a("  separate XBRL-to-narrative parser plus an explicit comparability caveat.")
    a("")

    a("-" * 78)
    a("2. ADDITIONAL COMPANY-YEARS RECOVERED (beyond the original 16)")
    a("-" * 78)
    a("  Found during verification, not on the original list:")
    for c, y, why in EXTRA:
        r = idx.get((c, y))
        if r:
            a(f"    {c:<32} {y:<10} ess_pages={geti(r,'ess_pages'):<3} "
              f"principles={geti(r,'principles_found')}/9 words={geti(r,'word_count'):<6} [{why}]")
        else:
            a(f"    {c:<32} {y:<10} NOT IN CSV [{why}]")
    a("")
    a("  Still failed:")
    for c, y, why in EXTRA_FAILED:
        a(f"    {c:<32} {y:<10}")
        a(f"        reason: {why}")
    a("")

    a("-" * 78)
    a("3. FINAL CORPUS COUNTS")
    a("-" * 78)
    a("  SOLID = ess_pages >= 5 AND principles >= 8 AND brsr_pages >= 8")
    a("")
    a(f"  SOLID   : {len(solid)}")
    a(f"  PARTIAL : {len(partial)}")
    a(f"  FAILED  : {len(failed)}")
    a(f"  TOTAL   : {len(rows)}")
    a("")
    if partial:
        a("  PARTIAL rows (some BRSR content, below a threshold):")
        for r in sorted(partial, key=lambda x: geti(x, "ess_pages")):
            a(f"    {r['company']:<32} {r['year']:<10} ess={geti(r,'ess_pages'):<3} "
              f"principles={geti(r,'principles_found')}/9 pages={geti(r,'brsr_pages'):<3} "
              f"words={geti(r,'word_count')}")
        a("")
    if failed:
        a("  FAILED rows (no BRSR form content at all - ess_pages = 0):")
        for r in sorted(failed, key=lambda x: x["company"]):
            a(f"    {r['company']:<32} {r['year']:<10} pages={geti(r,'brsr_pages'):<3} "
              f"words={geti(r,'word_count'):<6} src={r['source_file']}")
        a("")

    a("-" * 78)
    a("4. COMPLETENESS AGAINST THE COMPANY LIST")
    a("-" * 78)
    for line in completeness_report().split("\n"):
        a("  " + line)
    a("")

    a("-" * 78)
    a("5. TOTAL ROWS IN LPS_scores.csv")
    a("-" * 78)
    a(f"  {len(rows)}")
    a("")
    a("=" * 78)
    a("END - no downstream analysis performed.")
    a("=" * 78)

    text = "\n".join(o)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
