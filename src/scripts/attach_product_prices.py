"""Adjunta precios manuales a proveedores existentes.

Uso Git Bash / Linux / macOS:
python src/scripts/attach_product_prices.py --providers data/providers_real_b2b.json --prices data/product_prices.json --output data/providers_real_b2b_priced.json

Uso Windows con py launcher:
py src/scripts/attach_product_prices.py --providers data/providers_real_b2b.json --prices data/product_prices.json --output data/providers_real_b2b_priced.json
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def load_json_list(path: Path, root_key: str | None = None) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if root_key and isinstance(data, dict):
        if root_key not in data:
            raise ValueError(f"{path} debe contener una lista JSON o un objeto con clave '{root_key}'")
        data = data[root_key]

    if not isinstance(data, list):
        raise ValueError(f"{path} debe contener una lista JSON")

    invalid_items = [idx for idx, item in enumerate(data) if not isinstance(item, dict)]
    if invalid_items:
        raise ValueError(f"{path} contiene items que no son objetos JSON: {invalid_items[:10]}")

    return data


def validate_price_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    required = ("provider_name", "product_name", "price")
    missing = [field for field in required if item.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Precio #{index} incompleto; faltan campos: {missing}")

    try:
        price = float(item["price"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Precio #{index} tiene price inválido: {item.get('price')}") from exc

    if price < 0:
        raise ValueError(f"Precio #{index} no puede ser negativo: {price}")

    return {
        "product_name": str(item["product_name"]),
        "unit": str(item.get("unit") or "unidad"),
        "price": price,
        "currency": str(item.get("currency") or "ARS"),
        "updated_at": str(item.get("updated_at") or ""),
        "source": str(item.get("source") or "carga_manual"),
    }


def group_prices_by_provider(prices: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, item in enumerate(prices, start=1):
        provider_name = str(item.get("provider_name") or "")
        key = normalize_name(provider_name)
        grouped[key].append(validate_price_item(item, index))
    return grouped


def merge_prices(
    providers: list[dict[str, Any]], prices: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int, list[str]]:
    grouped_prices = group_prices_by_provider(prices)
    matched_keys: set[str] = set()
    enriched: list[dict[str, Any]] = []

    for provider in providers:
        provider_copy = dict(provider)
        provider_key = normalize_name(str(provider_copy.get("name") or ""))
        provider_prices = grouped_prices.get(provider_key, [])
        existing_prices = provider_copy.get("price_items") or []
        provider_copy["price_items"] = [*existing_prices, *provider_prices]
        if provider_prices:
            matched_keys.add(provider_key)
        enriched.append(provider_copy)

    unmatched_provider_names = sorted(
        str(price.get("provider_name"))
        for price in prices
        if normalize_name(str(price.get("provider_name") or "")) not in matched_keys
    )
    return enriched, len(matched_keys), unmatched_provider_names


def write_json_atomic(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="data/providers_real_b2b.json")
    parser.add_argument("--prices", default="data/product_prices.json")
    parser.add_argument("--output", default="data/providers_real_b2b_priced.json")
    parser.add_argument("--strict", action="store_true", help="Falla si hay precios con proveedor no encontrado")
    args = parser.parse_args()

    try:
        providers = load_json_list(Path(args.providers), root_key="providers")
        prices = load_json_list(Path(args.prices))
        enriched, matched_count, unmatched_names = merge_prices(providers, prices)
        write_json_atomic(Path(args.output), enriched)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"❌ Error adjuntando precios: {exc}")
        return 1

    print(f"✅ Proveedores leídos: {len(providers)}")
    print(f"✅ Precios leídos: {len(prices)}")
    print(f"✅ Proveedores con precios adjuntos: {matched_count}")
    print(f"📄 Archivo enriquecido: {args.output}")

    if matched_count == 0 and prices:
        provider_names = [str(provider.get("name")) for provider in providers[:10]]
        price_provider_names = sorted({str(price.get("provider_name")) for price in prices})
        print("⚠️ No se adjuntó ningún precio. Revisá que provider_name coincida con name.")
        print("   Proveedores disponibles (muestra):", provider_names)
        print("   provider_name en precios:", price_provider_names)

    if unmatched_names:
        print("⚠️ Precios sin proveedor encontrado:", unmatched_names)
        if args.strict:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
