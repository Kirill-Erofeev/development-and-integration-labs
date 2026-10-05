from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.common import DEFAULT_MODEL_PATH, FEATURE_COLUMNS, PROJECT_ROOT
from src.model_service import ModelService
from src.request_id import (
    configure_prediction_logging,
    log_prediction,
    log_prediction_error,
    resolve_request_id,
)

from .schemas import (
    HealthResponse, ModelInfoErrorResponse, ModelInfoResponse,
    PredictErrorResponse, PredictRequest, PredictResponse,
)


REQUEST_ID_HEADERS = {"X-Request-ID": {
    "description": "UUID запроса из ответа и лога",
    "schema": {"type": "string", "format": "uuid"},
}}


def create_app(model_path: Path | None = None) -> FastAPI:
    """Configure an application that loads its model during lifespan startup."""
    selected_model_path = (
        Path(model_path)
        if model_path is not None
        else Path(os.environ.get("ML_MODEL_PATH") or DEFAULT_MODEL_PATH)
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_prediction_logging()
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

    @application.middleware("http")
    async def request_identity(request: Request, call_next):
        if request.method != "POST" or request.url.path != "/predict":
            return await call_next(request)
        request_id = resolve_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        if response.status_code >= 400:
            log_prediction_error(request_id, response.status_code)
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Echoing invalid NaN/Infinity inputs would make the error response invalid JSON.
        errors = [
            {key: error[key] for key in ("loc", "msg", "type")}
            for error in exc.errors()
        ]
        content = {"detail": errors}
        if hasattr(request.state, "request_id"):
            content["request_id"] = request.state.request_id
        return JSONResponse(status_code=422, content=content)

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        content = {"detail": exc.detail}
        if hasattr(request.state, "request_id"):
            content["request_id"] = request.state.request_id
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @application.get("/", response_class=FileResponse, include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(PROJECT_ROOT / "static" / "index.html", media_type="text/html")

    @application.get(
        "/health",
        response_model=HealthResponse,
        summary="Проверить состояние сервиса и готовность модели",
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            model_loaded=application.state.model_service is not None,
        )

    @application.get(
        "/model-info",
        response_model=ModelInfoResponse,
        summary="Получить безопасный паспорт загруженной модели",
        responses={
            503: {"model": ModelInfoErrorResponse, "description": "Модель не загружена"},
            500: {"model": ModelInfoErrorResponse, "description": "Некорректные метаданные модели"},
        },
    )
    def model_info() -> ModelInfoResponse:
        service = application.state.model_service
        if service is None:
            raise HTTPException(status_code=503, detail="Модель не загружена")
        try:
            return ModelInfoResponse(**service.model_info())
        except (AttributeError, TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Не удалось получить паспорт модели") from None

    @application.post(
        "/predict",
        response_model=PredictResponse,
        summary="Предсказать класс одного ириса",
        responses={
            200: {"headers": REQUEST_ID_HEADERS},
            400: {"model": PredictErrorResponse, "description": "Не удалось прочитать тело запроса", "headers": REQUEST_ID_HEADERS},
            422: {"model": PredictErrorResponse, "description": "Неверный запрос", "headers": REQUEST_ID_HEADERS},
            503: {"model": PredictErrorResponse, "description": "Модель не загружена", "headers": REQUEST_ID_HEADERS},
            500: {"model": PredictErrorResponse, "description": "Не удалось выполнить прогноз", "headers": REQUEST_ID_HEADERS},
        },
    )
    def predict(
        payload: PredictRequest,
        request: Request,
        x_request_id: str | None = Header(
            default=None,
            description="Корректный UUID сохраняется; иначе сервер создаёт новый UUID",
        ),
    ) -> PredictResponse:
        service = application.state.model_service
        if service is None:
            raise HTTPException(status_code=503, detail="Модель не готова к предсказанию")
        features = [[getattr(payload, column) for column in FEATURE_COLUMNS]]
        try:
            result = service.predict(features)[0]
            response = PredictResponse(
                class_id=result["predicted_class"],
                class_name=result["predicted_name"],
                request_id=request.state.request_id,
            )
        except Exception:
            # Keep internal estimator errors and input values out of the response and log.
            raise HTTPException(status_code=500, detail="Не удалось выполнить прогноз") from None
        log_prediction(request.state.request_id, result["predicted_name"])
        return response

    return application


app = create_app()
