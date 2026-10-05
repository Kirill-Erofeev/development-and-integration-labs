from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Thread
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen

import pytest

from scripts.build_api_docs import build_site, validate_site
from scripts.export_openapi import main


ROOT = Path(__file__).resolve().parents[2]


def test_fresh_export_needs_no_model_lifespan_or_network(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "openapi.json"
    probe = r'''
from unittest.mock import patch
import runpy
import sys

sys.argv = ["scripts.export_openapi", "--output", sys.argv[1]]
with patch("src.model_service.ModelService.load", side_effect=AssertionError("model load")), \
     patch("socket.socket.connect", side_effect=AssertionError("network connect")), \
     patch("socket.socket.bind", side_effect=AssertionError("server bind")), \
     patch("uvicorn.run", side_effect=AssertionError("server startup")):
    runpy.run_module("scripts.export_openapi", run_name="__main__")
'''
    env = {**os.environ, "ML_MODEL_PATH": str(tmp_path / "missing-model.pkl")}
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", probe, str(output)],
        cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    schema = json.loads(output.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    assert schema["paths"]["/health"]["get"]["responses"]["200"]
    assert schema["paths"]["/predict"]["post"]["requestBody"]["required"] is True
    request = schema["components"]["schemas"]["PredictRequest"]
    assert set(request["required"]) == {
        "sepal_length", "sepal_width", "petal_length", "petal_width",
    }
    assert request["additionalProperties"] is False
    assert all(field["exclusiveMinimum"] == 0 for field in request["properties"].values())


def test_export_reports_unwritable_destination(tmp_path: Path, capsys) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("existing", encoding="utf-8")
    assert main(["--output", str(occupied / "openapi.json")]) == 1
    assert "Не удалось экспортировать OpenAPI" in capsys.readouterr().err
    assert occupied.read_text(encoding="utf-8") == "existing"


class ResourceLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.links.extend(value for key, value in attrs if key in {"href", "src"} and value)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def test_built_site_serves_relative_assets_and_schema_under_repo_prefix(tmp_path: Path) -> None:
    site = tmp_path / "project-name"
    expected = build_site(site)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(tmp_path)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/project-name/"
    try:
        for page in (base, urljoin(base, "api/")):
            with urlopen(page, timeout=5) as response:
                document = response.read().decode("utf-8")
            parser = ResourceLinks()
            parser.feed(document)
            assert parser.links
            for link in parser.links:
                assert not urlsplit(link).scheme and not link.startswith("/")
                resolved = urljoin(page, link)
                assert resolved.startswith(base)
                with urlopen(resolved, timeout=5) as response:
                    assert response.status == 200
                    assert response.read()
        assert re.search(r'url:\s*"\./openapi\.json"', document)
        assert "validatorUrl: null" in document
        assert "supportedSubmitMethods: []" in document
        with urlopen(urljoin(base, "api/openapi.json"), timeout=5) as response:
            assert json.load(response) == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_build_refreshes_schema_but_preserves_foreign_files(tmp_path: Path) -> None:
    site = tmp_path / "site"
    expected = build_site(site)
    (site / "api/openapi.json").write_text("{}", encoding="utf-8")
    assert build_site(site) == expected
    foreign = site / "keep.txt"
    foreign.write_text("do not delete", encoding="utf-8")
    with pytest.raises(ValueError, match="посторонние"):
        build_site(site)
    assert foreign.read_text(encoding="utf-8") == "do not delete"


def test_site_validation_rejects_missing_operation(tmp_path: Path) -> None:
    site = tmp_path / "site"
    schema = build_site(site)
    del schema["paths"]["/predict"]
    (site / "api/openapi.json").write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(ValueError, match="POST /predict"):
        validate_site(site)
