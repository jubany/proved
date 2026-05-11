import json
from pathlib import Path
from typing import Any

from collector.json_loader import load_providers_from_json

from .base import BaseAgent


class IngestionAgent(BaseAgent):
    """Subagente encargado de ingesta y normalización inicial."""

    name = "ingestion_agent"

    @staticmethod
    def _default_sources() -> list[Path]:
        repo_root = Path(__file__).resolve().parents[2]
        return [
            repo_root / "data" / "providers_real_b2b_priced.json",
            repo_root / "data" / "providers_real_b2b.json",
            repo_root / "data" / "providers_real.json",
            repo_root / "data" / "providers.json",
        ]

    @staticmethod
    def _load_source(source: Path) -> dict[str, Any]:
        try:
            providers = load_providers_from_json(str(source))
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"JSON inválido en {source}: {exc}"}
        except OSError as exc:
            return {"ok": False, "error": f"No se pudo leer {source}: {exc}"}

        return {"ok": True, "providers": providers}

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_path = payload.get("source_path")

        if source_path:
            source = Path(source_path)
            if not source.exists():
                return {"ok": False, "error": f"source_path no existe: {source}"}

            loaded = self._load_source(source)
            if not loaded["ok"]:
                return loaded
        else:
            skipped_sources = []
            source = None
            loaded = None

            for candidate in self._default_sources():
                if not candidate.exists():
                    continue

                candidate_loaded = self._load_source(candidate)
                if candidate_loaded["ok"]:
                    source = candidate
                    loaded = candidate_loaded
                    break

                skipped_sources.append(candidate_loaded["error"])

            if source is None or loaded is None:
                return {
                    "ok": False,
                    "error": (
                        "No se encontró un JSON válido en data/providers_real_b2b_priced.json, "
                        "data/providers_real_b2b.json, data/providers_real.json ni data/providers.json"
                    ),
                    "skipped_sources": skipped_sources,
                }

        providers = loaded["providers"]

        return {
            "ok": True,
            "providers": providers,
            "count": len(providers),
            "meta": {"source_path": str(source)},
        }
