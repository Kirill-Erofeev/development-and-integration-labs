"""Run explicit loopback HTTP checks and observe genuine browser form submissions."""

import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID


WORK_ROOT = Path(__file__).resolve().parent
REQUEST_ID = "e21f05a0-837f-4ea9-84a0-621ce8f8b0a8"
FEATURES = {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def local_base_url(value: str) -> str:
    """Keep this verification helper restricted to the explicitly started local service."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Нужен локальный HTTP origin без учётных данных, пути и query")
    return value.rstrip("/")


def http_request(base_url: str, path: str, payload: dict | None = None,
                 request_id: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    request = Request(
        local_base_url(base_url) + path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers, method="GET" if payload is None else "POST",
    )
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return {
            "status": response.status,
            "json": json.load(response),
            "x_request_id": response.headers.get("X-Request-ID"),
            "sent_request_id": request_id,
        }


def show_response(response: dict) -> None:
    print(f"HTTP {response['status']}")
    print("JSON: " + json.dumps(response["json"], ensure_ascii=False, sort_keys=True))
    print("X-Request-ID: " + str(response["x_request_id"]))


def assert_uuid(response: dict, expected: str | None = None) -> str:
    value = response["json"].get("request_id")
    assert isinstance(value, str) and str(UUID(value)) == value, "Неканонический UUID в JSON"
    assert response["x_request_id"] == value, "UUID заголовка и JSON различаются"
    if expected is not None:
        assert value == str(UUID(expected)), "Сервер не сохранил переданный UUID"
    else:
        assert UUID(value).version == 4, "Сервер должен сгенерировать UUIDv4"
    return value


def assert_prediction(response: dict, variant4: bool, expected_id: str | None = None) -> None:
    assert response["status"] == 200, "Ожидался успешный прогноз"
    if variant4:
        request_id = assert_uuid(response, expected_id)
        expected = {"class_id": 0, "class_name": "setosa", "request_id": request_id}
        assert type(response["json"].get("class_id")) is int
    else:
        expected = {"prediction": 0, "class_name": "setosa"}
        assert type(response["json"].get("prediction")) is int
    assert response["json"] == expected, "Прогноз не соответствует контрольному примеру Iris"


def assert_error(response: dict, variant4: bool, expected_id: str) -> None:
    assert response["status"] == 422, "Нулевой признак должен дать HTTP 422"
    errors = response["json"]["detail"]
    assert isinstance(errors, list) and any(
        error.get("loc") == ["body", "petal_width"] and error.get("type") == "greater_than"
        for error in errors
    ), "Ответ не описывает ошибку petal_width"
    if variant4:
        assert_uuid(response, expected_id)


def match_server_event(response: dict, log_path: Path) -> dict:
    """Read only the caller's exact server.log under this verification work directory."""
    absolute = log_path.absolute()
    for entry in (absolute, *absolute.parents):
        metadata = entry.lstat()
        if entry.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("Журнал не должен проходить через ссылку или reparse point")
    path = absolute.resolve(strict=True)
    if path.name != "server.log" or not path.is_relative_to(WORK_ROOT):
        raise ValueError("Разрешён только явно указанный server.log внутри каталога этого прогона")
    if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Ожидался обычный небольшой журнал нашего локального сервера")
    assert_prediction(response, True, response.get("sent_request_id"))
    expected = {
        "event": "prediction_completed", "request_id": response["json"]["request_id"],
        "class_name": response["json"]["class_name"],
    }
    matches = []
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.lstrip().startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event == expected:
                matches.append(event)
    assert matches, "Событие с UUID реального ответа не найдено в server.log"
    return {"event": expected, "matching_events": len(matches)}


def exercise_form(browser, base_url: str, *, invalid: bool = False, navigate: bool = True) -> dict:
    """Submit the actual page form; observe fetch without replacing responses or DOM results."""
    base_url = local_base_url(base_url)
    if navigate:
        browser.navigate(base_url + "/")
    assert browser.evaluate("location.origin") == base_url, "Страница открыта на другом origin"
    browser.wait_for_selector("#form")
    browser.evaluate("""new Promise((resolve, reject) => {
      const deadline = Date.now() + 15000;
      const check = () => {
        if (document.querySelectorAll('#passport dd').length === 4 &&
            document.querySelector('#health').textContent.includes('Сервис и модель готовы')) return resolve(true);
        if (Date.now() > deadline) return reject(new Error('Passport or readiness missing'));
        setTimeout(check, 50);
      }; check();
    })""")
    values = {**FEATURES, **({"petal_width": 0} if invalid else {})}
    expression = """(async () => {
      const values = VALUES;
      const form = document.querySelector('#form');
      if (!window.__liveOriginalFetch) {
        window.__liveOriginalFetch = window.fetch.bind(window);
        window.fetch = async (resource, options) => {
          const response = await window.__liveOriginalFetch(resource, options);
          if (new URL(resource, location.href).pathname === '/predict') {
            window.__liveLastResponse = {
              status: response.status, json: await response.clone().json(),
              x_request_id: response.headers.get('X-Request-ID'),
              sent_request_id: new Headers(options?.headers).get('X-Request-ID'),
            };
          }
          return response;
        };
      }
      window.__liveLastResponse = null;
      for (const [name, value] of Object.entries(values)) {
        const input = form.elements.namedItem(name);
        input.value = value;
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
      }
      let submission = 'form';
      if (form.checkValidity()) {
        form.requestSubmit();
      } else if (INVALID) {
        submission = 'browser-fetch-after-form-edit';
        const body = Object.fromEntries(new FormData(form));
        for (const name in body) body[name] = Number(body[name]);
        await fetch('/predict', {method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-Request-ID': crypto.randomUUID()},
          body: JSON.stringify(body)});
      } else {
        throw new Error('Valid control data rejected by native form validation');
      }
      await new Promise((resolve, reject) => {
        const deadline = Date.now() + 15000;
        const check = () => {
          if (window.__liveLastResponse && !form.querySelector('button').disabled) return resolve();
          if (Date.now() > deadline) return reject(new Error('Prediction did not finish'));
          setTimeout(check, 50);
        }; check();
      });
      const terms = [...document.querySelectorAll('#passport dt')];
      return {
        health: document.querySelector('#health').textContent,
        passport: Object.fromEntries(terms.map(term => [term.textContent, term.nextElementSibling.textContent])),
        inputs: Object.fromEntries(new FormData(form)), submission,
        last_request: window.__liveLastResponse,
        result: document.querySelector('#result').textContent,
        result_visible: !document.querySelector('#result').hidden,
        error: document.querySelector('#error').textContent,
        displayed_request_id: document.querySelector('#result code')?.textContent ?? null,
      };
    })()""".replace("VALUES", json.dumps(values)).replace("INVALID", "true" if invalid else "false")
    snapshot = browser.evaluate(expression)
    response = snapshot["last_request"]
    if invalid:
        assert_error(response, True, response["sent_request_id"])
        if snapshot["submission"] == "form":
            assert not snapshot["result_visible"] and snapshot["error"]
            assert response["json"]["request_id"] in snapshot["error"]
    else:
        assert_prediction(response, True, response["sent_request_id"])
        assert snapshot["result_visible"] and not snapshot["error"]
        assert snapshot["displayed_request_id"] == response["json"]["request_id"]
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить реальный локальный Iris API")
    parser.add_argument("command", choices=("health", "predict", "error", "model-info", "identity"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--variant4", action="store_true")
    parser.add_argument("--request-id", default=REQUEST_ID)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--response-json", help="Реальный объект last_request из exercise_form для сверки с логом")
    args = parser.parse_args(argv)
    try:
        local_base_url(args.base_url)
        if args.command in {"model-info", "identity"} and not args.variant4:
            raise ValueError("Эта проверка требует --variant4")
        if args.command == "identity":
            if args.log_path is None:
                raise ValueError("Для сверки нужен точный --log-path нашего server.log")
            response = (json.loads(args.response_json) if args.response_json else
                        http_request(args.base_url, "/predict", FEATURES))
            show_response(response)
            match = match_server_event(response, args.log_path)
            print("Совпадение с журналом: " + json.dumps(match, ensure_ascii=False, sort_keys=True))
        elif args.command in {"predict", "error"}:
            payload = {**FEATURES, **({"petal_width": 0} if args.command == "error" else {})}
            response = http_request(args.base_url, "/predict", payload, args.request_id)
            show_response(response)
            if args.command == "predict":
                assert_prediction(response, args.variant4, args.request_id)
            else:
                assert_error(response, args.variant4, args.request_id)
        else:
            response = http_request(args.base_url, "/" + args.command)
            show_response(response)
            assert response["status"] == 200
            if args.command == "health":
                flag = "model_loaded" if args.variant4 else "model_ready"
                assert response["json"] == {"status": "ok", flag: True}
                assert response["json"][flag] is True
            else:
                assert response["json"] == {
                    "model_type": "LogisticRegression", "classes": ["setosa", "versicolor", "virginica"],
                    "feature_count": 4, "model_loaded": True,
                }
                assert type(response["json"]["feature_count"]) is int
                assert response["json"]["model_loaded"] is True
        print("Проверка пройдена")
        return 0
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Проверка не пройдена: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
