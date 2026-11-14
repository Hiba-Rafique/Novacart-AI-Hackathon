from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response

from policyguard import __version__
from policyguard.config import Settings, get_settings
from policyguard.ingest import IndexValidationError, validate_index
from policyguard.reasoning import (
    ModelOutputError,
    PolicyService,
    ReasonerUnavailable,
    create_service,
)
from policyguard.retrieval import BM25Retriever

from .schemas import AskRequest, AskResponse, ErrorResponse

LOGGER = logging.getLogger("policyguard")
MAX_BODY_BYTES = 16 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", uuid.uuid4().hex)


def _error(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
) -> JSONResponse:
    payload = ErrorResponse.model_validate(
        {
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": request_id,
            }
        }
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def create_app(
    settings: Settings | None = None,
    service: PolicyService | None = None,
    retriever: BM25Retriever | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_settings = settings or get_settings()
        app.state.settings = runtime_settings
        app.state.ready = False
        app.state.ready_error = None
        app.state.manifest = None
        app.state.service = service

        if service is None:
            try:
                manifest = validate_index(
                    runtime_settings.policies_dir,
                    runtime_settings.index_dir,
                )
                runtime_retriever = retriever or BM25Retriever.from_index(
                    runtime_settings.index_dir,
                    default_top_k=runtime_settings.rag_top_k,
                )
                app.state.service = create_service(runtime_settings, runtime_retriever)
                app.state.manifest = manifest
                app.state.ready = True
            except (IndexValidationError, OSError, ValueError) as exc:
                LOGGER.error("policy index is not ready (%s): %s", type(exc).__name__, exc)
                app.state.ready_error = type(exc).__name__
        else:
            app.state.ready = True
        yield

    app = FastAPI(
        title="NovaCart PolicyGuard",
        version=__version__,
        description="Policy-only NovaCart assistant grounded in the supplied Markdown corpus.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return _error(
                        status_code=413,
                        code="REQUEST_TOO_LARGE",
                        message="The request body is too large.",
                        request_id=request.state.request_id,
                    )
            except ValueError:
                return _error(
                    status_code=400,
                    code="INVALID_CONTENT_LENGTH",
                    message="The Content-Length header is invalid.",
                    request_id=request.state.request_id,
                )
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return _error(
            status_code=422,
            code="INVALID_REQUEST",
            message="The request did not match the required schema.",
            request_id=_request_id(request),
        )

    @app.exception_handler(ReasonerUnavailable)
    async def reasoner_handler(request: Request, exc: ReasonerUnavailable):
        LOGGER.warning("reasoner unavailable: %s", type(exc).__name__)
        return _error(
            status_code=503,
            code="MODEL_UNAVAILABLE",
            message="The policy assistant is temporarily unavailable. Please retry.",
            request_id=_request_id(request),
            retryable=True,
        )

    @app.exception_handler(ModelOutputError)
    async def model_output_handler(request: Request, exc: ModelOutputError):
        LOGGER.warning("model output rejected: %s", type(exc).__name__)
        return _error(
            status_code=503,
            code="MODEL_OUTPUT_INVALID",
            message="The policy assistant could not verify its answer. Please retry.",
            request_id=_request_id(request),
            retryable=True,
        )

    @app.exception_handler(Exception)
    async def unexpected_handler(request: Request, exc: Exception):
        LOGGER.exception("unexpected error")
        return _error(
            status_code=500,
            code="INTERNAL_ERROR",
            message="The policy assistant encountered an unexpected error.",
            request_id=_request_id(request),
        )

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(request: Request):
        if not request.app.state.ready:
            return _error(
                status_code=503,
                code="INDEX_UNAVAILABLE",
                message="The policy index is not ready.",
                request_id=_request_id(request),
            )
        manifest = request.app.state.manifest
        return {
            "status": "ready",
            "documents": manifest.document_count if manifest else None,
            "chunks": manifest.chunk_count if manifest else None,
        }

    @app.get("/api/v1/info")
    async def info(request: Request):
        runtime_settings: Settings = request.app.state.settings
        manifest = request.app.state.manifest
        return {
            "version": __version__,
            "timezone": runtime_settings.app_timezone,
            "date_policy": "explicit_user_dates_only",
            "model_mode": "gemini" if runtime_settings.has_gemini else "offline-extractive",
            "documents": manifest.document_count if manifest else None,
            "chunks": manifest.chunk_count if manifest else None,
        }

    @app.post("/api/v1/ask", response_model=AskResponse)
    async def ask(request: Request, payload: AskRequest):
        if not request.app.state.ready or request.app.state.service is None:
            return _error(
                status_code=503,
                code="INDEX_UNAVAILABLE",
                message="The policy index is not ready.",
                request_id=_request_id(request),
            )
        response = await request.app.state.service.ask(
            payload,
            request_id=_request_id(request),
        )
        return response

    return app


app = create_app()
