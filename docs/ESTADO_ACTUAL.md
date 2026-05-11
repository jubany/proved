# Estado actual del proyecto (2026-05-04)

## Qué hace hoy
- Carga proveedores desde `data/providers.json`.
- Permite priorizar ranking por `calidad`, `precio` o `volumen`.
- Permite filtrar por búsqueda (`--query`) con scoring de relevancia.

## Actualización aplicada
- Se corrigió la carga del JSON para usar una ruta robusta basada en `Path(__file__)`.
- Esto evita errores por directorio de ejecución (por ejemplo, correr desde la raíz del repo vs `src/`).

## Salud técnica rápida
- Estructura simple y clara para un MVP.
- Falta cobertura de tests para `src/main.py`.
- El README principal sigue siendo muy genérico (template de Context Engineering) y no refleja completamente este caso de uso.

## Propuesta para empezar con agentes
1. **Agente Ingesta**
   - Recibe nuevos proveedores (CSV/JSON) y normaliza campos.
2. **Agente Evaluador**
   - Calcula scores con reglas y/o señales adicionales (SLA, tiempos, zona).
3. **Agente Recomendador**
   - Responde consultas en lenguaje natural (ej: "necesito lavandina por precio").
4. **Agente Validador**
   - Verifica calidad de datos y ejecuta checks antes de publicar ranking.

## Próximo sprint sugerido
- Agregar tests unitarios para filtros y ranking.
- Definir contrato de entrada de proveedores (schema Pydantic).
- Crear comando de "diagnóstico" (conteo de proveedores, categorías y campos faltantes).

## Mejora de scoring para datos reales OSM
- El scoring ya no depende únicamente de `rating` y `reviews_count`: cuando esos campos no existen, `calidad_score` usa completitud de datos (domicilio, coordenadas, teléfono, web/redes, productos y tags OSM).
- `precio_score` ahora favorece señales B2B como `mayorista`, `wholesale`, `distribuidor/distribuidora` y deja preparado el campo `price_items` para comparar precios cuando se carguen listas de productos.
- `volumen_score` prioriza proveedores mayoristas/distribuidores y señales de catálogo (`products`).
- Las recomendaciones ahora exponen domicilio, teléfono, web, redes, productos, precios cargados (`price_items`) y desglose de scores.

## Pendiente para comparación real de precios
- OSM no suele traer precios de productos. Para comparar "el más barato" necesitamos incorporar una fuente adicional: carga manual CSV/JSON, scraping autorizado, listas de precios de proveedores o integración futura con formularios.

## Enriquecimiento manual con precios
- Se agregó un ejemplo de lista de precios en `data/product_prices.example.json`.
- El script `src/scripts/attach_product_prices.py` une precios por `provider_name` y genera `data/providers_real_b2b_priced.json`.
- `IngestionAgent` prioriza el archivo con precios (`providers_real_b2b_priced.json`) antes del B2B sin precios.
- Las recomendaciones exponen `cheapest_price_items` para empezar a comparar productos baratos dentro de cada proveedor.

## Ranking por producto específico
- `CoordinatorAgent` acepta `product_query` para ordenar por precio cuando `priority="precio"`.
- `EvaluationAgent` busca coincidencias en `price_items.product_name` y prioriza el proveedor con el menor precio encontrado para ese producto.
- `RecommendationAgent` devuelve `matched_price_items` y `best_matched_price` para mostrar qué producto/precio justificó el ranking.
