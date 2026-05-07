import argparse
import sys
from pathlib import Path

from agents.coordinator_agent import CoordinatorAgent
from collector.json_loader import load_providers_from_json
from scoring.scorer import asignar_scores, calcular_score_total


def filtrar_providers(providers, query):
    if not query:
        return [(p, 0) for p in providers]

    query = query.lower()

    keywords = {
        "limpieza": ["limpieza", "higiene", "clean"],
        "mayorista": ["mayorista", "distribuidor"],
        "lavandina": ["lavandina", "cloro", "lejia"],
    }

    palabras_clave = keywords.get(query, [query])

    scored = []

    for p in providers:
        score = 0

        # prioridad máxima: productos
        if any(palabra in [prod.lower() for prod in p.products] for palabra in palabras_clave):
            score = 10

        # match en nombre
        elif any(palabra in p.name.lower() for palabra in palabras_clave):
            score = 5

        # match en categoría
        elif any(palabra in p.category.lower() for palabra in palabras_clave):
            score = 2

        if score > 0:
            scored.append((p, score))

    # ordenar por relevancia
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored


def _providers_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "providers.json"


def _print_agent_recommendations(result: dict) -> None:
    pipeline = result.get("pipeline", {})
    ingestion = pipeline.get("ingestion", {})
    evaluation = pipeline.get("evaluation", {})

    print(f"\n🔎 Ranking de proveedores (prioridad: {evaluation.get('priority')})")
    print(f"📄 Fuente: {ingestion.get('source_path')}")
    print(f"💰 Proveedores con price_items: {ingestion.get('priced_count', 0)}")
    if evaluation.get("product_query"):
        print(f"🔍 Producto: {evaluation.get('product_query')}")
        print(f"🎯 Proveedores con precio coincidente: {evaluation.get('matched_provider_count', 0)}")

    for warning in pipeline.get("warnings", []):
        print(f"⚠️ {warning}")
    print("")

    for index, provider in enumerate(result.get("recommendations", []), start=1):
        print(f"{index}. {provider['name']}")
        print(f"   📍 Dirección: {provider['address']}")
        print(f"   🏷️ Categoría: {provider['category']}")
        print(f"   ☎️ Teléfono: {provider['phone']}")
        best_price = provider.get("best_matched_price")
        if best_price:
            print(
                "   💵 Mejor precio: "
                f"{best_price.get('product_name')} - {best_price.get('price')} {best_price.get('currency', '')}"
            )
        print(f"   🧠 Scores: {provider['scores']}")
        print("")


def _legacy_main(args) -> int:
    providers = load_providers_from_json(str(_providers_path()))

    filtered = filtrar_providers(providers, args.query)

    if not filtered:
        print("\n❌ No se encontraron proveedores para esa búsqueda\n")
        return 0

    providers = [p for p, _ in filtered]
    relevance_map = {p.name: score for p, score in filtered}

    asignar_scores(providers)

    ranked = sorted(
        providers,
        key=lambda p: (relevance_map.get(p.name, 0) * 8 + calcular_score_total(p, args.priority)),
        reverse=True,
    )

    print(f"\n🔎 Ranking de proveedores (prioridad: {args.priority})")
    if args.query:
        print(f"🔍 Búsqueda: {args.query}")
    print("")

    for i, p in enumerate(ranked, start=1):
        score_total = calcular_score_total(p, args.priority)
        relevance = relevance_map.get(p.name, 0)

        print(f"{i}. {p.name}")
        print(f"   📍 Dirección: {p.address}")
        print(f"   ⭐ Rating: {p.rating}")
        print(f"   🧠 Score total: {score_total:.2f}")
        print(f"   🔍 Relevancia: {relevance}")
        print(f"   🏷️ Categoría: {p.category}")

        if args.priority == "calidad":
            print("   ✔️ Destaca por su reputación")
        elif args.priority == "precio":
            print("   ✔️ Buena opción económica")
        elif args.priority == "volumen":
            print("   ✔️ Ideal para compras grandes")

        print("")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority", default="calidad", choices=["calidad", "precio", "volumen"])
    parser.add_argument("--query", default="")
    parser.add_argument("--source", default="", help="JSON de proveedores; si se omite usa la prioridad automática de IngestionAgent")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--legacy", action="store_true", help="Usa el ranking histórico basado sólo en data/providers.json")
    args = parser.parse_args()

    if args.legacy:
        return _legacy_main(args)

    result = CoordinatorAgent().run(
        {
            "source_path": args.source,
            "priority": args.priority,
            "product_query": args.query,
            "top_n": args.top_n,
        }
    )
    if not result.get("ok"):
        print(f"❌ Error en {result.get('stage')}: {result.get('error')}")
        return 1

    _print_agent_recommendations(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())