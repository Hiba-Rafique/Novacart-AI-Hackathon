from datetime import date

from fastapi.testclient import TestClient

from policyguard.config import APP_ROOT, REPO_ROOT, Settings
from policyguard.main import create_app
from policyguard.reasoning import ReasonerUnavailable
from policyguard.schemas import (
    AskRequest,
    AskResponse,
    ConversationState,
)


class FakeService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def ask(self, request: AskRequest, *, request_id: str) -> AskResponse:
        if self.fail:
            raise ReasonerUnavailable("test failure")
        return AskResponse(
            status="ANSWER",
            answer="The standard fee is Rs. 250.",
            parts=[],
            citations=[],
            calculation=None,
            clarifying_question=None,
            conversation=ConversationState(original_question=None),
            resolved_contact_date=date(2026, 11, 14),
            request_id=request_id,
        )


def _client(service: FakeService) -> TestClient:
    app = create_app(settings=Settings(gemini_api_key=None), service=service)
    return TestClient(app, raise_server_exceptions=False)


def test_health_and_ui_routes() -> None:
    with _client(FakeService()) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").status_code == 200
        assert "NovaCart PolicyGuard" in client.get("/").text
        assert client.head("/").status_code == 200
        info = client.get("/api/v1/info").json()
        assert info["model_mode"] == "offline-extractive"
        assert info["date_policy"] == "explicit_user_dates_only"
        assert "resolved_server_date" not in info


def test_ask_route_returns_service_response_and_request_id() -> None:
    with _client(FakeService()) as client:
        response = client.post("/api/v1/ask", json={"question": "What is the Metro fee?"})

    assert response.status_code == 200
    assert response.json()["status"] == "ANSWER"
    assert response.headers["x-request-id"]
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_invalid_request_uses_error_shape() -> None:
    with _client(FakeService()) as client:
        response = client.post("/api/v1/ask", json={"question": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_reasoner_failure_maps_to_503() -> None:
    with _client(FakeService(fail=True)) as client:
        response = client.post("/api/v1/ask", json={"question": "What is the Metro fee?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert response.json()["error"]["retryable"] is True


def test_real_app_loads_committed_index_and_answers() -> None:
    app = create_app(
        settings=Settings(
            gemini_api_key=None,
            policies_dir=REPO_ROOT / "policies",
            index_dir=APP_ROOT / "data" / "index",
        )
    )

    with TestClient(app) as client:
        ready = client.get("/readyz")
        answer = client.post(
            "/api/v1/ask",
            json={
                "question": (
                    "My contact date is 2026-11-14. What is the shipping fee for Metro cities?"
                )
            },
        )

    assert ready.status_code == 200
    assert ready.json()["documents"] == 22
    assert answer.status_code == 200
    assert answer.json()["citations"]


def test_real_app_requires_contact_date_before_answering() -> None:
    app = create_app(
        settings=Settings(
            gemini_api_key=None,
            policies_dir=REPO_ROOT / "policies",
            index_dir=APP_ROOT / "data" / "index",
        )
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/ask", json={"question": "What is the Metro fee?"})

    assert response.status_code == 200
    assert response.json()["status"] == "CLARIFY"
    assert response.json()["resolved_contact_date"] is None
    assert response.json()["conversation"]["last_asked_field"] == "contact_date"
    assert response.json()["citations"] == []


def test_body_size_limit_returns_413() -> None:
    with _client(FakeService()) as client:
        response = client.post(
            "/api/v1/ask",
            content="{}",
            headers={"content-type": "application/json", "content-length": "20000"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
