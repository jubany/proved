from typing import Any

from .base import BaseAgent
from .evaluation_agent import EvaluationAgent, matched_price_items
from .ingestion_agent import IngestionAgent
from .recommendation_agent import RecommendationAgent


class CoordinatorAgent(BaseAgent):
    """Agente orquestador: coordina a los 3 subagentes."""

    name = "coordinator_agent"

    def __init__(self):
        self.ingestion = IngestionAgent()
        self.evaluation = EvaluationAgent()
        self.recommendation = RecommendationAgent()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        ingested = self.ingestion.run({"source_path": payload.get("source_path")})
        if not ingested.get("ok"):
            return {"ok": False, "stage": "ingestion", "error": ingested.get("error")}

        evaluated = self.evaluation.run(
            {
                "providers": ingested["providers"],
                "priority": payload.get("priority", "calidad"),
                "product_query": payload.get("product_query", ""),
            }
        )
        if not evaluated.get("ok"):
            return {"ok": False, "stage": "evaluation", "error": evaluated.get("error")}

        recommended = self.recommendation.run(
            {
                "ranked": evaluated["ranked"],
                "top_n": payload.get("top_n", 3),
                "product_query": payload.get("product_query", ""),
            }
        )
        if not recommended.get("ok"):
            return {"ok": False, "stage": "recommendation", "error": recommended.get("error")}

        providers = ingested["providers"]
        product_query = evaluated.get("product_query", "")
        priced_count = sum(1 for provider in providers if getattr(provider, "price_items", []))
        matched_provider_count = (
            sum(1 for provider in providers if matched_price_items(provider, product_query))
            if product_query
            else 0
        )
        warnings = []
        if product_query and payload.get("priority", "calidad") == "precio" and priced_count == 0:
            warnings.append(
                "No hay proveedores con price_items en la fuente cargada; cargá/adjuntá precios o pasá source_path al JSON enriquecido."
            )
        elif product_query and payload.get("priority", "calidad") == "precio" and matched_provider_count == 0:
            warnings.append(
                f"Hay {priced_count} proveedor(es) con precios, pero ninguno coincide con product_query='{product_query}'."
            )

        return {
            "ok": True,
            "pipeline": {
                "ingestion": {
                    "count": ingested["count"],
                    "source_path": ingested.get("meta", {}).get("source_path"),
                    "priced_count": priced_count,
                },
                "evaluation": {
                    "priority": evaluated["priority"],
                    "count": evaluated["count"],
                    "product_query": product_query,
                    "matched_provider_count": matched_provider_count,
                },
                "recommendation": {
                    "top_n": recommended["top_n"],
                    "count": len(recommended["recommendations"]),
                },
                "warnings": warnings,
            },
            "recommendations": recommended["recommendations"],
        }
