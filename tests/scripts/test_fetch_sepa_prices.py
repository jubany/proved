import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts import fetch_sepa_prices


def test_extract_price_items_by_branch_from_precios_producto_shape():
    response = {
        "producto": {"nombre": "Lavandina 1L", "presentacion": "1 lt"},
        "sucursales": [
            {"id": "10", "preciosProducto": {"precioLista": "1200.50"}},
            {"id_sucursal": "11", "preciosProducto": {"precioLista": 1100}},
            {"id": "12", "preciosProducto": {}},
        ],
        "fecha": "2026-05-07",
    }
    product = {"id_producto": "7790520017975", "product_name": "Lavandina", "unit": "unidad", "source": "sepa_api"}

    items = fetch_sepa_prices.extract_price_items_by_branch(response, product)

    assert items["10"]["product_name"] == "Lavandina 1L"
    assert items["10"]["price"] == 1200.50
    assert items["11"]["price"] == 1100.0
    assert "12" not in items


def test_build_priced_providers_uses_sucursales_and_product_prices(monkeypatch):
    branches = [
        {"id": "10", "banderaDescripcion": "Super A", "direccion": "Centro", "lat": -26.8, "lng": -65.2},
        {"id": "11", "banderaDescripcion": "Super B", "direccion": "Norte", "lat": -26.7, "lng": -65.1},
    ]
    products = [{"id_producto": "7790520017975", "product_name": "Lavandina", "unit": "unidad", "source": "sepa_api"}]

    def fake_fetch_producto(product_id, branch_ids, limit, timeout):
        assert product_id == "7790520017975"
        assert branch_ids == ["10", "11"]
        return {
            "producto": {"nombre": "Lavandina 1L"},
            "sucursales": [
                {"id": "10", "preciosProducto": {"precioLista": 1200}},
                {"id": "11", "preciosProducto": {"precioLista": 1150}},
            ],
        }

    monkeypatch.setattr(fetch_sepa_prices, "fetch_producto", fake_fetch_producto)

    providers = fetch_sepa_prices.build_priced_providers(branches, products, timeout=1, limit=2)

    assert [provider["name"] for provider in providers] == ["Super A", "Super B"]
    assert providers[0]["price_items"][0]["price"] == 1200.0
    assert providers[1]["products"] == ["Lavandina 1L"]
