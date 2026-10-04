from io import BytesIO
import json
from urllib.error import URLError
from unittest.mock import patch
from uuid import UUID

import pytest

from scripts.check_api import check_api, main


REQUEST_ID = "e21f05a0-837f-4ea9-84a0-621ce8f8b0a8"
PASSPORT = {
    "model_type": "LogisticRegression", "classes": ["setosa", "versicolor", "virginica"],
    "feature_count": 4, "model_loaded": True,
}


@pytest.fixture(autouse=True)
def fixed_uuid():
    with patch("scripts.check_api.uuid4", return_value=UUID(REQUEST_ID)):
        yield


def encoded_response(payload: object) -> BytesIO:
    response = BytesIO(json.dumps(payload).encode("utf-8"))
    response.headers = {"X-Request-ID": REQUEST_ID}
    return response


def test_smoke_checks_ready_model_and_prediction() -> None:
    expected = {"class_id": 0, "class_name": "setosa", "request_id": REQUEST_ID}
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_loaded": True}),
        encoded_response(PASSPORT),
        encoded_response(expected),
    ]) as request:
        assert check_api("http://example.invalid:8080/") == expected
    assert request.call_args_list[0].args == ("http://example.invalid:8080/health",)
    assert request.call_args_list[1].args == ("http://example.invalid:8080/model-info",)
    prediction_request = request.call_args_list[2].args[0]
    assert prediction_request.full_url == "http://example.invalid:8080/predict"
    assert prediction_request.method == "POST"
    assert prediction_request.get_header("X-request-id") == REQUEST_ID
    assert json.loads(prediction_request.data) == {
        "sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2,
    }
    assert all(call.kwargs["timeout"] == 10 for call in request.call_args_list)


@pytest.mark.parametrize("health", [{"status": "ok", "model_loaded": False}, {"status": "ok", "model_loaded": 1}, []])
def test_unready_model_prevents_prediction(health: object) -> None:
    with patch("scripts.check_api.urlopen", return_value=encoded_response(health)) as request:
        with pytest.raises(ValueError, match="готовность"):
            check_api("http://example.invalid")
    assert request.call_count == 1


@pytest.mark.parametrize("prediction", [
    {"class_id": 1, "class_name": "versicolor", "request_id": REQUEST_ID},
    {"class_id": False, "class_name": "setosa", "request_id": REQUEST_ID},
    {"class_id": 0},
    {"class_id": 0, "class_name": "setosa", "request_id": "invalid"},
])
def test_smoke_rejects_unexpected_prediction(prediction: object) -> None:
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_loaded": True}),
        encoded_response(PASSPORT),
        encoded_response(prediction),
    ]):
        with pytest.raises(ValueError, match="Предсказание"):
            check_api("http://example.invalid")


@pytest.mark.parametrize("failure", [URLError("unreachable"), ValueError("bad JSON")])
def test_smoke_reports_failure_without_traceback(failure: Exception, capsys) -> None:
    with patch("scripts.check_api.urlopen", side_effect=failure):
        assert main(["--base-url", "http://example.invalid"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "http://example.invalid" in output.err
    assert "Traceback" not in output.err


@pytest.mark.parametrize("passport", [
    [], {}, {**PASSPORT, "feature_count": 3}, {**PASSPORT, "model_loaded": 1},
    {**PASSPORT, "path": "/synthetic/model.pkl"},
])
def test_smoke_rejects_unexpected_passport(passport: object) -> None:
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_loaded": True}), encoded_response(passport),
    ]) as request:
        with pytest.raises(ValueError, match="Паспорт"):
            check_api("http://example.invalid")
    assert request.call_count == 2


def test_smoke_rejects_mismatched_response_header() -> None:
    prediction = encoded_response({"class_id": 0, "class_name": "setosa", "request_id": REQUEST_ID})
    prediction.headers["X-Request-ID"] = "invalid"
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_loaded": True}),
        encoded_response(PASSPORT), prediction,
    ]):
        with pytest.raises(ValueError, match="Предсказание"):
            check_api("http://example.invalid")
