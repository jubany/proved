"""Alias corto para combinar precios desde SEPA, Mercado Libre y carga manual.

Este archivo existe para evitar la confusión entre `fetch_prices.py` y el
script principal `fetch_prices_auto.py`. Ambos comandos aceptan los mismos
argumentos; este wrapper delega todo en `scripts.fetch_prices_auto.main`.

Ejemplo:
PYTHONPATH=src python src/scripts/fetch_prices.py \
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
