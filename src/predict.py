import argparse
import csv
import json
import math
import pickle
from pathlib import Path
from typing import TextIO

if __package__:
    from .common import DEFAULT_INPUT_PATH, DEFAULT_MODEL_PATH, FEATURE_COLUMNS
    from .model_service import ModelService
else:
    from common import DEFAULT_INPUT_PATH, DEFAULT_MODEL_PATH, FEATURE_COLUMNS
    from model_service import ModelService


def read_features(source: TextIO) -> list[list[float]]:
    """Read finite numeric features, allowing the declared columns in any order."""
    reader = csv.DictReader(source, strict=True)
    headers = reader.fieldnames
    if headers is None or len(headers) != len(FEATURE_COLUMNS) or set(headers) != set(FEATURE_COLUMNS):
        raise ValueError("CSV должен содержать ровно четыре колонки: " + ", ".join(FEATURE_COLUMNS))

    features = []
    for row in reader:
        if None in row or any(row[column] is None for column in FEATURE_COLUMNS):
            raise ValueError(f"Строка {reader.line_num}: число значений не соответствует заголовку")
        try:
            values = [float(row[column]) for column in FEATURE_COLUMNS]
        except ValueError as exc:
            raise ValueError(f"Строка {reader.line_num}: признаки должны быть числами") from exc
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"Строка {reader.line_num}: признаки должны быть конечными числами")
        features.append(values)
    if not features:
        raise ValueError("CSV не содержит объектов для предсказания")
    return features


def predict(
    input_path: Path = DEFAULT_INPUT_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> list[dict[str, int | str]]:
    """Load a trusted training artifact and predict without fitting a model."""
    service = ModelService.load(model_path)
    with Path(input_path).open(encoding="utf-8-sig", newline="") as source:
        features = read_features(source)
    return service.predict(features)


def format_predictions(predictions: list[dict[str, int | str]], output_format: str = "json") -> str:
    """Render predictions without changing their order or the inference result."""
    if output_format == "json":
        return json.dumps(predictions, ensure_ascii=False)
    if output_format == "text":
        return "\n".join(
            f"predicted_class={item['predicted_class']} predicted_name={item['predicted_name']}"
            for item in predictions
        )
    raise ValueError(f"Неизвестный формат вывода: {output_format}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Предсказать классы Iris по сохранённой модели")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH, help="Путь к модели")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="CSV с четырьмя признаками")
    parser.add_argument("--output-format", choices=("json", "text"), default="json", help="Формат вывода предсказаний")
    args = parser.parse_args()
    try:
        predictions = predict(args.input, args.model_path)
    except (OSError, ValueError, TypeError, EOFError, pickle.UnpicklingError, csv.Error) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")
    print(format_predictions(predictions, args.output_format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
