from __future__ import annotations

from datetime import datetime, timezone


def payload_for_message(message, phone="919999999999"):
    value = {"messages": [message], "contacts": [{"wa_id": phone}]}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": value}]}]}


def insert_report(store, phone="919999999999", report_id="RPT-001", extracted_text="Hemoglobin 11.2 low, glucose 110 elevated"):
    store.upsert_report(
        {
            "report_id": report_id,
            "report_uuid": f"uuid-{report_id}",
            "phone": phone,
            "patient_id": "P001",
            "report_type": "lab",
            "report_date": "2026-08-13",
            "pdf_url": "/tmp/report.pdf",
            "storage_key": "/tmp/report.pdf",
            "pdf_sha256": "sha",
            "extracted_text": extracted_text,
            "summary_en": None,
            "summary_ml": None,
            "summary_model": None,
            "processing_ms": 0,
            "summarized_at": None,
            "created_at": datetime.now(timezone.utc),
            "status": "received",
        }
    )


def test_missing_report_is_handled_safely(client, fake_whatsapp):
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-missing",
                "from": "919999999999",
                "timestamp": "1700000020",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    assert response.status_code == 200
    assert any("No report is linked" in call[2] for call in fake_whatsapp.calls if call[0] == "text")


def test_gemini_failure_returns_safe_message(client, store, fake_whatsapp, fake_gemini):
    insert_report(store)
    fake_gemini.error = RuntimeError("boom")
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-gfail-1",
                "from": "919999999999",
                "timestamp": "1700000021",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    fake_whatsapp.calls.clear()
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-gfail-2",
                "from": "919999999999",
                "timestamp": "1700000022",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_en", "title": "English"}},
            }
        ),
    )
    assert any("couldn't safely analyze" in call[2].lower() for call in fake_whatsapp.calls if call[0] == "text")


def test_malformed_gemini_response_returns_safe_message(client, store, fake_whatsapp, fake_gemini):
    insert_report(store)
    fake_gemini.result = {"tests": [], "key_findings": [], "doctor_discussion": [], "safety_notice": "⚠️"}
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-badjson-1",
                "from": "919999999999",
                "timestamp": "1700000023",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    fake_whatsapp.calls.clear()
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-badjson-2",
                "from": "919999999999",
                "timestamp": "1700000024",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_en", "title": "English"}},
            }
        ),
    )
    assert any("couldn't safely analyze" in call[2].lower() for call in fake_whatsapp.calls if call[0] == "text")


def test_emergency_halt_stops_normal_flow(client, store, fake_whatsapp):
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-emergency",
                "from": "919999999999",
                "timestamp": "1700000025",
                "type": "text",
                "text": {"body": "chest pain and trouble breathing"},
            }
        ),
    )
    assert response.status_code == 200
    state = store.get_state("919999999999")
    assert state["state"] == "emergency_halt"
    assert any("seek immediate" in call[2].lower() for call in fake_whatsapp.calls if call[0] == "text")
