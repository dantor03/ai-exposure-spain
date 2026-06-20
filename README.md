# AI Exposure of the Spanish Labour Market

**Who is most exposed to generative AI in Spain — and does the US "high-skill-biased"
pattern hold in a services- and tourism-weighted economy?**

This project (1) carries the established US occupational AI-exposure scores
(Eloundou et al., *GPTs are GPTs*, Science 2024) onto Spanish occupations via an
auditable SOC → ISCO-08 → CNO-2011 crosswalk, and (2) introduces a *validated
LLM-as-annotator* method that scores exposure directly on the European ESCO
taxonomy using Claude, benchmarked against the crosswalked human scores.

> **Status:** runs end-to-end. **US baseline** reproduces from auto-fetched data;
> **Spain result** runs from INE microdata in `data/raw/` (EPA + EES 2022). Both
> produce real figures and numbers. Granularity is capped at occupation major
> groups by Spanish public microdata — see the Spain caveat below.

### Reproducible right now (US baseline, no manual data)

```bash
pip install -r requirements.txt
python -m scripts.download_data        # auto-fetches Eloundou scores + OEWS
python -m scripts.run_us_baseline      # -> figures/wage_vs_exposure_US.png
```

Output (Eloundou human-β exposure × BLS OEWS May-2021, 767 detailed occupations,
130.6M workers):

| metric | value |
|---|---|
| Employment-weighted mean exposure | 0.32 |
| Share of US employment ≥0.5 exposure | **24.0%** |
| Wage–exposure gradient (∂exposure/∂log-wage) | **+0.18** (p≈5e-11) |

i.e. AI exposure rises with wages in the US — the benchmark the Spanish results
are tested against.

### Spain result (needs the INE microdata in `data/raw/`)

```bash
python -m scripts.run_spain                # -> figures/wage_vs_exposure_ES.png
```

Exposure crosswalked SOC-2018 → SOC-2010 → ISCO-08 → CNO-2011, aggregated to CNO
1-digit; employment from EPA 2026Q1; wages (median, dispersion) from EES-2022
microdata.

| Occupation group | Employment | Exposure | Median wage | p90/p10 |
|---|---:|---:|---:|---:|
| Clerical | 9.5% | **0.47** | €20.8k | 4.5 |
| Professionals | 20.8% | 0.44 | €35.5k | 5.4 |
| Managers | 4.2% | 0.42 | €50.9k | 4.0 |
| Technicians | 12.2% | 0.34 | €26.9k | 5.6 |
| Services & sales | 20.7% | 0.29 | €15.7k | 5.8 |
| Elementary / Craft / Operators / Agric. | ~32% | 0.09–0.11 | €14–21k | — |

- Employment-weighted **mean exposure: 0.29** (US: 0.32).
- **Wage–exposure gradient (group level, n=10): +0.24 (p≈0.002)** — Spain shows the
  same high-skill-biased exposure as the US.
- Worker-level (240k records) conditional wage premium of exposure is large and
  positive controlling for sex/education/sector/job-type. *Reported as a
  descriptive association only:* exposure varies across just 10 occupation groups,
  so model standard errors are optimistic (effective clusters ≈ 10) and the
  headline "share of workers highly exposed" is **not** identified at this
  granularity (it degenerates to ~0 because broad-group means wash out highly
  exposed detailed jobs). Both need 2-digit occupation — an INE custom-file request.

---

## Abstract

> We carry US occupational AI-exposure scores (Eloundou et al., 2024) onto Spanish
> occupations and combine them with INE labour-force (EPA, 22.3M workers) and
> structure-of-earnings microdata (EES 2022, 240k workers). Spain mirrors the US
> **high-skill-biased** pattern: cognitive white-collar groups (clerical,
> professionals, managers, technicians) are most exposed, manual trades least, and
> exposure rises with occupational pay (employment-weighted mean exposure **0.29**
> vs. 0.32 in the US). At the worker level, a one-unit rise in occupational exposure
> is associated with a large conditional wage premium, controlling for sex,
> education, sector and job type. **Caveat:** Spanish *public* microdata anonymises
> occupation to major groups (10–17), so the exposure resolution — and the
> precision of any single-occupation claim — is limited; finer (2-digit) work needs
> an INE custom-file request.

