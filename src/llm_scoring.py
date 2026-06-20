"""Methodological extension: score AI exposure directly on EU ESCO occupations
using Claude as the annotation instrument, then validate against the crosswalked
Eloundou scores.

The point is NOT "the LLM said so". The point is a *validated* measurement
instrument: we apply the published Eloundou exposure rubric verbatim, get a
structured 0-1 score per ESCO occupation, and then check rank/level agreement
against the established human-rated scores carried over via the crosswalk.
"""
from __future__ import annotations

import json
import os
import time

import pandas as pd
from anthropic import Anthropic

from . import config

# The Eloundou et al. (2023) exposure rubric, lightly condensed. Using their
# definition (rather than inventing our own) is what makes the scores comparable.
RUBRIC = """\
We define "exposure" as a measure of whether access to an LLM-powered assistant
would reduce the time required for a human to perform a task by at least 50%,
WITHOUT a reduction in quality.

Score the OCCUPATION below on a 0-1 scale, where the score is the estimated
fraction of the occupation's core tasks that are EXPOSED in this sense:
  - A task is exposed if an LLM (or simple LLM-powered software) could cut the
    time to do it by >=50% at equal quality.
  - It is NOT exposed if it requires physical action, hands-on judgement, or
    real-world interaction the model cannot provide.

Return STRICT JSON only: {"exposure": <float 0..1>, "rationale": "<=25 words"}.
"""


def build_prompt(occupation_label: str, description: str, tasks: list[str]) -> str:
    tasklist = "\n".join(f"- {t}" for t in tasks[:15])
    return (
        f"{RUBRIC}\n\n"
        f"OCCUPATION: {occupation_label}\n"
        f"DESCRIPTION: {description}\n"
        f"TYPICAL TASKS:\n{tasklist}\n"
    )


def score_occupation(
    client: Anthropic,
    occupation_label: str,
    description: str,
    tasks: list[str],
    model: str | None = None,
) -> dict:
    """One occupation -> {'exposure': float, 'rationale': str}."""
    resp = client.messages.create(
        model=model or config.ANTHROPIC_MODEL,
        max_tokens=200,
        temperature=0,  # deterministic annotation
        messages=[{"role": "user",
                   "content": build_prompt(occupation_label, description, tasks)}],
    )
    text = resp.content[0].text.strip()
    # Be defensive: extract the JSON object even if the model adds stray text.
    start, end = text.find("{"), text.rfind("}")
    obj = json.loads(text[start:end + 1])
    obj["exposure"] = float(obj["exposure"])
    return obj


def score_esco(
    esco: pd.DataFrame,
    model: str | None = None,
    sleep: float = 0.0,
) -> pd.DataFrame:
    """Score every ESCO occupation.

    `esco` columns expected: [esco_uri, label, description, tasks(list), isco4]
    Returns the input plus [exposure_llm, rationale].
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rows = []
    for r in esco.itertuples(index=False):
        try:
            out = score_occupation(client, r.label, r.description,
                                   list(r.tasks), model=model)
        except Exception as e:  # log and continue; never lose the whole run
            out = {"exposure": float("nan"), "rationale": f"ERROR: {e}"}
        rows.append({"esco_uri": r.esco_uri, "isco4": r.isco4,
                     "exposure_llm": out["exposure"], "rationale": out["rationale"]})
        if sleep:
            time.sleep(sleep)
    return esco.merge(pd.DataFrame(rows), on=["esco_uri", "isco4"], how="left")


def validate_against_crosswalk(
    llm_scores: pd.DataFrame,   # [isco4, exposure_llm]
    crosswalk_scores: pd.DataFrame,  # [isco4, exposure]  (Eloundou carried to ISCO)
) -> dict:
    """Spearman + Pearson agreement at the ISCO-4 level."""
    from scipy.stats import pearsonr, spearmanr

    a = (llm_scores.groupby("isco4", as_index=False)["exposure_llm"].mean())
    m = a.merge(crosswalk_scores, on="isco4", how="inner").dropna()
    return {
        "n": int(len(m)),
        "pearson": float(pearsonr(m["exposure_llm"], m["exposure"])[0]),
        "spearman": float(spearmanr(m["exposure_llm"], m["exposure"])[0]),
    }
