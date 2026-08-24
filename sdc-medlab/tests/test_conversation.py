from __future__ import annotations

from datetime import datetime, timezone


def payload_for_message(message, phone="919999999999"):
    value = {"messages": [message], "contacts": [{"wa_id": phone}]}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": value}]}]}


def test_booking_cancellation_resets_state(client, store, fake_whatsapp):
    store.set_state("919999999999", "booking", language="en", active_report_id="RPT-1")
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-cancel",
                "from": "919999999999",
                "timestamp": "1700000010",
                "type": "text",
                "text": {"body": "cancel"},
            }
        ),
    )
    assert response.status_code == 200
    state = store.get_state("919999999999")
    assert state["state"] == "idle"
    assert any(call[0] == "interactive" for call in fake_whatsapp.calls)


def test_support_ticket_created(client, store, fake_whatsapp):
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-support",
                "from": "919999999999",
                "timestamp": "1700000011",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "customer_support", "title": "Customer Support"}},
            }
        ),
    )
    assert response.status_code == 200
    assert store.db.support_requests.find_one({"phone": "919999999999"}) is not None
    assert any(call[0] == "text" and "support team" in call[2].lower() for call in fake_whatsapp.calls)
