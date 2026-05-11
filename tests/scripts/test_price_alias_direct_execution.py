import os
import subprocess
import sys


def _without_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def test_fetchprices_script_help_runs_without_pythonpath():
    result = subprocess.run(
        [sys.executable, "src/scripts/fetchprices.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=_without_pythonpath(),
    )

    assert result.returncode == 0
    assert "--products" in result.stdout


def test_fetch_prices_script_help_runs_without_pythonpath():
    result = subprocess.run(
        [sys.executable, "src/scripts/fetch_prices.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=_without_pythonpath(),
    )

    assert result.returncode == 0
    assert "--products" in result.stdout
