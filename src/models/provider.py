from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Provider:
    name: str
    address: str
    lat: float
    lng: float
    rating: Optional[float]
    reviews_count: Optional[int]
    category: str
    products: list[str]

    phone: str = ""
    website: str = ""
    social_links: list[str] = field(default_factory=list)
    price_items: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)

    # scores
    calidad_score: float = 0
    precio_score: float = 0
    volumen_score: float = 0
