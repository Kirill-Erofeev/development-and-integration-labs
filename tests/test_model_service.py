from pathlib import Path

import joblib
import pytest

from src.common import FEATURE_COLUMNS
from src.model_service import ModelService


def test_model_service_predicts_rows_with_saved_class_names(
    tmp_path: Path, synthetic_artifact: dict
) -> None:
    model_path = tmp_path / "synthetic_model.pkl"
    joblib.dump(synthetic_artifact, model_path)

    service = ModelService.load(model_path)
    results = service.predict([[1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]])

    assert results == [
        {"predicted_class": 2, "predicted_name": "gamma"},
        {"predicted_class": 2, "predicted_name": "gamma"},
    ]
    assert all(type(result["predicted_class"]) is int for result in results)


@pytest.mark.parametrize(
    "defect",
    [
        "not_a_bundle",
        "missing_metadata",
        "wrong_feature_order",
        "invalid_class_names",
        "missing_predict_method",
    ],
)
def test_model_service_rejects_invalid_artifact(
    tmp_path: Path, synthetic_artifact: dict, defect: str
) -> None:
    artifact = synthetic_artifact.copy()
    if defect == "not_a_bundle":
        artifact = ["invalid"]
    elif defect == "missing_metadata":
        del artifact["target_names"]
    elif defect == "wrong_feature_order":
        artifact["feature_columns"] = list(reversed(FEATURE_COLUMNS))
    elif defect == "invalid_class_names":
        artifact["target_names"] = [0, 1, 2]
    elif defect == "missing_predict_method":
        artifact["model"] = object()
    model_path = tmp_path / "invalid_model.pkl"
    joblib.dump(artifact, model_path)

    with pytest.raises(ValueError):
        ModelService.load(model_path)


def test_model_service_reports_missing_artifact(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ModelService.load(tmp_path / "missing_model.pkl")


def test_model_service_rejects_class_without_metadata(synthetic_artifact: dict) -> None:
    service = ModelService(synthetic_artifact["model"], ["alpha", "beta"])

    with pytest.raises(ValueError):
        service.predict([[1.0, 2.0, 3.0, 4.0]])
