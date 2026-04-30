import json
from models.provider import Provider


def load_providers_from_json(path: str) -> list[Provider]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    providers = []

    for item in data:
        provider = Provider(
            name=item["name"],
            address=item["address"],
            lat=item.get("lat", 0),
            lng=item.get("lng", 0),
            rating=item.get("rating"),
            reviews_count=item.get("reviews_count"),
            category=item.get("category", ""),
            products=item.get("products", [])  
        )
        providers.append(provider)

    return providers