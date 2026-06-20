"""Where every input comes from, and (where possible) how to fetch it.

Several Spanish sources (INE EPA microdata, structure-of-earnings) are behind
interactive portals and/or ship as fixed-width files with a separate layout, so
they can't be wget'd blindly. This script documents the exact source for each
input and downloads the ones that have stable direct URLs. Files land in
data/external/ (third-party, redistributable-ish) or data/raw/ (microdata).

Run:  python -m scripts.download_data
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "data" / "external"
RAW = ROOT / "data" / "raw"

# (url, dest) — only sources with a stable direct link. Others are manual (below).
DIRECT_DOWNLOADS: list[tuple[str, Path]] = [
    # Eloundou et al., "GPTs are GPTs" (Science 2024). Occupation-level exposure
    # ratings at O*NET-SOC: human + GPT-4, each as alpha/beta/gamma measures.
    # Repo: https://github.com/openai/GPTs-are-GPTs  | Paper: science.org/doi/10.1126/science.adj0998
    ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv",
     EXTERNAL / "eloundou_occ_level.csv"),
    # O*NET-SOC <-> SOC-2018 crosswalk (to collapse 8-digit O*NET-SOC to 6-digit SOC)
    ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/nem-onet-to-soc-crosswalk.xlsx",
     EXTERNAL / "onet_to_soc_crosswalk.xlsx"),
]

MANUAL_SOURCES = """
MANUAL DOWNLOADS (portal / fixed-width — grab once, drop into the right folder):

1) Eloundou et al. exposure scores  ->  data/external/eloundou_occ_level.csv  [AUTO]
   Downloaded directly from github.com/openai/GPTs-are-GPTs (data/occ_level.csv).
   Columns: O*NET-SOC Code, Title, {dv,human}_rating_{alpha,beta,gamma}.
   We default to human_rating_beta (= E1 + 0.5*E2), the paper's headline measure.

2) BLS SOC <-> ISCO-08 crosswalk    ->  data/external/soc_isco_crosswalk.csv
   BLS: https://www.bls.gov/soc/soc_2018_to_isco_08_crosswalk.xlsx

3) INE ISCO-08 <-> CNO-2011 table   ->  data/external/isco_cno_crosswalk.csv
   INE clasificaciones (CNO-2011): https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177033

4) EPA microdata (quarterly)        ->  data/raw/epa_YYYYtT.(sav|txt)
   INE microdatos: https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176918&menu=resultados&secc=1254736030639&idp=1254735976595
   Also mirrored on datos.gob.es:
   https://datos.gob.es/en/catalogo/ea0010587-encuesta-de-poblacion-activa-epa-resultados-trimestrales-de-la-encuesta-microdatos
   (download the .sav if offered; otherwise the fixed-width .txt + 'diseño de registro')

5) Encuesta de Estructura Salarial  ->  data/external/ees_wages_by_cno.csv
   INE: https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177025
   (mean annual gross earnings by CNO-2011 occupation)

6) ESCO occupations + tasks (for the Claude-scoring extension)
                                    ->  data/external/esco_occupations.csv
   ESCO download portal: https://esco.ec.europa.eu/en/use-esco/download
   (occupations CSV carries ISCO-08 codes, labels, descriptions, essential tasks)
"""


def main() -> int:
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    for url, dest in DIRECT_DOWNLOADS:
        print(f"[download] {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
    print(MANUAL_SOURCES)
    if not DIRECT_DOWNLOADS:
        print("No direct URLs wired up yet — fill DIRECT_DOWNLOADS once you "
              "confirm the Eloundou/BLS asset links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
