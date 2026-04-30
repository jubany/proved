import argparse

from scoring.scorer import asignar_scores, calcular_score_total
from collector.json_loader import load_providers_from_json


def filtrar_providers(providers, query):
    if not query:
        return [(p, 0) for p in providers]

    query = query.lower()

    keywords = {
        "limpieza": ["limpieza", "higiene", "clean"],
        "mayorista": ["mayorista", "distribuidor"],
        "lavandina": ["lavandina", "cloro", "lejia"]
    }

    palabras_clave = keywords.get(query, [query])

    scored = []

    for p in providers:
        score = 0

        # 🔥 prioridad máxima: productos
        if any(palabra in [prod.lower() for prod in p.products] for palabra in palabras_clave):
            score = 10

        # 🔥 match en nombre
        elif any(palabra in p.name.lower() for palabra in palabras_clave):
            score = 5

        # 🔹 match en categoría
        elif any(palabra in p.category.lower() for palabra in palabras_clave):
            score = 2

        if score > 0:
            scored.append((p, score))

    # ordenar por relevancia
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored


def main():
    # CLI
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority", default="calidad", choices=["calidad", "precio", "volumen"])
    parser.add_argument("--query", default="")
    args = parser.parse_args()

    # 1. Cargar datos
    providers = load_providers_from_json("../data/providers.json")

    # 2. Filtrar + relevancia
    filtered = filtrar_providers(providers, args.query)

    if not filtered:
        print("\n❌ No se encontraron proveedores para esa búsqueda\n")
        return

    providers = [p for p, _ in filtered]
    relevance_map = {p.name: score for p, score in filtered}

    # 3. Calcular scores
    asignar_scores(providers)

    # 4. Ranking híbrido (balanceado)
    ranked = sorted(
        providers,
        key=lambda p: (
            relevance_map.get(p.name, 0) * 8 +  # peso relevancia
            calcular_score_total(p, args.priority)
        ),
        reverse=True
    )

    print(f"\n🔎 Ranking de proveedores (prioridad: {args.priority})")
    if args.query:
        print(f"🔍 Búsqueda: {args.query}")
    print("")

    # 5. Output
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


if __name__ == "__main__":
    main()