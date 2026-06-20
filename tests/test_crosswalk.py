"""Minimal tests so the crosswalk logic is guaranteed correct before real data."""
import pandas as pd

from src.crosswalk import collapse, soc_to_cno


def test_collapse_averages_many_to_many():
    scores = pd.DataFrame({"soc6": ["A", "B"], "exposure": [1.0, 0.0]})
    xwalk = pd.DataFrame({"soc6": ["A", "B"], "isco4": ["X", "X"]})
    out = collapse(scores, xwalk, src_code="soc6", dst_code="isco4")
    assert out.loc[out.isco4 == "X", "exposure"].iloc[0] == 0.5


def test_two_hop_preserves_value():
    eloundou = pd.DataFrame({"soc6": ["A"], "exposure": [0.8]})
    soc_isco = pd.DataFrame({"soc6": ["A"], "isco4": ["X"]})
    isco_cno = pd.DataFrame({"isco4": ["X"], "cno2": ["10"]})
    out = soc_to_cno(eloundou, soc_isco, isco_cno)
    assert abs(out["exposure"].iloc[0] - 0.8) < 1e-9
