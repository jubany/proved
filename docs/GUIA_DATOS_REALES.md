# Guía para generar y validar proveedores reales

Esta guía resume el flujo local para trabajar con proveedores reales de Tucumán usando los scripts del proyecto.

## 1. Confirmar que estás en el repo correcto

Antes de ejecutar scripts, validá que estés parado en el repo `proved` y que existan los archivos esperados:

```bash
pwd
find src/scripts -maxdepth 1 -type f -print
```

> Nota: si tenés `ripgrep` instalado, también podés usar `rg --files src/scripts`. En Git Bash puede no venir instalado por defecto.

Tenés que ver, al menos:

```text
src/scripts/fetch_providers_overpass.py
src/scripts/filter_b2b_providers.py
```

Si `filter_b2b_providers.py` no aparece, tu copia local todavía no tiene los últimos cambios. En ese caso corré:

```bash
git pull
```

Si después de `git pull` sigue sin aparecer, revisá que estés en la rama correcta:

```bash
git branch --show-current
git log --oneline -n 5
```

## 2. Generar datos reales desde Overpass

En Git Bash / Linux / macOS:

```bash
export PYTHONPATH="$PWD/src"
py src/scripts/fetch_providers_overpass.py --limit 40 --output data/providers_real.json --request-timeout 90 --retries-per-endpoint 2 --retry-backoff 2.5
```

Este comando genera `data/providers_real.json`.

## 3. Regenerar el archivo B2B desde datos ya descargados

Si ya existe `data/providers_real.json`, podés crear o recrear `data/providers_real_b2b.json` sin volver a consultar Overpass:

```bash
py src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json
```

Este paso es útil si `providers_real_b2b.json` fue borrado o quedó vacío/corrupto.

## 4. Validar el archivo B2B

```bash
py - <<'PY'
import json

d = json.load(open("data/providers_real_b2b.json", encoding="utf-8"))
print("total_b2b:", len(d))
print("nombres:", [x.get("name") for x in d])
PY
```

## 5. Errores comunes

### `can't open file ... filter_b2b_providers.py`

Significa que el archivo no existe en tu copia local. Solución:

1. Confirmá que estás en `proved`.
2. Ejecutá `git pull`.
3. Verificá con `find src/scripts -maxdepth 1 -type f -print`.


### `bash: rg: command not found`

Significa que tu terminal no tiene instalado `ripgrep`. No es un problema del proyecto. Usá este comando equivalente:

```bash
find src/scripts -maxdepth 1 -type f -print
```

### `git pull` dice `Already up to date`, pero falta el script

Significa que tu rama local está sincronizada con el remoto que tenés configurado, pero ese remoto/rama todavía no contiene el commit donde se agregó el script. Para diagnosticarlo:

```bash
git remote -v
git branch --show-current
git log --oneline -n 5
find src/scripts -maxdepth 1 -type f -print
```

Si el archivo `src/scripts/filter_b2b_providers.py` no aparece en esa lista, tenés que traer la rama/commit que contiene ese archivo o crearlo localmente.

### `FileNotFoundError: data/providers_real_b2b.json`

Significa que el archivo B2B aún no fue generado. Solución:

```bash
py src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json
```

### `JSONDecodeError` al leer `providers_real_b2b.json`

Significa que el archivo existe pero está vacío o corrupto. Solución:

```bash
rm -f data/providers_real_b2b.json
py src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json
```

### `ModuleNotFoundError: No module named 'agents'`

Significa que Python no encuentra el paquete `src/agents`. Hay dos causas comunes:

1. `PYTHONPATH` no quedó configurado para la terminal actual.
2. Tu copia local todavía no tiene la carpeta `src/agents`.

Primero verificá ambas cosas:

```bash
echo "$PYTHONPATH"
find src/agents -maxdepth 1 -type f -print
```

Tenés que ver archivos como:

```text
src/agents/__init__.py
src/agents/coordinator_agent.py
src/agents/ingestion_agent.py
```

Si `find src/agents ...` responde `No such file or directory`, entonces no es un problema de Python: faltan los archivos de agentes en tu repo local. En ese caso, tenés que traer o crear los archivos del paquete `src/agents` antes de correr:

```bash
from agents.coordinator_agent import CoordinatorAgent
```

Si la carpeta existe, reconfigurá `PYTHONPATH` en esa misma terminal y probá de nuevo:

```bash
export PYTHONPATH="$PWD/src"
py - <<'PY'
import sys
print(sys.path[:3])
from agents.coordinator_agent import CoordinatorAgent
print("agents ok")
PY
```

## 6. Validar calidad básica de proveedores

Cuando exista `data/providers_real_b2b.json`, podés correr el validador automático:

```bash
py src/scripts/validate_providers_data.py --input data/providers_real_b2b.json
```

El reporte muestra:

- total de proveedores,
- proveedores sin nombre,
- proveedores sin dirección,
- categorías encontradas,
- duplicados por nombre,
- candidatos B2B aproximados,
- registros que no parecen B2B según nombre/categoría/tags.

Por defecto, el validador falla si:

