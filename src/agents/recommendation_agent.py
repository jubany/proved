from typing import Any

from .base import BaseAgent
from .evaluation_agent import matched_price_items


class RecommendationAgent(BaseAgent):
    """Subagente para traducir ranking en recomendaciones legibles."""

    name = "recommendation_agent"

    @staticmethod
    def _provider_attr(provider: Any, attr: str, default: Any) -> Any:
        value = getattr(provider, attr, default)
        return value if value not in (None, "") else default

    @staticmethod
    def _price_sort_value(item: Any) -> float:
        if not isinstance(item, dict):
            return float("inf")
        try:
            return float(item.get("price", 0))
        except (TypeError, ValueError):
            return float("inf")

    @classmethod
    def _cheapest_price_items(cls, provider: Any) -> list[dict[str, Any]]:
        price_items = cls._provider_attr(provider, "price_items", [])
        return sorted(price_items, key=cls._price_sort_value)[:5]

    @classmethod
    def _to_recommendation(cls, provider: Any, product_query: str = "") -> dict[str, Any]:
        price_items = cls._provider_attr(provider, "price_items", [])
        matched_items = matched_price_items(provider, product_query) if product_query else []
        return {
            "name": cls._provider_attr(provider, "name", "Sin nombre disponible"),
            "category": cls._provider_attr(provider, "category", "Sin categoría disponible"),
            "rating": getattr(provider, "rating", None),
            "address": cls._provider_attr(provider, "address", "Sin domicilio disponible"),
            "phone": cls._provider_attr(provider, "phone", "Sin teléfono disponible"),
            "website": cls._provider_attr(provider, "website", "Sin web disponible"),
            "social_links": cls._provider_attr(provider, "social_links", []),
            "products": cls._provider_attr(provider, "products", []),
            "price_items": price_items,
            "cheapest_price_items": cls._cheapest_price_items(provider),
            "matched_price_items": matched_items,
            "best_matched_price": matched_items[0] if matched_items else None,
            "scores": {
                "calidad": round(getattr(provider, "calidad_score", 0), 2),
                "precio": round(getattr(provider, "precio_score", 0), 2),
                "volumen": round(getattr(provider, "volumen_score", 0), 2),
            },
            "notes": {
                "prices": (
                    "Comparación por precio aplicada sobre matched_price_items."
                    if matched_items
                    else "Sin coincidencias de precio para product_query; revisá pipeline.ingestion.priced_count y pipeline.evaluation.matched_provider_count."
                ),
            },
        }

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        ranked = payload.get("ranked", [])
        top_n = payload.get("top_n", 3)
        product_query = payload.get("product_query", "")

        if not ranked:
            return {"ok": False, "error": "ranked es requerido"}

        selected = ranked[:top_n]
        recommendations = [self._to_recommendation(provider, product_query) for provider in selected]

        return {
            "ok": True,
            "top_n": top_n,
            "product_query": product_query,
            "recommendations": recommendations,
        }
