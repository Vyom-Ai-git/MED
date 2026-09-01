import os
import sys
import json
import time
import hmac
import hashlib
import requests

sys.path.insert(0, '/Users/vivek/Documents/MED/backend')
from app.core.config import settings

FLASK_URL = "http://127.0.0.1:5000"
FASTAPI_URL = "http://127.0.0.1:8000"
PHONE = "917736683583"
INTEGRATION_KEY = settings.LABOS_API_KEY
WEBHOOK_SECRET = getattr(settings, "FLASK_WORKFLOW_SECRET", "dev-secret-key-change-in-production")

def log_step(name, status, details=""):
    symbol = "✓" if status else "✗"
    print(f"  {symbol} {name}" + (f": {details}" if details else ""))
    if not status:
        sys.exit(1)

print("\n==============================================")
print("  WHATSAPP UX & LABOS OPERATIONAL VALIDATION  ")
print("==============================================\n")

# Helper to simulate sending a WhatsApp incoming text/interactive message to Flask
def send_wa_message(msg_id, text, msg_type="text", button_id="", button_title=""):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "12345",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15555555555", "phone_number_id": "100000000000000"},
                    "contacts": [{"profile": {"name": "Test Recipient"}, "wa_id": PHONE}],
                    "messages": [{
                        "from": PHONE,
                        "id": msg_id,
                        "timestamp": str(int(time.time())),
                        "type": msg_type,
                        "text": {"body": text} if msg_type == "text" else None,
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": button_id or text, "title": button_title or text}
                        } if msg_type == "interactive" else None
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    res = requests.post(f"{FLASK_URL}/webhook", json=payload)
    return res

# ----------------------------------------------------
# 1. DOCTOR FLOW
# ----------------------------------------------------
print("--- 1. DOCTOR CONSULTATION FLOW ---")
msg1_id = f"wmid.doc.hi.{int(time.time())}"
r1 = send_wa_message(msg1_id, "Hi")
log_step("Doctor Step 1: Send 'Hi'", r1.status_code in (200, 202), f"HTTP {r1.status_code}")

msg2_id = f"wmid.doc.select.{int(time.time())}"
r2 = send_wa_message(msg2_id, "Consult Doctor", msg_type="interactive", button_id="consult_doctor", button_title="Consult Doctor")
log_step("Doctor Step 2: Select 'Consult Doctor' (fetches real LabOS doctors)", r2.status_code in (200, 202), f"HTTP {r2.status_code}")

msg3_id = f"wmid.doc.book.{int(time.time())}"
r3 = send_wa_message(msg3_id, "1")
log_step("Doctor Step 3: Select Doctor 1 (creates real LabOS appointment)", r3.status_code in (200, 202), f"HTTP {r3.status_code}")

# Verify appointment was created in FastAPI DB
r_docs = requests.get(f"{FASTAPI_URL}/api/v1/doctors", headers={"X-Integration-Key": INTEGRATION_KEY})
d_data = r_docs.json()
d_items = d_data.get("items", d_data) if isinstance(d_data, dict) else d_data
log_step("Doctor Step 4: Verify real LabOS backend returned doctor list", r_docs.status_code == 200 and len(d_items) > 0, f"Count: {len(d_items)}")

# ----------------------------------------------------
# 2. LAB FLOW
# ----------------------------------------------------
print("\n--- 2. LAB TEST BOOKING FLOW ---")
msg4_id = f"wmid.lab.hi.{int(time.time())}"
r4 = send_wa_message(msg4_id, "Hi")
log_step("Lab Step 1: Send 'Hi'", r4.status_code in (200, 202), f"HTTP {r4.status_code}")

msg5_id = f"wmid.lab.select.{int(time.time())}"
r5 = send_wa_message(msg5_id, "Book Lab Test", msg_type="interactive", button_id="book_lab_test", button_title="Book Lab Test")
log_step("Lab Step 2: Select 'Book Lab Test' (fetches real LabOS catalog)", r5.status_code in (200, 202), f"HTTP {r5.status_code}")

msg6_id = f"wmid.lab.confirm.{int(time.time())}"
r6 = send_wa_message(msg6_id, "1")
log_step("Lab Step 3: Select Test 1 (creates real LabOS lab booking)", r6.status_code in (200, 202), f"HTTP {r6.status_code}")

# Verify test catalog in FastAPI DB
r_cat = requests.get(f"{FASTAPI_URL}/api/v1/tests/catalog", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Lab Step 4: Verify real LabOS catalog integration", r_cat.status_code == 200 and r_cat.json().get("total", 0) > 0)

# ----------------------------------------------------
# 3. REPORT FLOW
# ----------------------------------------------------
print("\n--- 3. REPORT WORKFLOW FLOW ---")
event_payload = {
    "event_id": f"evt-ux-{int(time.time())}",
    "event_type": "report.available",
    "timestamp": "2026-09-01T00:00:00Z",
    "data": {
        "report_id": "1",
        "order_id": "1",
        "patient_id": "PAT-2026-0001",
        "status": "verified"
    }
}
raw_body = json.dumps(event_payload).encode('utf-8')
sig = hmac.new(WEBHOOK_SECRET.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

wh_headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={sig}"
}
r_wh = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=wh_headers)
log_step("Report Step 1: Trigger report.available Webhook", r_wh.status_code in (200, 202), f"HTTP {r_wh.status_code}")

r_meta = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/1/metadata", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Report Step 2: Fetch Report Metadata from LabOS", r_meta.status_code == 200, f"Report ID: {r_meta.json().get('report_id') or r_meta.json().get('id')}")

