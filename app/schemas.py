from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sepal_length: float = Field(gt=0, allow_inf_nan=False, description="Длина чашелистика")
    sepal_width: float = Field(gt=0, allow_inf_nan=False, description="Ширина чашелистика")
    petal_length: float = Field(gt=0, allow_inf_nan=False, description="Длина лепестка")
    petal_width: float = Field(gt=0, allow_inf_nan=False, description="Ширина лепестка")


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction: int = Field(description="Идентификатор предсказанного класса")
    class_name: str = Field(description="Название предсказанного класса")


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = Field(description="Состояние сервиса")
    model_ready: bool = Field(description="Модель загружена и готова к предсказаниям")
