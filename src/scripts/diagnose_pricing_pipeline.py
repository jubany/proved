"""Diagnostica por qué un JSON enriquecido no muestra price_items en el ranking.

Uso:
python src/scripts/diagnose_pricing_pipeline.py --source data/providers_real_b2b_priced.json --query lavandina
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agents.coordinator_agent import CoordinatorAgent
from agents.evaluation_agent import matched_price_items
from collector import json_loader
from collector.json_loader import load_providers_from_json


def _provider_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("providers", [])
    if not isinstance(data, list):
        raise ValueError("El JSON debe ser una lista o un objeto con clave 'providers'")
    return [item for item in data if isinstance(item, dict)]


def _raw_report(path: Path) -> tuple[list[dict[str, Any]], int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    providers = _provider_items(data)
    raw_priced_count = sum(1 for provider in providers if provider.get("price_items"))
    return providers, raw_priced_count


def _print_price_samples(providers: list[dict[str, Any]], limit: int = 5) -> None:
    printed = 0
    for provider in providers:
        price_items = provider.get("price_items") or []
        if not price_items:
            continue
        print("---")
        print("raw provider:", provider.get("name"))
        print("raw price_items:", price_items[:3])
        printed += 1
        if printed >= limit:
            break


def run_diagnostics(source: Path, query: str) -> int:
    print("diagnose_pricing_pipeline")
    print("source:", source)
    print("source_exists:", source.exists())
    print("json_loader_file:", Path(json_loader.__file__).resolve())

    if not source.exists():
        print("❌ No existe el archivo indicado en --source")
        return 1

    try:
        raw_providers, raw_priced_count = _raw_report(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"❌ No se pudo leer/parsear el JSON: {exc}")
        return 1

    print("raw_providers:", len(raw_providers))
    print("raw_providers_with_price_items:", raw_priced_count)
    _print_price_samples(raw_providers)

    loaded_providers = load_providers_from_json(str(source))
    loaded_priced_count = sum(1 for provider in loaded_providers if getattr(provider, "price_items", []))
    loaded_matched_count = sum(1 for provider in loaded_providers if matched_price_items(provider, query)) if query else 0

    print("loaded_providers:", len(loaded_providers))
    print("loaded_providers_with_price_items:", loaded_priced_count)
    print("loaded_providers_matching_query:", loaded_matched_count)

    result = CoordinatorAgent().run(
        {"source_path": str(source), "priority": "precio", "product_query": query, "top_n": 5}
    )
    print("coordinator_ok:", result.get("ok"))
    print("coordinator_pipeline:", result.get("pipeline"))

    if raw_priced_count > 0 and loaded_priced_count == 0:
        print("❌ El JSON tiene price_items, pero json_loader no los está cargando. Actualizá src/collector/json_loader.py.")
        return 1
    if loaded_priced_count > 0 and result.get("pipeline", {}).get("ingestion", {}).get("priced_count") == 0:
        print("❌ El loader carga precios, pero CoordinatorAgent no los reporta. Actualizá src/agents/coordinator_agent.py.")
        return 1
    if raw_priced_count == 0:
        print("❌ El archivo enriquecido no tiene price_items. Reejecutá attach_product_prices.py y verificá matched_count.")
        return 1

    print("✅ Diagnóstico OK: el archivo y el loader tienen price_items.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/providers_real_b2b_priced.json")
    parser.add_argument("--query", default="lavandina")
    args = parser.parse_args()

    return run_diagnostics(Path(args.source), args.query)


if __name__ == "__main__":
    sys.exit(main())
