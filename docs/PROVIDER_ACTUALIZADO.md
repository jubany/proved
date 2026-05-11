# `src/models/provider.py` actualizado

Si al correr el pipeline aparece:

```text
TypeError: Provider.__init__() got an unexpected keyword argument 'phone'
```

significa que `src/collector/json_loader.py` ya está actualizado y está pasando campos nuevos (`phone`, `website`, `social_links`, `price_items`, `tags`), pero tu `src/models/provider.py` local todavía es la versión vieja y no acepta esos campos.

Reemplazá `src/models/provider.py` completo por este contenido:

```python
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Provider:
    name: str
    address: str
    lat: float
    lng: float
    rating: Optional[float]
    reviews_count: Optional[int]
    category: str
    products: list[str]

    phone: str = ""
    website: str = ""
    social_links: list[str] = field(default_factory=list)
    price_items: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)

    # scores
    calidad_score: float = 0
    precio_score: float = 0
    volumen_score: float = 0
```

Después validá:

```bash
python - <<'PY'
from pathlib import Path
text = Path("src/models/provider.py").read_text(encoding="utf-8")
print("tiene phone:", "phone: str" in text)
print("tiene price_items:", "price_items:" in text)
print("tiene tags:", "tags:" in text)
PY
```

La salida esperada es:

```text
tiene phone: True
tiene price_items: True
tiene tags: True
```