- el JSON está corrupto,
- el archivo no contiene una lista,
- la lista está vacía,
- hay proveedores sin nombre,
- más del 50% no parece B2B.

Podés ajustar el umbral B2B así:

```bash
py src/scripts/validate_providers_data.py --input data/providers_real_b2b.json --max-non-b2b-ratio 0.75
```

### `can't open file ... validate_providers_data.py` o no encuentra el validador

Significa que tu copia local todavía no tiene el script de validación. Verificalo con:

```bash
find src/scripts -maxdepth 1 -type f -print
```

Tenés que ver:

```text
src/scripts/validate_providers_data.py
```

Si no aparece, hay dos opciones:

1. Traer el commit/rama donde se agregó el archivo.
2. Crear manualmente `src/scripts/validate_providers_data.py` con el contenido del proyecto.

Antes de ejecutar el validador, también confirmá que el archivo de datos existe:

```bash
test -f data/providers_real_b2b.json && echo "B2B existe" || echo "Falta data/providers_real_b2b.json"
```

Si falta `data/providers_real_b2b.json`, regeneralo primero:

```bash
py src/scripts/filter_b2b_providers.py --input data/providers_real.json --output data/providers_real_b2b.json
```

## 7. Adjuntar precios manuales a proveedores B2B

OSM normalmente no trae precios. Para comparar productos baratos, creá una copia real a partir del ejemplo:

```bash
cp data/product_prices.example.json data/product_prices.json
```

Editá `data/product_prices.json` con tus precios reales y después ejecutá:

```bash
py src/scripts/attach_product_prices.py --providers data/providers_real_b2b.json --prices data/product_prices.json --output data/providers_real_b2b_priced.json
```

El archivo `data/providers_real_b2b_priced.json` queda listo para que `IngestionAgent` lo use primero. Si querés que falle cuando un precio no encuentra proveedor, agregá `--strict`.

### `cp: cannot stat 'data/product_prices.example.json'` o no existe el ejemplo de precios

Significa que tu copia local todavía no tiene `data/product_prices.example.json`. Verificalo con:

```bash
find data -maxdepth 1 -type f -name 'product_prices*' -print
```

Si no aparece, podés crear `data/product_prices.json` directamente con este contenido inicial:

```json
[
  {
    "provider_name": "Basualdo Mayorista",
    "product_name": "Lavandina 5L",
    "unit": "unidad",
    "price": 2500,
    "currency": "ARS",
    "updated_at": "2026-05-06",
    "source": "carga_manual"
  },
  {
    "provider_name": "San Cayetano Mayorista",
    "product_name": "Lavandina 5L",
    "unit": "unidad",
    "price": 2350,
    "currency": "ARS",
    "updated_at": "2026-05-06",
    "source": "carga_manual"
  }
]
```

También podés crearlo desde Git Bash con:

```bash
cat > data/product_prices.json <<'JSON'
[
  {
    "provider_name": "Basualdo Mayorista",
    "product_name": "Lavandina 5L",
    "unit": "unidad",
    "price": 2500,
    "currency": "ARS",
    "updated_at": "2026-05-06",
    "source": "carga_manual"
  },
  {
    "provider_name": "San Cayetano Mayorista",
    "product_name": "Lavandina 5L",
    "unit": "unidad",
    "price": 2350,
    "currency": "ARS",
    "updated_at": "2026-05-06",
    "source": "carga_manual"
  }
]
JSON
```

Después editá precios/productos/proveedores según tu información real y ejecutá `attach_product_prices.py`.

## 8. Ranking por producto específico

Cuando ya exista `data/providers_real_b2b_priced.json`, podés pedir ranking por producto:

```bash
export PYTHONPATH="$PWD/src"
py - <<'PY'
from agents.coordinator_agent import CoordinatorAgent

res = CoordinatorAgent().run({"priority": "precio", "product_query": "lavandina", "top_n": 5})
print("ok:", res.get("ok"))
print("pipeline:", res.get("pipeline"))
for r in res.get("recommendations", []):
    print("---")
    print("nombre:", r["name"])
    print("mejor_match:", r["best_matched_price"])
    print("matches:", r["matched_price_items"])
PY
```

Con `product_query`, el ranking por `precio` pone primero proveedores con coincidencias de producto y menor precio cargado.

### `KeyError: 'best_matched_price'` al probar `product_query`

Significa que tu copia local todavía tiene una versión vieja de los agentes. Para `product_query`, tienen que estar actualizados estos tres archivos:

```text
src/agents/evaluation_agent.py
src/agents/recommendation_agent.py
src/agents/coordinator_agent.py
```

Verificá rápido si están actualizados:

```bash
find src/agents -maxdepth 1 -type f -print
python - <<'PY'
from pathlib import Path
for path in [
    Path("src/agents/evaluation_agent.py"),
    Path("src/agents/recommendation_agent.py"),
    Path("src/agents/coordinator_agent.py"),
]:
    text = path.read_text(encoding="utf-8")
    print(path, "product_query=", "product_query" in text, "best_match=", "best_matched_price" in text)
PY
```

La salida esperada es:

