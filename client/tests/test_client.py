import json
from pathlib import Path

import pytest
import requests

from client import client


REQUEST_ID = "e21f05a0-837f-4ea9-84a0-621ce8f8b0a8"
VALID_RESPONSE = {"class_id": 0, "class_name": "setosa", "request_id": REQUEST_ID}


class FakeResponse:
    def __init__(self, payload, status_code=200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.status_checked = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        self.status_checked = True
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        assert self.status_checked
        if self.json_error is not None:
            raise self.json_error
        return self.payload


@pytest.fixture
def stub_post(monkeypatch):
    def install(payload=VALID_RESPONSE, status_code=200, error=None, json_error=None):
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            if error is not None:
                raise error
            return FakeResponse(payload, status_code, json_error)

        monkeypatch.setattr(client.requests, "post", post)
        return calls

    return install


@pytest.mark.parametrize(
    "payload",
    [
        {"class_id": 0, "class_name": "setosa", "request_id": REQUEST_ID},
        {"class_id": 1, "class_name": "versicolor", "request_id": REQUEST_ID},
        {"class_id": 2, "class_name": "virginica", "request_id": REQUEST_ID},
    ],
)
def test_run_prediction_saves_validated_response(tmp_path, stub_post, payload):
    calls = stub_post(payload=payload)
    result_path = tmp_path / "results" / "prediction.json"

    assert client.run_prediction("http://api:8000/", result_path) == payload

    assert json.loads(result_path.read_text(encoding="utf-8")) == payload
    assert list(result_path.parent.iterdir()) == [result_path]
    assert calls == [
        (
            "http://api:8000/predict",
            {
                "json": {
                    "sepal_length": 5.1,
                    "sepal_width": 3.5,
                    "petal_length": 1.4,
                    "petal_width": 0.2,
                },
                "timeout": 10,
                "allow_redirects": False,
            },
        )
    ]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"class_id": 0},
        {"class_id": True, "class_name": "versicolor", "request_id": REQUEST_ID},
        {"class_id": 0.0, "class_name": "setosa", "request_id": REQUEST_ID},
        {"class_id": "0", "class_name": "setosa", "request_id": REQUEST_ID},
        {"class_id": -1, "class_name": "virginica", "request_id": REQUEST_ID},
        {"class_id": 3, "class_name": "setosa", "request_id": REQUEST_ID},
        {"class_id": 0, "class_name": "versicolor", "request_id": REQUEST_ID},
        {"class_id": 0, "class_name": None, "request_id": REQUEST_ID},
        {"class_id": 0, "class_name": "setosa", "request_id": REQUEST_ID, "extra": 1},
    ],
)
def test_validate_prediction_rejects_invalid_schema(payload):
    with pytest.raises(ValueError):
        client.validate_prediction(payload)


@pytest.mark.parametrize("request_id", [None, 123, "invalid", REQUEST_ID.upper()])
def test_validate_prediction_rejects_invalid_request_id(request_id):
    with pytest.raises(ValueError):
        client.validate_prediction({**VALID_RESPONSE, "request_id": request_id})


@pytest.mark.parametrize(
    "response_options",
    [
        {"status_code": 503},
        {"status_code": 302},
        {"error": requests.Timeout("timeout")},
        {"error": requests.ConnectionError("connection failed")},
        {"json_error": requests.exceptions.JSONDecodeError("invalid JSON", "x", 0)},
        {"payload": {"class_id": 0, "class_name": "virginica", "request_id": REQUEST_ID}},
    ],
)
@pytest.mark.parametrize("existing_result", [False, True])
def test_main_failure_preserves_result(
    monkeypatch, tmp_path, stub_post, capsys, response_options, existing_result
):
    result_path = tmp_path / "prediction.json"
    previous_content = '{"class_id": 1, "class_name": "versicolor"}\n'
    if existing_result:
        result_path.write_text(previous_content, encoding="utf-8")
    monkeypatch.setenv("API_URL", "http://custom-api:9000")
    monkeypatch.setenv("RESULT_PATH", str(result_path))
    calls = stub_post(**response_options)

    assert client.main() == 1

    assert len(calls) == 1
    if existing_result:
        assert result_path.read_text(encoding="utf-8") == previous_content
    else:
        assert not result_path.exists()
    output = capsys.readouterr()
    assert "http://custom-api:9000" in output.out
    assert str(result_path) in output.out
    assert "Не удалось" in output.err
    assert "Traceback" not in output.err


def test_main_reads_environment(monkeypatch, tmp_path, stub_post, capsys):
    result_path = tmp_path / "custom" / "prediction.json"
    monkeypatch.setenv("API_URL", "http://configured-api:9000/")
    monkeypatch.setenv("RESULT_PATH", str(result_path))
    calls = stub_post()

    assert client.main() == 0

    assert calls[0][0] == "http://configured-api:9000/predict"
    assert json.loads(result_path.read_text(encoding="utf-8")) == VALID_RESPONSE
    output = capsys.readouterr()
    assert "http://configured-api:9000/" in output.out
    assert str(result_path) in output.out
    assert "Предсказание сохранено" in output.out
    assert not output.err


def test_main_uses_defaults(monkeypatch, capsys):
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.delenv("RESULT_PATH", raising=False)
    calls = []

    def run_prediction(api_url, result_path):
        calls.append((api_url, result_path))
        return VALID_RESPONSE

    monkeypatch.setattr(client, "run_prediction", run_prediction)

    assert client.main() == 0

    assert calls == [("http://api:8000", Path("/results/prediction.json"))]
    assert "http://api:8000" in capsys.readouterr().out


def test_main_reports_invalid_output_directory(monkeypatch, tmp_path, stub_post, capsys):
    blocked_directory = tmp_path / "file"
    blocked_directory.write_text("synthetic blocker", encoding="utf-8")
    result_path = blocked_directory / "prediction.json"
    monkeypatch.setenv("RESULT_PATH", str(result_path))
    stub_post()

    assert client.main() == 1

    assert blocked_directory.read_text(encoding="utf-8") == "synthetic blocker"
    assert "Не удалось" in capsys.readouterr().err


def test_failed_replacement_preserves_result_and_cleans_temp(
    monkeypatch, tmp_path, stub_post
):
    result_path = tmp_path / "prediction.json"
    previous_content = '{"class_id": 1, "class_name": "versicolor"}\n'
    result_path.write_text(previous_content, encoding="utf-8")
    stub_post()

    def replace(_self, _target):
        raise PermissionError("synthetic write failure")

    monkeypatch.setattr(Path, "replace", replace)

    with pytest.raises(PermissionError, match="synthetic write failure"):
        client.run_prediction("http://api:8000", result_path)

    assert result_path.read_text(encoding="utf-8") == previous_content
    assert list(tmp_path.iterdir()) == [result_path]
