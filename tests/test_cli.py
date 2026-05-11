import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _python_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def test_cli_help_documents_agent_pipeline_flags():
    result = subprocess.run(
        [sys.executable, "src/main.py", "--help"],
        cwd=REPO_ROOT,
        env=_python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--top-n" in result.stdout
    assert "--legacy" in result.stdout


def test_cli_accepts_source_and_top_n_for_price_lookup(tmp_path):
    source = tmp_path / "providers_real_b2b_priced.json"
    source.write_text(
        json.dumps(
            [
                {
                    "name": "San Cayetano Mayorista",
                    "address": "Tucumán",
                    "lat": 0,
                    "lng": 0,
                    "rating": None,
                    "reviews_count": None,
                    "category": "mayorista",
                    "products": ["limpieza"],
                    "price_items": [{"product_name": "Lavandina 5L", "price": 2350, "currency": "ARS"}],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "src/main.py",
            "--source",
            str(source),
            "--priority",
            "precio",
            "--query",
            "lavandina",
            "--top-n",
            "1",
        ],
        cwd=REPO_ROOT,
        env=_python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Fuente:" in result.stdout
    assert "Proveedores con price_items: 1" in result.stdout
    assert "Proveedores con precio coincidente: 1" in result.stdout
    assert "Mejor precio: Lavandina 5L - 2350" in result.stdout
