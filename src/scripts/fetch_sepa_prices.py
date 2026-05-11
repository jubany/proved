"""Genera proveedores con precios frescos desde la API pública usada por Precios Claros/SEPA.

La API de la web de Precios Claros no está documentada como contrato estable; por eso
este script encapsula el acceso y deja trazabilidad en `tags.sepa_*`.

Ejemplo:
PYTHONPATH=src python src/scripts/fetch_sepa_prices.py \
  --products data/sepa_products.example.json \
  --output data/providers_real_b2b_priced.json \
  --lat -26.8241 --lng -65.2226 --limit 30
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEPA_BASE_URL = "https://d3e6htiiul5ek9.cloudfront.net/prod"
USER_AGENT = "proved-sepa-price-agent/0.1"
PRICE_KEYS = (
    "precioLista",
    "precio_lista",
    "precio",
    "precio_unitario",
    "precioUnitario",
    "precioConIva",
    "precioConIVA",
)
BRANCH_ID_KEYS = ("id", "id_sucursal", "idSucursal", "sucursal_id", "sucursalId")
BRANCH_NAME_KEYS = ("banderaDescripcion", "comercioRazonSocial", "nombre", "descripcion", "comercio")
ADDRESS_KEYS = ("direccion", "domicilio", "calle", "ubicacion")
LAT_KEYS = ("lat", "latitud", "latitude")
LNG_KEYS = ("lng", "lon", "longitud", "longitude")


def _first_value(item: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_get(url: str, timeout: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"SEPA devolvió HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"SEPA URLError: {exc}") from exc


def _list_from_response(data: Any, preferred_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in preferred_keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def load_products(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} debe contener una lista JSON")

    products = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Producto #{index} debe ser un objeto JSON")
        product_id = str(item.get("id_producto") or item.get("ean") or item.get("barcode") or "").strip()
        if not product_id:
            raise ValueError(f"Producto #{index} necesita id_producto/ean/barcode")
        products.append(
            {
                "id_producto": product_id,
                "product_name": str(item.get("product_name") or item.get("name") or product_id),
                "unit": str(item.get("unit") or "unidad"),
                "source": str(item.get("source") or "sepa_api"),
            }
        )
    return products


def fetch_sucursales(lat: float, lng: float, limit: int, timeout: int) -> list[dict[str, Any]]:
    query = urlencode({"lat": lat, "lng": lng, "limit": limit})
    data = _json_get(f"{SEPA_BASE_URL}/sucursales?{query}", timeout=timeout)
    return _list_from_response(data, ("sucursales", "data", "results"))


def fetch_producto(product_id: str, branch_ids: list[str], limit: int, timeout: int) -> dict[str, Any]:
    query = urlencode(
        {
            "id_producto": product_id,
            "array_sucursales": ",".join(branch_ids),
            "limit": limit,
        }
    )
    return _json_get(f"{SEPA_BASE_URL}/producto?{query}", timeout=timeout)


def branch_id(branch: dict[str, Any]) -> str:
    return str(_first_value(branch, BRANCH_ID_KEYS, "")).strip()


def normalize_branch(branch: dict[str, Any]) -> dict[str, Any]:
    branch_identifier = branch_id(branch)
    name = str(_first_value(branch, BRANCH_NAME_KEYS, f"SEPA sucursal {branch_identifier}"))
    lat = _float_or_none(_first_value(branch, LAT_KEYS, 0)) or 0
    lng = _float_or_none(_first_value(branch, LNG_KEYS, 0)) or 0
    return {
        "name": name,
        "address": str(_first_value(branch, ADDRESS_KEYS, "Sin domicilio disponible")),
        "lat": lat,
        "lng": lng,
        "rating": None,
        "reviews_count": None,
        "category": "sepa_branch",
        "products": [],
        "phone": str(branch.get("telefono") or branch.get("phone") or ""),
        "website": str(branch.get("web") or branch.get("website") or ""),
        "social_links": [],
        "price_items": [],
        "tags": {"source": "sepa_api", "sepa_branch_id": branch_identifier, "sepa_raw": branch},
    }


def _price_from_container(container: dict[str, Any]) -> float | None:
    for key in PRICE_KEYS:
        price = _float_or_none(container.get(key))
        if price is not None:
            return price
    return None


def _branch_price_container(record: dict[str, Any]) -> dict[str, Any]:
    for key in ("preciosProducto", "precioProducto", "precios", "precio"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return record


def extract_price_items_by_branch(
    product_response: dict[str, Any], product: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    product_meta = product_response.get("producto") if isinstance(product_response.get("producto"), dict) else {}
    product_name = str(product_meta.get("nombre") or product_meta.get("descripcion") or product["product_name"])
    unit = str(product_meta.get("presentacion") or product.get("unit") or "unidad")
    records = _list_from_response(product_response, ("sucursales", "data", "results"))
    items_by_branch: dict[str, dict[str, Any]] = {}

    for record in records:
        record_branch_id = branch_id(record)
        if not record_branch_id:
            continue
        price_container = _branch_price_container(record)
        price = _price_from_container(price_container)
        if price is None:
            continue
        items_by_branch[record_branch_id] = {
            "product_name": product_name,
            "unit": unit,
            "price": price,
            "currency": "ARS",
            "updated_at": str(product_response.get("fecha") or product_response.get("updated_at") or ""),
            "source": product.get("source") or "sepa_api",
            "sepa_product_id": product["id_producto"],
        }
    return items_by_branch


def build_priced_providers(
    branches: list[dict[str, Any]], products: list[dict[str, Any]], timeout: int, limit: int
) -> list[dict[str, Any]]:
    providers_by_branch_id = {
        branch_id(branch): normalize_branch(branch) for branch in branches if branch_id(branch)
    }
    branch_ids = list(providers_by_branch_id)
    if not branch_ids:
        return []

    for product in products:
        response = fetch_producto(product["id_producto"], branch_ids, limit=limit, timeout=timeout)
        items_by_branch = extract_price_items_by_branch(response, product)
        for current_branch_id, price_item in items_by_branch.items():
            provider = providers_by_branch_id.get(current_branch_id)
            if not provider:
                continue
            provider["price_items"].append(price_item)
            product_name = price_item["product_name"]
            if product_name not in provider["products"]:
                provider["products"].append(product_name)

    return list(providers_by_branch_id.values())


def write_json_atomic(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", default="data/sepa_products.example.json")
    parser.add_argument("--output", default="data/providers_real_b2b_priced.json")
    parser.add_argument("--lat", type=float, default=-26.8241)
    parser.add_argument("--lng", type=float, default=-65.2226)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    try:
        products = load_products(Path(args.products))
        branches = fetch_sucursales(args.lat, args.lng, args.limit, args.timeout)
        providers = build_priced_providers(branches, products, timeout=args.timeout, limit=args.limit)
        write_json_atomic(Path(args.output), providers)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"❌ Error consultando SEPA: {exc}")
        return 1

    priced_count = sum(1 for provider in providers if provider.get("price_items"))
    price_items_count = sum(len(provider.get("price_items") or []) for provider in providers)
    print(f"✅ Sucursales SEPA leídas: {len(branches)}")
    print(f"✅ Productos consultados: {len(products)}")
    print(f"✅ Proveedores con precios: {priced_count}")
    print(f"✅ Precios encontrados: {price_items_count}")
    print(f"📄 Archivo enriquecido: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
