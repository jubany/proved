from models.provider import Provider
from scoring.scorer import calcular_score_total


def rankear(providers: list[Provider], priority: str) -> list[Provider]:
    return sorted(
        providers,
        key=lambda p: calcular_score_total(p, priority),
        reverse=True
    )