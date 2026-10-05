import json
import logging
from uuid import UUID
from types import SimpleNamespace

import pytest

from src.common import DEFAULT_MODEL_PATH
from src.model_service import ModelService
from src.request_id import prediction_event, resolve_request_id


REQUEST_ID = "e21f05a0-837f-4ea9-84a0-621ce8f8b0a8"


def prediction_records(caplog):
    return [json.loads(record.message) for record in caplog.records if record.name == "iris.predictions"]


def test_saved_model_passport_has_only_public_fields():
    service = ModelService.load(DEFAULT_MODEL_PATH)
    assert service.model_info() == {
        "model_type": "LogisticRegression",
        "classes": ["setosa", "versicolor", "virginica"],
        "feature_count": 4,
        "model_loaded": True,
    }


def test_passport_uses_same_loaded_model_and_returns_independent_names(client):
    expected = {
        "model_type": "DummyClassifier", "classes": ["alpha", "beta", "gamma"],
        "feature_count": 4, "model_loaded": True,
    }
    service = client.app.state.model_service
    passport = service.model_info()
    passport["classes"].append("unrelated")
    response = client.get("/model-info")
    assert response.status_code == 200
    assert response.json() == expected
    assert service.model_info() == expected


@pytest.mark.parametrize("feature_count", [None, True, 3, "4", 4.0])
def test_passport_rejects_incompatible_feature_metadata(feature_count):
    estimator = SimpleNamespace(n_features_in_=feature_count)
    service = ModelService(estimator, ["alpha", "beta", "gamma"])
    with pytest.raises(ValueError, match="Число признаков"):
        service.model_info()


def test_passport_rejects_missing_feature_metadata():
    with pytest.raises(ValueError, match="Число признаков"):
        ModelService(object(), ["alpha"]).model_info()


def test_model_info_hides_invalid_metadata_details(client, monkeypatch):
    monkeypatch.setattr(client.app.state.model_service._model, "n_features_in_", 3)
    response = client.get("/model-info")
    assert response.status_code == 500
    assert response.json() == {"detail": "Не удалось получить паспорт модели"}


def test_malformed_utf8_preserves_request_identity(client, caplog):
    with caplog.at_level(logging.INFO, logger="iris.predictions"):
        response = client.post(
            "/predict",
            content=b"\xff",
            headers={"Content-Type": "application/json", "X-Request-ID": REQUEST_ID},
        )
    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == response.json()["request_id"] == REQUEST_ID
    assert isinstance(response.json()["detail"], str)
    assert "Traceback" not in response.text
    assert prediction_records(caplog) == [{
        "event": "prediction_rejected", "request_id": REQUEST_ID, "status_code": 400,
    }]


def test_openapi_describes_request_id_in_prediction_errors(client):
    schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/predict"]["post"]["responses"]
    for code in ("400", "422", "503", "500"):
        assert responses[code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/PredictErrorResponse",
        }
        assert responses[code]["headers"]["X-Request-ID"]["schema"]["format"] == "uuid"
    assert set(schema["components"]["schemas"]["PredictErrorResponse"]["required"]) == {
        "detail", "request_id",
    }


@pytest.mark.parametrize("supplied", [REQUEST_ID, REQUEST_ID.upper(), "{" + REQUEST_ID + "}"])
def test_valid_request_id_is_canonical_in_response_header_and_log(client, payload, caplog, supplied):
    with caplog.at_level(logging.INFO, logger="iris.predictions"):
        response = client.post("/predict", json=payload, headers={"X-Request-ID": supplied})
    assert response.status_code == 200
    assert response.json() == {"class_id": 2, "class_name": "gamma", "request_id": REQUEST_ID}
    assert response.headers["X-Request-ID"] == REQUEST_ID
    assert prediction_records(caplog) == [prediction_event(REQUEST_ID, "gamma")]


@pytest.mark.parametrize("supplied", [None, "", "invalid", "../synthetic-path"])
def test_absent_or_invalid_request_id_gets_unique_uuid4(client, payload, supplied):
    headers = {} if supplied is None else {"X-Request-ID": supplied}
    responses = [client.post("/predict", json=payload, headers=headers) for _ in range(2)]
    identifiers = []
    for response in responses:
        assert response.status_code == 200
        value = response.json()["request_id"]
        assert str(UUID(value)) == value
        assert UUID(value).version == 4
        assert response.headers["X-Request-ID"] == value
        identifiers.append(value)
    assert identifiers[0] != identifiers[1]


def test_validation_error_already_has_request_id_and_safe_log(client, payload, caplog):
    invalid = {**payload, "petal_width": "synthetic-invalid-value"}
    with caplog.at_level(logging.INFO, logger="iris.predictions"):
        response = client.post("/predict", json=invalid, headers={"X-Request-ID": REQUEST_ID})
    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == response.json()["request_id"] == REQUEST_ID
    assert any(error["loc"] == ["body", "petal_width"] for error in response.json()["detail"])
    assert "synthetic-invalid-value" not in response.text
    assert prediction_records(caplog) == [{
        "event": "prediction_rejected", "request_id": REQUEST_ID, "status_code": 422,
    }]


def test_prediction_failure_hides_internal_details(client, payload, caplog, monkeypatch):
    def fail(_features):
        raise RuntimeError("synthetic-private-details")

    monkeypatch.setattr(client.app.state.model_service, "predict", fail)
    with caplog.at_level(logging.INFO, logger="iris.predictions"):
        response = client.post("/predict", json=payload, headers={"X-Request-ID": REQUEST_ID})
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == response.json()["request_id"] == REQUEST_ID
    assert "synthetic-private-details" not in response.text + caplog.text
    assert prediction_records(caplog) == [{
        "event": "prediction_failed", "request_id": REQUEST_ID, "status_code": 500,
    }]


def test_missing_runtime_model_reports_unavailability(client, payload, caplog):
    client.app.state.model_service = None
    assert client.get("/health").json() == {"status": "ok", "model_loaded": False}
    assert client.get("/model-info").status_code == 503
    with caplog.at_level(logging.INFO, logger="iris.predictions"):
        response = client.post("/predict", json=payload, headers={"X-Request-ID": REQUEST_ID})
    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == REQUEST_ID
    assert prediction_records(caplog) == [{
        "event": "prediction_failed", "request_id": REQUEST_ID, "status_code": 503,
    }]


def test_request_id_helpers_generate_uuid_and_safe_event():
    request_id = resolve_request_id("invalid")
    assert UUID(request_id).version == 4
    assert prediction_event(request_id, "setosa") == {
        "event": "prediction_completed", "request_id": request_id, "class_name": "setosa",
    }


def test_home_serves_same_origin_form(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="ru">' in response.text
    assert "Iris: паспорт модели и request ID" in response.text
    assert "request('/predict'" in response.text
    assert "request('/model-info')" in response.text
    assert "request('/health')" in response.text
    assert "crypto.randomUUID()" in response.text
    assert "innerHTML" not in response.text
