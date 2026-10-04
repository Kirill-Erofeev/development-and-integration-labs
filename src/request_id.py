import json
import logging
from uuid import UUID, uuid4


prediction_logger = logging.getLogger("iris.predictions")


def configure_prediction_logging() -> None:
    """Send safe JSON events to stderr once per process."""
    prediction_logger.setLevel(logging.INFO)
    if not any(getattr(handler, "iris_events", False) for handler in prediction_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.iris_events = True
        prediction_logger.addHandler(handler)


def resolve_request_id(value: str | None = None) -> str:
    """Canonicalize a UUID or generate a new UUID for absent or invalid input."""
    if value is not None:
        try:
            return str(UUID(value))
        except (ValueError, AttributeError, TypeError):
            pass
    return str(uuid4())


def prediction_event(request_id: str, class_name: str) -> dict[str, str]:
    """Expose only the correlation ID and the predicted class in a safe event."""
    return {
        "event": "prediction_completed",
        "request_id": request_id,
        "class_name": class_name,
    }


def log_prediction(request_id: str, class_name: str) -> None:
    prediction_logger.info(json.dumps(prediction_event(request_id, class_name), ensure_ascii=False))


def log_prediction_error(request_id: str, status_code: int) -> None:
    prediction_logger.warning(json.dumps({
        "event": "prediction_rejected" if status_code < 500 else "prediction_failed",
        "request_id": request_id,
        "status_code": status_code,
    }))
