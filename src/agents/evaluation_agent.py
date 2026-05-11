import unicodedata
from typing import Any

from models.provider import Provider
from ranking.ranker import rankear
from scoring.scorer import asignar_scores, calcular_score_total

from .base import BaseAgent


def _normalize_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def _provider_price_items(provider: Provider) -> list[dict[str, Any]]:
    price_items = getattr(provider, "price_items", []) or []
    return [item for item in price_items if isinstance(item, dict)]


def _price_value(item: dict[str, Any]) -> float:
    try:
        return float(item.get("price", 0))
    except (TypeError, ValueError):
        return float("inf")


def matched_price_items(provider: Provider, product_query: str) -> list[dict[str, Any]]:
    query = _normalize_query(product_query)
    if not query:
        return []

    matches = []
    for item in _provider_price_items(provider):
        searchable_parts = [
            str(item.get("product_name") or ""),
            str(item.get("name") or ""),
            str(item.get("category") or ""),
            str(item.get("unit") or ""),
        ]
        searchable_text = _normalize_query(" ".join(searchable_parts))
        if query in searchable_text:
            matches.append(item)

    return sorted(matches, key=_price_value)


def best_matched_price(provider: Provider, product_query: str) -> float | None:
    matches = matched_price_items(provider, product_query)
    if not matches:
        return None
    return _price_value(matches[0])


class EvaluationAgent(BaseAgent):
    """Subagente que calcula scores y arma ranking por prioridad."""

    name = "evaluation_agent"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        providers = payload.get("providers", [])
        priority = payload.get("priority", "calidad")
        product_query = payload.get("product_query", "")

        if not providers:
            return {"ok": False, "error": "providers es requerido"}

        asignar_scores(providers)

        if product_query and priority == "precio":
            ranked = sorted(
                providers,
                key=lambda provider: (
                    best_matched_price(provider, product_query) is None,
                    best_matched_price(provider, product_query) or float("inf"),
                    -calcular_score_total(provider, priority),
                ),
            )
        else:
            ranked = rankear(providers, priority=priority)

        return {
            "ok": True,
            "ranked": ranked,
            "priority": priority,
            "product_query": product_query,
            "count": len(ranked),
        }
