"""US baseline: merge Eloundou exposure with BLS OEWS employment + wages.

This runs end-to-end on data bundled in / fetched from the OpenAI repo, with no
Spanish microdata required. It validates the whole analytical pipeline (merge ->
employment-weighted exposure share -> wage-exposure gradient -> figure) and gives
us the US benchmark that the Spanish results will be compared against.

Run:  python -m scripts.run_us_baseline
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

from src import config
from src.data_loading import load_eloundou


def load_oews() -> pd.DataFrame:
    df = pd.read_csv(config.DATA_EXTERNAL / "national_May2021_dl.csv",
                     dtype=str, encoding="utf-8-sig")
    df = df[df["O_GROUP"] == "detailed"].copy()      # detailed SOC rows only
    df["soc6"] = df["OCC_CODE"].str.strip()
    for c in ("TOT_EMP", "A_MEAN"):
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False),
                              errors="coerce")        # '*','#' -> NaN
    return (df[["soc6", "TOT_EMP", "A_MEAN"]]
            .rename(columns={"TOT_EMP": "employment", "A_MEAN": "mean_wage"})
            .dropna())


def main() -> None:
    exposure = load_eloundou()                  # [soc6, exposure], human_rating_beta
    oews = load_oews()
    panel = exposure.merge(oews, on="soc6", how="inner")
    panel["employment_share"] = panel["employment"] / panel["employment"].sum()
    panel["log_wage"] = np.log(panel["mean_wage"])

    matched = len(panel)
    hi = panel["exposure"] >= 0.5
    share_hi = panel.loc[hi, "employment_share"].sum()

    model = smf.wls("exposure ~ log_wage", data=panel,
                    weights=panel["employment"]).fit(cov_type="HC1")
    slope, p = model.params["log_wage"], model.pvalues["log_wage"]

    print(f"Matched occupations:                    {matched}")
    print(f"Total employment covered:               {panel['employment'].sum():,.0f}")
    print(f"Mean exposure (employment-weighted):    "
          f"{np.average(panel['exposure'], weights=panel['employment']):.3f}")
    print(f"Share of US employment >=0.5 exposure:  {share_hi:.1%}")
    print(f"Wage-exposure gradient (d exposure / d log wage): "
          f"{slope:+.3f}  (p={p:.1e})")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(panel["mean_wage"], panel["exposure"],
               s=panel["employment_share"] * 6000, alpha=0.45, edgecolor="none")
    xs = np.linspace(panel["mean_wage"].min(), panel["mean_wage"].max(), 100)
    ax.plot(xs, model.params["Intercept"] + slope * np.log(xs),
            color="crimson", lw=2, label=f"slope={slope:+.2f} (p={p:.0e})")
    ax.set_xlabel("Mean annual wage (USD)")
    ax.set_ylabel("AI exposure (Eloundou human β)")
    ax.set_title("US: AI exposure rises with wages (baseline)")
    ax.legend()
    fig.tight_layout()
    out = config.FIGURES / "wage_vs_exposure_US.png"
    fig.savefig(out, dpi=150)
    print(f"Figure written: {out}")


if __name__ == "__main__":
    main()
