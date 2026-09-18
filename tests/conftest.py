from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
import joblib
import pytest
from sklearn.dummy import DummyClassifier

from app.api import create_app
from src.common import FEATURE_COLUMNS


@pytest.fixture
def synthetic_artifact() -> dict:
    model = DummyClassifier(strategy="constant", constant=2)
    model.fit([[1.0] * 4, [2.0] * 4, [3.0] * 4], [0, 1, 2])
    return {
        "model": model,
        "feature_columns": list(FEATURE_COLUMNS),
        "target_names": ["alpha", "beta", "gamma"],
    }


@pytest.fixture
def synthetic_model_path(tmp_path: Path, synthetic_artifact: dict) -> Path:
    model_path = tmp_path / "synthetic_model.pkl"
    joblib.dump(synthetic_artifact, model_path)
    return model_path


@pytest.fixture
def client(synthetic_model_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(synthetic_model_path)) as test_client:
        yield test_client


@pytest.fixture
def payload() -> dict[str, float]:
    return {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2,
    }
