from typing import Any

from .base import BaseAgent
from .evaluation_agent import EvaluationAgent
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

        return {
            "ok": True,
            "pipeline": {
                "ingestion": {"count": ingested["count"]},
                "evaluation": {
                    "priority": evaluated["priority"],
                    "count": evaluated["count"],
                    "product_query": evaluated.get("product_query", ""),
                },
                "recommendation": {
                    "top_n": recommended["top_n"],
                    "count": len(recommended["recommendations"]),
                },
            },
            "recommendations": recommended["recommendations"],
        }
