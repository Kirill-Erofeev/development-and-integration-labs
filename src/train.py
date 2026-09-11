import argparse
from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

if __package__:
    from .common import DEFAULT_MODEL_PATH, FEATURE_COLUMNS
else:
    from common import DEFAULT_MODEL_PATH, FEATURE_COLUMNS


def train(
    model_path: Path = DEFAULT_MODEL_PATH,
    *,
    test_size: float = 0.25,
    random_state: int = 42,
    max_iter: int = 300,
) -> float:
    """Train the original Iris experiment and persist its inference metadata."""
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size должен быть больше 0 и меньше 1")
    if max_iter < 1:
        raise ValueError("max_iter должен быть положительным")

    iris = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        iris.data,
        iris.target,
        test_size=test_size,
        random_state=random_state,
        stratify=iris.target,
    )
    model = LogisticRegression(max_iter=max_iter, random_state=random_state)
    model.fit(x_train, y_train)
    accuracy = float(accuracy_score(y_test, model.predict(x_test)))

    artifact = {
        "model": model,
        "feature_columns": list(FEATURE_COLUMNS),
        "target_names": iris.target_names.tolist(),
    }
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    return accuracy


def main() -> int:
    parser = argparse.ArgumentParser(description="Обучить классификатор Iris и сохранить модель")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH, help="Путь сохранения модели")
    parser.add_argument("--test-size", type=float, default=0.25, help="Доля тестовой выборки")
    parser.add_argument("--random-state", type=int, default=42, help="Начальное состояние генератора")
    parser.add_argument("--max-iter", type=int, default=300, help="Максимальное число итераций")
    args = parser.parse_args()
    try:
        accuracy = train(
            args.model_path,
            test_size=args.test_size,
            random_state=args.random_state,
            max_iter=args.max_iter,
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")
    print(f"accuracy={accuracy:.3f}")
    print(f"model_saved={args.model_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
