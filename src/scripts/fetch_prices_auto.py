"""Combina precios desde SEPA, Mercado Libre y carga manual en un JSON único.

Ejemplo:
PYTHONPATH=src python src/scripts/fetch_prices_auto.py \
  --products data/price_sources.example.json \
  --output data/providers_real_b2b_priced.json \
  --manual-providers data/providers_real_b2b.json \
  --manual-prices data/product_prices.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from scripts import fetch_sepa_prices as sepa
from scripts.attach_product_prices import load_json_list, merge_prices

MERCADOLIBRE_SEARCH_URL = "https://api.mercadolibre.com/sites/MLA/search"
DEFAULT_ML_CATEGORY = "MLA1246"
DEFAULT_LAT = -26.8241
DEFAULT_LNG = -65.2226
LOGGER = logging.getLogger(__name__)


class ProviderValidationError(ValueError):
    """Error de validación para proveedores generados por fuentes de precios."""



def load_price_sources(path: Path) -> list[dict[str, Any]]:
    """Carga productos a consultar en una o más fuentes."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} debe contener una lista JSON")

    products = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Producto #{index} debe ser un objeto JSON")
        product_name = str(item.get("product_name") or item.get("name") or "").strip()
        sepa_id = str(item.get("sepa_id_producto") or item.get("id_producto") or item.get("ean") or "").strip()
        ml_query = str(item.get("ml_query") or item.get("mercadolibre_query") or "").strip()
        if not product_name and not sepa_id and not ml_query:
            raise ValueError(f"Producto #{index} necesita product_name, sepa_id_producto/id_producto/ean o ml_query")
        products.append(
            {
                "product_name": product_name or sepa_id or ml_query,
                "unit": str(item.get("unit") or "unidad"),
                "sepa_id_producto": sepa_id,
                "ml_query": ml_query or product_name,
                "ml_category": str(item.get("ml_category") or DEFAULT_ML_CATEGORY),
            }
        )
    return products


def _sepa_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id_producto": product["sepa_id_producto"],
            "product_name": product["product_name"],
            "unit": product.get("unit") or "unidad",
            "source": "sepa_api",
        }
        for product in products
        if product.get("sepa_id_producto")
    ]


def fetch_sepa_providers(products: list[dict[str, Any]], lat: float, lng: float, limit: int, timeout: int) -> list[dict[str, Any]]:
    """Consulta sucursales SEPA cercanas y precios por EAN."""
    products_for_sepa = _sepa_products(products)
    if not products_for_sepa:
        return []
    branches = sepa.fetch_sucursales(lat, lng, limit, timeout)
    return sepa.build_priced_providers(branches, products_for_sepa, timeout=timeout, limit=limit)


def fetch_mercadolibre_search(query: str, category: str, limit: int, timeout: int) -> dict[str, Any]:
    params = {"q": query, "category": category, "limit": limit}
    return sepa._json_get(f"{MERCADOLIBRE_SEARCH_URL}?{urlencode(params)}", timeout=timeout)


def _seller_name(item: dict[str, Any]) -> str:
    seller = item.get("seller") if isinstance(item.get("seller"), dict) else {}
    seller_id = str(seller.get("id") or item.get("seller_id") or "").strip()
    nickname = str(seller.get("nickname") or item.get("seller_nickname") or "").strip()
    return nickname or (f"seller_{seller_id}" if seller_id else "vendedor_desconocido")


def _mercadolibre_provider_key(item: dict[str, Any]) -> str:
    seller = item.get("seller") if isinstance(item.get("seller"), dict) else {}
    seller_id = str(seller.get("id") or item.get("seller_id") or "").strip()
    return seller_id or _seller_name(item).lower()


def _mercadolibre_item_to_price_item(item: dict[str, Any], product: dict[str, Any]) -> dict[str, Any] | None:
    price = sepa._float_or_none(item.get("price"))
    if price is None:
        return None
    return {
        "product_name": str(item.get("title") or product["product_name"]),
        "unit": product.get("unit") or "unidad",
        "price": price,
        "currency": str(item.get("currency_id") or "ARS"),
        "updated_at": "",
        "source": "mercadolibre_api",
        "ml_item_id": str(item.get("id") or ""),
        "ml_permalink": str(item.get("permalink") or ""),
        "ml_query": product.get("ml_query") or product["product_name"],
    }



