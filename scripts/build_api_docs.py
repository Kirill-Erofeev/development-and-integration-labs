import argparse
import json
from pathlib import Path
import shutil
import sys

from scripts.export_openapi import export_openapi


DOCS = Path(__file__).resolve().parents[1] / "docs"
SOURCE_FILES = (
    "index.html",
    "api/index.html",
    "api/swagger-ui.css",
    "api/swagger-ui-bundle.js",
    "api/swagger-ui-bundle.js.LICENSE.txt",
    "api/LICENSE",
    "api/NOTICE",
)


def validate_site(output: Path) -> dict:
    """Reject incomplete artifacts and a contract missing the existing API operations."""
    for relative in (*SOURCE_FILES, "api/openapi.json"):
        path = output / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"В сборке отсутствует непустой файл: {relative}")
    schema = json.loads((output / "api/openapi.json").read_text(encoding="utf-8"))
    if not str(schema.get("openapi", "")).startswith("3."):
        raise ValueError("Ожидалась схема OpenAPI 3")
    paths = schema.get("paths", {})
    for path, method in (("/health", "get"), ("/predict", "post")):
        if method not in paths.get(path, {}):
            raise ValueError(f"В схеме отсутствует операция {method.upper()} {path}")
    return schema


def build_site(output: Path) -> dict:
    """Copy only the public documentation allowlist and generate the current contract."""
    output = output.resolve()
    if output == DOCS or DOCS in output.parents:
        raise ValueError("Каталог сборки должен находиться вне исходников docs")
    for relative in SOURCE_FILES:
        if not (DOCS / relative).is_file():
            raise ValueError(f"Отсутствует исходный файл: {relative}")
    expected = {*SOURCE_FILES, "api/openapi.json"}
    if output.exists():
        # Refuse foreign files instead of recursively deleting an arbitrary CLI path.
        for path in output.rglob("*"):
            if path.is_symlink() or (
                path.is_file() and path.relative_to(output).as_posix() not in expected
            ):
                raise ValueError("Каталог сборки содержит посторонние файлы или ссылки")
    for relative in SOURCE_FILES:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DOCS / relative, target)
    export_openapi(output / "api/openapi.json")
    return validate_site(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать статическую документацию API")
    parser.add_argument("--output", type=Path, default=Path("site"))
    args = parser.parse_args(argv)
    try:
        schema = build_site(args.output)
    except (OSError, ValueError) as exc:
        print(f"Не удалось собрать документацию: {exc}", file=sys.stderr)
        return 1
    print(f"Документация: {args.output}; OpenAPI {schema['openapi']}; маршрутов: {len(schema['paths'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
