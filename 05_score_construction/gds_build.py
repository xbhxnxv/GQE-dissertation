"""
GQE — GDS construction.
GDS = z(LPS) - z(OPS), computed WITHIN each fiscal year.

Run:  python3 gds_build.py <ops_tracker.xlsx> <LPS_scores.csv>
"""
import sys, re
import pandas as pd, numpy as np, openpyxl

# ---- OPS-tracker name  ->  LPS canonical name -------------------------------
# Only needed where the two files disagree. Extend as v4 introduces new names.
XWALK = {
    "TCS": "Tata Consultancy Services",
    "ITC": "ITC Ltd",
    "SBI": "State Bank of India",
    "IDFC First Bank": "IDFC First Bank",
    "Reliance Industries": "Reliance Industries",
    "Hindalco": "Hindalco Industries",
    "Grasim": "Grasim Industries",
    "UltraTech Cement": "UltraTech Cement",
    "Vedanta": "Vedanta Ltd",
    "NALCO": "National Aluminium Company",
    "IOC": "Indian Oil Corporation",
    "BPCL": "Bharat Petroleum",
    "Bajaj Finance": "Bajaj Finance",
    "Nestle India": "Nestle India",
    "Larsen & Toubro": "Larsen & Toubro",
    "Mahindra & Mahindra": "Mahindra & Mahindra",
    "LIC": "Life Insurance Corporation",
    "PNB": "Punjab National Bank",
    "ACC": "ACC Ltd",
    "Britannia": "Britannia Industries",
    "Dabur": "Dabur India",
    "Cipla": "Cipla",
    "Titan": "Titan Company",
    "Havells": "Havells India",
    "Marico": "Marico",
    "Emami": "Emami Ltd",
    "Biocon": "Biocon",
    "Lupin": "Lupin",
    "CDSL": "Central Depository Services",
    "BSE Ltd": "BSE Ltd",
    "Coal India": "Coal India",
    "Pidilite": "Pidilite Industries",
    "Shree Cement": "Shree Cement",
    "NMDC": "NMDC Ltd",
    "NTPC": "NTPC Ltd",
    "ONGC": "Oil & Natural Gas Corporation",
    "SAIL": "Steel Authority of India",
    "Wipro": "Wipro",
    "Infosys": "Infosys",
    # --- v4 additions, each verified by hand against LPS_scores.csv ---
    "Adani Green": "Adani Green Energy",
    "Alkem Labs": "Alkem Laboratories",
    "Cholamandalam": "Cholamandalam Finance",
    "Colgate India": "Colgate-Palmolive India",   # NOT Coal India
    "Divi's Labs": "Divi's Laboratories",
    "Dr Reddy's": "Dr Reddy's Laboratories",
    "Godrej Consumer": "Godrej Consumer Products",
    "HDFC Life": "HDFC Life Insurance",
    "ICICI Lombard": "ICICI Lombard General Insurance",   # NOT ICICI Bank
    "Jindal Steel": "Jindal Steel & Power",
    "LTTS": "L&T Technology Services",
    "Oracle Financial": "Oracle Financial Services",
    "Paytm": "Paytm (One 97 Communications)",
    "PolicyBazaar": "PB Fintech (PolicyBazaar)",
    "Power Grid": "Power Grid Corporation",
    "SBI Life": "SBI Life Insurance",
    "Sun Pharma": "Sun Pharmaceutical",
    "TVS Motor": "TVS Motor Company",
    "Tata Consumer": "Tata Consumer Products",
    "Torrent Pharma": "Torrent Pharmaceuticals",
    "Vedanta Limited": "Vedanta Ltd",
    # NO LPS ROW EXISTS — left unmapped deliberately, will report as unmatched:
    #   "IDFC First Bank"  -> absent from LPS
    #   "Tata Motors"      -> absent from LPS (do NOT map to Tata Power)
}

YEAR_FIX = {"FY 2022-23": "FY2022-23", "FY 2023-24": "FY2023-24"}

# OPS component columns in the tracker (E..L), by position
OPS_COLS = ["scope1", "scope12", "energy", "renew_energy",
            "renew_pct", "women_dir", "women_emp", "controversies"]
