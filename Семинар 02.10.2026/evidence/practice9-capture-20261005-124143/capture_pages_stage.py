"""Capture stage 9 only after root has merged it and aligned the local branch with main."""

import argparse
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE = Path(__file__).resolve().parent
REPO = BASE / "history-draft"
SITE_URL = "https://kirill-erofeev.github.io/development-and-integration-labs/"
API_URL = SITE_URL + "api/"
WORKFLOW = "publish-api-docs.yaml"
LOCAL_INJECTION_HOST = "gc.kis.v2.scr.kaspersky-labs.com"
PY = ["py", "-3.11", "-B"]


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=REPO, text=True, encoding="utf-8").strip()


def canonical(schema: dict) -> bytes:
    return json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def save_json(path: Path, data: dict) -> None:
    if path.suffix.lower() != ".json" or not path.resolve().is_relative_to(BASE):
        raise ValueError("Ожидался новый JSON внутри каталога текущего прогона")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class RuntimeAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "script" and "src" in attributes:
            self.resources.append(attributes["src"])
        if tag == "link" and "stylesheet" in attributes.get("rel", "").split():
            self.resources.append(attributes.get("href", ""))


def check_public(sha: str, destination: Path) -> None:
    """Fetch only the four explicit public resources and compare them with this checkout."""
    if git("rev-parse", "HEAD") != sha:
        raise ValueError("HEAD изменился до проверки опубликованной схемы")
    resources = ("", "openapi.json", "swagger-ui.css", "swagger-ui-bundle.js")
    opener = build_opener(NoRedirect())
    responses, metadata = {}, []
    for relative in resources:
        url = API_URL + relative
        request = Request(url, headers={"Cache-Control": "no-cache"}, method="GET")
        with opener.open(request, timeout=30) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError(f"Не получен прямой HTTP 200: {url}")
            data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError("Ресурс превысил ожидаемый размер 5 MiB")
            metadata.append({
                "url": url, "status": response.status, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "content_type": response.headers.get("Content-Type"),
                "date": response.headers.get("Date"), "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "checked_at": datetime.now().astimezone().isoformat(),
            })
            responses[relative] = data
        print(f"HTTP 200: {url}", flush=True)
    parser = RuntimeAssets()
    parser.feed(responses[""].decode("utf-8"))
    if sorted(parser.resources) != ["./swagger-ui-bundle.js", "./swagger-ui.css"]:
        raise ValueError("Swagger UI использует неожиданные или нелокальные CSS/JS")
    for relative in ("", "swagger-ui.css", "swagger-ui-bundle.js"):
        local = REPO / "site" / "api" / (relative or "index.html")
        if responses[relative].replace(b"\r\n", b"\n") != local.read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError(f"Опубликованный ресурс отличается от текущей сборки: {relative or 'index.html'}")
    remote_schema = json.loads(responses["openapi.json"])
    local_schema = json.loads((REPO / "site/api/openapi.json").read_text(encoding="utf-8"))
    if canonical(remote_schema) != canonical(local_schema):
        raise ValueError("Опубликованная OpenAPI не совпадает с локальной схемой этого SHA")
    for path, method in (("/health", "get"), ("/predict", "post")):
        if method not in remote_schema.get("paths", {}).get(path, {}):
            raise ValueError(f"В опубликованной схеме отсутствует {method.upper()} {path}")
    save_json(destination, {
        "head_sha": sha, "schema_equal": True,
        "canonical_schema_sha256": hashlib.sha256(canonical(local_schema)).hexdigest(),
        "paths": sorted(remote_schema["paths"]), "text_comparison": "LF/CRLF normalized",
        "responses": metadata,
    })
    print("OpenAPI: каноническое равенство локальной и опубликованной схем подтверждено")
    print("HTML, CSS и JS совпадают с локальной сборкой с учётом LF/CRLF; CDN отсутствует")


