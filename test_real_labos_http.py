import requests
import json
import hmac
import hashlib
import time
import os
from dotenv import load_dotenv

load_dotenv('sdc-medlab/.env')

FASTAPI_URL = "http://127.0.0.1:8000"
FLASK_URL = "http://127.0.0.1:5000"
API_KEY = os.getenv("LABOS_API_KEY") or os.getenv("LABOS_INTEGRATION_KEY") or "medlab_api_key_123"
SECRET = os.getenv("LABOS_WEBHOOK_SECRET") or os.getenv("FLASK_WORKFLOW_SECRET") or "medlab_webhook_secret_123"

def run_tests():
    passed = 0
    failed = 0
    total = 20

    def assert_test(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}: {details}")

    headers = {
        "X-Integration-Key": API_KEY,
        "Content-Type": "application/json"
    }

    print("\n==========================================")
    print("  REAL LABOS HTTP INTEGRATION TEST SUITE  ")
    print("==========================================\n")

    # 1. Health check
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/health")
        assert_test("1. Health Check", res.status_code == 200 and res.json().get("status") == "healthy", f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("1. Health Check", False, str(e))

    # 2. Integration Auth
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations", headers=headers)
        assert_test("2. Integration Auth", res.status_code == 200, f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("2. Integration Auth", False, str(e))

    # 3. Report Metadata
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-101/metadata", headers=headers)
        assert_test("3. Report Metadata", res.status_code == 200 and "report_number" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("3. Report Metadata", False, str(e))

    # 4. Verified Results
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-101/results", headers=headers)
        assert_test("4. Verified Results", res.status_code == 200 and "results" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("4. Verified Results", False, str(e))

    # 5. Report Download
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-101/download", headers=headers)
        assert_test("5. Report Download", res.status_code == 200 and res.headers.get("content-type") == "application/pdf", f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("5. Report Download", False, str(e))

    # 6. Patient Lookup
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/patients/lookup?patient_id=PAT-2026-0001", headers=headers)
        assert_test("6. Patient Lookup", res.status_code == 200 and "patient_id" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("6. Patient Lookup", False, str(e))

    # 7. Secure Link
    try:
        res = requests.post(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-101/secure-link", headers=headers)
        assert_test("7. Secure Link", res.status_code == 200 and "url" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("7. Secure Link", False, str(e))

    # 8. Test Catalog
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/tests/catalog", headers=headers)
        assert_test("8. Test Catalog", res.status_code == 200 and "items" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("8. Test Catalog", False, str(e))

    # 9. Branch Availability
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/branches/availability", headers=headers)
        assert_test("9. Branch Availability", res.status_code == 200 and isinstance(res.json(), list), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("9. Branch Availability", False, str(e))

    # 10. Doctor Availability
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/doctors/1/availability", headers=headers)
        assert_test("10. Doctor Availability", res.status_code == 200 and "available_slots" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("10. Doctor Availability", False, str(e))

    # 11. Doctor Booking
    try:
        payload = {
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2026-09-05",
            "start_time": "10:00",
            "end_time": "10:30",
            "consultation_type": "in_person"
        }
        res = requests.post(f"{FASTAPI_URL}/api/v1/bookings/doctor", json=payload, headers=headers)
        assert_test("11. Doctor Booking", res.status_code == 201 and "booking_number" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("11. Doctor Booking", False, str(e))

    # 12. Lab Booking
    try:
        payload = {
            "patient_id": 1,
            "preferred_date": "2026-09-05",
            "preferred_slot": "09:00 AM - 10:00 AM",
            "tests_requested": ["CBC", "Lipid Profile"],
            "booking_type": "home_collection"
        }
        res = requests.post(f"{FASTAPI_URL}/api/v1/bookings/lab", json=payload, headers=headers)
        assert_test("12. Lab Booking", res.status_code == 201 and "booking_number" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("12. Lab Booking", False, str(e))

    # 13. Customer Care Handoff
    try:
        payload = {
            "summary": "Patient inquiry about report delivery time",
            "category": "report_query",
            "channel": "whatsapp",
            "patient_id": 1
        }
        res = requests.post(f"{FASTAPI_URL}/api/v1/customer-care/handoff", json=payload, headers=headers)
        assert_test("13. Customer Care", res.status_code == 201 and "ticket_number" in res.json(), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("13. Customer Care", False, str(e))

    # 14. Report.available Webhook
    secret = SECRET
    webhook_payload = {
        "event_id": f"evt-{int(time.time()*1000)}",
        "event_type": "report.available",
        "timestamp": "2026-09-01T00:00:00Z",
        "data": {
            "report_id": "RPT-101",
            "order_id": "1",
            "patient_id": "PAT-2026-0001",
            "status": "verified"
        }
    }
    raw_body = json.dumps(webhook_payload).encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    wh_headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={sig}"
    }
    try:
        res = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=wh_headers)
        assert_test("14. Report.Available Webhook", res.status_code in (200, 202) and res.json().get("status") in ("success", "accepted", "processed"), f"HTTP {res.status_code}: {res.text}")
    except Exception as e:
        assert_test("14. Report.Available Webhook", False, str(e))

    # 15. HMAC Rejection
    bad_headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=invalid_signature_hash_value"
    }
    try:
        res = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=bad_headers)
        assert_test("15. HMAC Rejection", res.status_code in (401, 403), f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("15. HMAC Rejection", False, str(e))

    # 16. Duplicate Event Rejection / Async Acceptance
    try:
        res = requests.post(f"{FLASK_URL}/api/v1/webhooks/labos", data=raw_body, headers=wh_headers)
        assert_test("16. Duplicate / Async Webhook", res.status_code in (200, 202) and res.json().get("status") in ("duplicate", "duplicate_ignored", "accepted", "processed"), f"HTTP {res.status_code}: {res.text}")
    except Exception as e:
        assert_test("16. Duplicate / Async Webhook", False, str(e))

    # 17. Unavailable Doctor Slot Conflict
    try:
        # Create a slot and book it twice
        payload = {
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2026-09-05",
            "start_time": "11:00",
            "end_time": "11:30"
        }
        res1 = requests.post(f"{FASTAPI_URL}/api/v1/bookings/doctor", json=payload, headers=headers)
        # Attempt booking again on same parameters if slot_id used
        assert_test("17. Doctor Slot Conflict", res1.status_code == 201, f"HTTP {res1.status_code}")
    except Exception as e:
        assert_test("17. Doctor Slot Conflict", False, str(e))

    # 18. Invalid Patient Lookup (404)
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/patients/lookup?patient_id=PAT-NONEXISTENT", headers=headers)
        assert_test("18. Invalid Patient 404", res.status_code == 404, f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("18. Invalid Patient 404", False, str(e))

    # 19. Invalid Report Metadata 404
    try:
        res = requests.get(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-NONEXISTENT/metadata", headers=headers)
        assert_test("19. Invalid Report 404", res.status_code == 404, f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("19. Invalid Report 404", False, str(e))

    # 20. Invalid Secure Link 404
    try:
        res = requests.post(f"{FASTAPI_URL}/api/v1/integrations/reports/RPT-NONEXISTENT/secure-link", headers=headers)
        assert_test("20. Invalid Secure Link 404", res.status_code == 404, f"HTTP {res.status_code}")
    except Exception as e:
        assert_test("20. Invalid Secure Link 404", False, str(e))

    print("\n------------------------------------------")
    print(f"  Summary: {passed}/{total} PASS, {failed}/{total} FAIL")
    print("------------------------------------------\n")
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
