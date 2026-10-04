"""Read and wait for selected GitHub Actions runs without dispatching or changing them."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlencode


BASE = Path(__file__).resolve().parent
GH = BASE.parent / "tools" / "gh" / "bin" / "gh.exe"
REPOSITORY = "Kirill-Erofeev/development-and-integration-labs"
WORKFLOWS = ("ci.yaml", "delivery.yaml", "publish-api-docs.yaml")
RUN_FIELDS = "{id, url: .html_url, head_sha, head_branch, event, status, conclusion, path}"
JOB_FIELDS = "{name, status, conclusion, steps: [.steps[]? | {name, status, conclusion}]}"


def sha40(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise argparse.ArgumentTypeError("Нужен полный SHA из 40 шестнадцатеричных символов")
    return value.lower()


def positive(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("Значение должно быть положительным")
    return result


def api(endpoint: str, query: str, deadline: float):
    """Filter API metadata in gh before Python receives it; never print raw API errors."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Истекло время ожидания GitHub Actions")
    command = [
        str(GH), "api", "--hostname", "github.com", "--method", "GET", endpoint,
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28", "--jq", query,
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            timeout=min(30.0, remaining), check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("GitHub API не ответил в пределах таймаута запроса") from exc
    if result.returncode:
        status = re.search(r"\bHTTP (\d{3})\b", result.stderr)
        detail = f", HTTP {status.group(1)}" if status else ""
        raise RuntimeError(f"gh api завершился с кодом {result.returncode}{detail}")
    return json.loads(result.stdout)


def paged_items(endpoint: str, collection: str, fields: str, deadline: float) -> list[dict]:
    """Read filtered pages separately because gh disallows --slurp together with --jq."""
    items = []
    page = 1
    query = f"{{total_count, items: [.{collection}[] | {fields}]}}"
    while True:
        separator = "&" if "?" in endpoint else "?"
        result = api(f"{endpoint}{separator}page={page}", query, deadline)
        items.extend(result["items"])
        if not result["items"] or len(items) >= result["total_count"]:
            return items
        page += 1
        print(f"Чтение страницы метаданных {page}", file=sys.stderr, flush=True)


def workflow_name(run: dict) -> str:
    return run.get("path", "").split("@", 1)[0].rsplit("/", 1)[-1]


def matches(run: dict, args: argparse.Namespace) -> bool:
    return (
        workflow_name(run) in WORKFLOWS
        and (args.workflow is None or workflow_name(run) == args.workflow)
        and (args.sha is None or run.get("head_sha") == args.sha)
        and (args.event is None or run.get("event") == args.event)
        and (args.branch is None or run.get("head_branch") == args.branch)
    )


def latest_run(args: argparse.Namespace, deadline: float) -> dict | None:
    params = {"head_sha": args.sha, "per_page": 100}
    if args.event:
        params["event"] = args.event
    if args.branch:
        params["branch"] = args.branch
    endpoint = f"repos/{REPOSITORY}/actions/workflows/{args.workflow}/runs?{urlencode(params)}"
    runs = paged_items(endpoint, "workflow_runs", RUN_FIELDS, deadline)
    candidates = [run for run in runs if matches(run, args)]
    return max(candidates, key=lambda run: run["id"], default=None)


def public_result(run: dict, jobs: list[dict]) -> dict:
    """Keep only the requested run, job and step fields even for synthetic inputs."""
    output = {key: run.get(key) for key in (
        "id", "url", "head_sha", "head_branch", "event", "status", "conclusion",
    )}
    output["jobs"] = [
        {
            **{key: job.get(key) for key in ("name", "status", "conclusion")},
            "steps": [{key: step.get(key) for key in ("name", "status", "conclusion")}
                      for step in job.get("steps", [])],
        }
        for job in jobs
    ]
    return output


def summary_text(run: dict, result: dict, *, include_steps: bool = False) -> str:
    """Render lifecycle metadata compactly while keeping failed housekeeping steps visible."""
    lines = [
        f"Workflow: {workflow_name(run)} | Run: {result['id']}",
        str(result["url"]),
        f"SHA: {result['head_sha']}",
        f"Ветка: {result['head_branch']} | Событие: {result['event']}",
        f"Запуск: {result['status']} / {result['conclusion']}",
    ]
    for job in result["jobs"]:
        lines.append(f"Job {job['name']}: {job['status']} / {job['conclusion']}")
        if include_steps:
            for step in job["steps"]:
                housekeeping = re.match(r"^(set\s*up|post(?:\s|$)|complete job(?:\s|$))", step["name"], re.I)
                if housekeeping and step["conclusion"] in (None, "success", "skipped", "neutral"):
                    continue
                lines.append(f"  Step {step['name']}: {step['status']} / {step['conclusion']}")
    return "\n".join(lines)


def save_result(destination: Path, result: dict) -> None:
    """Create a new UTF-8 JSON file exclusively; never overwrite existing evidence."""
    if destination.suffix.lower() != ".json":
        raise ValueError("--save допускает только новый файл с расширением .json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def validate_completed(run: dict, jobs: list[dict]) -> None:
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise ValueError(f"Запуск {run['id']} завершился: {run['conclusion']}")
    if not jobs or any(job["status"] != "completed" for job in jobs):
        raise ValueError("API не подтвердил завершение всех jobs")
    if workflow_name(run) == "delivery.yaml":
        deploy = [job for job in jobs if job["name"] == "deploy_dry_run"]
        expected = "success" if run["head_branch"] == "main" else "skipped"
        if len(deploy) != 1 or deploy[0]["conclusion"] != expected:
            raise ValueError(f"Ожидался deploy_dry_run={expected}")
        print(f"Проверено: deploy_dry_run={expected}", file=sys.stderr, flush=True)


def wait_for_run(args: argparse.Namespace) -> tuple[dict, list[dict]]:
    deadline = time.monotonic() + args.timeout
    run_id = args.run_id
    last_progress = None
    last_progress_time = 0.0
    while time.monotonic() < deadline:
        if run_id is None:
            run = latest_run(args, deadline)
            if run is not None:
                run_id = run["id"]
        else:
            run = api(f"repos/{REPOSITORY}/actions/runs/{run_id}", RUN_FIELDS, deadline)
        if run is not None and not matches(run, args):
            raise ValueError("Запуск не соответствует workflow/SHA/event/branch; ожидание остановлено")
        progress = "ожидается появление запуска" if run is None else (
            f"run={run['id']} {run['status']} {run.get('conclusion') or ''}".rstrip()
        )
        now = time.monotonic()
        if progress != last_progress or now - last_progress_time >= 30:
            print(progress, file=sys.stderr, flush=True)
            last_progress, last_progress_time = progress, now
        if run is not None and run["status"] == "completed":
            endpoint = f"repos/{REPOSITORY}/actions/runs/{run_id}/jobs?filter=latest&per_page=100"
            jobs = paged_items(endpoint, "jobs", JOB_FIELDS, deadline)
            return run, jobs
        time.sleep(min(args.poll_interval, max(0.0, deadline - time.monotonic())))
    raise TimeoutError("Истекло время ожидания GitHub Actions")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Только чтение: дождаться GitHub Actions и вывести очищенный JSON",
    )
    parser.add_argument("--repo", choices=(REPOSITORY,), default=REPOSITORY)
    parser.add_argument("--workflow", choices=WORKFLOWS)
    parser.add_argument("--sha", type=sha40)
    parser.add_argument("--event")
    parser.add_argument("--branch")
    parser.add_argument("--run-id", type=positive)
    parser.add_argument("--poll-interval", type=positive, default=15)
    parser.add_argument("--timeout", type=positive, default=1200)
    parser.add_argument("--summary", action="store_true", help="Краткий вывод для снимка вместо JSON")
    parser.add_argument("--steps", action="store_true", help="Добавить существенные steps в --summary")
    parser.add_argument("--save", type=Path, help="Сохранить полный JSON в новый файл .json")
    args = parser.parse_args(argv)
    if args.run_id is None and (args.workflow is None or args.sha is None):
        parser.error("Для поиска обязательны --workflow и --sha; иначе укажите --run-id")
    if args.poll_interval > 30 or args.timeout > 1200:
        parser.error("Максимальный интервал — 30 секунд, общее ожидание — 1200 секунд")
    if args.steps and not args.summary:
        parser.error("--steps используется вместе с --summary")
    if args.save is not None:
        if args.save.suffix.lower() != ".json":
            parser.error("--save допускает только новый файл с расширением .json")
        if args.save.exists() or args.save.is_symlink():
            parser.error("Файл --save уже существует; перезапись запрещена")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not GH.is_file():
            raise FileNotFoundError(f"GitHub CLI не найден: {GH}")
        run, jobs = wait_for_run(args)
        result = public_result(run, jobs)
        output = summary_text(run, result, include_steps=args.steps) if args.summary else (
            json.dumps(result, ensure_ascii=False, indent=2)
        )
        print(output, flush=True)
        if args.save is not None:
            save_result(args.save, result)
            print(f"JSON сохранён: {args.save}", file=sys.stderr, flush=True)
        validate_completed(run, jobs)
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"Проверка GitHub Actions не пройдена: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
