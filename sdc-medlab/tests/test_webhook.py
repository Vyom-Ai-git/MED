from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


def payload_for_message(message, phone="919999999999"):
    value = {"messages": [message], "contacts": [{"wa_id": phone}]}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": value}]}]}


def test_meta_get_verification_success(client):
    response = client.get(
        "/webhook?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=abc123"
    )
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "abc123"


def test_meta_get_verification_failure(client):
    response = client.get(
        "/webhook?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=abc123"
    )
    assert response.status_code == 403


def test_empty_post_returns_ok(client):
    response = client.post("/webhook", json={})
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_text_message_routes_to_menu(client, fake_whatsapp):
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-1",
                "from": "919999999999",
                "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
                "type": "text",
                "text": {"body": "help"},
            }
        ),
    )
    assert response.status_code == 200
    assert fake_whatsapp.calls
    kind, phone, body, buttons = fake_whatsapp.calls[-1]
    assert kind == "interactive"
    assert phone == "919999999999"
    assert "How can I help" in body
    assert any(button["id"] == "analyze_report" for button in buttons)


def test_duplicate_message_is_ignored(client, fake_whatsapp):
    message = {
        "id": "msg-dup",
        "from": "919999999999",
        "timestamp": "1700000000",
        "type": "text",
        "text": {"body": "menu"},
    }
    payload = payload_for_message(message)
    assert client.post("/webhook", json=payload).status_code == 200
    first_call_count = len(fake_whatsapp.calls)
    assert client.post("/webhook", json=payload).status_code == 200
    assert len(fake_whatsapp.calls) == first_call_count


def _labos_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_labos_webhook_rejects_missing_signature(client):
    response = client.post("/api/v1/webhooks/labos", json={"event_id": "evt-1"})
    assert response.status_code == 401


def test_labos_webhook_rejects_invalid_signature(client):
    response = client.post(
        "/api/v1/webhooks/labos",
        data='{"event_id":"evt-1"}',
        content_type="application/json",
        headers={"X-Vyoma-Signature": "sha256=bad"},
    )
    assert response.status_code == 403


def test_labos_webhook_waits_when_patient_phone_is_missing(client, app_and_clients, fake_labos):
    app, fake_whatsapp, _ = app_and_clients
    app.config["LABOS_WORKFLOW"].labos = fake_labos
    payload = {
        "event_id": "evt-wait-1",
        "event_type": "report.available",
        "report_id": "RPT-100",
        "patient_id": "P100",
        "report_number": "LAB-100",
    }
    body = b'{"event_id":"evt-wait-1","event_type":"report.available","report_id":"RPT-100","patient_id":"P100","report_number":"LAB-100"}'
    response = client.post(
        "/api/v1/webhooks/labos",
        data=body,
        content_type="application/json",
        headers={"X-Vyoma-Signature": _labos_signature("labos-webhook-secret", body)},
    )
    assert response.status_code == 202
    assert response.get_json()["status"] == "waiting_for_labos_api"
    assert not fake_whatsapp.calls


def test_labos_webhook_processes_report_and_is_idempotent(client, app_and_clients, fake_labos):
    app, fake_whatsapp, _ = app_and_clients
    app.config["LABOS_WORKFLOW"].labos = fake_labos
    app.config["LABOS_WORKFLOW"].whatsapp = fake_whatsapp
    app.config["LABOS_WORKFLOW"].report_service.whatsapp = fake_whatsapp
    fake_labos.report_metadata = {
        "patient_phone": "919999999999",
        "patient_name": "Sanju",
        "critical_flag": False,
        "structured_result": {
            "tests": [
                {"name": "Hemoglobin", "value": "11.2", "unit": "g/dL", "status": "low"},
                {"name": "Sugar", "value": "110", "unit": "mg/dL", "status": "elevated"},
            ]
        },
    }
    body = b'{"event_id":"evt-ok-1","event_type":"report.available","report_id":"RPT-101","patient_id":"P101","report_number":"LAB-101"}'
    response = client.post(
        "/api/v1/webhooks/labos",
        data=body,
        content_type="application/json",
        headers={"X-Vyoma-Signature": _labos_signature("labos-webhook-secret", body)},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "processed"
    assert any(call[0] == "interactive" for call in fake_whatsapp.calls)

    fake_whatsapp.calls.clear()
    duplicate = client.post(
        "/api/v1/webhooks/labos",
        data=body,
        content_type="application/json",
        headers={"X-Vyoma-Signature": _labos_signature("labos-webhook-secret", body)},
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json()["status"] == "duplicate"
    assert not fake_whatsapp.calls
