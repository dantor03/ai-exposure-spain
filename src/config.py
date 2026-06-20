"""Central paths and constants for the AI-exposure-Spain project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = ROOT / "data" / "raw"           # INE EPA microdata, INE structure-of-earnings
DATA_EXTERNAL = ROOT / "data" / "external" # Eloundou scores, official crosswalks, ESCO dump
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"

for _p in (DATA_RAW, DATA_EXTERNAL, DATA_PROCESSED, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

# --- Classification systems in play -------------------------------------------
# Eloundou et al. publish exposure at US SOC-2018 (via O*NET-SOC).
# We bridge:  US SOC-2018  ->  ISCO-08  ->  CNO-2011 (Spain).
# EPA microdata code occupation at CNO-2011 2-digit (sometimes 1-digit, public files).
SOC_LEVEL = "soc6"      # 6-digit detailed SOC in Eloundou file
ISCO_LEVEL = "isco4"    # 4-digit ISCO-08
CNO_LEVEL = "cno2"      # EPA public microdata expose CNO-2011 at 2-digit ("CNO1")

# --- Claude scoring (methodological extension) --------------------------------
# Bulk annotation task over ~3k ESCO occupations: default to a fast, cheap model.
# Bump to a larger model for a validation subsample if you want higher fidelity.
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"   # cheap bulk scorer
ANTHROPIC_MODEL_VALIDATION = "claude-sonnet-4-6"  # higher-quality re-score on a sample
