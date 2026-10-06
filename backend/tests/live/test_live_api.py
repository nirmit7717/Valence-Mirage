"""Live smoke tests against a running server with real LLM credentials.

Opt-in only:
    $env:VM_LIVE_BASE_URL = "http://localhost:8000"
    .\\venv\\Scripts\\python -m pytest -m live
Optionally set VM_LIVE_BEARER to a JWT to run as a logged-in user.
"""

import os

import httpx
import pytest

BASE_URL = os.getenv("VM_LIVE_BASE_URL", "").rstrip("/")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not BASE_URL, reason="set VM_LIVE_BASE_URL to run live tests"),
]


@pytest.fixture
def live():
    with httpx.Client(base_url=BASE_URL, timeout=180.0) as http:
        yield http


def _start(live) -> tuple[str, dict]:
    headers = {}
    bearer = os.getenv("VM_LIVE_BEARER")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    response = live.post(
        "/session/new",
        json={"player_name": "LiveTester", "character_class": "warrior", "campaign_size": "small"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    if data.get("guest_token"):
        headers["X-Session-Token"] = data["guest_token"]
    return data["session_id"], headers


def _act(live, session_id, headers, action):
    response = live.post(f"/session/{session_id}/action", json={"action": action}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_health(live):
    response = live.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_narration_is_non_empty(live):
    session_id, headers = _start(live)
    body = _act(live, session_id, headers, "I open the wooden chest")
    assert len(body["narration"]) > 20


def test_rich_narration_on_success(live):
    session_id, headers = _start(live)
    for _ in range(5):
        body = _act(live, session_id, headers, "I carefully examine the table in front of me")
        if body.get("redo_turn") or body["outcome"] == "combat_active":
            continue
        if body["outcome"] in ("success", "critical_success"):
            assert len(body["narration"]) > 50
            return
    pytest.skip("no success outcome in 5 tries")


def test_failure_narration_explains_consequence(live):
    session_id, headers = _start(live)
    for _ in range(5):
        body = _act(live, session_id, headers, "I attempt to leap across the chasm while blindfolded")
        if body.get("redo_turn") or body["outcome"] == "combat_active":
            continue
        if body["outcome"] in ("failure", "critical_failure"):
            assert len(body["narration"]) > 30
            return
    pytest.skip("no failure outcome in 5 tries")


def test_history_records_turns(live):
    session_id, headers = _start(live)
    _act(live, session_id, headers, "I look around")
    _act(live, session_id, headers, "I examine the nearest door")
    response = live.get(f"/session/{session_id}/history", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
