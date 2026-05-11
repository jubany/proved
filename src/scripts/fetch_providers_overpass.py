"""Descarga proveedores reales de Tucumán usando Overpass + Nominatim.

Uso Linux/macOS:
PYTHONPATH=src python3 src/scripts/fetch_providers_overpass.py --limit 100 --output data/providers_real.json --b2b-output data/providers_real_b2b.json

Uso Windows Git Bash (py launcher):
export PYTHONPATH="$PWD/src"
py src/scripts/fetch_providers_overpass.py --limit 100 --output data/providers_real.json --b2b-output data/providers_real_b2b.json
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
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
B2B_PATTERN = re.compile(r"(mayorista|distribuidora|distribuidor|limpieza|higiene)", re.I)


def http_get_json(url: str, timeout: int = 60) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:  # nosec B310
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
        with urlopen(req, timeout=timeout) as response:  # nosec B310
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


def build_address(tags: dict[str, Any]) -> str:
    if tags.get("addr:full"):
        return str(tags["addr:full"])

    street = str(tags.get("addr:street") or "").strip()
    house_number = str(tags.get("addr:housenumber") or "").strip()
    city = str(tags.get("addr:city") or "").strip()
    state = str(tags.get("addr:state") or "").strip()

    street_line = " ".join(part for part in (street, house_number) if part)
    return ", ".join(part for part in (street_line, city, state) if part)


def first_tag_value(tags: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        if tags.get(key):
            return str(tags[key])
    return ""


def social_links(tags: dict[str, Any]) -> list[str]:
    keys = (
        "facebook",
        "contact:facebook",
        "instagram",
        "contact:instagram",
        "twitter",
        "contact:twitter",
        "linkedin",
        "contact:linkedin",
    )
    return [str(tags[key]) for key in keys if tags.get(key)]


def normalize_category(tags: dict[str, Any]) -> str:
    raw_category = str(tags.get("shop") or tags.get("wholesale") or tags.get("office") or "").lower()
    name = str(tags.get("name") or "")
    description = str(tags.get("description") or "")
    searchable = " ".join([raw_category, name, description])

    if re.search(r"mayorista|wholesale", searchable, re.I):
        return "mayorista"
    if re.search(r"distribuidora|distribuidor", searchable, re.I):
        return "distribuidor"
    if re.search(r"limpieza|higiene", searchable, re.I):
        return "limpieza"
    return raw_category


def to_provider(el: dict[str, Any]) -> ProviderNormalized:
    tags = el.get("tags", {})
    center = el.get("center", {})
    lat = el.get("lat", center.get("lat", 0.0))
    lng = el.get("lon", center.get("lon", 0.0))

    products: list[str] = []
    for key in ("product", "products"):
        if tags.get(key):
            products.extend([p.strip() for p in tags[key].split(";") if p.strip()])

    return ProviderNormalized(
        name=tags.get("name", ""),
        address=build_address(tags),
        lat=float(lat or 0.0),
        lng=float(lng or 0.0),
        rating=None,
        reviews_count=None,
        category=normalize_category(tags),
        products=products,
        phone=first_tag_value(tags, ("phone", "contact:phone", "contact:mobile", "mobile")),
        website=first_tag_value(tags, ("website", "contact:website", "url")),
        social_links=social_links(tags),
        price_items=[],
        source="osm",
        osm_type=el.get("type"),
        osm_id=el.get("id"),
        tags=tags,
    )


def is_b2b_provider(provider: ProviderNormalized) -> bool:
    tag_values = " ".join(str(value) for value in provider.tags.values())
    searchable = " ".join([provider.name, provider.category, tag_values])
    return bool(B2B_PATTERN.search(searchable))


def dedupe_providers(providers: list[ProviderNormalized]) -> list[ProviderNormalized]:
    clean: list[ProviderNormalized] = []
    seen: set[tuple[str, int | None]] = set()
    for provider in providers:
        key = (provider.name.lower().strip(), provider.osm_id)
        if not provider.name.strip() or key in seen:
            continue
        seen.add(key)
        clean.append(provider)
    return clean


def write_json_atomic(path: Path, providers: list[ProviderNormalized]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([p.model_dump() for p in providers], ensure_ascii=False, indent=2)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


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
            except Exception as exc:  # pragma: no cover
                last_error = exc
                print(
                    f"⚠️ Endpoint falló ({endpoint}) intento "
                    f"{attempt}/{retries_per_endpoint + 1}: {exc}"
                )
                if attempt <= retries_per_endpoint:
                    time.sleep(retry_backoff_seconds)
        if data is not None:
            break

    if data is None:
        raise RuntimeError(f"Fallaron todos los endpoints Overpass: {last_error}")

    elements = data.get("elements", [])[:limit]
    return dedupe_providers([to_provider(el) for el in elements])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="data/providers_real.json")
    parser.add_argument(
        "--b2b-output",
        default="data/providers_real_b2b.json",
        help="Archivo JSON filtrado para mayoristas/distribuidores/limpieza",
    )
    parser.add_argument("--only-b2b", action="store_true", help="Escribe solo datos B2B en --output")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay posterior a la consulta")
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=120,
        help="Timeout en segundos para cada request HTTP a Overpass",
    )
    parser.add_argument(
        "--retries-per-endpoint",
        type=int,
        default=2,
        help="Reintentos por endpoint Overpass además del primer intento",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=2.0,
        help="Segundos de espera entre reintentos",
    )
    args = parser.parse_args()

    try:
        providers = fetch_providers(
            limit=args.limit,
            retries_per_endpoint=args.retries_per_endpoint,
            request_timeout=args.request_timeout,
            retry_backoff_seconds=args.retry_backoff,
        )
    except KeyboardInterrupt:
        print(
            "\n⏹️ Ejecución interrumpida por usuario. "
            "Podés bajar --limit o subir --request-timeout para reintentar."
        )
        raise

    b2b_providers = [provider for provider in providers if is_b2b_provider(provider)]
    output_providers = b2b_providers if args.only_b2b else providers

    write_json_atomic(Path(args.output), output_providers)
    if args.b2b_output:
        write_json_atomic(Path(args.b2b_output), b2b_providers)

    time.sleep(args.sleep)

    print(f"✅ Proveedores normalizados: {len(providers)}")
    print(f"✅ Proveedores B2B: {len(b2b_providers)}")
    print(f"📄 Archivo general: {args.output}")
    if args.b2b_output:
        print(f"📄 Archivo B2B: {args.b2b_output}")


if __name__ == "__main__":
    main()
