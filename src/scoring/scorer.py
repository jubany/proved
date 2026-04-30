from math import log
from models.provider import Provider


def calcular_calidad(p: Provider) -> float:
    if p.rating is None:
        return 0
    return p.rating * log((p.reviews_count or 0) + 1)


def calcular_precio(p: Provider) -> float:
    score = 5
    if "mayorista" in p.category.lower():
        score += 3
    if p.reviews_count and p.reviews_count > 50:
        score += 2
    return score


def calcular_volumen(p: Provider) -> float:
    if "distribuidor" in p.category.lower():
        return 10
    return 5


def asignar_scores(providers: list[Provider]) -> None:
    for p in providers:
        p.calidad_score = calcular_calidad(p)
        p.precio_score = calcular_precio(p)
        p.volumen_score = calcular_volumen(p)


def calcular_score_total(p: Provider, priority: str) -> float:
    if priority == "calidad":
        return p.calidad_score * 0.6 + p.precio_score * 0.2 + p.volumen_score * 0.2
    elif priority == "precio":
        return p.precio_score * 0.6 + p.calidad_score * 0.2 + p.volumen_score * 0.2
    elif priority == "volumen":
        return p.volumen_score * 0.6 + p.calidad_score * 0.2 + p.precio_score * 0.2
    else:
        return p.calidad_score