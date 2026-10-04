import io
import json
from pathlib import Path
import subprocess
import sys

import joblib
import pytest
from sklearn.linear_model import LogisticRegression

from src.common import DEFAULT_INPUT_PATH, FEATURE_COLUMNS, PROJECT_ROOT
from src.predict import predict, read_features
from src.train import train


HEADER = ",".join(FEATURE_COLUMNS)
VALID_ROW = "5.1,3.5,1.4,0.2"


@pytest.fixture
def trained_model(tmp_path: Path) -> Path:
    model_path = tmp_path / "iris_model.pkl"
    accuracy = train(model_path)
    assert 0.0 <= accuracy <= 1.0
    assert model_path.is_file()
    return model_path


@pytest.mark.parametrize(
    ("csv_text", "expected"),
    [
        (
            f"{HEADER}\n{VALID_ROW}\n6.7,3.0,5.2,2.3\n",
            [[5.1, 3.5, 1.4, 0.2], [6.7, 3.0, 5.2, 2.3]],
        ),
        (
            "petal_width,sepal_length,petal_length,sepal_width\n"
            "0.2,5.1,1.4,3.5\n",
            [[5.1, 3.5, 1.4, 0.2]],
        ),
        (
            f"{HEADER}\n{VALID_ROW}\n\n",
            [[5.1, 3.5, 1.4, 0.2]],
        ),
    ],
    ids=["multiple_rows", "reordered_columns", "trailing_blank_line"],
)
def test_read_features_returns_canonical_feature_order(
    csv_text: str, expected: list[list[float]]
) -> None:
    assert read_features(io.StringIO(csv_text)) == expected


@pytest.mark.parametrize(
    "csv_text",
    [
        "",
        f"{HEADER}\n",
        "sepal_length,sepal_width,petal_length\n5.1,3.5,1.4\n",
        "sepal_length,sepal_width,petal_length,petal_length\n5.1,3.5,1.4,0.2\n",
        f"{HEADER},target\n{VALID_ROW},0\n",
        f"{HEADER}\n5.1,3.5,1.4\n",
        f"{HEADER}\n{VALID_ROW},0\n",
        f"{HEADER}\n5.1,,1.4,0.2\n",
        f"{HEADER}\ninvalid,3.5,1.4,0.2\n",
        f"{HEADER}\nnan,3.5,1.4,0.2\n",
        f"{HEADER}\n5.1,3.5,inf,-inf\n",
    ],
    ids=[
        "empty_input",
        "no_data_rows",
        "missing_column",
        "duplicate_column",
        "extra_column",
        "short_row",
        "long_row",
        "empty_value",
        "nonnumeric_value",
        "nan",
        "infinities",
    ],
)
def test_read_features_rejects_invalid_input(csv_text: str) -> None:
    with pytest.raises(ValueError):
        read_features(io.StringIO(csv_text))


def test_saved_model_predicts_sample_without_fitting(
    trained_model: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = joblib.load(trained_model)
    assert isinstance(artifact["model"], LogisticRegression)
    assert artifact["feature_columns"] == list(FEATURE_COLUMNS)
    assert len(artifact["target_names"]) == 3
    assert all(isinstance(name, str) for name in artifact["target_names"])

    with DEFAULT_INPUT_PATH.open(encoding="utf-8", newline="") as source:
        features = read_features(source)
    expected_classes = artifact["model"].predict(features).tolist()

    def unexpected_fit(*args: object, **kwargs: object) -> None:
        pytest.fail("Prediction must use the saved estimator without fitting it.")

    monkeypatch.setattr(LogisticRegression, "fit", unexpected_fit)
    results = predict(input_path=DEFAULT_INPUT_PATH, model_path=trained_model)

    assert results == [{"predicted_class": 0, "predicted_name": "setosa"}]
    assert len(results) == len(features) > 0
    assert results == [
        {
            "predicted_class": int(class_id),
            "predicted_name": artifact["target_names"][int(class_id)],
        }
        for class_id in expected_classes
    ]
    assert all(type(result["predicted_class"]) is int for result in results)


def test_predict_cli_finds_default_input_from_another_directory(
    trained_model: Path, tmp_path: Path
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "src" / "predict.py"),
            "--model-path",
            str(trained_model),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == predict(model_path=trained_model)


def test_predict_cli_reports_missing_model_without_traceback(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "src" / "predict.py"),
            "--model-path",
            str(tmp_path / "missing_model.pkl"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stderr.strip()
    assert "Traceback" not in completed.stdout + completed.stderr


def test_train_cli_saves_requested_model_from_another_directory(tmp_path: Path) -> None:
    model_path = tmp_path / "cli_model.pkl"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "src" / "train.py"),
            "--model-path",
            str(model_path),
            "--test-size",
            "0.3",
            "--random-state",
            "7",
            "--max-iter",
            "400",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "accuracy=" in completed.stdout
    assert "model_saved=" in completed.stdout
    assert model_path.is_file()
    artifact = joblib.load(model_path)
    assert artifact["feature_columns"] == list(FEATURE_COLUMNS)
    assert isinstance(artifact["model"], LogisticRegression)
    assert artifact["model"].max_iter == 400
