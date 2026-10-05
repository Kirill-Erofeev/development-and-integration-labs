import argparse
import json
from pathlib import Path
import sys


def export_openapi(output: Path) -> dict:
    """Export the application contract without entering its lifespan or using HTTP."""
    from app.api import app

    schema = app.openapi()
    encoded = json.dumps(schema, ensure_ascii=False, indent=2, allow_nan=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded + "\n", encoding="utf-8")
    return schema


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Экспортировать OpenAPI без запуска сервера")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        schema = export_openapi(args.output)
    except (OSError, ValueError) as exc:
        print(f"Не удалось экспортировать OpenAPI: {exc}", file=sys.stderr)
        return 1
    print(f"OpenAPI {schema['openapi']}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
