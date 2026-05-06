"""Filtra proveedores B2B desde un JSON ya generado.

Sirve como paso seguro cuando ya existe `data/providers_real.json` y se quiere
recrear `data/providers_real_b2b.json` sin volver a consultar Overpass.

Uso Git Bash / Linux / macOS:
python src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json

Uso Windows con py launcher:
py src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

B2B_PATTERN = re.compile(r"(mayorista|distribuidora|distribuidor|limpieza|higiene)", re.I)


def _tags_text(tags: Any) -> str:
    if not isinstance(tags, dict):
        return ""
    return " ".join(str(value) for value in tags.values())


def is_b2b_provider(provider: dict[str, Any]) -> bool:
    searchable = " ".join(
        [
            str(provider.get("name") or ""),
            str(provider.get("category") or ""),
            _tags_text(provider.get("tags")),
        ]
    )
    return bool(B2B_PATTERN.search(searchable))


def dedupe_providers(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    seen: set[tuple[str, Any]] = set()

    for provider in providers:
        name = str(provider.get("name") or "").strip()
        key = (name.lower(), provider.get("osm_id"))
        if not name or key in seen:
            continue
        seen.add(key)
        clean.append(provider)

    return clean


def write_json_atomic(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(payload)
        tmp_path = Path(tmp_file.name)
    tmp_path.replace(path)


def filter_b2b(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as file:
        providers = json.load(file)

    if not isinstance(providers, list):
        raise ValueError(f"{input_path} debe contener una lista JSON")

    b2b_providers = dedupe_providers([provider for provider in providers if is_b2b_provider(provider)])
    write_json_atomic(output_path, b2b_providers)
    return b2b_providers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/providers_real.json")
    parser.add_argument("--output", default="data/providers_real_b2b.json")
    args = parser.parse_args()

    b2b_providers = filter_b2b(Path(args.input), Path(args.output))

    print(f"✅ Proveedores B2B: {len(b2b_providers)}")
    print(f"📄 Archivo B2B: {args.output}")
    print("muestra:", [provider.get("name") for provider in b2b_providers[:8]])


if __name__ == "__main__":
    main()