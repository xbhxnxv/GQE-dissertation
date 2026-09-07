"""
GQE - Stage 3b. Descriptive statistics (Results chapter Table 1).

LPS and OPS are reported RAW. Standardisation is applied only when the GDS is
constructed, which is why GDS is the only row with a mean of zero. An earlier
caption described all three as standardised; that was wrong and is corrected
here.

Input  : GDS_FINAL.csv
Output : descriptive_stats.csv, console table
"""
import pandas as pd

GDS = "GDS_FINAL.csv"
OUT = "descriptive_stats.csv"
VARS = [("LPS_finbert", "LPS (FinBERT)", "raw"),
        ("OPS", "OPS", "raw"),
        ("GDS", "GDS", "standardised")]


def main():
    d = pd.read_csv(GDS)
    rows = []
    for col, label, scale in VARS:
        for year, g in d.groupby("year"):
            x = g[col].dropna()
            rows.append({
                "variable": label, "scale": scale, "year": year, "n": len(x),
                "mean": round(x.mean(), 4), "sd": round(x.std(ddof=1), 4),
                "min": round(x.min(), 4), "p25": round(x.quantile(.25), 4),
                "median": round(x.median(), 4), "p75": round(x.quantile(.75), 4),
                "max": round(x.max(), 4),
            })
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False)
    print(t.to_string(index=False))
    print(f"\ncompany-years: {len(d)}   companies: {d['company'].nunique()}")
    paired = d.groupby("company")["year"].nunique().eq(2).sum()
    print(f"companies with both years (paired sample for H1): {paired}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
