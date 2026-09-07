"""
GQE - Stage 8. What actually drives the greenwashing score?

GDS is a constructed measure, so before interpreting it, it is worth asking what
information it is really carrying. Three models are fitted on the same feature
set - LASSO for a sparse linear read, Random Forest and XGBoost for non-linear
structure - and SHAP values are computed on the gradient-boosted model to
attribute each prediction to its inputs.

This is diagnostic, not predictive. Nothing here is a forecast; the models exist
to answer "if GDS is high, which inputs put it there?"

Features: log Scope 1+2 emissions, firm size, leverage, and the 8 LDA topic
shares. Emissions is included deliberately even though it feeds OPS - the point
of the exercise is to show HOW MUCH of the score is emissions.

Inputs : GDS_FINAL.csv, GDS_scores.csv, _analysis_panel.csv, topic_assignments.csv
Output : shap_importance.csv, shap_gds_drivers.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LassoCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import shap

GDS = "GDS_FINAL.csv"
SCORES = "GDS_scores.csv"
PANEL = "_analysis_panel.csv"
ASSIGN = "topic_assignments.csv"
OUT_CSV = "shap_importance.csv"
OUT_PNG = "shap_gds_drivers.png"
SEED = 42

TOPIC_NAMES = {
    "topic_0_share": "Workforce",
    "topic_1_share": "Customers/data",
    "topic_2_share": "Waste/packaging",
    "topic_3_share": "Energy/water/emis",
    "topic_4_share": "Public policy",
    "topic_5_share": "Health&safety",
    "topic_6_share": "Ethics/anti-corr",
    "topic_7_share": "Stakeholder/comm",
}


def build_design():
    g = pd.read_csv(GDS)
    s = pd.read_csv(SCORES)
    p = pd.read_csv(PANEL)[["company", "year", "log_market_cap", "leverage"]]
    a = pd.read_csv(ASSIGN)

    xmap = dict(zip(s["company"], s["company_ops"]))
    a["company"] = a["company"].map(lambda c: xmap.get(c, c))

    em = s[["company_ops", "year", "scope12"]].rename(columns={"company_ops": "company"})
    d = (g.merge(em, on=["company", "year"], how="left")
           .merge(p, on=["company", "year"], how="left")
           .merge(a[["company", "year"] + list(TOPIC_NAMES)],
                  on=["company", "year"], how="left"))

    d["Emissions (log)"] = np.log1p(d["scope12"])
    d = d.rename(columns={"log_market_cap": "Firm size (log mcap)",
                          "leverage": "Leverage", **TOPIC_NAMES})
    feats = (["Emissions (log)", "Firm size (log mcap)", "Leverage"]
             + list(TOPIC_NAMES.values()))
    d = d.dropna(subset=feats + ["GDS"])
    return d[feats], d["GDS"], feats


def main():
    X, y, feats = build_design()
    print(f"design matrix: {X.shape[0]} company-years x {X.shape[1]} features")
    cv = KFold(5, shuffle=True, random_state=SEED)

    # ---- LASSO -------------------------------------------------------------
    Xs = StandardScaler().fit_transform(X)
    lasso = LassoCV(cv=cv, random_state=SEED, max_iter=20000).fit(Xs, y)
    print(f"\nLASSO   alpha={lasso.alpha_:.4f}  "
          f"R2(cv)={cross_val_score(lasso, Xs, y, cv=cv).mean():.3f}")
    for f, c in sorted(zip(feats, lasso.coef_), key=lambda t: -abs(t[1])):
        if abs(c) > 1e-8:
            print(f"    {f:<24}{c:+.4f}")

    # ---- Random Forest -----------------------------------------------------
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=3,
                               random_state=SEED, n_jobs=-1).fit(X, y)
    print(f"\nRandom Forest  R2(cv)={cross_val_score(rf, X, y, cv=cv).mean():.3f}")

    # ---- XGBoost + SHAP ----------------------------------------------------
    gbm = xgb.XGBRegressor(n_estimators=400, max_depth=3, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8,
                           random_state=SEED).fit(X, y)
    print(f"XGBoost        R2(cv)={cross_val_score(gbm, X, y, cv=cv).mean():.3f}")

    sv = shap.TreeExplainer(gbm).shap_values(X)
    imp = (pd.DataFrame({"feature": feats,
                         "mean_abs_shap": np.abs(sv).mean(axis=0)})
             .sort_values("mean_abs_shap", ascending=False))
    imp.to_csv(OUT_CSV, index=False)
    print("\nSHAP mean |value| (higher = more influence on GDS):")
    print(imp.to_string(index=False))

    shap.summary_plot(sv, X, show=False, max_display=len(feats))
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    print(f"\nwritten: {OUT_CSV}, {OUT_PNG}")


if __name__ == "__main__":
    main()
