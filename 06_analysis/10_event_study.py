"""
GQE - Stage 4a. Event study: market-model abnormal returns around BRSR disclosure.

Benchmark is the NIFTY 500, not the NIFTY 100, because 99 of the 100 sample
firms are NIFTY 100 constituents; regressing a constituent on an index it helps
constitute biases beta upward and shrinks the residual the study is trying to
measure.

Estimation window : 250 trading days ending 11 days before the event
                    (t-260 .. t-11), minimum 100 usable observations.
Event windows     : (0,0), (-1,+1), (0,+1), (0,+5), (-5,+5), (-5,+20)
Model             : R_it = alpha_i + beta_i * R_mt + e_it   (OLS, per firm-event)
Abnormal return   : AR_it = R_it - (alpha_i + beta_i * R_mt)
CAR               : sum of AR over the window

Inputs : stock_prices.csv, nifty500_benchmark.csv, disclosure_dates.csv,
         GDS_FINAL.csv, firm_financials.csv, _company_universe.csv
Output : event_study_CARs.csv
"""
import numpy as np
import pandas as pd

PRICES = "stock_prices.csv"
BENCH = "nifty500_benchmark.csv"
DATES = "disclosure_dates.csv"
GDS = "GDS_FINAL.csv"
FIN = "firm_financials.csv"
UNIVERSE = "_company_universe.csv"
OUT = "event_study_CARs.csv"

EST_START, EST_END = -260, -11   # trading days relative to the event day
MIN_EST_OBS = 100

WINDOWS = {
    "AR_0":       (0, 0),
    "CAR_m1_p1":  (-1, 1),
    "CAR_0_p1":   (0, 1),
    "CAR_0_p5":   (0, 5),
    "CAR_m5_p5":  (-5, 5),
    "CAR_m5_p20": (-5, 20),
}


def load():
    px = pd.read_csv(PRICES, parse_dates=["date"])
    bm = pd.read_csv(BENCH, parse_dates=["date"])
    bm = bm[["date", "daily_return"]].rename(columns={"daily_return": "mkt_return"})
    ev = pd.read_csv(DATES, parse_dates=["event_date"])
    gds = pd.read_csv(GDS)
    fin = pd.read_csv(FIN)
    uni = pd.read_csv(UNIVERSE)
    return px, bm, ev, gds, fin, uni


def market_model(firm_panel, t0):
    """Fit R_i = a + b*R_m on the estimation window ending 11 days pre-event."""
    lo = max(0, t0 + EST_START)
    hi = t0 + EST_END
    est = firm_panel.iloc[lo:hi + 1].dropna(subset=["daily_return", "mkt_return"])
    if len(est) < MIN_EST_OBS:
        return None, None, len(est)
    beta, alpha = np.polyfit(est["mkt_return"], est["daily_return"], 1)
    return alpha, beta, len(est)


def main():
    px, bm, ev, gds, fin, uni = load()

    # one event per company-year; keep only company-years that carry a GDS score
    ev = ev.merge(gds[["company", "year", "GDS"]], on=["company", "year"], how="inner")
    ev = ev.dropna(subset=["event_date"]).sort_values(["company", "year"])

    rows = []
    skipped = []

    for company, ev_firm in ev.groupby("company"):
        panel = px[px["company"] == company].sort_values("date").reset_index(drop=True)
        if panel.empty:
            skipped.append((company, "no price series"))
            continue
        panel = panel.merge(bm, on="date", how="left")

        for _, e in ev_firm.iterrows():
            # day 0 = first trading day on or after the disclosure date
            after = panel.index[panel["date"] >= e["event_date"]]
            if len(after) == 0:
                skipped.append((company, f"{e['year']} event after price history"))
                continue
            t0 = int(after[0])

            alpha, beta, n_est = market_model(panel, t0)
            if alpha is None:
                skipped.append((company, f"{e['year']} estimation window {n_est} obs"))
                continue

            ab = panel["daily_return"] - (alpha + beta * panel["mkt_return"])

            rec = {
                "company": company,
                "year": e["year"],
                "event_date": e["event_date"].date(),
                "GDS": e["GDS"],
                "alpha": alpha,
                "beta": beta,
                "n_est": n_est,
            }
            for name, (a, b) in WINDOWS.items():
                lo, hi = t0 + a, t0 + b
                if lo < 0 or hi >= len(panel):
                    rec[name] = np.nan
                else:
                    rec[name] = ab.iloc[lo:hi + 1].sum()
            rows.append(rec)

    car = pd.DataFrame(rows)

    # attach the controls used by the cross-sectional regressions
    car = car.merge(fin[["company", "year", "log_market_cap", "leverage"]],
                    on=["company", "year"], how="left")
    car = car.rename(columns={"log_market_cap": "log_mcap"})
    car = car.merge(uni[["company", "sector"]], on="company", how="left")

    keep = (["company", "year", "event_date", "GDS"] + list(WINDOWS)
            + ["log_mcap", "leverage", "sector"])
    car[keep].to_csv(OUT, index=False)

    print(f"events with usable CARs : {len(car)}")
    print(f"events skipped          : {len(skipped)}")
    for c, why in skipped:
        print(f"   {c:<34} {why}")
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
