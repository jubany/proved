# PRP: Sistema de recomendación de proveedores de limpieza en Tucumán

## Objetivo
Desarrollar una herramienta que recolecte, procese y recomiende proveedores de artículos de limpieza en Tucumán, Argentina, optimizando la elección según criterios definidos por el usuario (precio, calidad, volumen).

---

## Definición de datos

Estructura del proveedor:

{
  "name": string,
  "address": string,
  "location": {
    "lat": float,
    "lng": float
  },
  "rating": float,
  "reviews_count": int,
  "phone": string | null,
  "website": string | null,
  "category": string
}

---

## Inputs del sistema

- query: tipo de producto (ej: "artículos de limpieza")
- priority:
  - "precio"
  - "calidad"
  - "volumen"

---

## Paso 1: Recolección de datos

- Utilizar fuente primaria:
  - Google Places API (o simulación inicial)

- Buscar:
  - proveedores en Tucumán relacionados a limpieza

- Limitar resultados iniciales (ej: top 20)

---

## Paso 2: Limpieza y normalización

- Eliminar duplicados
- Asegurar estructura uniforme
- Completar valores faltantes con null

---

## Paso 3: Filtrado

- Filtrar solo negocios relevantes:
  - keywords: limpieza, distribuidor, mayorista

- Eliminar:
  - negocios no relacionados

---

## Paso 4: Scoring (evaluación)

Definir puntajes:

- Calidad_score = rating * log(reviews_count + 1)

- Precio_score (estimado):
  - mayoristas → puntaje alto
  - minoristas → puntaje medio

- Volumen_score:
  - basado en categoría del negocio

---

## Paso 5: Ranking dinámico

Según input del usuario:

- Si prioridad = "calidad":
  ordenar por Calidad_score

- Si prioridad = "precio":
  ordenar por Precio_score

- Si prioridad = "volumen":
  ordenar por Volumen_score

---

## Paso 6: Output

Formato:

[
  {
    "rank": int,
    "name": string,
    "address": string,
    "rating": float,
    "reason": string
  }
]

---

## Ejemplo de output

1. Distribuidora Limpieza Norte
   - Rating: 4.5
   - Motivo: alta reputación y volumen mayorista

---

## Validación

- ¿Los resultados pertenecen a Tucumán?
- ¿Los datos tienen estructura correcta?
- ¿El ranking cambia según prioridad?

---

## Casos de prueba

Input:
- "lavandina"
- prioridad: "calidad"

Esperado:
- proveedores con mayor rating primero

---

## Manejo de errores

- Sin resultados → devolver mensaje claro
- Datos incompletos → ignorar o marcar como parcial

---

## Iteraciones futuras

- Integrar scraping de sitios web
- Agregar redes sociales
- Mejorar estimación de precios