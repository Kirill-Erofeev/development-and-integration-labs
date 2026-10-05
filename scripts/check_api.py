import argparse
import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen


def check_api(base_url: str) -> dict:
    """Check readiness and a synthetic prediction against a running API."""
    base_url = base_url.rstrip("/")
    with urlopen(f"{base_url}/health", timeout=10) as response:
        health = json.load(response)
    if not isinstance(health, dict) or health.get("status") != "ok" or health.get("model_ready") is not True:
        raise ValueError("API не подтвердил готовность модели")

    payload = {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}
    request = Request(
        f"{base_url}/predict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        prediction = json.load(response)
    if (
        not isinstance(prediction, dict)
        or type(prediction.get("prediction")) is not int
        or prediction != {"prediction": 0, "class_name": "setosa"}
    ):
        raise ValueError("Предсказание не соответствует контрольному примеру Iris")
    return prediction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить готовность и предсказание API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args(argv)
    try:
        prediction = check_api(args.base_url)
    except (URLError, OSError, ValueError) as exc:
        print(f"Проверка API {args.base_url} не пройдена: {exc}", file=sys.stderr)
        return 1
    print(f"API {args.base_url} готов; предсказание: {json.dumps(prediction, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
