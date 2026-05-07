from typing import Any
from pydantic import BaseModel, Field


class ProviderNormalized(BaseModel):
    name: str = Field(default="")
    address: str = Field(default="")
    lat: float = Field(default=0.0)
    lng: float = Field(default=0.0)
    rating: float | None = Field(default=None)
    reviews_count: int | None = Field(default=None)
    category: str = Field(default="")
    products: list[str] = Field(default_factory=list)
    source: str = Field(default="osm")
    osm_type: str | None = Field(default=None)
    osm_id: int | None = Field(default=None)
    tags: dict[str, Any] = Field(default_factory=dict)