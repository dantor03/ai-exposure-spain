"""Spain pipeline: exposure (Eloundou, crosswalked) x EPA employment x EES wages.

Crosswalk chain:
    Eloundou SOC-2018 -> SOC-2010 -> ISCO-08 -> CNO-2011 (4-digit)
then aggregate to CNO 1-digit, the granularity the *public* EPA microdata exposes.

Run:  python -m scripts.run_spain
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyreadr
import pyreadstat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

from src import config
from src.crosswalk import collapse
from src.data_loading import load_eloundou

EXT = config.DATA_EXTERNAL
RAW = config.DATA_RAW

# EES letter groups (A-Q) -> CNO-2011 1-digit major group
EES_LETTER_TO_CNO1 = {
    "A": "1", "B": "2", "C": "2", "D": "3", "E": "4", "F": "4",
    "G": "5", "H": "5", "I": "5", "J": "6", "K": "7", "L": "7",
    "M": "8", "N": "8", "O": "9", "P": "9", "Q": "0",
}
CNO1_LABEL = {
    "0": "Military", "1": "Managers", "2": "Professionals", "3": "Technicians",
    "4": "Clerical", "5": "Services & sales", "6": "Skilled agric.",
    "7": "Craft & trades", "8": "Plant/machine operators", "9": "Elementary",
}


def build_exposure_cno1() -> pd.DataFrame:
    exposure = load_eloundou()                       # [soc6, exposure] SOC-2018

    soc18_10 = pd.read_excel(EXT / "soc_isco_crosswalk.xlsx", header=8,
                             dtype=str)               # BLS 2010<->2018
    soc18_10 = soc18_10.rename(columns={"2018 SOC Code": "soc6",
                                        "2010 SOC Code": "soc10"})[["soc6", "soc10"]]

    rda = pyreadr.read_r(str(EXT / "soc10_isco08.rda"))["soc10_isco08"]
    rda["soc10"] = rda["soc10"].astype(str).str.replace(r"^(\d{2})(\d{4})$", r"\1-\2",
                                                        regex=True)
    soc10_isco = rda[["soc10", "isco08"]].rename(columns={"isco08": "isco4"})

    isco_cno = pd.read_excel(EXT / "isco_cno_crosswalk.xls", sheet_name=0,
                             header=2, dtype=str)
    isco_cno = (isco_cno.rename(columns={"CIUO08": "isco4", "CNO11": "cno4"})
                .dropna(subset=["cno4"])[["isco4", "cno4"]])

    # Chain the hops, mean-collapsing each many-to-many step.
    at_soc10 = collapse(exposure, soc18_10, src_code="soc6", dst_code="soc10")
    at_isco = collapse(at_soc10, soc10_isco, src_code="soc10", dst_code="isco4")
    at_cno4 = collapse(at_isco, isco_cno, src_code="isco4", dst_code="cno4")

    at_cno4["cno1"] = at_cno4["cno4"].str.slice(0, 1)
    return (at_cno4.dropna(subset=["exposure"])
            .groupby("cno1", as_index=False)["exposure"].mean())


def load_epa_employment(fname: str = "EPA_2026T1.sav") -> pd.DataFrame:
    df, _ = pyreadstat.read_sav(str(RAW / fname), encoding="LATIN1",
                                usecols=["OCUP1", "AOI", "FACTOREL"])
    df["FACTOREL"] = pd.to_numeric(df["FACTOREL"], errors="coerce")  # weight is string in .sav
    emp = df[df["AOI"].isin(["03", "04"])].copy()     # occupied (main-job occupation in OCUP1)
    emp = emp[emp["OCUP1"].str.strip() != ""]
    return (emp.groupby(emp["OCUP1"].str.strip())["FACTOREL"].sum()
            .rename("employment").rename_axis("cno1").reset_index())


def _wq(values: np.ndarray, weights: np.ndarray, q: float = 0.5) -> float:
    """Weighted quantile."""
    o = np.argsort(values)
    v, w = values[o], weights[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= np.sum(w)
    return float(np.interp(q, cw, v))


def load_ees_microdata(fname: str = "EES_2022.sav") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (group_summary, worker_level).

    Annual gross salary = RETRINOIN + RETRIIN (gross annual pay, incl. and not
    incl. sick-leave-derived). Occupation = CNO1 major group (letter A-Q) -> 1-digit.
    Weight = FACTOTAL.
    """
    cols = ["CNO1", "FACTOTAL", "RETRINOIN", "RETRIIN", "SEXO", "ESTU",
            "CNACE", "TIPOJOR"]
    df, _ = pyreadstat.read_sav(str(RAW / fname), encoding="LATIN1", usecols=cols)
    for c in ["FACTOTAL", "RETRINOIN", "RETRIIN"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["wage"] = df["RETRINOIN"] + df["RETRIIN"]
    df["letter"] = df["CNO1"].astype(str).str.slice(0, 1)
    df["cno1"] = df["letter"].map(EES_LETTER_TO_CNO1)
    df = df.dropna(subset=["cno1", "wage", "FACTOTAL"])
    df = df[df["wage"] > 0]

    rows = []
    for g, sub in df.groupby("cno1"):
        v, w = sub["wage"].to_numpy(), sub["FACTOTAL"].to_numpy()
        rows.append({"cno1": g,
                     "wage_mean": np.average(v, weights=w),
                     "wage_median": _wq(v, w, 0.5),
                     "wage_p90_p10": _wq(v, w, 0.9) / _wq(v, w, 0.1),
                     "n_workers": len(sub)})
    return pd.DataFrame(rows), df


def main() -> None:
    exposure = build_exposure_cno1()
    emp = load_epa_employment()
    wage_groups, workers = load_ees_microdata()

    panel = (emp.merge(exposure, on="cno1", how="left")
             .merge(wage_groups, on="cno1", how="left"))
    panel["label"] = panel["cno1"].map(CNO1_LABEL)
    panel["employment_share"] = panel["employment"] / panel["employment"].sum()
    panel["log_wage"] = np.log(panel["wage_median"])

    wmean = np.average(panel["exposure"], weights=panel["employment"])
    reg = panel.dropna(subset=["exposure", "log_wage"])
    grad = smf.wls("exposure ~ log_wage", data=reg,
                   weights=reg["employment"]).fit(cov_type="HC1")

    # Worker-level conditional wage premium (descriptive): do workers in more
    # AI-exposed occupations earn more, controlling for sex/education/sector/job type?
    w = workers.merge(exposure, on="cno1", how="left").dropna(subset=["exposure"])
    w["log_wage"] = np.log(w["wage"])
    prem = smf.wls("log_wage ~ exposure + C(SEXO) + C(ESTU) + C(CNACE) + C(TIPOJOR)",
                   data=w, weights=w["FACTOTAL"]).fit(cov_type="HC1")

    cols = ["cno1", "label", "employment_share", "exposure", "wage_median",
            "wage_p90_p10"]
    print(panel[cols].sort_values("exposure", ascending=False).to_string(index=False))
    print(f"\nEmployment (EPA, weighted):              {panel['employment'].sum():,.0f}")
    print(f"EES workers analysed:                    {len(workers):,}")
    print(f"Employment-weighted mean exposure:       {wmean:.3f}")
    print(f"Wage-exposure gradient (group, n={int(grad.nobs)}):    "
          f"{grad.params['log_wage']:+.3f} (p={grad.pvalues['log_wage']:.3f})")
    print(f"Worker-level conditional wage premium of exposure: "
          f"{prem.params['exposure']:+.3f} log-pts (p={prem.pvalues['exposure']:.1e}); "
          f"i.e. a 0->1 exposure shift ~ {100*prem.params['exposure']:+.0f}% wage, "
          f"controlling for sex/education/sector/job-type.")

    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.scatter(panel["wage_median"], panel["exposure"],
               s=panel["employment_share"] * 4000, alpha=.55, edgecolor="none")
    for _, r in panel.iterrows():
        if pd.notna(r["exposure"]) and pd.notna(r["wage_median"]):
            ax.annotate(r["label"], (r["wage_median"], r["exposure"]), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Median annual gross wage, EES 2022 (EUR)")
    ax.set_ylabel("AI exposure (crosswalked Eloundou human β)")
    ax.set_title("Spain: AI exposure vs. wage by occupation group (1-digit CNO)")
    fig.tight_layout()
    fig.savefig(config.FIGURES / "wage_vs_exposure_ES.png", dpi=150)
    print(f"\nFigure written: {config.FIGURES / 'wage_vs_exposure_ES.png'}")


if __name__ == "__main__":
    main()
