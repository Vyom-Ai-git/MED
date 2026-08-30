from __future__ import annotations

from datetime import datetime, timezone


def payload_for_message(message, phone="919999999999"):
    value = {"messages": [message], "contacts": [{"wa_id": phone}]}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": value}]}]}


def insert_report(store, phone="919999999999", report_id="RPT-001", summary_en=None, summary_ml=None, extracted_text="Hemoglobin 11.2 low, glucose 110 elevated"):
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
            "summary_en": summary_en,
            "summary_ml": summary_ml,
            "summary_model": "gemini-test",
            "processing_ms": 0,
            "summarized_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "status": "received",
        }
    )


def test_analyze_button_prompts_language(client, store, fake_whatsapp):
    insert_report(store)
    response = client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-analyze-1",
                "from": "919999999999",
                "timestamp": "1700000001",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    assert response.status_code == 200
    assert fake_whatsapp.calls[-1][0] == "interactive"
    assert fake_whatsapp.calls[-1][2] == "Please choose your language."
    assert {button["id"] for button in fake_whatsapp.calls[-1][3]} == {"lang_en", "lang_ml"}


def test_cached_english_summary_skips_gemini(client, store, fake_whatsapp, fake_gemini):
    insert_report(store, summary_en="Cached English summary")
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-lang-en",
                "from": "919999999999",
                "timestamp": "1700000002",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    fake_whatsapp.calls.clear()
    fake_gemini.calls.clear()
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-lang-en-2",
                "from": "919999999999",
                "timestamp": "1700000003",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_en", "title": "English"}},
            }
        ),
    )
    assert not fake_gemini.calls
    assert any(call[0] == "text" and "Cached English summary" in call[2] for call in fake_whatsapp.calls)


def test_cached_malayalam_summary_skips_gemini(client, store, fake_whatsapp, fake_gemini):
    insert_report(store, summary_ml="Cached Malayalam summary")
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-lang-ml",
                "from": "919999999999",
                "timestamp": "1700000004",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    fake_whatsapp.calls.clear()
    fake_gemini.calls.clear()
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-lang-ml-2",
                "from": "919999999999",
                "timestamp": "1700000005",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_ml", "title": "മലയാളം"}},
            }
        ),
    )
    assert not fake_gemini.calls
    assert any(call[0] == "text" and "Cached Malayalam summary" in call[2] for call in fake_whatsapp.calls)


def test_report_followup_actions_are_sent_after_analysis(client, store, fake_whatsapp, fake_gemini):
    insert_report(store)
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-lang-en-3",
                "from": "919999999999",
                "timestamp": "1700000006",
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
                "id": "msg-lang-en-4",
                "from": "919999999999",
                "timestamp": "1700000007",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_en", "title": "English"}},
            }
        ),
    )
    assert any(call[0] == "text" and "AI Report Summary" in call[2] for call in fake_whatsapp.calls)
    assert any(call[0] == "interactive" and call[2] == "What would you like to do next?" for call in fake_whatsapp.calls)


def test_labos_report_uses_gemini_for_each_language(client, store, fake_whatsapp, fake_gemini):
    store.upsert_report(
        {
            "report_id": "LABOS-RPT-1",
            "report_uuid": "uuid-LABOS-RPT-1",
            "phone": "919999999999",
            "patient_id": "P001",
            "patient_name": "Sanju",
            "report_number": "LAB-001",
            "source_system": "labos",
            "structured_result": {
                "tests": [
                    {
                        "test_name": "Hemoglobin",
                        "result_value": "11.2",
                        "unit": "g/dL",
                        "reference_range": "12-15",
                        "flag": "low",
                    }
                ]
            },
            "summary_en": None,
            "summary_ml": None,
            "status": "received",
        }
    )
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-labos-analyze",
                "from": "919999999999",
                "timestamp": "1700000010",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "analyze_report", "title": "Analyze with AI"}},
            }
        ),
    )
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-labos-en",
                "from": "919999999999",
                "timestamp": "1700000011",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_en", "title": "English"}},
            }
        ),
    )
    client.post(
        "/webhook",
        json=payload_for_message(
            {
                "id": "msg-labos-ml",
                "from": "919999999999",
                "timestamp": "1700000012",
                "type": "interactive",
                "interactive": {"button_reply": {"id": "lang_ml", "title": "Malayalam"}},
            }
        ),
    )
    assert [language for _, language in fake_gemini.calls] == ["en", "ml"]
    assert "Hemoglobin" in fake_gemini.calls[0][0]
    assert "reference range: 12-15" in fake_gemini.calls[0][0]
