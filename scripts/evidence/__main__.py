"""Command-line entry points for collection, validation, rendering, and browser capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .record import EvidenceRun, load_manifest
from .render import render_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Сбор и оформление фактических результатов проверок")
    subparsers = parser.add_subparsers(dest="action", required=True)
    collect = subparsers.add_parser("collect", help="Выполнить одну команду и сохранить результат")
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--cwd", type=Path, required=True)
    collect.add_argument("--title", required=True)
    collect.add_argument("--label", default="Проверка")
    collect.add_argument("--expected-sha")
    collect.add_argument("--expected-returncode", type=int, default=0)
    collect.add_argument("--timeout", type=float, default=180)
    collect.add_argument("command", nargs=argparse.REMAINDER)
    validate = subparsers.add_parser("validate", help="Проверить манифест и журнал")
    validate.add_argument("manifest", type=Path)
    render = subparsers.add_parser("render", help="Создать HTML из проверенного манифеста")
    render.add_argument("manifest", type=Path)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--title")
    render.add_argument("--description", default="Фактические результаты выполненных команд.")
    render.add_argument("--label", action="append", dest="labels")
    render.add_argument("--tail", type=int)
    capture = subparsers.add_parser("capture", help="Снять реальную HTML-страницу, Swagger или интерфейс")
    capture.add_argument("--url", required=True)
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--cwd", type=Path, required=True)
    capture.add_argument("--profile-root", type=Path, required=True)
    capture.add_argument("--browser", type=Path)
    capture.add_argument("--wait-selector")
    args = parser.parse_args(argv)
    try:
        if args.action == "collect":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("после -- нужна команда argv")
            with EvidenceRun(args.output, cwd=args.cwd, title=args.title, expected_sha=args.expected_sha) as run:
                result = run.command(args.label, command, timeout=args.timeout, expected_returncode=args.expected_returncode)
            print(run.manifest_path)
            return 0 if result["status"] in {"succeeded", "expected_failure"} else 1
        if args.action == "validate":
            data, _ = load_manifest(args.manifest)
            print(f"Манифест проверен; состояние прогона: {data['status']}")
            return 0 if data["status"] in {"succeeded", "expected_failure"} else 1
        if args.action == "render":
            print(render_report(args.manifest, args.output, title=args.title, description=args.description,
                                labels=args.labels, tail=args.tail))
            return 0
        if args.action == "capture":
            from .browser import BrowserSession

            with BrowserSession(profile_root=args.profile_root, browser=args.browser) as browser:
                result = browser.capture(args.url, args.output, cwd=args.cwd, wait_selector=args.wait_selector)
            print(result)
            return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Не удалось завершить действие: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
