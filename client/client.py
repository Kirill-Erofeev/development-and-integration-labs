import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import UUID

import requests


DEFAULT_API_URL = "http://api:8000"
DEFAULT_RESULT_PATH = "/results/prediction.json"
CLASS_NAMES = ("setosa", "versicolor", "virginica")
FEATURES = {
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2,
}


def validate_prediction(data: object) -> dict[str, int | str]:
    """Accept only the API response schema with a consistent Iris class name."""
    if not isinstance(data, dict) or set(data) != {"class_id", "class_name", "request_id"}:
        raise ValueError("Ответ API должен содержать только class_id, class_name и request_id")
    prediction = data["class_id"]
    if type(prediction) is not int or not 0 <= prediction < len(CLASS_NAMES):
        raise ValueError("Поле class_id должно быть целым числом от 0 до 2")
    class_name = data["class_name"]
    if not isinstance(class_name, str) or class_name != CLASS_NAMES[prediction]:
        raise ValueError("Поле class_name не соответствует значению class_id")
    request_id = data["request_id"]
    if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
        raise ValueError("Поле request_id должно содержать канонический UUID")
    return {"class_id": prediction, "class_name": class_name, "request_id": request_id}


def run_prediction(api_url: str, result_path: Path) -> dict[str, int | str]:
    """Make one bounded request and atomically save a validated response."""
    endpoint = api_url.rstrip("/") + "/predict"
    with requests.post(
        endpoint, json=FEATURES, timeout=10, allow_redirects=False
    ) as response:
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise requests.HTTPError(
                f"API вернул перенаправление HTTP {response.status_code}",
                response=response,
            )
        prediction = validate_prediction(response.json())

    result_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        # Replacing a complete file keeps an earlier result intact if writing fails.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=result_path.parent,
            prefix=f".{result_path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(prediction, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        temporary_path.replace(result_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return prediction


def main() -> int:
    api_url = os.environ.get("API_URL", DEFAULT_API_URL)
    result_path = Path(os.environ.get("RESULT_PATH", DEFAULT_RESULT_PATH))
    print(f"API_URL: {api_url}")
    print(f"RESULT_PATH: {result_path}")
    try:
        prediction = run_prediction(api_url, result_path)
    except (requests.RequestException, ValueError, OSError) as exc:
        print(f"Не удалось получить или сохранить предсказание: {exc}", file=sys.stderr)
        return 1
    print(
        f"Предсказание сохранено в {result_path}: "
        f"класс {prediction['class_id']} ({prediction['class_name']}), "
        f"request ID {prediction['request_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
