import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts import fetch_prices_auto


def test_fetch_mercadolibre_providers_groups_items_by_seller(monkeypatch):
    products = [
        {
            "product_name": "Lavandina 5L",
            "unit": "unidad",
            "ml_query": "lavandina 5 litros mayorista",
            "ml_category": "MLA1246",
        }
    ]

    def fake_search(query, category, limit, timeout):
        assert query == "lavandina 5 litros mayorista"
        assert category == "MLA1246"
        return {
            "results": [
                {
                    "id": "MLA1",
                    "title": "Lavandina 5 litros pack",
                    "price": 4200,
                    "currency_id": "ARS",
                    "permalink": "https://example.test/mla1",
                    "seller": {"id": 99, "nickname": "MAYORISTA_ONLINE"},
                },
                {
                    "id": "MLA2",
                    "title": "Lavandina 5L oferta",
                    "price": "3900",
                    "seller": {"id": 99, "nickname": "MAYORISTA_ONLINE"},
                },
            ]
        }

    monkeypatch.setattr(fetch_prices_auto, "fetch_mercadolibre_search", fake_search)

    providers = fetch_prices_auto.fetch_mercadolibre_providers(products, limit=50, timeout=1)

    assert len(providers) == 1
    assert providers[0]["name"] == "MercadoLibre - MAYORISTA_ONLINE"
    assert len(providers[0]["price_items"]) == 2
    assert providers[0]["price_items"][1]["price"] == 3900.0


def test_merge_provider_sources_deduplicates_by_source_key():
    first = {
        "name": "SEPA A",
        "category": "sepa_branch",
        "products": ["Lavandina 1L"],
        "price_items": [{"product_name": "Lavandina 1L", "price": 1200}],
        "tags": {"source": "sepa_api", "sepa_branch_id": "10"},
    }
    second = {
        "name": "SEPA A actualizado",
        "category": "sepa_branch",
        "products": ["Detergente 1L"],
        "price_items": [{"product_name": "Detergente 1L", "price": 1500}],
        "tags": {"source": "sepa_api", "sepa_branch_id": "10"},
    }
    ml = {
        "name": "MercadoLibre - Seller",
        "category": "marketplace_online",
        "products": ["Lavandina 5L"],
        "price_items": [{"product_name": "Lavandina 5L", "price": 3900}],
        "tags": {"source": "mercadolibre_api", "ml_seller_key": "99"},
    }

    providers = fetch_prices_auto.merge_provider_sources([[first], [second], [ml]])

    assert len(providers) == 2
    assert providers[0]["products"] == ["Lavandina 1L", "Detergente 1L"]
    assert len(providers[0]["price_items"]) == 2
