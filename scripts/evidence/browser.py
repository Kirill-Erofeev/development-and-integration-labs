"""Capture actual browser pages through a hidden, isolated Chrome CDP session."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen, url2pathname
import uuid

from .record import git_provenance, hidden_options, now, safe_path, verified_sha


def find_chrome() -> Path:
    candidates = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                  Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")]
    if os.name != "nt":
        candidates = [Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium"), Path("/usr/bin/chromium-browser")]
    for candidate in candidates:
        if candidate.is_file():
            return safe_path(candidate)
    raise FileNotFoundError("Chrome не найден; укажите --browser")


class BrowserSession:
    """Start lazily and leave the explicitly located profile available for diagnostics."""

    width = 1440
    height = 1000

    def __init__(self, *, profile_root: Path, browser: Path | None = None):
        self.profile_root = safe_path(profile_root)
        self.browser = browser
        self.process: subprocess.Popen | None = None
        self.connection: Any = None
        self.sequence = 0

    def start(self) -> BrowserSession:
        if self.process is not None:
            raise RuntimeError("Сеанс Chrome уже запущен")
        try:
            import websocket
        except ImportError as exc:
            raise RuntimeError("Для снимков установите scripts/evidence/requirements.txt") from exc
        browser = find_chrome() if self.browser is None else safe_path(self.browser)
        if not browser.is_file():
            raise FileNotFoundError(f"Chrome не найден: {browser}")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.profile_root.mkdir(parents=True, exist_ok=True)
        self.profile = self.profile_root / ("chrome-" + uuid.uuid4().hex[:12])
        self.profile.mkdir(exist_ok=False)
        argv = [
            str(browser), "--headless=new", f"--user-data-dir={self.profile}",
            f"--remote-debugging-port={port}", "--remote-debugging-address=127.0.0.1",
            "--window-size=1440,1000", "--force-device-scale-factor=1", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking",
            "--disable-component-update", "--disable-sync", "--disable-extensions",
            "--disable-default-apps", "--disable-crash-reporter", "--disable-breakpad", "about:blank",
        ]
        self.stderr_path = self.profile / "browser-stderr.log"
        with self.stderr_path.open("xb") as stderr_stream:
            self.process = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=stderr_stream, **hidden_options())
        try:
            deadline = time.monotonic() + 30
            while True:
                if self.process.poll() is not None:
                    raise RuntimeError(f"Chrome завершился с кодом {self.process.returncode}; журнал: {self.stderr_path}")
                try:
                    with urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as response:
                        targets = json.load(response)
                    target = next(item for item in targets if item["type"] == "page")
                    break
                except (URLError, OSError, StopIteration):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Chrome не открыл CDP за 30 секунд")
                    time.sleep(0.1)
            self.connection = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
            self.call("Page.enable")
            self.call("Runtime.enable")
            self.call("Emulation.setDeviceMetricsOverride", {
                "width": self.width, "height": self.height, "deviceScaleFactor": 1, "mobile": False,
            })
            return self
        except BaseException:
            self.close()
            raise

    def call(self, method: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.connection is None:
            raise RuntimeError("Сеанс Chrome не запущен")
        self.sequence += 1
        identifier = self.sequence
        self.connection.send(json.dumps({"id": identifier, "method": method, "params": parameters or {}}))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            response = json.loads(self.connection.recv())
            if response.get("id") == identifier:
                if "error" in response:
                    raise RuntimeError(f"CDP {method}: {response['error']}")
                return response.get("result", {})
        raise TimeoutError(f"CDP не ответил: {method}")

    def evaluate(self, expression: str) -> Any:
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in result:
            raise RuntimeError("Ошибка выполнения JavaScript в странице")
        return result.get("result", {}).get("value")

    def navigate(self, url: str, *, timeout: float = 45) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https", "file"} or parsed.username or parsed.password:
            raise ValueError("Нужен URL http/https/file без учётных данных")
        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                raise ValueError("Удалённый file URL не поддерживается")
            path = safe_path(Path(url2pathname(parsed.path)))
            if path.suffix.lower() not in {".html", ".htm"}:
                raise ValueError("Локальная страница должна быть HTML")
        result = self.call("Page.navigate", {"url": url})
        if result.get("errorText"):
            raise RuntimeError("Ошибка навигации: " + result["errorText"])
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.call("Page.getFrameTree")["frameTree"]["frame"]
            loader_ready = not result.get("loaderId") or frame.get("loaderId") == result["loaderId"]
            ready = self.evaluate("document.readyState === 'complete' && location.href !== 'about:blank'")
            if loader_ready and ready:
                return
            time.sleep(0.1)
        raise TimeoutError("Страница не загрузилась за отведённое время")

    def wait_for_selector(self, selector: str, *, timeout: float = 45) -> None:
        deadline = time.monotonic() + timeout
        expression = "Boolean(document.querySelector(" + json.dumps(selector) + "))"
        while time.monotonic() < deadline:
            if self.evaluate(expression):
                return
            time.sleep(0.1)
        raise TimeoutError(f"Элемент страницы не появился: {selector}")

    def screenshot(self, destination: Path) -> tuple[Path, int]:
        """Capture the actual full page at 1440 CSS pixels without resizing its bitmap."""
        target = safe_path(destination)
        if target.suffix.lower() != ".png":
            raise ValueError("Снимок должен иметь расширение .png")
        if target.exists():
            raise FileExistsError(f"Снимок уже существует: {target}")
        self.evaluate("document.fonts.ready.then(() => true)")
        self.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        metrics = self.call("Page.getLayoutMetrics")
        content = metrics.get("cssContentSize") or metrics["contentSize"]
        if math.ceil(content["width"]) > self.width:
            raise ValueError("Страница шире 1440 px: исправьте переполнение перед захватом")
        height = max(self.height, math.ceil(content["height"]))
        if height > 32768:
            raise ValueError("Страница выше 32768 px; разделите отчёт на несколько снимков")
        result = self.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": True,
            "clip": {"x": 0, "y": 0, "width": self.width, "height": height, "scale": 1},
        })
        bitmap = base64.b64decode(result["data"], validate=True)
        if not bitmap.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Chrome не вернул PNG")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(bitmap)
        return target, height

    def capture(self, url: str, destination: Path, *, cwd: Path, wait_selector: str | None = None) -> Path:
        """Navigate to an explicit URL and capture it with provenance metadata."""
        target = safe_path(destination)
        sidecar = target.with_suffix(".png.json")
        if target.exists() or sidecar.exists():
            raise FileExistsError("PNG или его манифест уже существует")
        self.navigate(url)
        return self.capture_current(target, cwd=cwd, wait_selector=wait_selector, requested_url=url)

    def capture_current(
        self, destination: Path, *, cwd: Path, wait_selector: str | None = None,
        requested_url: str | None = None,
    ) -> Path:
        """Preserve an interacted page state and capture its actual URL with a sidecar."""
        target = safe_path(destination)
        sidecar = target.with_suffix(".png.json")
        if target.exists() or sidecar.exists():
            raise FileExistsError("PNG или его манифест уже существует")
        before = git_provenance(safe_path(cwd))
        started_at = now()
        if wait_selector:
            self.wait_for_selector(wait_selector)
        final_url = self.evaluate("location.href")
        page_title = self.evaluate("document.title")
        target, height = self.screenshot(target)
        after = git_provenance(safe_path(cwd))
        metadata = {
            "schema_version": 1, "kind": "browser_capture", "url": requested_url or final_url, "final_url": final_url,
            "page_title": page_title, "started_at": started_at, "finished_at": now(),
            "width": self.width, "height": height, "device_scale_factor": 1,
            "wait_selector": wait_selector, "png_file": target.name,
            "png_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "provenance_before": before, "provenance_after": after,
            "verified_worktree_sha": verified_sha(before, after),
            "source_note": "SHA характеризует рабочее дерево; соответствие запущенного сервера этому дереву проверяется отдельно.",
        }
        with sidecar.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return target

    def close(self) -> None:
        if self.connection is not None:
            try:
                self.call("Browser.close")
            except Exception:
                pass
            self.connection.close()
            self.connection = None
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)

    def __enter__(self) -> BrowserSession:
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
