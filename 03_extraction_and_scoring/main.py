"""
End-to-end LPS pipeline: extract BRSR sections from local PDFs, score them with
FinBERT / ClimateBERT / Loughran-McDonald, and write LPS_scores.csv.

Resumable: re-running skips (company, year) rows already present in the output CSV.
"""
import os
import sys
import time
import csv
from collections import defaultdict

from company_mapping import match_company, parse_fiscal_year
from extract_brsr import extract_brsr_section
from score import load_finbert, load_climatebert, score_lm, chunk_text

DATASET_DIR = r"C:\Users\ASUS\Desktop\me\Dissertation\dataset"
OUTPUT_CSV = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_scores.csv"
LOG_PATH = r"C:\Users\ASUS\Desktop\me\Dissertation\LPS_pipeline\run_log.txt"
FIELDNAMES = ["company", "year", "LPS_finbert", "LPS_climatebert", "LPS_lm",
              "brsr_pages", "principles_found", "ess_pages", "word_count", "source_file"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def build_targets():
    files = [f for f in os.listdir(DATASET_DIR) if f.lower().endswith(".pdf")]
    groups = defaultdict(list)
    unmatched, skipped_year = [], []
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
    return groups, unmatched, skipped_year


def load_done_rows():
    done = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                done.add((row["company"], row["year"]))
    return done


def pick_best_candidate(company, fy, candidates):
    """If multiple files map to the same (company, fy), extract all and keep the richest."""
    best = None
    for fname in candidates:
        path = os.path.join(DATASET_DIR, fname)
        try:
            result = extract_brsr_section(path)
        except Exception as e:
            log(f"  WARN extraction failed for {fname}: {e}")
            continue
        # prefer the candidate with real BRSR-form content, not just principle mentions
        n_principles = len(result["principles_found"])
        score = (result.get("ess_pages", 0), n_principles, result["num_pages"])
        if best is None or score > best[0]:
            best = (score, fname, result)
    if best is None:
        return None, None
    _, fname, result = best
    if len(candidates) > 1:
        dropped = [c for c in candidates if c != fname]
        log(f"  duplicate files for {company} {fy}: kept {fname}, dropped {dropped}")
    return fname, result


def main():
    open(LOG_PATH, "a").close()
    log("=== LPS pipeline run started ===")

    groups, unmatched, skipped_year = build_targets()
    log(f"Found {sum(len(v) for v in groups.values())} candidate files across {len(groups)} (company, year) targets")
    if unmatched:
        log(f"Unmatched company filenames ({len(unmatched)}): {unmatched}")
    if skipped_year:
        log(f"Skipped filenames with no valid FY22-23/23-24 year ({len(skipped_year)}): {skipped_year}")

    done = load_done_rows()
    log(f"{len(done)} rows already in {OUTPUT_CSV}, will skip those")

    log("Loading FinBERT...")
    finbert = load_finbert()
    log("FinBERT loaded.")

    climatebert = None
    try:
        log("Loading ClimateBERT...")
        climatebert = load_climatebert()
        log("ClimateBERT loaded.")
    except Exception as e:
        log(f"ClimateBERT failed to load, will skip it and continue with FinBERT + LM only: {e}")

    write_header = not os.path.exists(OUTPUT_CSV)
    out_f = open(OUTPUT_CSV, "a", encoding="utf-8", newline="")
    writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()
        out_f.flush()

    targets = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    total = len(targets)
    no_brsr_found = []
    failed = []

    for idx, ((company, fy), candidates) in enumerate(targets, 1):
        if (company, fy) in done:
            continue

        fname, result = pick_best_candidate(company, fy, candidates)
        if result is None:
            log(f"[{idx}/{total}] {company} {fy}: ALL candidates failed extraction")
            failed.append((company, fy))
            continue

        if not result["text"].strip():
            log(f"[{idx}/{total}] {company} {fy}: no BRSR content found in {fname} (total_pages={result['total_pages']})")
            no_brsr_found.append((company, fy))
            continue

        chunks = chunk_text(result["text"])
        t0 = time.time()
        try:
            lps_finbert = finbert.score_chunks(chunks)
        except Exception as e:
            log(f"  FinBERT scoring failed for {company} {fy}: {e}")
            lps_finbert = None

        lps_climatebert = None
        if climatebert is not None:
            try:
                lps_climatebert = climatebert.score_chunks(chunks)
            except Exception as e:
                log(f"  ClimateBERT scoring failed for {company} {fy}: {e}")

        try:
            lps_lm = score_lm(result["text"])
        except Exception as e:
            log(f"  LM scoring failed for {company} {fy}: {e}")
            lps_lm = None

        dt = time.time() - t0
        row = {
            "company": company,
            "year": fy,
            "LPS_finbert": lps_finbert,
            "LPS_climatebert": lps_climatebert,
            "LPS_lm": lps_lm,
            "brsr_pages": result["num_pages"],
            "principles_found": len(result["principles_found"]),
            "ess_pages": result.get("ess_pages", 0),
            "word_count": len(result["text"].split()),
            "source_file": fname,
        }
        writer.writerow(row)
        out_f.flush()

        fb_str = f"{lps_finbert:.4f}" if lps_finbert is not None else "NA"
        cb_str = f"{lps_climatebert:.4f}" if lps_climatebert is not None else "NA"
        lm_str = f"{lps_lm:.4f}" if lps_lm is not None else "NA"
        log(f"[{idx}/{total}] {company} {fy}: finbert={fb_str} climatebert={cb_str} lm={lm_str} "
            f"({result['num_pages']}pg, {len(result['principles_found'])}/9 principles, {len(chunks)} chunks, {dt:.1f}s)")

    out_f.close()
    log("=== Pipeline run complete ===")
    if no_brsr_found:
        log(f"No BRSR content found for {len(no_brsr_found)} targets: {no_brsr_found}")
    if failed:
        log(f"Extraction failed entirely for {len(failed)} targets: {failed}")
    log(f"Results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