```text
src/agents/evaluation_agent.py product_query= True best_match= True
src/agents/recommendation_agent.py product_query= True best_match= True
src/agents/coordinator_agent.py product_query= True best_match= False
```

Si `recommendation_agent.py` muestra `best_match=False`, actualizá ese archivo: debe devolver las claves `matched_price_items` y `best_matched_price` dentro de cada recomendación.

Si `coordinator_agent.py` muestra `product_query=False`, el coordinador no está pasando la búsqueda de producto hacia evaluación/recomendación. En ese caso, aunque llames:

```python
CoordinatorAgent().run({"priority": "precio", "product_query": "lavandina", "top_n": 5})
```

el ranking se comportará como ranking general por precio y las recomendaciones no tendrán el match de producto.

### `NameError: name 'PY' is not defined` o aparece `cat > ... <<'PY'` dentro de un `.py`

Eso significa que pegaste un bloque pensado para la terminal dentro del archivo Python. Las líneas como estas **no son código Python**:

```bash
cat > src/agents/evaluation_agent.py <<'PY'
PY
```

Son marcadores de Git Bash para crear archivos. Si aparecen dentro de `src/agents/*.py`, Python intenta ejecutarlas y falla.

Para limpiar esos marcadores en los agentes, desde la raíz de `proved` corré:

```bash
for f in src/agents/evaluation_agent.py src/agents/recommendation_agent.py src/agents/coordinator_agent.py; do
  python - "$f" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
clean = [line for line in lines if not line.startswith("cat > ") and line != "PY"]
path.write_text("\n".join(clean) + "\n", encoding="utf-8")
PY
done
```

Después validá que ya no queden marcadores:

```bash
find src/agents -maxdepth 1 -type f -print
python - <<'PY'
from pathlib import Path
for path in Path("src/agents").glob("*.py"):
    text = path.read_text(encoding="utf-8")
    print(path, "cat_marker=", "cat > " in text, "py_marker=", "\nPY\n" in f"\n{text}\n")
PY
```

Y compilá:

```bash
python -m py_compile src/agents/evaluation_agent.py src/agents/recommendation_agent.py src/agents/coordinator_agent.py
```

## 6. Alternativa: precios frescos desde SEPA / Precios Claros

Overpass/Nominatim sirve para descubrir proveedores y sucursales, pero no publica precios de productos. Para precios diarios de grandes comercios podés usar SEPA / Precios Claros con `fetch_sepa_prices.py`.

Primero armá una lista de productos con EAN/código de barras en un JSON como `data/sepa_products.example.json`:

```json
[
  {
    "id_producto": "7790520017975",
    "product_name": "Lavandina 1L",
    "unit": "unidad",
    "source": "sepa_api"
  }
]
```

Luego consultá sucursales cercanas a San Miguel de Tucumán y precios por producto:

```bash
export PYTHONPATH="$PWD/src"
python src/scripts/fetch_sepa_prices.py \
  --products data/sepa_products.example.json \
  --output data/providers_real_b2b_priced.json \
  --lat -26.8241 \
  --lng -65.2226 \
  --limit 30
```

> Importante: la API web de Precios Claros/SEPA no está publicada como contrato oficial estable. Si cambia la forma de respuesta, usá como fallback el dataset abierto diario de SEPA o actualizá el extractor.

Después podés rankear:

```bash
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 5
```

## 7. Combinación automática: SEPA + Mercado Libre + carga manual

Si querés replicar el flujo del mapa (SEPA para supermercados, Mercado Libre para vendedores online y carga manual para B2B locales), usá `fetch_prices_auto.py`.

El archivo de entrada combina EAN para SEPA y búsqueda para Mercado Libre:

```json
[
  {
    "product_name": "Ayudín lavandina 5L",
    "unit": "unidad",
    "sepa_id_producto": "7790580499176",
    "ml_query": "lavandina 5 litros mayorista",
    "ml_category": "MLA1246"
  }
]
```

Ejecutá con el alias corto `fetch_prices.py` (o `fetchprices.py`, sin guion bajo; ambos delegan en `fetch_prices_auto.py`):

```bash
export PYTHONPATH="$PWD/src"
python src/scripts/fetch_prices.py \
  --products data/price_sources.example.json \
  --output data/providers_real_b2b_priced.json \
  --lat -26.8241 \
  --lng -65.2226 \
  --limit 30 \
  --manual-providers data/providers_real_b2b.json \
  --manual-prices data/product_prices.json
```
Si preferís el nombre sin guion bajo, el comando equivalente empieza con `python src/scripts/fetchprices.py`. Los alias `fetch_prices.py` y `fetchprices.py` también ajustan el import path automáticamente cuando los ejecutás directo desde la raíz del repo.


El resultado mezcla proveedores de fuentes distintas y deja `tags.source` para saber de dónde vino cada uno (`sepa_api`, `mercadolibre_api` o `manual_price_file`). Después se usa el mismo ranking:

```bash
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 10
```

Podés desactivar fuentes con `--skip-sepa` o `--skip-mercadolibre` si una API cambia o falla temporalmente.
