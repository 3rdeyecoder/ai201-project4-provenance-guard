import json

from app import app


def test_submit_and_appeal_flow():
    client = app.test_client()

    response = client.post(
        "/submit",
        json={
            "text": "Artificial intelligence represents a transformative paradigm shift in modern society.",
            "creator_id": "tester-1",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["content_id"]
    assert payload["attribution"] in {"likely_ai", "likely_human", "uncertain"}
    assert 0.0 <= payload["confidence"] <= 1.0
    assert payload["label"]

    appeal_response = client.post(
        "/appeal",
        json={
            "content_id": payload["content_id"],
            "creator_reasoning": "I wrote this myself from personal experience.",
        },
    )

    assert appeal_response.status_code == 200
    appeal_payload = appeal_response.get_json()
    assert appeal_payload["status"] == "under_review"

    log_response = client.get("/log")
    assert log_response.status_code == 200
    log_payload = log_response.get_json()
    assert len(log_payload["entries"]) >= 2