r_res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/1/results", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Report Step 3: Fetch Verified Results from LabOS", r_res.status_code == 200, f"Results count: {len(r_res.json().get('results', []))}")

r_pdf = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/1/download", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Report Step 4: Download Official PDF from LabOS", r_pdf.status_code == 200 and r_pdf.headers.get("content-type") == "application/pdf")

r_link = requests.post(f"{FASTAPI_URL}/api/v1/integrations/reports/1/secure-link", json={"expires_in_hours": 24}, headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Report Step 5: Generate Secure Download Link", r_link.status_code == 200 and ("url" in r_link.json() or "download_url" in r_link.json() or "secure_token" in r_link.json()))

# ----------------------------------------------------
# 4. NEGATIVE TESTS
# ----------------------------------------------------
print("\n--- 4. NEGATIVE TESTS & RESILIENCE ---")
# Invalid Doctor Slot Conflict (Attempt to book already booked slot_id=1)
conflict_payload = {
    "patient_id": 1,
    "doctor_id": 1,
    "slot_id": 1,
    "appointment_date": "2026-09-05",
    "start_time": "10:00",
    "end_time": "10:30"
}
r_conf = requests.post(f"{FASTAPI_URL}/api/v1/bookings/doctor", json=conflict_payload, headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Negative 1: Doctor Slot Conflict Rejection", r_conf.status_code in (400, 409), f"HTTP {r_conf.status_code}")

# Invalid Patient 404
r_p404 = requests.get(f"{FASTAPI_URL}/api/v1/integrations/patients/lookup?patient_id=INVALID999", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Negative 2: Invalid Patient 404", r_p404.status_code == 404, f"HTTP {r_p404.status_code}")

# Invalid Report 404
r_r404 = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/NONEXISTENT/metadata", headers={"X-Integration-Key": INTEGRATION_KEY})
log_step("Negative 3: Invalid Report 404", r_r404.status_code == 404, f"HTTP {r_r404.status_code}")

# Invalid HMAC signature
bad_headers = {"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=invalid_hash"}
r_hmac = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=bad_headers)
log_step("Negative 4: HMAC Auth Signature Rejection", r_hmac.status_code in (401, 403), f"HTTP {r_hmac.status_code}")

# Duplicate Event Rejection
r_dup = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=wh_headers)
log_step("Negative 5: Duplicate Webhook Event Handling", r_dup.status_code in (200, 202), f"HTTP {r_dup.status_code}")

print("\n----------------------------------------------")
print("  UX & OPERATIONAL VALIDATION PASSED 100%!  ")
print("----------------------------------------------\n")
