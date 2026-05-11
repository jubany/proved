import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from collector.json_loader import load_providers_from_json


def write_json(tmp_path, payload):
    path = tmp_path / "providers.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_loads_provider_object_and_normalizes_price_aliases(tmp_path):
    path = write_json(
        tmp_path,
        {
            "providers": [
                {
                    "name": "Basualdo Mayorista",
                    "address": "Tucumán",
                    "lat": 0,
                    "lng": 0,
                    "rating": None,
                    "reviews_count": None,
                    "category": "mayorista",
                    "products": ["limpieza"],
                    "prices": [{"name": "Lavandína 5L", "price": 2500, "currency": "ARS"}],
                }
            ]
        },
    )

    providers = load_providers_from_json(str(path))

    assert providers[0].name == "Basualdo Mayorista"
    assert providers[0].price_items == [
        {"name": "Lavandína 5L", "price": 2500, "currency": "ARS", "product_name": "Lavandína 5L"}
    ]


def test_loader_rejects_object_without_providers_key(tmp_path):
    path = write_json(tmp_path, {"items": []})

    with pytest.raises(ValueError, match="providers"):
        load_providers_from_json(str(path))
