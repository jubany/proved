# Bootstrap local del paquete `src/agents`

Usá esta guía si tu copia local de `proved` no tiene la carpeta `src/agents` y Python falla con:

```text
ModuleNotFoundError: No module named 'agents'
```

## 1. Crear archivos de agentes

Parado en la raíz del repo `proved`, ejecutá o copiá los archivos equivalentes para crear:

```text
src/agents/__init__.py
src/agents/base.py
src/agents/ingestion_agent.py
src/agents/evaluation_agent.py
src/agents/recommendation_agent.py
src/agents/coordinator_agent.py
```

## 2. Verificar que existen

```bash
find src/agents -maxdepth 1 -type f -print
```

La salida debe incluir, como mínimo:

```text
src/agents/__init__.py
src/agents/coordinator_agent.py
src/agents/ingestion_agent.py
```

## 3. Probar importación

```bash
export PYTHONPATH="$PWD/src"
py - <<'PY'
from agents.coordinator_agent import CoordinatorAgent
print("agents ok", CoordinatorAgent.name)
PY
```

## 4. Probar pipeline con datos reales B2B

```bash
export PYTHONPATH="$PWD/src"
py - <<'PY'
from agents.coordinator_agent import CoordinatorAgent

res = CoordinatorAgent().run({"priority": "calidad", "top_n": 5})
print("ok:", res.get("ok"))
print("pipeline:", res.get("pipeline"))
print("recommendations:", res.get("recommendations"))
PY
```

## 5. Recordatorio

Si `data/providers_real_b2b.json` existe, `IngestionAgent` debe usarlo antes que `data/providers_real.json` y `data/providers.json`.

## 6. Probar precios de un producto específico

Si ya tenés un JSON enriquecido con `price_items` (por ejemplo `data/providers_real_b2b_priced.json`), probá primero el pipeline nuevo desde la CLI:

```bash
export PYTHONPATH="$PWD/src"
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 5
```

La salida debe mostrar:

- `Fuente`: el JSON que realmente se leyó.
- `Proveedores con price_items`: cuántos proveedores tienen listas de precios cargadas.
- `Proveedores con precio coincidente`: cuántos proveedores tienen un producto que matchea con `--query`.
- `Mejor precio`: el precio más barato encontrado para cada recomendación con match.

Si no pasás `--source`, `IngestionAgent` intenta automáticamente, en este orden:

1. `data/providers_real_b2b_priced.json`
2. `data/providers_real_b2b.json`
3. `data/providers_real.json`
4. `data/providers.json`

Si ves `Proveedores con price_items: 0`, el sistema está leyendo un archivo sin precios. En ese caso, pasá `--source` con la ruta del JSON enriquecido o generá el archivo con:

```bash
export PYTHONPATH="$PWD/src"
python src/scripts/attach_product_prices.py \
  --providers data/providers_real_b2b.json \
  --prices data/product_prices.json \
  --output data/providers_real_b2b_priced.json
```

## 7. Error común: ejecutar el JSON como si fuera un comando

Si en Git Bash escribís sólo la ruta del archivo:

```bash
data/providers_real_b2b_priced.json
```

Bash intenta ejecutar el contenido del JSON como script. Por eso pueden aparecer errores como:

```text
data/providers_real_b2b_priced.json: line 1: [: missing `]'
data/providers_real_b2b_priced.json: line 183: syntax error: unexpected end of file
```

Ese mensaje no significa necesariamente que el JSON esté roto: significa que lo ejecutaste. Para usarlo, pasalo como argumento `--source`:

```bash
export PYTHONPATH="$PWD/src"
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 5
```

Para revisar si el JSON existe y es válido, usá:

```bash
ls -lh data/providers_real_b2b_priced.json
python -m json.tool data/providers_real_b2b_priced.json > /tmp/providers_real_b2b_priced.validated.json
```

Y para inspeccionar cuántos proveedores/precios cargó:

```bash
export PYTHONPATH="$PWD/src"
python - <<'PY'
import json
from pathlib import Path

path = Path("data/providers_real_b2b_priced.json")
data = json.loads(path.read_text(encoding="utf-8"))
providers = data["providers"] if isinstance(data, dict) else data
print("providers:", len(providers))
print("con price_items:", sum(1 for provider in providers if provider.get("price_items")))
PY
```

## 8. Error: `unrecognized arguments: --source ... --top-n ...`

Ese error significa que tu `src/main.py` local todavía es la versión vieja, porque la versión nueva declara `--source`, `--top-n` y `--legacy` en el parser de la CLI.

Primero verificá qué opciones reconoce tu archivo actual:

```bash
export PYTHONPATH="$PWD/src"
python src/main.py --help
```

Si en la ayuda no aparecen `--source` y `--top-n`, actualizá tu rama local y confirmá el último commit:

```bash
git status
git pull
git log -1 --oneline
```

Después repetí:

```bash
export PYTHONPATH="$PWD/src"
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 5
```

Alternativa temporal si todavía no podés actualizar: usá el pipeline directamente desde Python, que no depende de los argumentos de `main.py`:

```bash
export PYTHONPATH="$PWD/src"
python - <<'PY'
from agents.coordinator_agent import CoordinatorAgent

res = CoordinatorAgent().run({
    "source_path": "data/providers_real_b2b_priced.json",
    "priority": "precio",
    "product_query": "lavandina",
    "top_n": 5,
})

