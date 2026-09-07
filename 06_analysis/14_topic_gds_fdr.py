"""
GQE - Stage 6b. Topic-GDS associations and Benjamini-Hochberg FDR correction.

Sixteen tests are run: each of the 8 LDA themes against GDS, and each against
the operational component zOPS. Running sixteen tests and reporting the
significant ones without adjustment would manufacture findings, so a
Benjamini-Hochberg false discovery rate correction is applied across the whole
family. Bonferroni is reported alongside as the conservative bound.

Inputs : topic_assignments.csv, GDS_FINAL.csv, GDS_scores.csv
Output : topic_gds_correlations.csv, console FDR table
"""
import numpy as np
import pandas as pd
from scipy import stats

ASSIGN = "topic_assignments.csv"
GDS = "GDS_FINAL.csv"
SCORES = "GDS_scores.csv"       # supplies the LPS-name -> tracker-name crosswalk
OUT = "topic_gds_correlations.csv"

TOPIC_LABELS = {
    0: "Workforce/wages/rights",
    1: "Customers/product/data",
    2: "Waste/packaging/circularity",
    3: "Energy/water/emissions",
    4: "Public policy advocacy",
    5: "Health & safety",
    6: "Ethics/anti-corruption",
    7: "Stakeholder/community",
}


def benjamini_hochberg(pvals):
    """Return BH-adjusted p-values (step-up, monotone-enforced)."""
    p = np.asarray(pvals, dtype=float)
    n = p.size
    order = np.argsort(p)
    adj = p[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out


def main():
    a = pd.read_csv(ASSIGN)
    g = pd.read_csv(GDS)

    # topic_assignments carries LPS-canonical company names; GDS_FINAL carries
    # the OPS-tracker names. Joining them naively silently drops ~40% of rows,
    # so the crosswalk that gds_build.py already resolved is reused here rather
    # than matched again.
    xw = pd.read_csv(SCORES)[["company", "company_ops"]].drop_duplicates()
    xmap = dict(zip(xw["company"], xw["company_ops"]))
    a["company"] = a["company"].map(lambda c: xmap.get(c, c))

    m = a.merge(g, on=["company", "year"], how="inner")
    dropped = sorted(set(a["company"]) - set(g["company"]))
    print(f"company-years with both topic shares and a GDS: {len(m)}")
    if dropped:
        print(f"no GDS row for: {dropped}")

    rows = []
    for k, label in TOPIC_LABELS.items():
        col = f"topic_{k}_share"
        r_g, p_g = stats.pearsonr(m[col], m["GDS"])
        r_l, p_l = stats.pearsonr(m[col], m["zLPS"])
        r_o, p_o = stats.pearsonr(m[col], m["zOPS"])
        rows.append({"topic": k, "label": label,
                     "corr_GDS": round(r_g, 3), "p_GDS": round(p_g, 4),
                     "corr_zLPS": round(r_l, 3), "p_zLPS": round(p_l, 4),
                     "corr_zOPS": round(r_o, 3), "p_zOPS": round(p_o, 4)})
    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False)

    # ---- the family of 16: 8 themes x GDS, 8 themes x zOPS -------------------
    fam = ([(f"{r.label} x GDS", r.p_GDS) for r in res.itertuples()]
           + [(f"{r.label} x zOPS", r.p_zOPS) for r in res.itertuples()])
    names = [n for n, _ in fam]
    praw = np.array([p for _, p in fam])
    pfdr = benjamini_hochberg(praw)
    pbon = np.minimum(praw * len(praw), 1.0)

    print(f"\n{'test':<38}{'raw p':>10}{'FDR p':>10}{'Bonf p':>10}{'survives':>11}")
    order = np.argsort(praw)
    for i in order:
        verdict = "yes" if pfdr[i] < 0.05 else "no"
        print(f"{names[i]:<38}{praw[i]:>10.4f}{pfdr[i]:>10.4f}"
              f"{pbon[i]:>10.4f}{verdict:>11}")

    print(f"\nsurvive FDR (q<0.05)   : {(pfdr < 0.05).sum()} / {len(praw)}")
    print(f"survive Bonferroni     : {(pbon < 0.05).sum()} / {len(praw)}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
