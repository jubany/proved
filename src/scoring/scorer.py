from math import log
from typing import Any

from models.provider import Provider

B2B_KEYWORDS = ("mayorista", "wholesale", "distribuidor", "distribuidora")
WHOLESALE_KEYWORDS = ("mayorista", "wholesale")
DISTRIBUTOR_KEYWORDS = ("distribuidor", "distribuidora")
EMPTY_TEXT_VALUES = {
    "",
    "sin domicilio disponible",
    "sin direccion disponible",
    "sin dirección disponible",
    "sin telefono disponible",
    "sin teléfono disponible",
    "none",
    "null",
}


def _provider_attr(p: Provider, attr: str, default: Any) -> Any:
    value = getattr(p, attr, default)
    return value if value is not None else default


def _has_text_value(value: Any) -> bool:
    return str(value or "").strip().lower() not in EMPTY_TEXT_VALUES


def _searchable_text(p: Provider) -> str:
    tags = _provider_attr(p, "tags", {})
    products = _provider_attr(p, "products", [])
    price_items = _valid_price_items(p)
    tag_values = " ".join(str(value) for value in tags.values()) if tags else ""
    price_values = " ".join(str(item.get("product_name", "")) for item in price_items)
    return " ".join(
        [
            str(_provider_attr(p, "name", "")),
            str(_provider_attr(p, "category", "")),
            " ".join(products),
            tag_values,
            price_values,
        ]
    ).lower()


def _has_valid_coordinates(p: Provider) -> bool:
    return bool(_provider_attr(p, "lat", 0) and _provider_attr(p, "lng", 0))


def _valid_price_items(p: Provider) -> list[dict[str, Any]]:
    valid_items = []
    for item in _provider_attr(p, "price_items", []):
        if not isinstance(item, dict):
            continue
        try:
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            continue
        if price >= 0:
            valid_items.append({**item, "price": price})
    return valid_items


def _unique_price_product_count(p: Provider) -> int:
    names = {
        str(item.get("product_name", "")).strip().lower()
        for item in _valid_price_items(p)
        if str(item.get("product_name", "")).strip()
    }
    return len(names)


def _data_completeness_score(p: Provider) -> float:
    score = 0.0
    if _has_text_value(_provider_attr(p, "address", "")):
        score += 2.0
    if _has_valid_coordinates(p):
        score += 2.0
    if _has_text_value(_provider_attr(p, "phone", "")):
        score += 1.5
    if _has_text_value(_provider_attr(p, "website", "")):
        score += 1.0
    if _provider_attr(p, "social_links", []):
        score += 1.0
    if _provider_attr(p, "products", []):
        score += 1.0
    if _valid_price_items(p):
        score += 1.0
    tags = _provider_attr(p, "tags", {})
    if tags:
        score += min(len(tags) / 10, 2.0)
    return min(score, 10.0)


def calcular_calidad(p: Provider) -> float:
    # Si hay rating/reviews, mantenemos la señal original pero la acotamos a una escala 0-10.
    rating = _provider_attr(p, "rating", None)
    if rating is not None:
        return min(rating * log((_provider_attr(p, "reviews_count", 0) or 0) + 1), 10.0)

    # En OSM normalmente no hay rating/reviews, así que usamos completitud de datos.
    return _data_completeness_score(p)


def calcular_precio(p: Provider) -> float:
    score = 5.0
    text = _searchable_text(p)
    price_items = _valid_price_items(p)

    if any(keyword in text for keyword in WHOLESALE_KEYWORDS):
        score += 2.5
    if any(keyword in text for keyword in DISTRIBUTOR_KEYWORDS):
        score += 1.5
    if "supermarket" in text:
        score += 0.5
    if price_items:
        # Tener lista de precios es una señal fuerte para comparar precio real.
        score += 2.0
        score += min(_unique_price_product_count(p), 3) * 0.4
    reviews_count = _provider_attr(p, "reviews_count", None)
    if reviews_count and reviews_count > 50:
        score += 1.0

    return min(score, 10.0)


def calcular_volumen(p: Provider) -> float:
    text = _searchable_text(p)
    score = 5.0

    if any(keyword in text for keyword in DISTRIBUTOR_KEYWORDS):
        score += 3.0
    if any(keyword in text for keyword in WHOLESALE_KEYWORDS):
        score += 2.0
    if "supermarket" in text:
        score += 0.5
    products = _provider_attr(p, "products", [])
    if products:
        score += min(len(products), 2)
    if _valid_price_items(p):
        score += min(_unique_price_product_count(p), 3) * 0.5

    return min(score, 10.0)


def asignar_scores(providers: list[Provider]) -> None:
    for p in providers:
        p.calidad_score = calcular_calidad(p)
        p.precio_score = calcular_precio(p)
        p.volumen_score = calcular_volumen(p)


def calcular_score_total(p: Provider, priority: str) -> float:
    if priority == "calidad":
        return p.calidad_score * 0.6 + p.precio_score * 0.2 + p.volumen_score * 0.2
    elif priority == "precio":
        return p.precio_score * 0.6 + p.calidad_score * 0.2 + p.volumen_score * 0.2
    elif priority == "volumen":
        return p.volumen_score * 0.6 + p.calidad_score * 0.2 + p.precio_score * 0.2
    else:
        return p.calidad_score
