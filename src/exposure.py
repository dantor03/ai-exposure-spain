"""Build the Spanish exposure dataset and run the headline analysis.

Headline question (the one Massenkoff / McCrory will care about):
    In the US, AI exposure rises with wages (high-skill bias). Does the same
    hold in Spain's more services/tourism-weighted labour market, or is the
    gradient flatter / differently shaped?
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from . import config


def build_panel(
    exposure_cno: pd.DataFrame,   # [cno2, exposure]
    epa: pd.DataFrame,            # person-level EPA, has cno2 + weight (+ covariates)
    earnings: pd.DataFrame,       # [cno2, mean_wage]
) -> pd.DataFrame:
    """Collapse EPA to occupation level and merge exposure + wages."""
    emp = (
        epa.dropna(subset=["cno2"])
        .groupby("cno2")
        .agg(employment=("weight", "sum"))
        .reset_index()
    )
    panel = (
        emp.merge(exposure_cno, on="cno2", how="left")
        .merge(earnings, on="cno2", how="left")
    )
    panel["employment_share"] = panel["employment"] / panel["employment"].sum()
    panel["log_wage"] = np.log(panel["mean_wage"])
    return panel


def share_of_workforce_exposed(panel: pd.DataFrame, threshold: float = 0.5) -> float:
    """Employment-weighted share of workers in high-exposure occupations."""
    hi = panel["exposure"] >= threshold
    return float(panel.loc[hi, "employment_share"].sum())


def wage_exposure_gradient(panel: pd.DataFrame) -> "smf.ols":
    """Regress occupation exposure on log wage (employment-weighted).

    A positive, significant slope => US-style high-skill-biased exposure.
    """
    model = smf.wls(
        "exposure ~ log_wage",
        data=panel.dropna(subset=["exposure", "log_wage"]),
        weights=panel.dropna(subset=["exposure", "log_wage"])["employment"],
    ).fit(cov_type="HC1")
    return model


if __name__ == "__main__":
    print("Run via notebooks/02_eda_and_exposure and 03_econometric_models, "
          "or import these functions. This module has no side effects on import.")
