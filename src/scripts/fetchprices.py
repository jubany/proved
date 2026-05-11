"""Alias sin guion bajo para combinar precios desde SEPA, Mercado Libre y manual.

Este wrapper existe para quienes buscan ejecutar `fetchprices.py` en vez de
`fetch_prices.py`. Ambos delegan en el script principal
`scripts.fetch_prices_auto.main` y aceptan los mismos argumentos.

Ejemplo:
PYTHONPATH=src python src/scripts/fetchprices.py \
  --products data/price_sources.example.json \
  --output data/providers_real_b2b_priced.json
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.fetch_prices_auto import main


if __name__ == "__main__":
    sys.exit(main())
