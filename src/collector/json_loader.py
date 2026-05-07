import json
from typing import Any

from models.provider import Provider


PHONE_KEYS = ("phone", "contact:phone", "contact:mobile", "mobile")
WEBSITE_KEYS = ("website", "contact:website", "url")
SOCIAL_KEYS = (
    "facebook",
    "contact:facebook",
    "instagram",
    "contact:instagram",
    "twitter",
    "contact:twitter",
    "linkedin",
    "contact:linkedin",
)


def _first_tag_value(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    tags = item.get("tags") or {}
    for key in keys:
        value = item.get(key) or tags.get(key)
        if value:
            return str(value)
    return ""


def _social_links(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags") or {}
    values = []
    for key in SOCIAL_KEYS:
        value = item.get(key) or tags.get(key)
        if value:
            values.append(str(value))
    return values


def _provider_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        if "providers" not in data:
            raise ValueError("El objeto JSON debe incluir la clave 'providers'")
        data = data["providers"]
    if not isinstance(data, list):
        raise ValueError("El JSON de proveedores debe ser una lista o un objeto con clave 'providers'")
    invalid_items = [index for index, item in enumerate(data) if not isinstance(item, dict)]
    if invalid_items:
        raise ValueError(f"El JSON contiene proveedores que no son objetos: {invalid_items[:10]}")
    return data


def _price_items(item: dict[str, Any]) -> list[dict[str, Any]]:
    price_items = item.get("price_items") or item.get("prices") or item.get("product_prices") or []
    if not isinstance(price_items, list):
        return []

    normalized_items = []
    for price_item in price_items:
        if not isinstance(price_item, dict):
            continue
        normalized_item = dict(price_item)
        if "product_name" not in normalized_item and normalized_item.get("name"):
            normalized_item["product_name"] = normalized_item["name"]
        normalized_items.append(normalized_item)
    return normalized_items


def load_providers_from_json(path: str) -> list[Provider]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    providers = []

    for item in _provider_items(data):
        provider = Provider(
            name=item["name"],
            address=item["address"],
            lat=item.get("lat", 0),
            lng=item.get("lng", 0),
            rating=item.get("rating"),
            reviews_count=item.get("reviews_count"),
            category=item.get("category", ""),
            products=item.get("products", []),
            phone=_first_tag_value(item, PHONE_KEYS),
            website=_first_tag_value(item, WEBSITE_KEYS),
            social_links=item.get("social_links") or _social_links(item),
            price_items=_price_items(item),
            tags=item.get("tags", {}),
        )
        providers.append(provider)

    return providers