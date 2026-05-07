"""Valida calidad básica de datos de proveedores.

Uso Git Bash / Linux / macOS:
python src/scripts/validate_providers_data.py --input data/providers_real_b2b.json

Uso Windows con py launcher:
py src/scripts/validate_providers_data.py --input data/providers_real_b2b.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

B2B_PATTERN = re.compile(r"(mayorista|distribuidora|distribuidor|limpieza|higiene|wholesale)", re.I)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} debe contener una lista JSON")

    invalid_items = [idx for idx, item in enumerate(data) if not isinstance(item, dict)]
    if invalid_items:
        raise ValueError(f"{path} contiene items que no son objetos JSON: {invalid_items[:10]}")

    return data


def _tags_text(tags: Any) -> str:
    if not isinstance(tags, dict):
        return ""
    return " ".join(str(value) for value in tags.values())


def is_b2b_candidate(provider: dict[str, Any]) -> bool:
    searchable = " ".join(
        [
            str(provider.get("name") or ""),
            str(provider.get("category") or ""),
            _tags_text(provider.get("tags")),
        ]
    )
    return bool(B2B_PATTERN.search(searchable))


def build_report(providers: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(provider.get("name") or "").strip() for provider in providers]
    normalized_names = [name.lower() for name in names if name]
    duplicate_names = sorted(name for name, count in Counter(normalized_names).items() if count > 1)

    categories = Counter(str(provider.get("category") or "N/A") for provider in providers)
    b2b_candidates = [provider for provider in providers if is_b2b_candidate(provider)]

    return {
        "total": len(providers),
        "missing_name": sum(1 for name in names if not name),
        "missing_address": sum(1 for provider in providers if not provider.get("address")),
        "categories": categories.most_common(),
        "duplicate_names": duplicate_names,
        "b2b_candidates": len(b2b_candidates),
        "non_b2b_candidates": len(providers) - len(b2b_candidates),
    }


def print_report(input_path: Path, report: dict[str, Any]) -> None:
    print(f"archivo: {input_path}")
    print(f"total: {report['total']}")
    print(f"sin_nombre: {report['missing_name']}")
    print(f"sin_direccion: {report['missing_address']}")
    print(f"categorias: {report['categories']}")
    print(f"duplicados: {report['duplicate_names']}")
    print(f"b2b_aprox: {report['b2b_candidates']}")
    print(f"no_b2b_aprox: {report['non_b2b_candidates']}")


def validate_report(
    report: dict[str, Any],
    max_missing_name_ratio: float,
    max_non_b2b_ratio: float,
) -> list[str]:
    errors: list[str] = []
    total = report["total"]

    if total == 0:
        return ["El archivo no contiene proveedores"]

    missing_name_ratio = report["missing_name"] / total
    non_b2b_ratio = report["non_b2b_candidates"] / total

    if missing_name_ratio > max_missing_name_ratio:
        errors.append(
            f"Demasiados proveedores sin nombre: {missing_name_ratio:.1%} "
            f"> {max_missing_name_ratio:.1%}"
        )

    if non_b2b_ratio > max_non_b2b_ratio:
        errors.append(
            f"Demasiados proveedores fuera del patrón B2B: {non_b2b_ratio:.1%} "
            f"> {max_non_b2b_ratio:.1%}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/providers_real_b2b.json")
    parser.add_argument("--max-missing-name-ratio", type=float, default=0.0)
    parser.add_argument("--max-non-b2b-ratio", type=float, default=0.5)
    args = parser.parse_args()

    input_path = Path(args.input)

    try:
        providers = load_json_list(input_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"❌ Error leyendo {input_path}: {exc}")
        return 1

    report = build_report(providers)
    print_report(input_path, report)

    errors = validate_report(
        report,
        max_missing_name_ratio=args.max_missing_name_ratio,
        max_non_b2b_ratio=args.max_non_b2b_ratio,
    )

    if errors:
        print("❌ Validación fallida:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("✅ Validación OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())