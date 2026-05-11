import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from models.provider import Provider
from scoring.scorer import asignar_scores, calcular_calidad, calcular_precio, calcular_volumen


def provider(**overrides):
    data = {
        "name": "Basualdo Mayorista",
        "address": "",
        "lat": 0,
        "lng": 0,
        "rating": None,
        "reviews_count": None,
        "category": "supermarket",
        "products": [],
    }
    data.update(overrides)
    return Provider(**data)


def test_price_items_and_mayorista_signal_raise_price_score_above_baseline():
    priced_provider = provider(price_items=[{"product_name": "Lavandina 5L", "price": 2500}])

    assert calcular_precio(priced_provider) > 5.0
    assert calcular_volumen(priced_provider) > 5.0


def test_data_completeness_ignores_placeholder_text_and_rewards_real_contact_data():
    empty_provider = provider(name="Proveedor", address="Sin domicilio disponible", phone="Sin teléfono disponible")
    complete_provider = provider(
        name="Proveedor",
        address="Chacabuco 123",
        phone="03814526210",
        website="https://example.com",
        social_links=["https://instagram.com/example"],
        products=["lavandina"],
        price_items=[{"product_name": "Lavandina 5L", "price": 2350}],
    )

    assert calcular_calidad(empty_provider) == 0.0
    assert calcular_calidad(complete_provider) > calcular_calidad(empty_provider)


def test_asignar_scores_caps_scores_to_ten():
    strong_provider = provider(
        name="Distribuidora Mayorista",
        address="Chacabuco 123",
        lat=-26.8,
        lng=-65.2,
        phone="03814526210",
        category="wholesale distribuidor",
        products=["lavandina", "detergente", "desinfectante"],
        price_items=[
            {"product_name": "Lavandina 5L", "price": 2350},
            {"product_name": "Detergente 5L", "price": 3100},
            {"product_name": "Jabón líquido 5L", "price": 2900},
        ],
        tags={"shop": "wholesale", "phone": "03814526210"},
    )

    asignar_scores([strong_provider])

    assert 0 <= strong_provider.calidad_score <= 10
    assert 0 <= strong_provider.precio_score <= 10
    assert 0 <= strong_provider.volumen_score <= 10
