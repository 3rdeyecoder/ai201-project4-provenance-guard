import socket

from app import app, find_available_port


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


def test_find_available_port_skips_busy_ports():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        occupied_port = sock.getsockname()[1]
        sock.listen(1)

        candidate = find_available_port(start=occupied_port, max_attempts=3)
        assert candidate != occupied_port