# Higher value = WORSE environmental performance -> invert before combining
INVERT = {"scope1", "scope12", "energy", "controversies"}


def read_tracker(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["OPS Data Tracker"] if "OPS Data Tracker" in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = []
    for r in range(1, ws.max_row + 1):
        co = ws.cell(r, 1).value
        yr = ws.cell(r, 4).value
        if not co or not isinstance(co, str) or not yr:
            continue
        if not re.search(r"20\d\d", str(yr)):
            continue
        rec = {"company_ops": co.strip(),
               "year": YEAR_FIX.get(str(yr).strip(), str(yr).strip())}
        for i, name in enumerate(OPS_COLS):
            v = ws.cell(r, 5 + i).value
            rec[name] = pd.to_numeric(v, errors="coerce") if v not in (None, "") else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def z(s):
    s = pd.to_numeric(s, errors="coerce")
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and sd > 0 else s * 0.0


def build_ops(df):
    """Equal-weighted mean of available z-scored components, within year."""
    out = []
    for yr, g in df.groupby("year"):
        g = g.copy()
        parts = []
        for c in OPS_COLS:
            if g[c].notna().sum() < 3:      # too sparse to standardise
                continue
            zc = z(g[c])
            if c in INVERT:
                zc = -zc
            g["_z_" + c] = zc
            parts.append("_z_" + c)
        g["ops_n_fields"] = g[parts].notna().sum(axis=1) if parts else 0
        g["OPS"] = g[parts].mean(axis=1, skipna=True) if parts else np.nan
        out.append(g)
    return pd.concat(out, ignore_index=True)


def main(ops_path, lps_path):
    ops = read_tracker(ops_path)
    ops["company"] = ops.company_ops.map(lambda x: XWALK.get(x, x))
    ops = build_ops(ops)

    lps = pd.read_csv(lps_path)
    for c in ["ess_pages", "principles_found", "brsr_pages"]:
        lps[c] = pd.to_numeric(lps[c], errors="coerce").fillna(0)
    lps["solid"] = (lps.ess_pages >= 5) & (lps.principles_found >= 8) & (lps.brsr_pages >= 8)
    # Documented exception: a BRSR that is substantive on every independent
    # quality measure but misses the principle-count bar due to header-detection
    # (principle headers not matched by the regex) is readmitted. Specified on
    # extraction-quality grounds, not on results. Affects 1 row: Tata Steel FY2022-23
    # (ess=18, pages=42, words=21,847 — all above the SOLID median of 15/27/13,108).
    lps.loc[(lps.ess_pages >= 10) & (lps.principles_found >= 7)
            & (lps.brsr_pages >= 15) & (lps.word_count >= 15000), "solid"] = True

    m = ops.merge(lps[["company", "year", "LPS_finbert", "LPS_climatebert",
                       "LPS_lm", "solid"]],
                  on=["company", "year"], how="inner")

    print(f"OPS rows={len(ops)}  LPS rows={len(lps)}  MERGED={len(m)}")
    unmatched = sorted(set(ops.company) - set(lps.company))
    if unmatched:
        print(f"\nUNMATCHED OPS companies ({len(unmatched)}) — add to XWALK:")
        for u in unmatched:
            print("  ", u)

    m = m[m.solid].copy()
    print(f"After SOLID filter: {len(m)}")

    res = []
    for yr, g in m.groupby("year"):
        g = g.copy()
        g["zLPS"] = z(g.LPS_finbert)
        g["zOPS"] = z(g.OPS)
        g["GDS"] = g.zLPS - g.zOPS
        res.append(g)
    out = pd.concat(res, ignore_index=True)

    out.to_csv("GDS_scores.csv", index=False)
    print("\n=== GDS by year ===")
    print(out.groupby("year").GDS.agg(["count", "mean", "std", "min", "max"]).round(4))
    print("\nTop 10 GDS (highest greenwashing signal):")
    print(out.nlargest(10, "GDS")[["company", "year", "LPS_finbert", "OPS", "GDS"]].round(4).to_string(index=False))
    print("\nWritten: GDS_scores.csv")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
