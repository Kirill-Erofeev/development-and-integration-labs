from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.common import DEFAULT_MODEL_PATH, FEATURE_COLUMNS
from src.model_service import ModelService

from .schemas import HealthResponse, PredictRequest, PredictResponse


def create_app(model_path: Path | None = None) -> FastAPI:
    """Configure an application that loads its model during lifespan startup."""
    selected_model_path = (
        Path(model_path)
        if model_path is not None
        else Path(os.environ.get("ML_MODEL_PATH") or DEFAULT_MODEL_PATH)
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            service = ModelService.load(selected_model_path)
        except Exception as exc:
            raise RuntimeError(
                f"Не удалось загрузить модель из {selected_model_path}: {exc}"
            ) from exc

        application.state.model_service = service
        try:
            yield
        finally:
            application.state.model_service = None

    application = FastAPI(
        title="API классификации ирисов",
        description="Предсказание класса Iris по четырём признакам сохранённой моделью.",
        lifespan=lifespan,
    )
    application.state.model_service = None

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Echoing invalid NaN/Infinity inputs would make the error response invalid JSON.
        errors = [
            {key: error[key] for key in ("loc", "msg", "type")}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.get(
        "/health",
        response_model=HealthResponse,
        summary="Проверить состояние сервиса и готовность модели",
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            model_ready=application.state.model_service is not None,
        )

    @application.post(
        "/predict",
        response_model=PredictResponse,
        summary="Предсказать класс одного ириса",
    )
    def predict(request: PredictRequest) -> PredictResponse:
        service = application.state.model_service
        if service is None:
            raise HTTPException(status_code=503, detail="Модель не готова к предсказанию")
        features = [[getattr(request, column) for column in FEATURE_COLUMNS]]
        result = service.predict(features)[0]
        return PredictResponse(
            prediction=result["predicted_class"],
            class_name=result["predicted_name"],
        )

    return application


app = create_app()
