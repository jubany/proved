import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_fetchprices_alias_imports_auto_main():
    from scripts import fetch_prices_auto, fetchprices

    assert fetchprices.main is fetch_prices_auto.main
