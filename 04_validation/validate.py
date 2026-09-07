"""
Validation-only pass over LPS_scores.csv.

Reads (never writes) LPS_scores.csv, re-reads the source PDFs for word counts
and a BRSR-presence diagnostic, and writes LPS_validation_summary.txt.

Deliberately does NOT compute GDS, run regressions, or fit any model.
"""
import os
import re
import csv
import statistics

import fitz

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
SCORES_CSV = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_scores.csv"
SUMMARY_TXT = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_validation_summary.txt"

ESS_RE = re.compile(r"essential indicators|leadership indicators", re.I)
SEC_RE = re.compile(r"section\s+[abc]\s*[:\-]", re.I)


def fnum(v):
    """Parse a CSV cell to float, or None if blank/unparseable."""
    if v is None:
        return None
    v = v.strip()
    if v == "" or v.lower() in ("na", "none", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def brsr_diagnostic(pdf_path):
    """Return (word_count_of_whole_pdf, pages_with_essential_indicators, pages_with_section_abc)."""
    try:
        with fitz.open(pdf_path) as doc:
            words = 0
            ess = 0
            sec = 0
            for page in doc:
                t = page.get_text() or ""
                words += len(t.split())
                if ESS_RE.search(t):
                    ess += 1
                if SEC_RE.search(t):
                    sec += 1
            return words, ess, sec
    except Exception:
        return None, None, None


def main():
    if not os.path.exists(SCORES_CSV):
        raise SystemExit(f"{SCORES_CSV} not found - run main.py first")

    with open(SCORES_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    out = []
    w = out.append

    w("=" * 78)
    w("LPS VALIDATION SUMMARY")
    w("Validation only - no GDS, no regressions, no downstream modelling.")
    w("LPS_scores.csv was read but NOT modified.")
    w("=" * 78)
    w("")
    w(f"Rows in LPS_scores.csv: {len(rows)}")
    w("")

    # ---------------- enrich rows with word counts + BRSR presence -------------
    # main.py now records ess_pages and word_count directly; fall back to
    # re-reading the PDF only for older CSVs that lack those columns.
    for r in rows:
        if r.get("ess_pages") not in (None, "") and r.get("word_count") not in (None, ""):
            try:
                r["_ess"] = int(r["ess_pages"])
                r["_words"] = int(r["word_count"])
                r["_sec"] = None
            except ValueError:
                r["_ess"] = r["_words"] = r["_sec"] = None
        else:
            src = r.get("source_file", "")
            path = os.path.join(DATASET_DIR, src) if src else None
            if path and os.path.exists(path):
                words, ess, sec = brsr_diagnostic(path)
            else:
                words, ess, sec = None, None, None
            r["_words"] = words
            r["_ess"] = ess
            r["_sec"] = sec
        try:
            r["_principles"] = int(r.get("principles_found") or 0)
        except ValueError:
            r["_principles"] = 0
        try:
            r["_pages"] = int(r.get("brsr_pages") or 0)
        except ValueError:
            r["_pages"] = 0

    # ---------------- 1. COVERAGE --------------------------------------------
    w("-" * 78)
    w("1. COVERAGE")
    w("-" * 78)

    clean = [r for r in rows if r["_principles"] == 9]
    partial = [r for r in rows if 1 <= r["_principles"] <= 8]
    none_p = [r for r in rows if r["_principles"] == 0]

    w(f"  Clean  (9/9 principles) : {len(clean):4d}")
    w(f"  Partial(1-8 principles) : {len(partial):4d}")
    w(f"  Zero   (0/9 principles) : {len(none_p):4d}")
    w("")

    # thin extractions: little text relative to a real BRSR section
    thin = [r for r in rows if r["_pages"] <= 3 or r["_principles"] <= 2]
    w(f"  Suspiciously thin extractions (<=3 pages or <=2 principles): {len(thin)}")
    for r in sorted(thin, key=lambda x: (x["_principles"], x["_pages"])):
        w(f"    {r['company']:<34} {r['year']:<10} "
          f"pages={r['_pages']:<3} principles={r['_principles']}/9  src={r['source_file']}")
    w("")

    # Distinguish 'BRSR absent from PDF' from 'BRSR present but under-extracted'
    w("  Root-cause split for weak rows (principles < 9):")
    w("    'BRSR ABSENT'      = source PDF has no Essential/Leadership Indicators at all")
    w("                         -> data problem: the correct BRSR file needs downloading")
    w("    'UNDER-EXTRACTED'  = BRSR form IS in the PDF but the extractor missed part of it")
    w("                         -> code problem on our side")
    w("")
    absent, under = [], []
    for r in rows:
        if r["_principles"] >= 9:
            continue
        if r["_ess"] is None:
            continue
        (absent if r["_ess"] == 0 else under).append(r)

    w(f"    BRSR ABSENT     : {len(absent)}")
    for r in sorted(absent, key=lambda x: x["company"]):
        w(f"      {r['company']:<34} {r['year']:<10} ess_pages=0  src={r['source_file']}")
    w("")
    w(f"    UNDER-EXTRACTED : {len(under)}")
    for r in sorted(under, key=lambda x: x["company"]):
        w(f"      {r['company']:<34} {r['year']:<10} "
          f"ess_pages={r['_ess']:<3} got {r['_principles']}/9  src={r['source_file']}")
    w("")

    # word counts per document
    w("  Word count of source PDF per company-year (full document):")
    for r in sorted(rows, key=lambda x: (x["company"], x["year"])):
        wc = r["_words"]
        wc_s = f"{wc:,}" if wc is not None else "n/a"
        w(f"    {r['company']:<34} {r['year']:<10} words={wc_s:>10}  "
          f"brsr_pages={r['_pages']:<3} principles={r['_principles']}/9")
    w("")

    # ---------------- 2. SCORE SANITY ----------------------------------------
    w("-" * 78)
    w("2. SCORE SANITY (LPS_finbert)")
    w("-" * 78)

    fb = [(r, fnum(r.get("LPS_finbert"))) for r in rows]
    fb_vals = [v for _, v in fb if v is not None]
    missing_fb = [r for r, v in fb if v is None]

    if not fb_vals:
        w("  No usable LPS_finbert values found.")
    else:
        mn, mx = min(fb_vals), max(fb_vals)
        mean = statistics.mean(fb_vals)
        sd = statistics.pstdev(fb_vals) if len(fb_vals) > 1 else 0.0
        w(f"  n        = {len(fb_vals)}")
        w(f"  min      = {mn:.6f}")
        w(f"  max      = {mx:.6f}")
        w(f"  mean     = {mean:.6f}")
        w(f"  std dev  = {sd:.6f}")
        w(f"  range    = {mx - mn:.6f}")
        w("")
        if sd < 1e-6:
            w("  *** FLAG: near-zero spread - all FinBERT scores are effectively identical.")
            w("      This would indicate a scoring fault, not a real finding.")
        elif (mx - mn) < 0.01:
            w("  *** FLAG: scores span < 0.01 - suspiciously tight clustering.")
        else:
            w("  OK: scores show meaningful spread (not degenerate).")

        exact_zero = [r for r, v in fb if v is not None and v == 0.0]
        if exact_zero:
            w("")
            w(f"  *** FLAG: {len(exact_zero)} row(s) with LPS_finbert exactly 0.0 "
              f"(usually means empty text):")
            for r in exact_zero:
                w(f"      {r['company']:<34} {r['year']:<10} src={r['source_file']}")
        else:
            w("  OK: no LPS_finbert values are exactly 0.0.")

    if missing_fb:
        w("")
        w(f"  Rows with no FinBERT score ({len(missing_fb)}):")
        for r in missing_fb:
            w(f"      {r['company']:<34} {r['year']:<10}")
    w("")

    # LM degenerate check (|LM| == 1 means the text was tiny)
    lm_deg = [r for r in rows
              if (v := fnum(r.get("LPS_lm"))) is not None and abs(v) == 1.0]
    if lm_deg:
        w(f"  *** FLAG: {len(lm_deg)} row(s) with LPS_lm exactly +/-1.0 - degenerate, "
          f"means almost no words matched the LM dictionary:")
        for r in lm_deg:
            w(f"      {r['company']:<34} {r['year']:<10} "
              f"LPS_lm={r['LPS_lm']}  pages={r['_pages']} principles={r['_principles']}/9")
        w("")

    # ---------------- 3. CROSS-METHOD ----------------------------------------
    w("-" * 78)
    w("3. CROSS-METHOD CHECK (FinBERT vs Loughran-McDonald)")
    w("-" * 78)
    w("  Expectation: FinBERT should read ESG prose less negatively than the LM")
    w("  dictionary, so FinBERT > LM should hold for most company-years.")
    w("")

    pairs = []
    for r in rows:
        a, b = fnum(r.get("LPS_finbert")), fnum(r.get("LPS_lm"))
        if a is not None and b is not None:
            pairs.append((r, a, b))

    if not pairs:
        w("  No rows have both FinBERT and LM scores.")
    else:
        gt = [p for p in pairs if p[1] > p[2]]
        pct = 100.0 * len(gt) / len(pairs)
        w(f"  Comparable rows      : {len(pairs)}")
        w(f"  FinBERT > LM         : {len(gt)}  ({pct:.1f}%)")
        w(f"  FinBERT <= LM        : {len(pairs) - len(gt)}  ({100 - pct:.1f}%)")
        diffs = [a - b for _, a, b in pairs]
        w(f"  mean(FinBERT - LM)   : {statistics.mean(diffs):.6f}")
        w(f"  median(FinBERT - LM) : {statistics.median(diffs):.6f}")
        w("")
        if pct >= 80:
            w("  OK: matches the expected direction strongly.")
        elif pct >= 60:
            w("  OK-ish: expected direction holds for a clear majority.")
        else:
            w("  *** FLAG: expected direction does NOT hold for most rows - worth a look.")
        w("")
        w("  Rows where FinBERT <= LM (counter to expectation):")
        for r, a, b in sorted(pairs, key=lambda p: p[1] - p[2]):
            if a <= b:
                w(f"      {r['company']:<34} {r['year']:<10} "
                  f"finbert={a:+.4f} lm={b:+.4f} diff={a-b:+.4f}")
    w("")

    # ---------------- 4. OUTLIERS --------------------------------------------
    w("-" * 78)
    w("4. OUTLIERS (LPS_finbert extremes)")
    w("-" * 78)
    scored = [(r, v) for r, v in fb if v is not None]
    if scored:
        hi = sorted(scored, key=lambda p: p[1], reverse=True)[:5]
        lo = sorted(scored, key=lambda p: p[1])[:5]
        w("  5 HIGHEST (most linguistically positive):")
        for r, v in hi:
            w(f"    {v:+.4f}  {r['company']:<34} {r['year']:<10} "
              f"pages={r['_pages']:<3} principles={r['_principles']}/9")
        w("")
        w("  5 LOWEST (least linguistically positive):")
        for r, v in lo:
            w(f"    {v:+.4f}  {r['company']:<34} {r['year']:<10} "
              f"pages={r['_pages']:<3} principles={r['_principles']}/9")
        w("")
        w("  NOTE: check whether any extreme also has a low principle count - if so its")
        w("  score rests on very little text and should not be read as a real signal.")
    w("")

    # ---------------- 5. QUALITY-FILTERED DISTRIBUTION ------------------------
    w("-" * 78)
    w("5. EFFECT OF EXTRACTION QUALITY ON THE DISTRIBUTION")
    w("-" * 78)
    w("  Principle count alone is not a sufficient quality filter: a 1-3 page BRSR")
    w("  contents/index page can list all 9 principles while containing no report.")
    w("  SOLID = ess_pages >= 5 AND principles >= 8 AND brsr_pages >= 8.")
    w("  PARTIAL = has some real BRSR form content (ess_pages > 0) but misses a bar.")
    w("  FAILED  = no BRSR form content at all (ess_pages == 0).")
    w("")

    def is_solid(r):
        return ((r["_ess"] or 0) >= 5 and r["_principles"] >= 8 and r["_pages"] >= 8
                and fnum(r.get("LPS_finbert")) is not None)

    solid = [r for r in rows if is_solid(r)]
    failed = [r for r in rows if (r["_ess"] or 0) == 0]
    partial = [r for r in rows if not is_solid(r) and (r["_ess"] or 0) > 0]

    w(f"  SOLID   : {len(solid)}")
    w(f"  PARTIAL : {len(partial)}")
    w(f"  FAILED  : {len(failed)}")
    w(f"  TOTAL   : {len(rows)}")
    w("")
    if partial or failed:
        w("  Every row that is not SOLID, with ess_pages and word_count:")
        for r in sorted(partial + failed,
                        key=lambda x: ((x["_ess"] or 0), x["_pages"])):
            tag = "FAILED " if (r["_ess"] or 0) == 0 else "PARTIAL"
            w(f"    {tag}  {r['company']:<32} {r['year']:<10} "
              f"ess_pages={r['_ess'] if r['_ess'] is not None else '?':<4} "
              f"principles={r['_principles']}/9  pages={r['_pages']:<3} "
              f"words={r['_words'] if r['_words'] is not None else '?'}")
        w("")
    sv = [fnum(r["LPS_finbert"]) for r in solid]
    if sv and fb_vals:
        w("  LPS_finbert   ALL rows (n=%d): min=%.4f max=%.4f mean=%.4f sd=%.4f"
          % (len(fb_vals), min(fb_vals), max(fb_vals),
             statistics.mean(fb_vals), statistics.pstdev(fb_vals)))
        w("  LPS_finbert SOLID rows (n=%d): min=%.4f max=%.4f mean=%.4f sd=%.4f"
          % (len(sv), min(sv), max(sv), statistics.mean(sv), statistics.pstdev(sv)))
        w("")
        ss = sorted(solid, key=lambda r: fnum(r["LPS_finbert"]), reverse=True)
        w("  5 HIGHEST (SOLID rows only):")
        for r in ss[:5]:
            w(f"    {fnum(r['LPS_finbert']):+.4f}  {r['company']:<32} {r['year']:<10} "
              f"pages={r['_pages']} words={r['_words']}")
        w("  5 LOWEST (SOLID rows only):")
        for r in ss[-5:]:
            w(f"    {fnum(r['LPS_finbert']):+.4f}  {r['company']:<32} {r['year']:<10} "
              f"pages={r['_pages']} words={r['_words']}")
    w("")
    w("  NOTE: LPS_scores.csv is unmodified by this script. brsr_pages,")
    w("  principles_found, ess_pages and word_count are all present in it, so any")
    w("  of these filters can be applied at analysis time.")
    w("")

    w("=" * 78)
    w("END OF VALIDATION SUMMARY")
    w("=" * 78)

    text = "\n".join(out)
    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nWritten to {SUMMARY_TXT}")


if __name__ == "__main__":
    main()
