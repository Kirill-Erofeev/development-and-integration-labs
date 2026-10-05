from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sepal_length: float = Field(gt=0, allow_inf_nan=False, description="Длина чашелистика")
    sepal_width: float = Field(gt=0, allow_inf_nan=False, description="Ширина чашелистика")
    petal_length: float = Field(gt=0, allow_inf_nan=False, description="Длина лепестка")
    petal_width: float = Field(gt=0, allow_inf_nan=False, description="Ширина лепестка")


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_id: int = Field(description="Идентификатор предсказанного класса")
    class_name: str = Field(description="Название предсказанного класса")
    request_id: UUID = Field(description="UUID запроса, общий для ответа и серверного лога")


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = Field(description="Состояние сервиса")
    model_loaded: bool = Field(description="Модель загружена и готова к предсказаниям")


class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_type: str = Field(description="Тип загруженного классификатора")
    classes: list[str] = Field(description="Названия классов в порядке их идентификаторов")
    feature_count: int = Field(gt=0, description="Число входных признаков")
    model_loaded: bool = Field(description="Модель загружена")


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loc: list[str | int]
    msg: str
    type: str


class PredictErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str | list[ValidationIssue]
    request_id: UUID


class ModelInfoErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
