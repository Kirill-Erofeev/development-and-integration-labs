from copy import deepcopy
import json
import subprocess
import sys

import pytest

from src.common import PROJECT_ROOT
from src.predict import format_predictions


@pytest.fixture
def predictions() -> list[dict[str, int | str]]:
    return [
        {"predicted_class": 0, "predicted_name": "setosa"},
        {"predicted_class": 2, "predicted_name": "virginica"},
    ]


@pytest.mark.parametrize("explicit_format", [False, True], ids=["default", "explicit"])
def test_json_format_preserves_predictions_and_integer_classes(
    predictions: list[dict[str, int | str]], explicit_format: bool
) -> None:
    if explicit_format:
        output = format_predictions(predictions, output_format="json")
    else:
        output = format_predictions(predictions)

    decoded = json.loads(output)
    assert decoded == predictions
    assert isinstance(decoded, list)
    assert all(type(item["predicted_class"]) is int for item in decoded)


def test_text_format_preserves_multiple_predictions_in_order(
    predictions: list[dict[str, int | str]],
) -> None:
    assert format_predictions(predictions, output_format="text") == (
        "predicted_class=0 predicted_name=setosa\n"
        "predicted_class=2 predicted_name=virginica"
    )


def test_unknown_output_format_is_rejected(
    predictions: list[dict[str, int | str]],
) -> None:
    with pytest.raises(ValueError):
        format_predictions(predictions, output_format="unsupported")


@pytest.mark.parametrize("output_format", ["json", "text"])
def test_format_does_not_mutate_predictions(
    predictions: list[dict[str, int | str]], output_format: str
) -> None:
    predictions = list(reversed(predictions))
    original = deepcopy(predictions)

    format_predictions(predictions, output_format=output_format)

    assert predictions == original


def run_predict(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "predict.py"), *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


@pytest.fixture(scope="module")
def default_cli_output() -> subprocess.CompletedProcess[str]:
    completed = run_predict()
    assert completed.returncode == 0, completed.stderr
    return completed


def test_cli_explicit_json_matches_default(
    default_cli_output: subprocess.CompletedProcess[str],
) -> None:
    explicit = run_predict("--output-format", "json")

    assert explicit.returncode == 0, explicit.stderr
    assert explicit.stdout == default_cli_output.stdout
    decoded = json.loads(explicit.stdout)
    assert isinstance(decoded, list)
    assert decoded
    assert all(type(item["predicted_class"]) is int for item in decoded)


def test_cli_text_contains_one_line_per_prediction(
    default_cli_output: subprocess.CompletedProcess[str],
) -> None:
    completed = run_predict("--output-format", "text")
    predictions = json.loads(default_cli_output.stdout)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        f"predicted_class={item['predicted_class']} predicted_name={item['predicted_name']}"
        for item in predictions
    ]


def test_cli_rejects_unknown_output_format() -> None:
    completed = run_predict("--output-format", "unsupported")

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "--output-format" in completed.stderr
    assert "Traceback" not in completed.stderr
