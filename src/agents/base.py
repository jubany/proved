from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Contrato mínimo para cualquier agente del sistema."""

    name: str

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta el agente con un payload y retorna un resultado serializable."""
        raise NotImplementedError
