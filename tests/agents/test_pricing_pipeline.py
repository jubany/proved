import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agents.coordinator_agent import CoordinatorAgent


def write_providers(tmp_path, providers):
    path = tmp_path / "providers_priced.json"
    path.write_text(json.dumps({"providers": providers}, ensure_ascii=False), encoding="utf-8")
    return path


def base_provider(name, price_items=None):
    return {
        "name": name,
        "address": "Tucumán",
        "lat": 0,
        "lng": 0,
        "rating": None,
        "reviews_count": None,
        "category": "mayorista",
        "products": ["limpieza"],
        "price_items": price_items or [],
    }


def test_price_priority_ranks_matching_product_by_lowest_price(tmp_path):
    source = write_providers(
        tmp_path,
        [
            base_provider("Basualdo Mayorista", [{"product_name": "Lavandína 5L", "price": 2500, "currency": "ARS"}]),
            base_provider("San Cayetano Mayorista", [{"product_name": "Lavandina 5L", "price": 2350, "currency": "ARS"}]),
        ],
    )

    result = CoordinatorAgent().run(
        {"source_path": str(source), "priority": "precio", "product_query": "lavandina", "top_n": 2}
    )

    assert result["ok"] is True
    assert result["pipeline"]["ingestion"]["source_path"] == str(source)
    assert result["pipeline"]["ingestion"]["priced_count"] == 2
    assert result["pipeline"]["evaluation"]["matched_provider_count"] == 2
    assert result["pipeline"]["warnings"] == []
    assert [item["name"] for item in result["recommendations"]] == [
        "San Cayetano Mayorista",
        "Basualdo Mayorista",
    ]
    assert result["recommendations"][0]["best_matched_price"]["price"] == 2350


def test_price_priority_warns_when_loaded_source_has_no_prices(tmp_path):
    source = write_providers(tmp_path, [base_provider("Distribuidora Norte")])

    result = CoordinatorAgent().run(
        {"source_path": str(source), "priority": "precio", "product_query": "lavandina", "top_n": 1}
    )

    assert result["ok"] is True
    assert result["pipeline"]["ingestion"]["priced_count"] == 0
    assert result["pipeline"]["evaluation"]["matched_provider_count"] == 0
    assert "No hay proveedores con price_items" in result["pipeline"]["warnings"][0]
    assert result["recommendations"][0]["best_matched_price"] is None
