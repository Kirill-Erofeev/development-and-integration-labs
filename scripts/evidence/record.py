"""Persist real command output with timestamps, Git provenance, and checked offsets."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time
from typing import Any, Sequence


SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SCHEMA_VERSION = 1


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def safe_path(path: Path) -> Path:
    """Reject links and Windows reparse points before following an explicit path."""
    absolute = Path(os.path.abspath(path))
    for item in (*reversed(absolute.parents), absolute):
        try:
            metadata = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Ссылки и reparse points не допускаются: {item}")
    return absolute


def hidden_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": startup}


def git_provenance(cwd: Path) -> dict[str, Any]:
    """Read commit identity and path/status metadata only, never file contents."""
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.quotepath=false", *arguments], cwd=cwd,
            capture_output=True, encoding="utf-8", errors="strict", timeout=30,
            check=False, **hidden_options(),
        )
        if completed.returncode:
            raise ValueError("Не удалось подтвердить Git-версию рабочего каталога")
        return completed.stdout

    sha = git("rev-parse", "--verify", "HEAD").strip()
    if not SHA.fullmatch(sha):
        raise ValueError("Git вернул некорректный SHA")
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=no")
    return {
        "head_sha": sha,
        "repository": str(safe_path(Path(git("rev-parse", "--show-toplevel").strip()))),
        "status_porcelain": status,
        "tracked_clean": not status,
    }


def _stop_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15, check=False, **hidden_options())
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()


def verified_sha(before: dict[str, Any], after: dict[str, Any]) -> str | None:
    if before == after and not before["status_porcelain"]:
        return before["head_sha"]
    return None


def command_status(record: dict[str, Any]) -> str:
    if record["launch_error"] is not None:
        return "launch_failed"
    if record["timed_out"]:
        return "timed_out"
    if record["returncode"] != record["expected_returncode"]:
        return "failed"
    return "succeeded" if record["returncode"] == 0 else "expected_failure"


def run_status(records: list[dict[str, Any]], finalized: bool) -> str:
    if not finalized:
        return "incomplete"
    if not records or any(record["status"] not in {"succeeded", "expected_failure"} for record in records):
        return "failed"
    return "expected_failure" if any(record["status"] == "expected_failure" for record in records) else "succeeded"


class EvidenceRun:
    """Execute explicit argv lists; checkpoint every result, including command failures.

    Modified tracked files are recorded but never identified as a verified commit.
    The caller remains responsible for selecting authorized commands and inputs.
    """

    def __init__(self, directory: Path, *, cwd: Path, title: str, expected_sha: str | None = None):
        self.directory = safe_path(directory)
        self.cwd = safe_path(cwd)
        provenance = git_provenance(self.cwd)
        if expected_sha is not None and provenance["head_sha"] != expected_sha:
            raise ValueError("HEAD не совпадает с ожидаемым полным SHA")
        self.directory.mkdir(parents=True, exist_ok=False)
        self.manifest_path = self.directory / "manifest.json"
        self.log_path = self.directory / "commands.log"
        self.log_path.touch(exist_ok=False)
        self.manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "title": title, "cwd": str(self.cwd),
            "started_at": now(), "finished_at": None, "status": "incomplete",
            "log_file": "commands.log", "commands": [],
        }
        self._save()

    def _save(self) -> None:
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.manifest_path)

    def command(
        self, label: str, argv: Sequence[str], *, timeout: float = 180,
        expected_returncode: int = 0,
    ) -> dict[str, Any]:
        if self.manifest["finished_at"] is not None:
            raise ValueError("Завершённый прогон нельзя продолжать")
        if not label or any(item["label"] == label for item in self.manifest["commands"]):
            raise ValueError("Нужно непустое уникальное имя команды")
        if isinstance(argv, (str, bytes)) or not argv or any(not isinstance(item, str) for item in argv):
            raise ValueError("Команда должна быть непустым списком строк argv")
        if not math.isfinite(timeout) or timeout <= 0 or type(expected_returncode) is not int:
            raise ValueError("Некорректный timeout или ожидаемый код завершения")
        before = git_provenance(self.cwd)
        record: dict[str, Any] = {
            "sequence": len(self.manifest["commands"]) + 1, "label": label,
            "argv": list(argv), "cwd": str(self.cwd), "started_at": now(),
            "expected_returncode": expected_returncode, "timed_out": False,
            "launch_error": None, "returncode": None, "provenance_before": before,
        }
        started = time.monotonic()
        stdout = stderr = b""
        try:
            process = subprocess.Popen(
                list(argv), cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=os.name != "nt", **hidden_options(),
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                _stop_process_tree(process)
                stdout, stderr = process.communicate()
            except BaseException:
                _stop_process_tree(process)
                process.communicate()
                raise
            record["returncode"] = process.returncode
        except OSError as exc:
            record["launch_error"] = f"{type(exc).__name__}: {exc}"
        record["finished_at"] = now()
        record["duration_seconds"] = round(time.monotonic() - started, 6)
        record["provenance_after"] = git_provenance(self.cwd)
        record["verified_sha"] = verified_sha(before, record["provenance_after"])
        record["status"] = command_status(record)
        with self.log_path.open("ab") as stream:
            stream.write((f"\n=== {record['sequence']}: {label} ===\n" + subprocess.list2cmdline(list(argv)) + "\n").encode("utf-8"))
            for name, raw in (("stdout", stdout), ("stderr", stderr)):
                stream.write(f"--- {name} ---\n".encode("utf-8"))
                text = raw.decode("utf-8", errors="replace")
                content = text.encode("utf-8")
                record[name] = {
                    "offset": stream.tell(), "length": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "utf8_lossless": content == raw,
                }
                stream.write(content)
                stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.manifest["commands"].append(record)
        self._save()
        return record

    def finish(self) -> Path:
        if self.manifest["finished_at"] is None:
            self.manifest["finished_at"] = now()
            self.manifest["status"] = run_status(self.manifest["commands"], True)
            self._save()
        return self.manifest_path

    def __enter__(self) -> EvidenceRun:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc_type is None:
            self.finish()


def _instant(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Отсутствует время захвата")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Время захвата должно содержать часовой пояс")
    return result


def load_manifest(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """Validate one explicit manifest and its adjacent log before rendering anything."""
    source = safe_path(path)
    if source.suffix.lower() != ".json":
        raise ValueError("Манифест должен иметь расширение .json")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or data.get("log_file") != "commands.log":
        raise ValueError("Неизвестная схема или путь журнала")
    if not isinstance(data.get("title"), str) or not isinstance(data.get("cwd"), str) or not Path(data["cwd"]).is_absolute():
        raise ValueError("Отсутствует заголовок или абсолютный cwd")
    start, end = _instant(data.get("started_at")), _instant(data.get("finished_at"))
    if end < start:
        raise ValueError("Противоречивое время прогона")
    records = data.get("commands")
    if not isinstance(records, list) or not records:
        raise ValueError("Нет результатов команд")
    log_path = safe_path(source.parent / "commands.log")
    log_size = log_path.stat().st_size
    outputs: dict[str, dict[str, str]] = {}
    last_end = 0
    with log_path.open("rb") as stream:
        for index, record in enumerate(records, 1):
            if not isinstance(record, dict):
                raise ValueError("Некорректная запись команды")
            label = record.get("label")
            if not isinstance(label, str) or not label or label in outputs or record.get("sequence") != index:
                raise ValueError("Нарушен порядок или уникальность команд")
            argv = record.get("argv")
            if not isinstance(argv, list) or not argv or any(not isinstance(item, str) for item in argv):
                raise ValueError("Некорректная команда argv")
            if record.get("cwd") != data["cwd"]:
                raise ValueError("Рабочий каталог команды не совпадает с манифестом")
            command_start, command_end = _instant(record.get("started_at")), _instant(record.get("finished_at"))
            if not start <= command_start <= command_end <= end:
                raise ValueError("Время команды выходит за границы прогона")
            duration = record.get("duration_seconds")
            if type(duration) not in {int, float} or not math.isfinite(duration) or duration < 0:
                raise ValueError("Некорректная длительность")
            if type(record.get("expected_returncode")) is not int or type(record.get("timed_out")) is not bool:
                raise ValueError("Нет ожидаемого кода или признака timeout")
            launch_error = record.get("launch_error")
            if launch_error is not None and (not isinstance(launch_error, str) or not launch_error):
                raise ValueError("Некорректная ошибка запуска")
            if (launch_error is None and type(record.get("returncode")) is not int) or (launch_error is not None and record.get("returncode") is not None):
                raise ValueError("Некорректный код завершения")
            if record.get("status") != command_status(record):
                raise ValueError("Статус противоречит фактическому результату команды")
            for key in ("provenance_before", "provenance_after"):
                provenance = record.get(key)
                if not isinstance(provenance, dict) or not isinstance(provenance.get("head_sha"), str) or not SHA.fullmatch(provenance["head_sha"]):
                    raise ValueError("Не подтверждён полный Git SHA")
                if not isinstance(provenance.get("status_porcelain"), str) or not isinstance(provenance.get("repository"), str):
                    raise ValueError("Нет состояния рабочего дерева Git")
                if type(provenance.get("tracked_clean")) is not bool or provenance["tracked_clean"] != (not provenance["status_porcelain"]):
                    raise ValueError("tracked_clean противоречит состоянию Git")
            if record.get("verified_sha") != verified_sha(record["provenance_before"], record["provenance_after"]):
                raise ValueError("verified_sha не соответствует состоянию дерева")
            outputs[label] = {}
            for name in ("stdout", "stderr"):
                location = record.get(name)
                if not isinstance(location, dict):
                    raise ValueError("Нет адреса захваченного вывода")
                offset, length = location.get("offset"), location.get("length")
                if type(offset) is not int or type(length) is not int or offset < last_end or length < 0 or offset + length > log_size:
                    raise ValueError("Некорректный диапазон журнала")
                if type(location.get("utf8_lossless")) is not bool:
                    raise ValueError("Не указано качество декодирования UTF-8")
                stream.seek(offset)
                content = stream.read(length)
                if hashlib.sha256(content).hexdigest() != location.get("sha256"):
                    raise ValueError("Контрольная сумма вывода не совпадает с журналом")
                outputs[label][name] = content.decode("utf-8", errors="strict")
                last_end = offset + length
    if data.get("status") != run_status(records, True):
        raise ValueError("Итоговый статус противоречит результатам команд")
    return data, outputs
