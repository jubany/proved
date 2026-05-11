import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.diagnose_pricing_pipeline import run_diagnostics


def test_diagnostics_succeeds_when_priced_source_loads(tmp_path, capsys):
    source = tmp_path / "providers_real_b2b_priced.json"
    source.write_text(
        json.dumps(
            [
                {
                    "name": "San Cayetano Mayorista",
                    "address": "Tucumán",
                    "lat": 0,
                    "lng": 0,
                    "rating": None,
                    "reviews_count": None,
                    "category": "mayorista",
                    "products": ["limpieza"],
                    "price_items": [{"product_name": "Lavandina 5L", "price": 2350, "currency": "ARS"}],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = run_diagnostics(source, "lavandina")
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "raw_providers_with_price_items: 1" in output
    assert "loaded_providers_with_price_items: 1" in output
    assert "✅ Diagnóstico OK" in output


def test_diagnostics_fails_when_source_has_no_price_items(tmp_path, capsys):
    source = tmp_path / "providers_real_b2b_priced.json"
    source.write_text(json.dumps([{"name": "Basualdo Mayorista", "address": ""}]), encoding="utf-8")

    exit_code = run_diagnostics(source, "lavandina")
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "raw_providers_with_price_items: 0" in output
    assert "Reejecutá attach_product_prices.py" in output
