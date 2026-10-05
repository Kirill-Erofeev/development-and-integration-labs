from io import BytesIO
import json
from urllib.error import URLError
from unittest.mock import patch

import pytest

from scripts.check_api import check_api, main


def encoded_response(payload: object) -> BytesIO:
    return BytesIO(json.dumps(payload).encode("utf-8"))


def test_smoke_checks_ready_model_and_prediction() -> None:
    expected = {"prediction": 0, "class_name": "setosa"}
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_ready": True}),
        encoded_response(expected),
    ]) as request:
        assert check_api("http://example.invalid:8080/") == expected
    assert request.call_args_list[0].args == ("http://example.invalid:8080/health",)
    prediction_request = request.call_args_list[1].args[0]
    assert prediction_request.full_url == "http://example.invalid:8080/predict"
    assert prediction_request.method == "POST"
    assert json.loads(prediction_request.data) == {
        "sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2,
    }
    assert all(call.kwargs["timeout"] == 10 for call in request.call_args_list)


@pytest.mark.parametrize("health", [{"status": "ok", "model_ready": False}, {"status": "ok", "model_ready": 1}, []])
def test_unready_model_prevents_prediction(health: object) -> None:
    with patch("scripts.check_api.urlopen", return_value=encoded_response(health)) as request:
        with pytest.raises(ValueError, match="готовность"):
            check_api("http://example.invalid")
    assert request.call_count == 1


@pytest.mark.parametrize("prediction", [
    {"prediction": 1, "class_name": "versicolor"},
    {"prediction": False, "class_name": "setosa"},
    {"prediction": 0},
])
def test_smoke_rejects_unexpected_prediction(prediction: object) -> None:
    with patch("scripts.check_api.urlopen", side_effect=[
        encoded_response({"status": "ok", "model_ready": True}),
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
