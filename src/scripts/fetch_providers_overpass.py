"""Descarga proveedores reales de Tucumán usando Overpass + Nominatim."""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from models.provider_pydantic import ProviderNormalized

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "proved-ingestion-agent/0.1 (+https://example.local)"


def http_get_json(url: str, timeout: int = 60) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_form_json(url: str, form_data: dict[str, str], timeout: int = 120) -> dict[str, Any]:
    payload = urlencode(form_data).encode("utf-8")
    req = Request(
        url,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        raise RuntimeError(f"Overpass devolvió HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Overpass URLError: {exc}") from exc
    except socket.timeout as exc:
        raise RuntimeError(f"Overpass timeout: {exc}") from exc


def geocode_tucuman() -> tuple[float, float, float, float]:
    params = "?q=" + quote("Tucumán, Argentina") + "&format=jsonv2&limit=1"
    data = http_get_json(NOMINATIM_SEARCH_URL + params)
    if not data:
        raise RuntimeError("Nominatim no devolvió resultados para Tucumán")
    item = data[0]
    return (
        float(item["boundingbox"][0]),
        float(item["boundingbox"][2]),
        float(item["boundingbox"][1]),
        float(item["boundingbox"][3]),
    )


def build_overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    return f"""
    [out:json][timeout:120];
    (
      nwr["shop"="wholesale"]({south},{west},{north},{east});
      nwr["wholesale"]({south},{west},{north},{east});
      nwr["name"~"distribuidora|mayorista|limpieza|higiene",i]({south},{west},{north},{east});
      nwr["description"~"distribuidora|mayorista|limpieza|higiene",i]({south},{west},{north},{east});
    );
    out center;
    """.strip()


def to_provider(el: dict[str, Any]) -> ProviderNormalized:
    tags = el.get("tags", {})
    center = el.get("center", {})
    lat = el.get("lat", center.get("lat", 0.0))
    lng = el.get("lon", center.get("lon", 0.0))
    category = tags.get("shop") or tags.get("wholesale") or tags.get("office") or ""

    products: list[str] = []
    for key in ("product", "products"):
        if tags.get(key):
            products.extend([p.strip() for p in tags[key].split(";") if p.strip()])

    return ProviderNormalized(
        name=tags.get("name", ""),
        address=tags.get("addr:full") or tags.get("addr:street", ""),
        lat=float(lat or 0.0),
        lng=float(lng or 0.0),
        rating=None,
        reviews_count=None,
        category=category,
        products=products,
        source="osm",
        osm_type=el.get("type"),
        osm_id=el.get("id"),
        tags=tags,
    )


def fetch_providers(
    limit: int,
    retries_per_endpoint: int = 2,
    request_timeout: int = 120,
    retry_backoff_seconds: float = 2.0,
) -> list[ProviderNormalized]:
    bbox = geocode_tucuman()
    query = build_overpass_query(bbox)

    last_error: Exception | None = None
    data: dict[str, Any] | None = None

    for endpoint in OVERPASS_URLS:
        for attempt in range(1, retries_per_endpoint + 2):
            try:
                data = http_post_form_json(endpoint, {"data": query}, timeout=request_timeout)
                break
            except Exception as exc:
                last_error = exc
                print(f"⚠️ Endpoint falló ({endpoint}) intento {attempt}/{retries_per_endpoint + 1}: {exc}")
                if attempt <= retries_per_endpoint:
                    time.sleep(retry_backoff_seconds)
        if data is not None:
            break

    if data is None:
        raise RuntimeError(f"Fallaron todos los endpoints Overpass: {last_error}")

    elements = data.get("elements", [])[:limit]

    providers: list[ProviderNormalized] = []
    seen: set[tuple[str, int | None]] = set()

    for el in elements:
        provider = to_provider(el)
        key = (provider.name.lower().strip(), provider.osm_id)
        if not provider.name.strip() or key in seen:
            continue
        seen.add(key)
        providers.append(provider)

    return providers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="data/providers_real.json")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay entre requests")
    parser.add_argument("--request-timeout", type=int, default=120)
    parser.add_argument("--retries-per-endpoint", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    args = parser.parse_args()

    providers = fetch_providers(
        limit=args.limit,
        retries_per_endpoint=args.retries_per_endpoint,
        request_timeout=args.request_timeout,
        retry_backoff_seconds=args.retry_backoff,
    )

    time.sleep(args.sleep)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([p.model_dump() for p in providers], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ Proveedores normalizados: {len(providers)}")
    print(f"📄 Archivo: {output}")


if __name__ == "__main__":
    main()