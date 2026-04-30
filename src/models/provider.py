from dataclasses import dataclass
from typing import Optional


@dataclass
class Provider:
    name: str
    address: str
    lat: float
    lng: float
    rating: Optional[float]
    reviews_count: Optional[int]
    category: str
    products: list[str]  #

    # scores
    calidad_score: float = 0
    precio_score: float = 0
    volumen_score: float = 0