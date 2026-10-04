"""Render checked captures in the original course evidence card style."""

from __future__ import annotations

import html
from pathlib import Path
import subprocess
from typing import Sequence

from .record import load_manifest, now, safe_path


CARD_CSS = """*{box-sizing:border-box}body{margin:0;background:#eef2f6;color:#152536;font-family:Segoe UI,Arial,sans-serif}
main{max-width:1360px;margin:36px auto;padding:36px 42px;background:#fff;border-top:8px solid #245f90;border-radius:10px}
.label{font-size:18px;font-weight:600;letter-spacing:1px;color:#245f90}h1{font-size:34px;margin:14px 0 16px}
.description{font-size:21px;line-height:1.5;margin-bottom:20px}.metadata{font-size:17px;color:#45576a;line-height:1.55}
h2{font-size:22px;margin:25px 0 12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;padding:20px 22px;
font:19px/1.55 Consolas,monospace;background:#f3f6f9;border:1px solid #cbd5df;border-radius:6px}
footer{font-size:17px;margin-top:26px;line-height:1.5;color:#45576a}"""

STATUS_TEXT = {
    "succeeded": "Код завершения соответствует ожидаемому: 0",
    "expected_failure": "Получен ожидаемый ненулевой код завершения",
    "failed": "Проверка не завершилась ожидаемым результатом",
    "timed_out": "Превышено время ожидания; процесс остановлен",
    "launch_failed": "Процесс не удалось запустить",
}


def render_report(
    manifest: Path, destination: Path, *, title: str | None = None,
    description: str = "Фактические результаты выполненных команд.",
    labels: Sequence[str] | None = None, tail: int | None = None,
) -> Path:
    """Escape all captured values and disclose every excerpt and failed result."""
    data, outputs = load_manifest(manifest)
    if tail is not None and (type(tail) is not int or tail <= 0):
        raise ValueError("tail должен быть положительным целым числом")
    selected = [record["label"] for record in data["commands"]] if labels is None else list(labels)
    if not selected or len(selected) != len(set(selected)) or any(label not in outputs for label in selected):
        raise ValueError("Нужен непустой список уникальных существующих команд")
    records = {record["label"]: record for record in data["commands"]}
    sections: list[str] = []

    def section(label: str, text: str) -> None:
        sections.append(f"<section><h2>{html.escape(label)}</h2><pre>{html.escape(text)}</pre></section>")

    for label in selected:
        record = records[label]
        before, after = record["provenance_before"], record["provenance_after"]
        provenance = (
            f"Проверенный SHA отслеживаемого дерева Git: {record['verified_sha']}"
            if record["verified_sha"] else
            f"HEAD до команды: {before['head_sha']}\nHEAD после команды: {after['head_sha']}\n"
            "Проверенный SHA не присваивается: отслеживаемые файлы изменены или HEAD сменился."
        )
        details = (
            f"> {subprocess.list2cmdline(record['argv'])}\n"
            f"Код завершения: {record['returncode']}; ожидаемый: {record['expected_returncode']}; "
            f"длительность: {record['duration_seconds']} с"
        )
        if not record['verified_sha']:
            details += "\n" + provenance
        if record["launch_error"]:
            details += "\nОшибка запуска: " + record["launch_error"]
        combined = details
        for name in ("stdout", "stderr"):
            output = outputs[label][name]
            if not output:
                continue
            if not record[name]["utf8_lossless"]:
                section(label + " · кодировка " + name, "Некорректные последовательности UTF-8 заменены при сохранении вывода.")
            lines = output.splitlines(keepends=True)
            if tail is not None and len(lines) > tail:
                output = f"Показаны последние {tail} из {len(lines)} строк; полный вывод — commands.log.\n\n" + "".join(lines[-tail:])
            combined += "\n\n" + name + ":\n" + output
        section(label, combined)

    all_failures = [record["label"] for record in data["commands"] if record["status"] not in {"succeeded", "expected_failure"}]
    overview = "Статус всего прогона: " + STATUS_TEXT[data["status"]]
    if all_failures:
        overview += ". Неуспешные команды: " + ", ".join(all_failures)
    if len(selected) != len(data["commands"]):
        overview += f". Выбрано команд: {len(selected)} из {len(data['commands'])}"
    page_title = data["title"] if title is None else title
    verified = sorted({item['verified_sha'] for item in data['commands'] if item['verified_sha']})
    metadata = (
        f"Проверка: {html.escape(data['started_at'])} — {html.escape(data['finished_at'])}<br>"
        f"Git: {html.escape(', '.join(verified)) if verified else 'см. состояние команд'}<br>"
        + html.escape(overview)
    )
    document = (
        '<!doctype html>\n<html lang="ru"><head><meta charset="utf-8">'
        f"<title>{html.escape(page_title)}</title><style>{CARD_CSS}</style></head><body><main>"
        '<div class="label">РАЗРАБОТКА И ИНТЕГРАЦИЯ · ФАКТИЧЕСКАЯ ПРОВЕРКА</div>'
        f"<h1>{html.escape(page_title)}</h1><div class=\"description\">{html.escape(description)}</div>"
        f'<div class="metadata">{metadata}</div>' + "".join(sections)
        + f"<footer>Рабочий каталог: {html.escape(data['cwd'])}<br>"
        + f"Источник: {html.escape(str(safe_path(manifest)))} и commands.log.<br>"
        + f"Сформировано: {html.escape(now())}. Снимок HTML-карточки с фактическим выводом команд."
        "</footer></main></body></html>"
    )
    target = safe_path(destination)
    if target.suffix.lower() != ".html":
        raise ValueError("HTML должен иметь расширение .html")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(document)
    return target
