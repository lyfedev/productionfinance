"""Contract tests for the /health and / skeleton routes (D-20)."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_exact_key_set():
    response = client.get("/health")
    body = response.json()
    assert set(body.keys()) == {"status", "version", "git_sha", "boot_time"}


def test_health_status_is_ok():
    response = client.get("/health")
    assert response.json()["status"] == "ok"


def test_health_version_matches_app_version():
    response = client.get("/health")
    assert response.json()["version"] == app.version


def test_health_boot_time_is_iso8601_utc():
    response = client.get("/health")
    boot_time = response.json()["boot_time"]
    parsed = datetime.fromisoformat(boot_time)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_health_boot_time_stable_across_requests():
    first = client.get("/health").json()["boot_time"]
    second = client.get("/health").json()["boot_time"]
    assert first == second


def test_health_git_sha_is_nonempty_string():
    response = client.get("/health")
    git_sha = response.json()["git_sha"]
    assert isinstance(git_sha, str)
    assert len(git_sha) > 0


def test_index_returns_200_with_project_name():
    response = client.get("/")
    assert response.status_code == 200
    assert "ProductionFinance" in response.text
