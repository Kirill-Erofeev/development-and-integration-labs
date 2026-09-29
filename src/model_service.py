from collections.abc import Sequence
from pathlib import Path
from typing import Any

import joblib

if __package__:
    from .common import FEATURE_COLUMNS
else:
    from common import FEATURE_COLUMNS


class ModelService:
    """Reuse a trusted estimator and its class metadata without fitting it."""

    def __init__(self, model: Any, target_names: Sequence[str]) -> None:
        self._model = model
        self._target_names = tuple(target_names)

    @classmethod
    def load(cls, model_path: Path) -> "ModelService":
        """Load and validate the artifact produced by the training command."""
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Модель не найдена: {model_path}. Сначала запустите src/train.py"
            )

        artifact = joblib.load(model_path)
        if not isinstance(artifact, dict) or set(artifact) != {
            "model",
            "feature_columns",
            "target_names",
        }:
            raise ValueError(
                "Неверный формат модели: создайте артефакт с помощью src/train.py"
            )

        feature_columns = artifact["feature_columns"]
        if not isinstance(feature_columns, list) or feature_columns != list(FEATURE_COLUMNS):
            raise ValueError(
                "Схема признаков модели не соответствует входному интерфейсу"
            )

        target_names = artifact["target_names"]
        if (
            not isinstance(target_names, list)
            or not target_names
            or not all(isinstance(name, str) for name in target_names)
        ):
            raise ValueError("В модели отсутствуют корректные названия классов")

        model = artifact["model"]
        if not callable(getattr(model, "predict", None)):
            raise ValueError("Артефакт не содержит классификатор")
        return cls(model, target_names)

    def predict(
        self, features: Sequence[Sequence[float]]
    ) -> list[dict[str, int | str]]:
        """Predict rows in FEATURE_COLUMNS order with the loaded estimator."""
        classes = self._model.predict(features)
        predictions = []
        for class_id in classes:
            class_id = int(class_id)
            if not 0 <= class_id < len(self._target_names):
                raise ValueError(
                    "Предсказанный класс отсутствует в метаданных модели"
                )
            predictions.append(
                {
                    "predicted_class": class_id,
                    "predicted_name": self._target_names[class_id],
                }
            )
        return predictions