def recheck_workflow(record: Path, sha: str, destination: Path) -> int:
    """Recheck the previously recorded run ID instead of selecting another concurrent run."""
    from github_checks import main

    previous = json.loads(record.read_text(encoding="utf-8"))
    if previous["head_sha"] != sha or previous["head_branch"] != "main" or previous["event"] != "push":
        raise ValueError("Первичная запись workflow не соответствует ожидаемому main/push/SHA")
    code = main([
        "--run-id", str(previous["id"]), "--workflow", WORKFLOW, "--sha", sha,
        "--event", "push", "--branch", "main", "--summary", "--steps", "--save", str(destination),
    ])
    if code == 0:
        for snapshot in (previous, json.loads(destination.read_text(encoding="utf-8"))):
            jobs = {job["name"]: job for job in snapshot["jobs"]}
            for name in ("build", "deploy"):
                if name not in jobs or jobs[name]["status"] != "completed" or jobs[name]["conclusion"] != "success":
                    raise ValueError(f"Pages job {name} не подтвердил успешное завершение")
        print("Pages: build=success, deploy=success; run ID проверен повторно")
    return code


def current_sha() -> str:
    sha = git("rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Нужен точный 40-символьный SHA")
    if git("branch", "--show-current") != "replay-20261005/lab-09-pages" or git("rev-parse", "github/main") != sha:
        raise ValueError("Root должен сначала выровнять replay-20261005/lab-09-pages с github/main")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Отслеживаемые файлы должны быть чистыми до фиксации доказательств")
    return sha


