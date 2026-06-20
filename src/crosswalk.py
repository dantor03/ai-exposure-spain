"""Map US-SOC exposure scores onto Spanish CNO-2011 occupations.

Pipeline:  SOC-2018  --(BLS SOC<->ISCO)-->  ISCO-08  --(INE ISCO<->CNO)-->  CNO-2011

Each step is a many-to-many correspondence, so we aggregate by an (optionally
employment-weighted) mean. Keeping the steps explicit and auditable is the whole
point: a reviewer can check the join at every hop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def collapse(
    scores: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    src_code: str,
    dst_code: str,
    value: str = "exposure",
    weight: str | None = None,
) -> pd.DataFrame:
    """Push `value` from src classification to dst classification through a crosswalk.

    Parameters
    ----------
    scores    : DataFrame with columns [src_code, value (, weight)]
    crosswalk : DataFrame with columns [src_code, dst_code]
    weight    : optional employment-weight column present in `scores`

    Many-to-many correspondences are collapsed by an (optionally weighted) mean.
    Destination codes with no matched score are kept as NaN so coverage is honest.
    """
    merged = crosswalk.merge(scores, on=src_code, how="left", validate="m:m")
    all_dst = crosswalk[[dst_code]].drop_duplicates()

    use_w = weight is not None and weight in merged
    m = merged.dropna(subset=[value]).copy()
    if use_w:
        m["_wv"] = m[value].astype(float) * m[weight].astype(float)
        agg = m.groupby(dst_code).agg(_num=("_wv", "sum"), _den=(weight, "sum"))
        agg[value] = np.where(agg["_den"] != 0, agg["_num"] / agg["_den"], np.nan)
        res = agg[[value]]
    else:
        res = m.groupby(dst_code)[value].mean().to_frame()

    out = all_dst.merge(res, on=dst_code, how="left")
    coverage = out[value].notna().mean()
    print(f"[crosswalk] {src_code} -> {dst_code}: "
          f"{len(out)} dst codes, coverage={coverage:.1%}")
    return out


def soc_to_cno(
    eloundou: pd.DataFrame,
    soc_isco: pd.DataFrame,
    isco_cno: pd.DataFrame,
    value: str = "exposure",
) -> pd.DataFrame:
    """Full two-hop crosswalk SOC -> ISCO -> CNO.

    Expects:
      eloundou : [soc6, exposure]          (Eloundou et al. scores)
      soc_isco : [soc6, isco4]             (BLS SOC <-> ISCO-08 correspondence)
      isco_cno : [isco4, cno2]             (INE ISCO-08 <-> CNO-2011 table)
    Returns [cno2, exposure].
    """
    at_isco = collapse(eloundou, soc_isco, src_code="soc6", dst_code="isco4",
                       value=value)
    at_cno = collapse(at_isco, isco_cno, src_code="isco4", dst_code="cno2",
                      value=value)
    return at_cno


if __name__ == "__main__":
    # Smoke test on toy data so the module is runnable before real files land.
    eloundou = pd.DataFrame({"soc6": ["15-1252", "25-2021", "53-3032"],
                             "exposure": [0.9, 0.3, 0.05]})
    soc_isco = pd.DataFrame({"soc6": ["15-1252", "25-2021", "53-3032"],
                             "isco4": ["2512", "2341", "8332"]})
    isco_cno = pd.DataFrame({"isco4": ["2512", "2341", "8332"],
                             "cno2": ["27", "23", "84"]})
    print(soc_to_cno(eloundou, soc_isco, isco_cno))