print("ok:", res.get("ok"))
print("pipeline:", res.get("pipeline"))
for item in res.get("recommendations", []):
    print(item["name"], item.get("best_matched_price"))
PY
```

## 9. Warnings de Git Bash: `LF will be replaced by CRLF`

Si después de `git add .` ves warnings como:

```text
warning: in the working copy of 'src/agents/ingestion_agent.py', LF will be replaced by CRLF the next time Git touches it
```

no es un error del código ni del JSON. Git está avisando que, por la configuración de Windows (`core.autocrlf`), podría convertir finales de línea LF a CRLF en tu copia local.

Para este proyecto conviene mantener LF en archivos fuente y datos (`.py`, `.json`, `.md`, `.sh`). La raíz del repo incluye `.gitattributes` con reglas explícitas para eso.

Después de actualizar la rama, podés normalizar tu copia local con:

```bash
git rm --cached -r .
git reset --hard
```

⚠️ Usá `git reset --hard` sólo si no tenés cambios locales sin guardar. Si tenés datos locales que no querés perder, primero hacé backup o revisá con:

```bash
git status
```

Si los warnings aparecieron al agregar archivos reales como `data/product_prices.json` o `data/providers_real_b2b_priced.json`, podés continuar con `git status` y commitear normalmente; los warnings no bloquean el commit.

## 10. Tengo `product_prices.json`, pero el ranking dice `Proveedores con price_items: 0`

`data/product_prices.json` es sólo la lista manual de precios. El ranking no lee ese archivo directamente: primero hay que adjuntarlo a los proveedores y regenerar `data/providers_real_b2b_priced.json`.

Ejecutá:

```bash
export PYTHONPATH="$PWD/src"
python src/scripts/attach_product_prices.py \
  --providers data/providers_real_b2b.json \
  --prices data/product_prices.json \
  --output data/providers_real_b2b_priced.json
```

La salida importante es:

```text
✅ Proveedores con precios adjuntos: 2
```

Si dice `0`, entonces los `provider_name` del archivo de precios no coinciden con el campo `name` de los proveedores. El script muestra una muestra de nombres disponibles y los `provider_name` cargados para comparar.

Después de adjuntar precios, recién ahí corré:

```bash
export PYTHONPATH="$PWD/src"
python src/main.py --source data/providers_real_b2b_priced.json --priority precio --query lavandina --top-n 5
```

## 11. `attach_product_prices.py` adjuntó precios, pero `main.py` muestra `Fuente: None` y `price_items: 0`

Si el script mostró:

```text
✅ Proveedores con precios adjuntos: 2
```

pero después el ranking muestra:

```text
📄 Fuente: None
💰 Proveedores con price_items: 0
```

entonces el archivo `data/providers_real_b2b_priced.json` probablemente quedó bien, pero tu copia local todavía tiene una versión vieja de `src/collector/json_loader.py`, `src/agents/ingestion_agent.py` o `src/agents/coordinator_agent.py`.

Corré el diagnóstico:

```bash
export PYTHONPATH="$PWD/src"
python src/scripts/diagnose_pricing_pipeline.py --source data/providers_real_b2b_priced.json --query lavandina
```

Lectura rápida del resultado:

- `raw_providers_with_price_items: 2` y `loaded_providers_with_price_items: 0`: actualizá `src/collector/json_loader.py`.
- `loaded_providers_with_price_items: 2` y `coordinator_pipeline.ingestion.priced_count: 0`: actualizá `src/agents/coordinator_agent.py`.
- `raw_providers_with_price_items: 0`: reejecutá `attach_product_prices.py` o revisá que estés mirando el archivo correcto.

## 12. Error: `can't open file ... diagnose_pricing_pipeline.py`

Ese error significa que tu copia local todavía no tiene el archivo `src/scripts/diagnose_pricing_pipeline.py`. Podés resolverlo de dos maneras:

1. Actualizá la rama y verificá que el archivo exista:

```bash
git pull
ls -lh src/scripts/diagnose_pricing_pipeline.py
```

2. Si querés diagnosticar sin ese archivo, corré este bloque inline desde la raíz del repo:

```bash
export PYTHONPATH="$PWD/src"
python - <<'PY'
import json
from pathlib import Path
from agents.coordinator_agent import CoordinatorAgent
from agents.evaluation_agent import matched_price_items
from collector.json_loader import load_providers_from_json

source = Path("data/providers_real_b2b_priced.json")
query = "lavandina"
print("source:", source)
print("source_exists:", source.exists())

data = json.loads(source.read_text(encoding="utf-8"))
raw_providers = data["providers"] if isinstance(data, dict) else data
print("raw_providers:", len(raw_providers))
print("raw_providers_with_price_items:", sum(1 for p in raw_providers if p.get("price_items")))

for provider in raw_providers:
    if provider.get("price_items"):
        print("---")
        print("raw provider:", provider.get("name"))
        print("raw price_items:", provider.get("price_items")[:3])

loaded = load_providers_from_json(str(source))
print("loaded_providers:", len(loaded))
print("loaded_providers_with_price_items:", sum(1 for p in loaded if getattr(p, "price_items", [])))
print("loaded_providers_matching_query:", sum(1 for p in loaded if matched_price_items(p, query)))

res = CoordinatorAgent().run({
    "source_path": str(source),
    "priority": "precio",
    "product_query": query,
    "top_n": 5,
})
print("coordinator_ok:", res.get("ok"))
print("coordinator_pipeline:", res.get("pipeline"))
PY
```
