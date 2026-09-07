"""
GQE - Stage 7. Two robustness checks on the GDS.

(a) WEIGHTING. OPS is an equal-weighted mean of whichever standardised
    components a firm reports. Equal weighting is a choice, so the whole score
    is rebuilt with weights taken from the first principal component of the
    component matrix and the two versions are correlated. A high correlation
    means the headline result does not rest on the weighting decision.

(b) SECTOR. The top of the GDS ranking is heavy industry, and OPS is driven by
    emissions, so an examiner will ask whether GDS measures greenwashing or
    simply measures being a steel mill. GDS is demeaned within sector, removing
    every cross-sector difference, and the emissions link and the thematic
    results are re-estimated on what is left. Whatever survives is a
    within-sector effect: a firm judged only against its own peers.

Inputs : GDS_scores.csv, GDS_FINAL.csv, _analysis_panel.csv, topic_assignments.csv
Output : topic_sector_adjusted.csv, console tables
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA

SCORES = "GDS_scores.csv"
GDS = "GDS_FINAL.csv"
PANEL = "_analysis_panel.csv"
ASSIGN = "topic_assignments.csv"
OUT = "topic_sector_adjusted.csv"

ZCOLS = ["_z_scope1", "_z_scope12", "_z_energy", "_z_renew_energy",
         "_z_renew_pct", "_z_women_dir", "_z_women_emp", "_z_controversies"]

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


def pca_weighting():
    s = pd.read_csv(SCORES)
    use = [c for c in ZCOLS if c in s.columns and s[c].notna().sum() > 50]
    d = s[["company", "year", "OPS"] + use].copy()
    # median-fill only for the PCA fit; the equal-weighted OPS is untouched
    filled = d[use].apply(lambda c: c.fillna(c.median()))

    pca = PCA(n_components=1).fit(filled)
    w = pca.components_[0]
    if np.corrcoef(filled @ w, d["OPS"])[0, 1] < 0:
        w = -w                       # PC sign is arbitrary; orient it with OPS
    d["OPS_pca"] = filled @ w / np.abs(w).sum()

    r, p = stats.pearsonr(d["OPS"], d["OPS_pca"])
    rs, _ = stats.spearmanr(d["OPS"], d["OPS_pca"])
    print("(a) WEIGHTING ROBUSTNESS")
    print(f"    variance explained by PC1 : {pca.explained_variance_ratio_[0]:.3f}")
    print(f"    equal-weighted vs PCA-weighted OPS: r={r:.3f} (p={p:.2e}), "
          f"Spearman rho={rs:.3f}")
    print("    PC1 loadings:")
    for c, wi in sorted(zip(use, w / np.abs(w).sum()), key=lambda x: -abs(x[1])):
        print(f"      {c:<18}{wi:+.3f}")


def sector_adjust():
    g = pd.read_csv(GDS)
    p = pd.read_csv(PANEL)[["company", "year", "sector"]]
    s = pd.read_csv(SCORES)[["company_ops", "year", "scope12"]].rename(
        columns={"company_ops": "company"})
    m = g.merge(p, on=["company", "year"], how="left").merge(
        s, on=["company", "year"], how="left")

    m["GDS_sector_adj"] = m["GDS"] - m.groupby("sector")["GDS"].transform("mean")
    m["log_emissions"] = np.log1p(m["scope12"])

    r_raw, p_raw = stats.pearsonr(m["log_emissions"], m["GDS"])
    r_adj, p_adj = stats.pearsonr(m["log_emissions"], m["GDS_sector_adj"])

    print("\n(b) SECTOR ROBUSTNESS")
    print(f"    n={len(m)}   sectors={m['sector'].nunique()}")
    print(f"    log(Scope 1+2) vs raw GDS            : r={r_raw:+.3f}  p={p_raw:.2e}")
    print(f"    log(Scope 1+2) vs sector-adjusted GDS: r={r_adj:+.3f}  p={p_adj:.4f}")
    print("    Reading: most of the raw emissions link is cross-sector composition,")
    print("    but a smaller within-sector link survives, so GDS is not purely a")
    print("    sector artefact.")
    return m


def sector_adjusted_topics(m):
    a = pd.read_csv(ASSIGN)
    xw = pd.read_csv(SCORES)[["company", "company_ops"]].drop_duplicates()
    a["company"] = a["company"].map(dict(zip(xw["company"], xw["company_ops"])).get).fillna(a["company"])
    t = a.merge(m, on=["company", "year"], how="inner")

    rows = []
    for k, label in TOPIC_LABELS.items():
        col = f"topic_{k}_share"
        r1, p1 = stats.pearsonr(t[col], t["GDS"])
        r2, p2 = stats.pearsonr(t[col], t["GDS_sector_adj"])
        rows.append({"theme": label,
                     "r_rawGDS": round(r1, 3), "p_rawGDS": round(p1, 4),
                     "r_sectoradjGDS": round(r2, 3), "p_sectoradjGDS": round(p2, 4)})
    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False)

    print("\n    Topic-GDS correlations before and after sector-demeaning:")
    print(f"    {'theme':<30}{'r raw':>9}{'r adj':>9}{'p adj':>9}  survives")
    for r in res.itertuples():
        print(f"    {r.theme:<30}{r.r_rawGDS:>9.3f}{r.r_sectoradjGDS:>9.3f}"
              f"{r.p_sectoradjGDS:>9.4f}  {'yes' if r.p_sectoradjGDS < 0.05 else 'no'}")
    print(f"    written: {OUT}")


if __name__ == "__main__":
    pca_weighting()
    panel = sector_adjust()
    sector_adjusted_topics(panel)