def _validate_price_item(item: Any, provider_name: str, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ProviderValidationError(f"{provider_name}: price_items[{index}] debe ser un objeto JSON")

    product_name = str(item.get("product_name") or item.get("name") or "").strip()
    if not product_name:
        raise ProviderValidationError(f"{provider_name}: price_items[{index}] no tiene product_name")

    price = sepa._float_or_none(item.get("price"))
    if price is None or price < 0:
        raise ProviderValidationError(f"{provider_name}: price_items[{index}] tiene price inválido: {item.get('price')}")

    normalized = dict(item)
    normalized["product_name"] = product_name
    normalized["price"] = price
    normalized["unit"] = str(normalized.get("unit") or "unidad")
    normalized["currency"] = str(normalized.get("currency") or "ARS")
    normalized["source"] = str(normalized.get("source") or "unknown")
    return normalized


def validate_provider(provider: Any, source_label: str, index: int) -> dict[str, Any]:
    """Valida y normaliza un proveedor antes de mezclarlo en el flujo automático."""
    if not isinstance(provider, dict):
        raise ProviderValidationError(f"{source_label}[{index}] debe ser un objeto JSON")

    provider_name = str(provider.get("name") or "").strip()
    if not provider_name:
        raise ProviderValidationError(f"{source_label}[{index}] no tiene name")

    normalized = dict(provider)
    normalized["name"] = provider_name
    normalized["address"] = str(normalized.get("address") or "Sin domicilio disponible")
    normalized["category"] = str(normalized.get("category") or source_label)

    products = normalized.get("products") or []
    if not isinstance(products, list):
        raise ProviderValidationError(f"{provider_name}: products debe ser una lista")
    normalized["products"] = [str(product) for product in products if str(product).strip()]

    price_items = normalized.get("price_items") or []
    if not isinstance(price_items, list):
        raise ProviderValidationError(f"{provider_name}: price_items debe ser una lista")
    normalized["price_items"] = [
        _validate_price_item(item, provider_name, item_index) for item_index, item in enumerate(price_items)
    ]

    tags = normalized.get("tags") or {}
    if not isinstance(tags, dict):
        raise ProviderValidationError(f"{provider_name}: tags debe ser un objeto JSON")
    tags.setdefault("source", source_label)
    normalized["tags"] = tags
    return normalized


def validate_providers(providers: list[dict[str, Any]], source_label: str) -> list[dict[str, Any]]:
    """Descarta proveedores inválidos y registra el detalle para diagnóstico."""
    valid_providers = []
    for index, provider in enumerate(providers):
        try:
            valid_providers.append(validate_provider(provider, source_label, index))
        except ProviderValidationError as exc:
            LOGGER.warning("Proveedor descartado desde %s: %s", source_label, exc)
    LOGGER.info(
        "Validación de proveedores %s: %s válidos, %s descartados",
        source_label,
        len(valid_providers),
        len(providers) - len(valid_providers),
    )
    return valid_providers


def fetch_validated_provider_source(source_label: str, fetcher: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Ejecuta una fuente de proveedores, registra errores y valida su salida."""
    try:
        providers = fetcher()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        LOGGER.error("No se pudo consultar %s: %s", source_label, exc)
        return []
    if not isinstance(providers, list):
        LOGGER.error("La fuente %s devolvió %s; se esperaba una lista", source_label, type(providers).__name__)
        return []
    return validate_providers(providers, source_label)


def fetch_mercadolibre_providers(products: list[dict[str, Any]], limit: int, timeout: int) -> list[dict[str, Any]]:
    """Busca ofertas de Mercado Libre y agrupa resultados por vendedor."""
    providers_by_seller: dict[str, dict[str, Any]] = {}
    for product in products:
        query = product.get("ml_query") or product["product_name"]
        if not query:
            continue
        response = fetch_mercadolibre_search(query, product.get("ml_category") or DEFAULT_ML_CATEGORY, limit, timeout)
        results = sepa._list_from_response(response, ("results",))
        for item in results:
            price_item = _mercadolibre_item_to_price_item(item, product)
            if not price_item:
                continue
            seller_key = _mercadolibre_provider_key(item)
            seller_name = _seller_name(item)
            provider = providers_by_seller.setdefault(
                seller_key,
                {
                    "name": f"MercadoLibre - {seller_name}",
                    "address": "Online",
                    "lat": 0,
                    "lng": 0,
                    "rating": None,
                    "reviews_count": None,
                    "category": "marketplace_online",
                    "products": [],
                    "phone": "",
                    "website": "https://www.mercadolibre.com.ar",
                    "social_links": [],
                    "price_items": [],
                    "tags": {"source": "mercadolibre_api", "ml_seller_key": seller_key},
                },
            )
            provider["price_items"].append(price_item)
            if price_item["product_name"] not in provider["products"]:
                provider["products"].append(price_item["product_name"])
    return list(providers_by_seller.values())


def load_manual_priced_providers(providers_path: Path | None, prices_path: Path | None) -> list[dict[str, Any]]:
    """Aplica product_prices.json sobre proveedores locales si ambos paths están presentes."""
    if not providers_path or not prices_path:
        return []
    if not providers_path.exists() or not prices_path.exists():
        return []
    providers = load_json_list(providers_path, root_key="providers")
    prices = load_json_list(prices_path)
    enriched, _, _ = merge_prices(providers, prices)
    for provider in enriched:
        provider.setdefault("tags", {})["source"] = provider.get("tags", {}).get("source") or "manual_price_file"
    return enriched


def _provider_key(provider: dict[str, Any]) -> str:
    tags = provider.get("tags") if isinstance(provider.get("tags"), dict) else {}
    source = str(tags.get("source") or provider.get("category") or "local")
    external_id = tags.get("sepa_branch_id") or tags.get("ml_seller_key")
    if external_id:
        return f"{source}:{external_id}"
    return f"{source}:{str(provider.get('name') or '').strip().lower()}"


def merge_provider_sources(provider_groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Deduplica proveedores por fuente/id y concatena sus price_items."""
    merged: dict[str, dict[str, Any]] = {}
    for group in provider_groups:
        for provider in group:
            key = _provider_key(provider)
            if key not in merged:
                provider_copy = dict(provider)
                provider_copy["price_items"] = list(provider.get("price_items") or [])
                provider_copy["products"] = list(provider.get("products") or [])
                merged[key] = provider_copy
                continue
            current = merged[key]
            current["price_items"].extend(provider.get("price_items") or [])
            for product in provider.get("products") or []:
                if product not in current["products"]:
                    current["products"].append(product)
    return list(merged.values())


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", default="data/price_sources.example.json")
    parser.add_argument("--output", default="data/providers_real_b2b_priced.json")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lng", type=float, default=DEFAULT_LNG)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--skip-sepa", action="store_true")
    parser.add_argument("--skip-mercadolibre", action="store_true")
    parser.add_argument("--manual-providers", default="data/providers_real_b2b.json")
    parser.add_argument("--manual-prices", default="data/product_prices.json")
    args = parser.parse_args()

    try:
        products = load_price_sources(Path(args.products))
        sepa_providers = (
            []
            if args.skip_sepa
            else fetch_validated_provider_source(
                "sepa_api", lambda: fetch_sepa_providers(products, args.lat, args.lng, args.limit, args.timeout)
            )
        )
        ml_providers = (
            []
            if args.skip_mercadolibre
            else fetch_validated_provider_source(
                "mercadolibre_api", lambda: fetch_mercadolibre_providers(products, args.limit, args.timeout)
            )
        )
        manual_providers = fetch_validated_provider_source(
            "manual_price_file", lambda: load_manual_priced_providers(Path(args.manual_providers), Path(args.manual_prices))
        )
        providers = merge_provider_sources([sepa_providers, ml_providers, manual_providers])
        sepa.write_json_atomic(Path(args.output), providers)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"❌ Error generando precios automáticos: {exc}")
        return 1

    priced_count = sum(1 for provider in providers if provider.get("price_items"))
    price_items_count = sum(len(provider.get("price_items") or []) for provider in providers)
    print(f"✅ Productos configurados: {len(products)}")
    print(f"✅ Proveedores SEPA: {len(sepa_providers)}")
    print(f"✅ Proveedores MercadoLibre: {len(ml_providers)}")
    print(f"✅ Proveedores manuales/locales: {len(manual_providers)}")
    print(f"✅ Proveedores finales: {len(providers)}")
    print(f"✅ Proveedores con precios: {priced_count}")
    print(f"✅ Precios encontrados: {price_items_count}")
    print(f"📄 Archivo enriquecido: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