## Two headline figures _(generated into `figures/`)_

1. `figures/wage_vs_exposure.png` — scatter of occupational AI exposure vs. mean
   wage, bubble-sized by employment. **The money chart.**
2. `figures/exposure_by_sector.png` — exposure distribution across major CNO groups.

---

## Method

```
US SOC-2018  ──(BLS SOC↔ISCO)──▶  ISCO-08  ──(INE ISCO↔CNO)──▶  CNO-2011 (Spain)
   │ Eloundou exposure scores                                        │
   └────────────────────────────────────────────────────────────────┘
                              merge with EPA employment + EES wages
                                          │
              ┌───────────────────────────┴───────────────────────────┐
        Baseline (crosswalk)                          Extension (Claude on ESCO)
   defensible, anchored on human                validate LLM scores vs. crosswalk
   ratings → Spanish exposure map               (Spearman / Pearson at ISCO-4)
```

Each crosswalk hop is a many-to-many correspondence collapsed by an
(optionally employment-weighted) mean — implemented and unit-tested in
[`src/crosswalk.py`](src/crosswalk.py).

## Repository layout

```
data/
  raw/         INE EPA microdata, structure-of-earnings   (git-ignored)
  external/    Eloundou scores, BLS/INE crosswalks, ESCO   (git-ignored)
  processed/   cleaned, crosswalked panels                 (git-ignored)
src/
  config.py        paths, classification levels, model ids
  crosswalk.py     SOC → ISCO → CNO mapping (unit-tested)
  data_loading.py  loaders for every source, normalised columns
  exposure.py      build occupation panel + wage–exposure regression
  llm_scoring.py   Claude-on-ESCO scoring + validation against crosswalk
scripts/
  download_data.py documents & fetches all sources
notebooks/
  01_data_crosswalk.ipynb     SOC → CNO mapping, coverage checks
  02_eda_and_exposure.ipynb   descriptives + the two headline figures
  03_econometric_models.ipynb wage–exposure gradient, robustness
tests/               pytest for the crosswalk logic
figures/             tracked output charts (kept small)
```

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Fetch sources (mostly manual — follow the printed instructions)
python -m scripts.download_data

# 2. Sanity-check the crosswalk logic
pytest -q

# 3. Run the analysis
jupyter lab   # run notebooks 01 → 02 → 03

# (optional) 4. Claude-on-ESCO scoring extension
export ANTHROPIC_API_KEY=sk-...
python -c "from src.llm_scoring import score_esco; ..."   # see notebook 02
```

## Data sources

| Input | Source |
|---|---|
| AI exposure scores (US SOC) | Eloundou et al., *GPTs are GPTs*, **Science 2024** |
| SOC ↔ ISCO-08 | US BLS crosswalk |
| ISCO-08 ↔ CNO-2011 | INE clasificaciones |
| Employment by occupation | INE — Encuesta de Población Activa (EPA) microdata |
| Wages by occupation | INE — Encuesta de Estructura Salarial |
| EU occupations + tasks | ESCO (European Commission) |

Exact links and download notes: [`scripts/download_data.py`](scripts/download_data.py).

## Limitations

- Crosswalks are many-to-many; aggregation introduces measurement error we
  quantify via coverage diagnostics at each hop.
- "Exposure" measures *technical potential*, not realised adoption or labour
  demand — it is an upper bound on disruption, not a forecast.
- LLM-rated scores are validated against, not a replacement for, human ratings.

## Author

Daniel Torres González — [github.com/dantor03](https://github.com/dantor03)
