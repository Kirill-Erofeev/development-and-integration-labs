"""Check failure preservation, traceable excerpts, and honest Git provenance."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.evidence import EvidenceRun, load_manifest, render_report
from scripts.evidence import record as evidence_record
from scripts.evidence.__main__ import main


@pytest.fixture
def provenance(monkeypatch, tmp_path):
    value = {"head_sha": "a" * 40, "repository": str(tmp_path),
             "status_porcelain": "", "tracked_clean": True}
    monkeypatch.setattr(evidence_record, "git_provenance", lambda cwd: copy.deepcopy(value))
    return value


def capture(tmp_path, provenance, code, *, expected=0, timeout=20):
    with EvidenceRun(tmp_path / "capture", cwd=tmp_path, title="Синтетическая проверка") as run:
        run.command("Команда", [sys.executable, "-B", "-X", "utf8", "-c", code],
                    expected_returncode=expected, timeout=timeout)
    return run.manifest_path


def test_real_failure_survives_roundtrip_and_render(tmp_path, provenance):
    manifest = capture(tmp_path, provenance,
                       "import sys; print('<script>alert(1)</script>'); print('ошибка', file=sys.stderr); sys.exit(7)")
    data, outputs = load_manifest(manifest)
    assert data["status"] == "failed"
    assert data["commands"][0]["returncode"] == 7
    assert outputs["Команда"]["stderr"].strip() == "ошибка"
    report = render_report(manifest, tmp_path / "report.html", title="<img src=x>").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
    assert "&lt;img src=x&gt;" in report
    assert "Неуспешные команды: Команда" in report
    assert "Код завершения: 7; ожидаемый: 0" in report
    assert main(["validate", str(manifest)]) == 1


def test_expected_error_is_distinguished_from_success(tmp_path, provenance):
    manifest = capture(tmp_path, provenance, "raise SystemExit(3)", expected=3)
    data, _ = load_manifest(manifest)
    assert data["status"] == "expected_failure"
    assert data["commands"][0]["status"] == "expected_failure"


def test_timeout_preserves_partial_output_and_does_not_pass(tmp_path, provenance):
    manifest = capture(tmp_path, provenance, "import time; print('started', flush=True); time.sleep(10)", timeout=0.3)
    data, outputs = load_manifest(manifest)
    assert data["status"] == "failed"
    assert data["commands"][0]["status"] == "timed_out"
    assert outputs["Команда"]["stdout"].strip() == "started"


def test_launch_error_is_saved(tmp_path, provenance):
    with EvidenceRun(tmp_path / "capture", cwd=tmp_path, title="Ошибка запуска") as run:
        run.command("Нет программы", [str(tmp_path / "missing-executable")])
    data, _ = load_manifest(run.manifest_path)
    assert data["status"] == "failed"
    assert data["commands"][0]["status"] == "launch_failed"
    assert data["commands"][0]["returncode"] is None


def test_modified_output_is_rejected_before_html_is_created(tmp_path, provenance):
    manifest = capture(tmp_path, provenance, "print('original')")
    log = manifest.with_name("commands.log")
    log.write_bytes(log.read_bytes().replace(b"original", b"modified"))
    destination = tmp_path / "report.html"
    with pytest.raises(ValueError, match="сумма"):
        render_report(manifest, destination)
    assert not destination.exists()


@pytest.mark.parametrize("mutation", ["status", "verified_sha", "range", "time", "tracked_clean"])
def test_inconsistent_manifest_cannot_claim_valid_evidence(tmp_path, provenance, mutation):
    manifest = capture(tmp_path, provenance, "raise SystemExit(1)")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    record = data["commands"][0]
    if mutation == "status":
        record["status"] = "succeeded"
        data["status"] = "succeeded"
    elif mutation == "verified_sha":
        record["verified_sha"] = "b" * 40
    elif mutation == "range":
        record["stdout"]["offset"] = -1
    elif mutation == "tracked_clean":
        record["provenance_before"]["tracked_clean"] = False
    else:
        record["finished_at"] = "2000-01-01T00:00:00+00:00"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(manifest)


def test_dirty_tracked_tree_never_receives_verified_sha(tmp_path, provenance):
    provenance.update(status_porcelain=" M app/example.py\0", tracked_clean=False)
    manifest = capture(tmp_path, provenance, "print('result')")
    data, _ = load_manifest(manifest)
    assert data["commands"][0]["verified_sha"] is None
    html = render_report(manifest, tmp_path / "dirty.html").read_text(encoding="utf-8")
    assert "Проверенный SHA не присваивается" in html


def test_provenance_reads_only_tracked_status_metadata(monkeypatch, tmp_path):
    commands = []

    def git(argv, **kwargs):
        commands.append(argv)
        output = ("a" * 40 + "\n") if "HEAD" in argv else str(tmp_path) + "\n" if "--show-toplevel" in argv else ""
        return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")

    monkeypatch.setattr(evidence_record.subprocess, "run", git)
    data = evidence_record.git_provenance(tmp_path)
    assert data["tracked_clean"] is True
    assert any("--untracked-files=no" in command for command in commands)
    assert all("diff" not in command and "show" not in command for command in commands)


def test_excerpt_discloses_omissions_and_hidden_failure(tmp_path, provenance):
    with EvidenceRun(tmp_path / "capture", cwd=tmp_path, title="Выборка") as run:
        run.command("Плохая команда", [sys.executable, "-c", "raise SystemExit(1)"])
        run.command("Строки", [sys.executable, "-c", "print('one'); print('two'); print('three')"])
    html = render_report(run.manifest_path, tmp_path / "excerpt.html", labels=["Строки"], tail=2).read_text(encoding="utf-8")
    assert "Показаны последние 2 из 3 строк" in html
    assert "Выбрано команд: 1 из 2" in html
    assert "Неуспешные команды: Плохая команда" in html
    assert "two\nthree" in html.replace("\r\n", "\n")


def test_wrong_sha_does_not_start_capture(tmp_path, provenance):
    destination = tmp_path / "capture"
    with pytest.raises(ValueError, match="SHA"):
        EvidenceRun(destination, cwd=tmp_path, title="SHA", expected_sha="b" * 40)
    assert not destination.exists()


def test_imports_do_not_require_browser_dependency_or_create_artifacts():
    code = """
import pathlib
import subprocess
import sys
sys.modules['websocket'] = None
def forbidden(*args, **kwargs):
    raise AssertionError('import side effect')
pathlib.Path.mkdir = forbidden
pathlib.Path.write_text = forbidden
subprocess.Popen = forbidden
import scripts.evidence
import scripts.evidence.browser
import scripts.evidence.__main__
"""
    completed = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=20,
                               **evidence_record.hidden_options())
    assert completed.returncode == 0, completed.stderr
