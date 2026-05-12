import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agents.ingestion_agent import IngestionAgent


def test_default_sources_prioritize_priced_providers_file():
    source_names = [path.name for path in IngestionAgent._default_sources()]

    assert source_names[:4] == [
        "providers_real_b2b_priced.json",
        "providers_real_b2b.json",
        "providers_real.json",
        "providers.json",
    ]