def execute() -> dict:
    from capture_stage import capture, manifest

    sha = current_sha()
    target = REPO / manifest["stages"][8]["folder"]
    for name in ("practice9-export", "practice9-workflow", "practice9-swagger"):
        if any((target / "screenshots" / (name + suffix)).exists() for suffix in (".png", ".png.json")):
            raise FileExistsError(f"Снимок {name} уже существует; автоматической перезаписи нет")
    result_path = BASE / "result-practice9.json"
    if result_path.exists():
        raise FileExistsError("Итог result-practice9.json уже существует")
    scratch = BASE / ("pages-check-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    scratch.mkdir(exist_ok=False)
    first, again, http_record = (scratch / name for name in ("workflow.json", "workflow-recheck.json", "http.json"))
    missing_model = REPO / ".verification" / "missing-model-for-pages-proof.pkl"
    if missing_model.exists():
        raise FileExistsError("Контрольный путь отсутствующей модели неожиданно существует")
    build = (
        "import os,sys; os.environ['ML_MODEL_PATH']=sys.argv[1]; "
        "print('ML_MODEL_PATH намеренно указывает на отсутствующий файл'); "
        "from scripts.build_api_docs import main; raise SystemExit(main(['--output','site']))"
    )
    validate = (
        "import json; from pathlib import Path; "
        "s=json.loads(Path('site/api/openapi.json').read_text(encoding='utf-8')); "
        "assert 'get' in s['paths']['/health'] and 'post' in s['paths']['/predict']; "
        "print('JSON валиден; OpenAPI',s['openapi']); print('Маршруты:',', '.join(sorted(s['paths'])))"
    )
    workflow_args = PY + [str(BASE / "github_checks.py"), "--workflow", WORKFLOW, "--sha", sha,
                          "--event", "push", "--branch", "main", "--summary", "--steps", "--save", str(first)]
    groups = [
        ("practice9-export", "Практика 9 · экспорт OpenAPI без сервера и модели", [
            ("Тесты экспорта и статики", PY + ["-m", "pytest", "-q", "scripts/tests/test_export_openapi.py"], 0, 180),
            ("Сборка с отсутствующей моделью", PY + ["-c", build, str(missing_model)], 0, 120),
            ("Проверка JSON и контракта", PY + ["-c", validate], 0, 30),
        ]),
        ("practice9-workflow", "Практика 9 · GitHub Pages и опубликованная схема", [
            ("Pages workflow main", workflow_args, 0, 1250),
            ("HTTP и соответствие опубликованной схемы", PY + [str(Path(__file__).resolve()), "check-public", "--sha", sha, "--save", str(http_record)], 0, 150),
            ("Повторная проверка Pages run", PY + [str(Path(__file__).resolve()), "recheck-workflow", "--record", str(first), "--sha", sha, "--save", str(again)], 0, 1250),
        ], ["Pages workflow main", "HTTP и соответствие опубликованной схемы"]),
    ]
    # Keep the final proof result unavailable until the genuine public browser capture succeeds.
    result = capture(9, groups, prefix="practice9-capture")
    folder = (REPO / result["manifest"]).parent
    for source in (first, again, http_record, Path(__file__).resolve(), BASE / "github_checks.py"):
        shutil.copyfile(source, folder / source.name)
    return finish_browser(result, target, sha)


def finish_browser(result: dict, target: Path, sha: str, preserved: dict | None = None) -> dict:
    """Add the real browser proof without rerunning or replacing command evidence."""
    from capture_api_stage import BrowserSession, frame

    folder = (REPO / result["manifest"]).parent
    result_path = BASE / "result-practice9.json"
    screenshot = target / "screenshots/practice9-swagger.png"
    for path in (result_path, screenshot, screenshot.with_suffix(".png.json"), folder / "browser-state.json",
                 folder / "practice9-swagger-browser.png", folder / "practice9-swagger-browser.png.json",
                 folder / "practice9-swagger-frame.html", folder / "capture_pages_stage-resume.py"):
        if path.exists():
            raise FileExistsError(f"Продолжение не перезаписывает существующий файл: {path.name}")
    with BrowserSession(profile_root=REPO / ".verification/browser") as browser:
        # Block the observed local antivirus injection only in this isolated CDP session.
        browser.call("Network.enable")
        browser.call("Network.setBlockedURLs", {"urls": [f"https://{LOCAL_INJECTION_HOST}/*"]})
        browser.navigate(API_URL)
        browser.wait_for_selector(".swagger-ui .opblock")
        # Swagger UI binds expansion to the semantic button, not its surrounding div.
        for method, path in (("get", "/health"), ("post", "/predict")):
            browser.evaluate("""(() => {
            const path = """ + json.dumps(path) + """;
            const block = [...document.querySelectorAll('.opblock')].find(el =>
              el.querySelector('.opblock-summary-path')?.textContent.trim() === path);
            if (!block) throw new Error('Endpoint is missing: ' + path);
            if (!block.classList.contains('is-open')) block.querySelector('button.opblock-summary-control').click();
            return true;
            })()""")
            browser.wait_for_selector(f".opblock-{method}.is-open .opblock-body")
        state = browser.evaluate("""(() => {
          const config = window.ui.getConfigs();
          return {url: location.href, schema_url: config.url,
            supported_submit_methods: config.supportedSubmitMethods, validator_url: config.validatorUrl,
            operations: [...document.querySelectorAll('.opblock')].map(el => ({
              method: el.querySelector('.opblock-summary-method')?.textContent.trim(),
              path: el.querySelector('.opblock-summary-path')?.textContent.trim(),
              expanded: el.classList.contains('is-open')})),
            resources: performance.getEntriesByType('resource').map(item => {
              const resource = new URL(item.name);
              return {url: resource.origin === location.origin ? item.name : resource.origin + '/<path-omitted>',
                host: resource.hostname, initiator: item.initiatorType, status: item.responseStatus};
            })};
        })()""")
        if state["url"].split("#", 1)[0] != API_URL or state["schema_url"] != "./openapi.json":
            raise ValueError("Браузер открыл неожиданный URL документации или схемы")
        if state["supported_submit_methods"] != [] or state["validator_url"] is not None:
            raise ValueError("Статический Swagger допускает запросы API или внешний validator")
        if {(item["method"], item["path"]) for item in state["operations"] if item["expanded"]} != {
            ("GET", "/health"), ("POST", "/predict")
        }:
            raise ValueError("Оба ожидаемых маршрута должны быть раскрыты")
        for resource in state["resources"]:
            if urlsplit(resource["url"]).scheme in {"http", "https"} and not resource["url"].startswith(SITE_URL):
                blocked_injection = resource["host"] == LOCAL_INJECTION_HOST and resource["status"] == 0
                favicon_probe = (resource["url"] == "https://kirill-erofeev.github.io/favicon.ico"
                                 and resource["initiator"] == "other" and resource["status"] == 404)
                if not blocked_injection and not favicon_probe:
                    raise ValueError("В браузере обнаружен незаблокированный ресурс вне публичного сайта репозитория")
        runtime = {item["url"] for item in state["resources"] if item["status"] == 200}
        if not {API_URL + name for name in ("openapi.json", "swagger-ui.css", "swagger-ui-bundle.js")} <= runtime:
            raise ValueError("Браузер не подтвердил HTTP 200 схемы, CSS и JS")
        state["favicon_note"] = "Chrome может проверять /favicon.ico на корне хоста (404); это не ресурс Swagger UI"
        state["local_software_injection"] = {
            "blocked_host": LOCAL_INJECTION_HOST,
            "reason": "Локальный антивирус добавляет script; загрузка заблокирована только в изолированном CDP-сеансе",
            "source_html_check": "Отдельная HTTP-проверка опубликованного HTML сохранена в http.json; CSS/JS локальные",
        }
        # Preserve the downloaded JSON text: JavaScript turns schema numeric 0.0 into 0.
        browser_schema = json.loads(browser.evaluate("window.ui.specSelectors.specStr()"))
        local_schema = json.loads((REPO / "site/api/openapi.json").read_text(encoding="utf-8"))
        if canonical(browser_schema) != canonical(local_schema):
            raise ValueError("Схема, загруженная браузером, отличается от локальной сборки")
        state["canonical_schema_sha256"] = hashlib.sha256(canonical(browser_schema)).hexdigest()
        state["schema_equal"] = True
        state["schema_source"] = "Исходный JSON, загруженный Swagger UI (specSelectors.specStr)"
        save_json(folder / "browser-state.json", {"head_sha": sha, **state})
        frame(browser, screenshot, "Практика 9 · опубликованный Swagger UI", folder, sha)
    if git("rev-parse", "HEAD") != sha or git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Рабочее дерево изменилось во время фиксации доказательств")
    if preserved:
        for path, digest in preserved.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Существующее доказательство изменилось: {path.name}")
        source = folder / "capture_pages_stage-resume.py"
        with source.open("xb") as stream:
            stream.write(Path(__file__).read_bytes())
        result["resume_source"] = str(source.relative_to(REPO))
    result["screenshots"].append(str(screenshot.relative_to(REPO)))
    result["public_url"] = API_URL
    result["workflow_metadata"] = str((folder / "workflow.json").relative_to(REPO))
    result["http_metadata"] = str((folder / "http.json").relative_to(REPO))
    save_json(result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def resume() -> dict:
    """Validate the exact partial result, then capture only its missing Swagger screenshot."""
    from capture_stage import manifest

    sha = current_sha()
    record = BASE / "result-practice9-capture.json"
    result = json.loads(record.read_text(encoding="utf-8"))
    target = REPO / manifest["stages"][8]["folder"]
    expected_shots = [target / f"screenshots/practice9-{name}.png" for name in ("export", "workflow")]
    if result["stage"] != 9 or result["sha"] != sha or result["screenshots"] != [
        str(path.relative_to(REPO)) for path in expected_shots
    ]:
        raise ValueError("Частичный результат не соответствует текущему SHA или двум ожидаемым PNG")
    manifest_path = (REPO / result["manifest"]).resolve(strict=True)
    folder = manifest_path.parent
    if folder.parent != (target / "evidence").resolve() or not folder.name.startswith("practice9-capture-") or manifest_path.name != "manifest.json":
        raise ValueError("Манифест находится вне ожидаемого каталога доказательств")
    evidence = json.loads(manifest_path.read_text(encoding="utf-8"))
    commands = evidence["commands"]
    if evidence["status"] != "succeeded" or len(commands) != 6 or evidence["log_file"] != "commands.log":
        raise ValueError("Ожидались шесть успешно выполненных команд")
    log = (folder / "commands.log").read_bytes()
    for command in commands:
        if command["status"] != "succeeded" or command["returncode"] != 0 or command["verified_sha"] != sha:
            raise ValueError("Команда не подтверждает успешное выполнение на текущем SHA")
        for side in ("before", "after"):
            provenance = command[f"provenance_{side}"]
            if provenance["head_sha"] != sha or not provenance["tracked_clean"]:
                raise ValueError("Происхождение команды не соответствует чистому текущему SHA")
        for channel in ("stdout", "stderr"):
            segment = command[channel]
            data = log[segment["offset"]:segment["offset"] + segment["length"]]
            if len(data) != segment["length"] or hashlib.sha256(data).hexdigest() != segment["sha256"]:
                raise ValueError("Хеш сохранённого вывода команды не совпадает")
    for shot in expected_shots:
        metadata = json.loads(shot.with_suffix(".png.json").read_text(encoding="utf-8"))
        if metadata["verified_worktree_sha"] != sha or hashlib.sha256(shot.read_bytes()).hexdigest() != metadata["png_sha256"]:
            raise ValueError("SHA или хеш готового PNG не совпадает")
    workflows = [json.loads((folder / name).read_text(encoding="utf-8")) for name in ("workflow.json", "workflow-recheck.json")]
    if workflows[0]["id"] != workflows[1]["id"]:
        raise ValueError("Первичная и повторная записи описывают разные Pages run")
    for workflow in workflows:
        if any(workflow[key] != value for key, value in {
            "head_sha": sha, "head_branch": "main", "event": "push", "status": "completed", "conclusion": "success"
        }.items()):
            raise ValueError("Сохранённый workflow не подтверждает успешный main/push текущего SHA")
        jobs = {job["name"]: job for job in workflow["jobs"]}
        if any(jobs[name]["status"] != "completed" or jobs[name]["conclusion"] != "success" for name in ("build", "deploy")):
            raise ValueError("Сохранённые Pages jobs не завершились успешно")
    http = json.loads((folder / "http.json").read_text(encoding="utf-8"))
    expected_urls = {API_URL + name for name in ("", "openapi.json", "swagger-ui.css", "swagger-ui-bundle.js")}
    schema = json.loads((REPO / "site/api/openapi.json").read_text(encoding="utf-8"))
    if http["head_sha"] != sha or http["schema_equal"] is not True or http["canonical_schema_sha256"] != hashlib.sha256(canonical(schema)).hexdigest():
        raise ValueError("Сохранённая HTTP-проверка не соответствует текущей локальной схеме")
    if {item["url"] for item in http["responses"]} != expected_urls or any(item["status"] != 200 for item in http["responses"]):
        raise ValueError("Сохранённая HTTP-проверка не подтверждает все четыре ресурса")
    kept = [record, manifest_path, *(folder / name for name in (
        "commands.log", "workflow.json", "workflow-recheck.json", "http.json", "capture_pages_stage.py", "github_checks.py",
        "practice9-export.html", "practice9-workflow.html")), *expected_shots,
        *(shot.with_suffix(".png.json") for shot in expected_shots)]
    preserved = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in kept}
    print("Возобновление: SHA, шесть команд, журналы, Pages workflow, HTTP и два PNG проверены; команды не повторяются", flush=True)
    return finish_browser(result, target, sha, preserved)


def main() -> int:
    parser = argparse.ArgumentParser(description="Зафиксировать реальные доказательства этапа GitHub Pages")
    parser.add_argument("action", nargs="?", default="capture", choices=("capture", "resume", "check-public", "recheck-workflow"))
    parser.add_argument("--sha")
    parser.add_argument("--save", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    if args.action == "capture":
        execute()
    elif args.action == "resume":
        resume()
    else:
        if not args.sha or not re.fullmatch(r"[0-9a-f]{40}", args.sha) or args.save is None:
            parser.error("Для внутренней проверки нужны --sha и --save")
        if args.action == "check-public":
            check_public(args.sha, args.save)
        elif args.record is None:
            parser.error("Нужен --record с первичной записью workflow")
        else:
            return recheck_workflow(args.record, args.sha, args.save)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
