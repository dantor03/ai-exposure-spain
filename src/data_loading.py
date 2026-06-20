"""Loaders for the external and raw datasets.

These functions assume the files have already been fetched into data/external/
and data/raw/ (see scripts/download_data.py for sources). They normalise column
names so the rest of the pipeline is classification-agnostic.
"""
from __future__ import annotations

import pandas as pd

from . import config


# --- Eloundou et al. "GPTs are GPTs" exposure scores --------------------------
def load_eloundou(
    filename: str = "eloundou_occ_level.csv",
    measure: str = "human_rating_beta",
) -> pd.DataFrame:
    """Return [soc6, exposure] from openai/GPTs-are-GPTs data/occ_level.csv.

    Available measures (rater_rating_construct):
      rater     : 'human' (annotators) | 'dv' (GPT-4)
      construct : 'alpha' = E1            (fully exposed only)
                  'beta'  = E1 + 0.5*E2   (headline measure)
                  'gamma' = E1 + E2       (inclusive upper bound)
    Default = human_rating_beta. Swap `measure` for robustness checks.
    """
    valid = {f"{r}_rating_{c}" for r in ("human", "dv")
             for c in ("alpha", "beta", "gamma")}
    if measure not in valid:
        raise ValueError(f"measure must be one of {sorted(valid)}")

    df = pd.read_csv(config.DATA_EXTERNAL / filename)
    df = df.rename(columns={"O*NET-SOC Code": "soc_onet", measure: "exposure"})
    # Collapse O*NET-SOC (8-digit, e.g. 15-1252.00) to SOC-2018 6-digit (15-1252).
    df["soc6"] = df["soc_onet"].astype(str).str.slice(0, 7)
    return df.groupby("soc6", as_index=False)["exposure"].mean()


# --- Crosswalks ---------------------------------------------------------------
def load_soc_isco(filename: str = "soc_isco_crosswalk.csv") -> pd.DataFrame:
    """Return [soc6, isco4] from the BLS SOC<->ISCO-08 correspondence."""
    df = pd.read_csv(config.DATA_EXTERNAL / filename, dtype=str)
    df = df.rename(columns={"SOC Code": "soc6", "ISCO Code": "isco4"})
    return df[["soc6", "isco4"]].dropna().drop_duplicates()


def load_isco_cno(filename: str = "isco_cno_crosswalk.csv") -> pd.DataFrame:
    """Return [isco4, cno2] from the INE ISCO-08<->CNO-2011 table."""
    df = pd.read_csv(config.DATA_EXTERNAL / filename, dtype=str)
    df = df.rename(columns={"ISCO08": "isco4", "CNO11": "cno2"})
    df["cno2"] = df["cno2"].str.slice(0, 2)
    return df[["isco4", "cno2"]].dropna().drop_duplicates()


# --- EPA microdata (INE) ------------------------------------------------------
def load_epa(filename: str, layout: str | None = None) -> pd.DataFrame:
    """Load one EPA quarterly microdata file.

    INE ships fixed-width text plus a layout ('diseño de registro'). The cleanest
    route is the SPSS/.sav export when available (pyreadstat). We keep only the
    fields we need and rename them to neutral names.
    """
    path = config.DATA_RAW / filename
    if path.suffix.lower() in {".sav", ".dta"}:
        import pyreadstat
        df, _meta = pyreadstat.read_file_multiprocessing(
            pyreadstat.read_sav if path.suffix.lower() == ".sav" else pyreadstat.read_dta,
            str(path),
        )
    else:
        # Fixed-width: requires the column spec from the INE layout file.
        if layout is None:
            raise ValueError("Fixed-width EPA file needs a `layout` colspec path.")
        spec = pd.read_csv(layout)  # columns: name,start,end
        colspecs = list(zip(spec["start"] - 1, spec["end"]))
        df = pd.read_fwf(path, colspecs=colspecs, names=spec["name"])

    rename = {
        "OCUP1": "cno2",    # occupation, CNO-2011 1/2-digit (confirm code in layout)
        "FACTOREL": "weight",  # elevation/population weight
        "EDAD5": "age",
        "SEXO1": "sex",
        "NFORMA": "education",
        "AOI": "labour_status",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df})
    keep = [c for c in ["cno2", "weight", "age", "sex", "education", "labour_status"]
            if c in df]
    return df[keep]


# --- Earnings (Encuesta de Estructura Salarial) -------------------------------
def load_earnings(filename: str = "ees_wages_by_cno.csv") -> pd.DataFrame:
    """Return [cno2, mean_wage] (annual gross), from the INE structure-of-earnings."""
    df = pd.read_csv(config.DATA_EXTERNAL / filename, dtype={"cno2": str})
    return df[["cno2", "mean_wage"]]
