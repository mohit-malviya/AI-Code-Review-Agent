import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.api.webhook import verify_github_signature
from app.services.approval_service import (
    FirestoreApprovalStore,
    JsonFileApprovalStore,
    create_approval_request,
    get_approval_request,
)

client = TestClient(app)


def test_health_check_endpoint():
    """Verify /health responds with 200 for Cloud Run probes."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-code-review-agent"


def test_root_endpoint():
    """Verify root endpoint responds with 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Code Review Agent is running" in response.json()["message"]


def test_webhook_signature_verification_valid():
    """Verify valid HMAC signature is accepted."""
    secret = "test_webhook_secret_123"
    raw_body = b'{"action": "ping"}'
    valid_sig = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": secret}):
        assert verify_github_signature(raw_body, valid_sig) is True


def test_webhook_signature_verification_invalid():
    """Verify invalid HMAC signature is rejected."""
    secret = "test_webhook_secret_123"
    raw_body = b'{"action": "ping"}'
    invalid_sig = "sha256=invalidhashvalue1234567890"

    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": secret}):
        assert verify_github_signature(raw_body, invalid_sig) is False


def test_webhook_signature_missing_when_secret_configured():
    """Verify missing signature is rejected when secret is set."""
    secret = "test_webhook_secret_123"
    raw_body = b'{"action": "ping"}'

    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": secret}):
        assert verify_github_signature(raw_body, None) is False


def test_webhook_endpoint_rejects_unauthorized_post():
    """Verify /webhook returns 401 when signature is invalid."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "my_secret"}):
        response = client.post(
            "/webhook",
            content=b'{"test": "payload"}',
            headers={
                "X-Hub-Signature-256": "sha256=bad_sig",
                "X-GitHub-Event": "push",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401
        assert "Invalid or missing GitHub webhook signature" in response.json()["detail"]


def test_webhook_endpoint_allows_when_secret_unset():
    """Verify /webhook allows requests when no secret is configured (dev mode)."""
    with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": ""}, clear=True):
        with patch("app.api.webhook.process_github_event"):
            response = client.post(
                "/webhook",
                json={"repository": {"name": "test"}, "action": "opened"},
                headers={"X-GitHub-Event": "ping"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "accepted"


def test_firestore_store_fallback():
    """Verify FirestoreApprovalStore falls back gracefully when Firestore is unavailable."""
    fs = FirestoreApprovalStore()
    # In local testing without GCP credentials or firestore, db will be None
    assert fs.get("non-existent-id") is None
