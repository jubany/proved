import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.attach_product_prices import load_json_list, merge_prices


def test_load_json_list_accepts_provider_object_with_root_key(tmp_path):
    source = tmp_path / "providers.json"
    source.write_text(json.dumps({"providers": [{"name": "Basualdo Mayorista"}]}), encoding="utf-8")

    assert load_json_list(source, root_key="providers") == [{"name": "Basualdo Mayorista"}]


def test_merge_prices_attaches_lavandina_to_matching_provider_names():
    providers = [
        {"name": "Basualdo Mayorista", "price_items": []},
        {"name": "San Cayetano Mayorista"},
    ]
    prices = [
        {"provider_name": "Basualdo Mayorista", "product_name": "Lavandina 5L", "price": 2500},
        {"provider_name": "San Cayetano Mayorista", "product_name": "Lavandina 5L", "price": 2350},
    ]

    enriched, matched_count, unmatched_names = merge_prices(providers, prices)

    assert matched_count == 2
    assert unmatched_names == []
    assert enriched[0]["price_items"][0]["product_name"] == "Lavandina 5L"
    assert enriched[1]["price_items"][0]["price"] == 2350.0
