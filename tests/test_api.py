from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
import joblib
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from app.api import create_app
from src.common import DEFAULT_MODEL_PATH, FEATURE_COLUMNS


@contextmanager
def client_for(model_path: Path | None = None) -> Iterator[TestClient]:
    with TestClient(create_app(model_path)) as client:
        yield client


def assert_field_error(response, field: str) -> None:
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(field in error["loc"] and error.get("msg") for error in errors)


def test_health_reports_loaded_model(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_ready": True}


def test_predict_uses_explicit_artifact_before_environment(
    synthetic_model_path: Path,
    tmp_path: Path,
    payload: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "missing_environment_model.pkl"))

    with client_for(synthetic_model_path) as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json() == {"prediction": 2, "class_name": "gamma"}
    assert type(response.json()["prediction"]) is int


def test_predict_uses_artifact_selected_by_environment(
    synthetic_model_path: Path,
    payload: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ML_MODEL_PATH", str(synthetic_model_path))

    with client_for() as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json() == {"prediction": 2, "class_name": "gamma"}


def test_predict_with_real_saved_model(payload: dict[str, float]) -> None:
    with client_for(DEFAULT_MODEL_PATH) as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json() == {"prediction": 0, "class_name": "setosa"}


def test_json_key_order_does_not_change_model_feature_order(
    client: TestClient, payload: dict[str, float], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = client.app.state.model_service
    original_predict = service.predict
    received_rows = []

    def capture_features(rows):
        received_rows.extend(rows)
        return original_predict(rows)

    monkeypatch.setattr(service, "predict", capture_features)
    reordered_payload = dict(reversed(list(payload.items())))
    response = client.post("/predict", json=reordered_payload)

    assert response.status_code == 200
    assert received_rows == [[5.1, 3.5, 1.4, 0.2]]


def test_predict_rejects_missing_field(
    client: TestClient, payload: dict[str, float]
) -> None:
    del payload["petal_width"]

    assert_field_error(client.post("/predict", json=payload), "petal_width")


@pytest.mark.parametrize("value", ["invalid", "0.2", True])
def test_predict_rejects_nonnumeric_value(
    client: TestClient, payload: dict[str, float], value: object
) -> None:
    invalid_payload = {**payload, "petal_width": value}

    assert_field_error(client.post("/predict", json=invalid_payload), "petal_width")


def test_predict_accepts_integer_numbers(client: TestClient) -> None:
    response = client.post(
        "/predict",
        json={"sepal_length": 5, "sepal_width": 3, "petal_length": 1, "petal_width": 1},
    )

    assert response.status_code == 200
    assert response.json() == {"prediction": 2, "class_name": "gamma"}


@pytest.mark.parametrize("value", [0.0, -0.5], ids=["zero", "negative"])
def test_predict_rejects_nonpositive_value(
    client: TestClient, payload: dict[str, float], value: float
) -> None:
    payload["petal_width"] = value

    assert_field_error(client.post("/predict", json=payload), "petal_width")


def test_predict_rejects_extra_field(
    client: TestClient, payload: dict[str, float]
) -> None:
    invalid_payload = {**payload, "unexpected": 1.0}

    assert_field_error(client.post("/predict", json=invalid_payload), "unexpected")


def test_predict_rejects_malformed_json(client: TestClient) -> None:
    response = client.post(
        "/predict",
        content='{"sepal_length":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize("literal", ["NaN", "Infinity"])
def test_predict_rejects_nonfinite_json(client: TestClient, literal: str) -> None:
    response = client.post(
        "/predict",
        content=(
            '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,'
            '"petal_width":' + literal + "}"
        ),
        headers={"Content-Type": "application/json"},
    )

    assert_field_error(response, "petal_width")
    assert client.get("/health").json() == {"status": "ok", "model_ready": True}


def test_model_is_loaded_once_for_multiple_requests(
    synthetic_model_path: Path,
    payload: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_load = joblib.load
    loaded_paths = []

    def tracked_load(path: Path):
        loaded_paths.append(Path(path))
        return original_load(path)

    monkeypatch.setattr("src.model_service.joblib.load", tracked_load)

    with client_for(synthetic_model_path) as client:
        assert loaded_paths == [synthetic_model_path]
        for _ in range(2):
            response = client.post("/predict", json=payload)
            assert response.status_code == 200
            assert response.json() == {"prediction": 2, "class_name": "gamma"}
        assert loaded_paths == [synthetic_model_path]


def test_requests_do_not_fit_estimators(
    synthetic_model_path: Path,
    payload: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_fit(*args: object, **kwargs: object) -> None:
        pytest.fail("The API must use the saved estimator without fitting it.")

    monkeypatch.setattr(DummyClassifier, "fit", unexpected_fit)
    monkeypatch.setattr(LogisticRegression, "fit", unexpected_fit)

    with client_for(synthetic_model_path) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json() == {"prediction": 2, "class_name": "gamma"}


def test_documentation_and_openapi_expose_request_and_response_contracts(
    client: TestClient,
) -> None:
    for route in ("/docs", "/redoc"):
        response = client.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    response = client.get("/openapi.json")
    assert response.status_code == 200
    specification = response.json()
    assert "get" in specification["paths"]["/health"]
    operation = specification["paths"]["/predict"]["post"]
    assert "422" in operation["responses"]
    schemas = specification["components"]["schemas"]
    request = schemas["PredictRequest"]
    assert set(request["required"]) == set(FEATURE_COLUMNS)
    assert request["additionalProperties"] is False
    for column in FEATURE_COLUMNS:
        assert request["properties"][column]["type"] == "number"
        assert request["properties"][column]["exclusiveMinimum"] == 0
    prediction = schemas["PredictResponse"]
    assert set(prediction["required"]) == {"prediction", "class_name"}
    assert prediction["properties"]["prediction"]["type"] == "integer"
    assert prediction["properties"]["class_name"]["type"] == "string"
    assert schemas["HealthResponse"]["properties"]["model_ready"]["type"] == "boolean"


def test_missing_model_fails_during_startup(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as error:
        with client_for(tmp_path / "missing_model.pkl"):
            pytest.fail("Application startup must fail when its model is missing.")

    assert isinstance(error.value.__cause__, FileNotFoundError)
