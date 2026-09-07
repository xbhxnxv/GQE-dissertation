"""
GQE - Stage 4b. Significance tests on the event-study CARs (H2).

Produces the three things the supervisor asked for on top of the point
estimates: 95% confidence intervals, Cohen's d, and a high-minus-low portfolio
comparison. Nothing here is framed as a null: with n around 190 over two
reporting years the design can only detect medium or larger effects, so a
non-significant negative estimate is reported as underpowered.

Input  : event_study_CARs.csv
Output : console tables (Tables 2 and 3 of the Results chapter)
"""
import numpy as np
import pandas as pd
from scipy import stats

CARS = "event_study_CARs.csv"
MAIN_WINDOWS = ["CAR_m1_p1", "CAR_0_p5", "CAR_m5_p5", "CAR_m5_p20"]
SPLIT_WINDOWS = ["CAR_m1_p1", "CAR_m5_p5", "CAR_m5_p20"]
LABEL = {
    "CAR_m1_p1": "(-1,+1)",
    "CAR_0_p5": "(0,+5)",
    "CAR_m5_p5": "(-5,+5)",
    "CAR_m5_p20": "(-5,+20)",
}


def mean_car_table(df):
    print("Table 2. Mean CAR, market model vs NIFTY 500")
    print(f"{'window':<10}{'n':>5}{'mean CAR':>11}{'95% CI':>22}"
          f"{'t':>8}{'p':>8}{'d':>8}")
    for w in MAIN_WINDOWS:
        x = df[w].dropna()
        n = len(x)
        m = x.mean()
        sd = x.std(ddof=1)
        se = sd / np.sqrt(n)
        t, p = stats.ttest_1samp(x, 0.0)
        lo, hi = m - 1.96 * se, m + 1.96 * se
        d = m / sd
        ci = f"[{lo*100:+.2f}%, {hi*100:+.2f}%]"
        print(f"{LABEL[w]:<10}{n:>5}{m*100:>10.2f}%{ci:>22}"
              f"{t:>8.2f}{p:>8.3f}{d:>8.2f}")


def high_minus_low_table(df):
    """Median split on GDS; Welch t-test because the two groups differ in spread."""
    cut = df["GDS"].median()
    print("\nTable 3. High-GDS minus low-GDS portfolio CAR (median split)")
    print(f"{'window':<10}{'difference':>12}{'95% CI on difference':>26}"
          f"{'Welch t':>10}{'p':>8}")
    for w in SPLIT_WINDOWS:
        hi_g = df.loc[df["GDS"] > cut, w].dropna()
        lo_g = df.loc[df["GDS"] <= cut, w].dropna()
        diff = hi_g.mean() - lo_g.mean()
        se = np.sqrt(hi_g.var(ddof=1) / len(hi_g) + lo_g.var(ddof=1) / len(lo_g))
        t, p = stats.ttest_ind(hi_g, lo_g, equal_var=False)
        ci = f"[{(diff-1.96*se)*100:+.2f}%, {(diff+1.96*se)*100:+.2f}%]"
        print(f"{LABEL[w]:<10}{diff*100:>11.2f}%{ci:>26}{t:>10.2f}{p:>8.3f}")


def cross_sectional(df):
    """CAR regressed on GDS with size and leverage controls, HC3 robust SEs."""
    import statsmodels.api as sm
    print("\nCross-sectional regressions: CAR ~ GDS + log(mcap) + leverage")
    for w in MAIN_WINDOWS:
        d = df[[w, "GDS", "log_mcap", "leverage"]].dropna()
        X = sm.add_constant(d[["GDS", "log_mcap", "leverage"]])
        fit = sm.OLS(d[w], X).fit(cov_type="HC3")
        b = fit.params["GDS"]
        se = fit.bse["GDS"]
        print(f"  {LABEL[w]:<10} n={int(fit.nobs):>4}  b_GDS={b:+.5f}  "
              f"se={se:.5f}  t={b/se:+.2f}  p={fit.pvalues['GDS']:.3f}")


def main():
    df = pd.read_csv(CARS)
    print(f"company-years in event study: {len(df)}\n")
    mean_car_table(df)
    high_minus_low_table(df)
    try:
        cross_sectional(df)
    except ImportError:
        print("\n(statsmodels not available - skipping cross-sectional block)")


if __name__ == "__main__":
    main()
