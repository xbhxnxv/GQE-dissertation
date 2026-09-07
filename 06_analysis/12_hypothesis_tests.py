"""
GQE - Stage 5. Hypothesis tests H1 and H3, plus the pooled panel regression.

H1  Did disclosure-performance divergence change between FY2022-23 and FY2023-24?
H2  Do higher-GDS firms earn more negative abnormal returns? (11_event_study_tests.py)
H3  Does divergence concentrate in particular sectors?

IMPORTANT CONSTRUCTION NOTE FOR H1
GDS is built from z-scores taken WITHIN each fiscal year, so both years have a
mean of exactly zero by construction. Comparing GDS levels across years is
therefore meaningless - it can only ever return zero. H1 is tested on the raw
components instead: the FinBERT LPS and the raw OPS composite, neither of which
is re-centred each year. The paired sample is the companies with both years.

Inputs : GDS_FINAL.csv, GDS_scores.csv, _analysis_panel.csv
Output : console tables
"""
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

GDS = "GDS_FINAL.csv"
SCORES = "GDS_scores.csv"
PANEL = "_analysis_panel.csv"


def h1_language_change():
    s = pd.read_csv(SCORES)
    wide = s.pivot_table(index="company", columns="year",
                         values=["LPS_finbert", "OPS"], aggfunc="first")
    paired = wide.dropna()
    n = len(paired)
    print("H1  Change between the two mandatory BRSR years")
    print(f"    paired companies (both years): {n}")

    for var in ["LPS_finbert", "OPS"]:
        a = paired[(var, "FY2022-23")]
        b = paired[(var, "FY2023-24")]
        d = b - a
        t, p = stats.ttest_rel(b, a)
        w, pw = stats.wilcoxon(b, a)
        se = d.std(ddof=1) / np.sqrt(n)
        print(f"    {var:<12} FY22-23 mean={a.mean():+.4f}   FY23-24 mean={b.mean():+.4f}")
        print(f"    {'':<12} mean change={d.mean():+.4f}   "
              f"95% CI [{d.mean()-1.96*se:+.4f}, {d.mean()+1.96*se:+.4f}]")
        print(f"    {'':<12} paired t={t:+.2f} p={p:.3f} | Wilcoxon p={pw:.3f} | "
              f"Cohen dz={d.mean()/d.std(ddof=1):+.3f}")

    g = pd.read_csv(GDS)
    print("\n    GDS level by year (zero by construction - NOT a testable quantity):")
    print(g.groupby("year")["GDS"].agg(["count", "mean", "std"]).round(4).to_string())


def h3_sector():
    g = pd.read_csv(GDS)
    p = pd.read_csv(PANEL)[["company", "year", "sector"]]
    m = g.merge(p, on=["company", "year"], how="left").dropna(subset=["sector"])

    groups = [v["GDS"].values for _, v in m.groupby("sector") if len(v) >= 3]
    f, pf = stats.f_oneway(*groups)
    h, ph = stats.kruskal(*groups)
    total_ss = ((m["GDS"] - m["GDS"].mean()) ** 2).sum()
    within_ss = sum(((v["GDS"] - v["GDS"].mean()) ** 2).sum()
                    for _, v in m.groupby("sector"))
    eta2 = 1 - within_ss / total_ss

    print("\nH3  Sector concentration of divergence")
    print(f"    sectors with n>=3 : {len(groups)}    company-years: {len(m)}")
    print(f"    one-way ANOVA   F={f:.2f}  p={pf:.2e}")
    print(f"    Kruskal-Wallis  H={h:.2f}  p={ph:.2e}")
    print(f"    eta-squared     ={eta2:.3f}  "
          f"({eta2*100:.1f}% of GDS variance sits between sectors)")
    print("\n    Sector means (descending):")
    tab = (m.groupby("sector")["GDS"].agg(["count", "mean", "std"])
             .sort_values("mean", ascending=False).round(3))
    print(tab.to_string())


def pooled_regression():
    """
    Pooled OLS with year and sector fixed effects and HC3 robust standard errors.
    Not firm fixed effects: with two observations per firm and a within-year
    standardised outcome, firm dummies absorb almost all usable variation.
    """
    g = pd.read_csv(GDS)
    p = pd.read_csv(PANEL)[["company", "year", "sector", "log_market_cap", "leverage"]]
    m = g.merge(p, on=["company", "year"], how="left").dropna(
        subset=["GDS", "log_market_cap", "leverage", "sector"])

    X = pd.get_dummies(m[["sector", "year"]], drop_first=True).astype(float)
    X["log_market_cap"] = m["log_market_cap"].values
    X["leverage"] = m["leverage"].values
    X = sm.add_constant(X)
    fit = sm.OLS(m["GDS"].values, X).fit(cov_type="HC3")

    print("\nPooled OLS: GDS ~ size + leverage + sector FE + year FE (HC3 robust SE)")
    print(f"    n={int(fit.nobs)}   R2={fit.rsquared:.3f}   adj R2={fit.rsquared_adj:.3f}")
    for v in ["log_market_cap", "leverage"]:
        print(f"    {v:<16} b={fit.params[v]:+.4f}  se={fit.bse[v]:.4f}  "
              f"t={fit.tvalues[v]:+.2f}  p={fit.pvalues[v]:.3f}")


if __name__ == "__main__":
    h1_language_change()
    h3_sector()
    pooled_regression()
