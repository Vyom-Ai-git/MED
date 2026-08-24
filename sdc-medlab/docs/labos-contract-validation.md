# LabOS Contract Validation

**Date**: 2026-08-17  
**Status**: ✅ CONTRACT COMPLETE - All 11 Capabilities Defined

---

## Official OpenAPI Specification

The authoritative LabOS API contract is defined in [docs/labos-openapi.json](./labos-openapi.json). This document is machine-readable and drives Flask client implementation.

---

## 11 Required Capabilities

### 1. **Report Available Webhook / Integration Event**

**LabOS Endpoint (POST)**: `/api/v1/integrations/n8n/test`

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Authentication** | `X-Integration-Key` header |
| **Purpose** | Test webhook reachability before subscribing to report.available events |
| **Request Body** | `{ "webhook_url": "string (URI)" }` |
| **Response (200)** | `{ "status": "string", "message": "string" }` |
| **Error Responses** | 400 (invalid URL), 401 (unauthorized) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `test_webhook()` |

**Get Integration Logs**: `GET /api/v1/integrations/logs`
- Query params: `limit` (default 50), `offset` (default 0)
- Returns array of integration event logs with timestamps

---

### 2. **Report Metadata API**

**Primary Endpoint (GET)**: `/api/v1/integrations/reports/{id}/metadata`  
**Alternative (GET)**: `/api/v1/reports/{id}/metadata`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Path Parameter** | `id` (UUID, required) |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `ReportMetadata` schema |
| **Response Fields** | `report_id`, `patient_id`, `created_at`, `report_type`, `status`, `verified_at`, `verified_by` |
| **Status Enum** | `draft`, `pending_verification`, `verified`, `released` |
| **Error Responses** | 401 (unauthorized), 404 (not found) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_report_metadata(report_id)` |

---

### 3. **Verified Report Results API**

**Primary Endpoint (GET)**: `/api/v1/integrations/reports/{id}/results`  
**Alternative (GET)**: `/api/v1/reports/{id}/results`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Path Parameter** | `id` (UUID, required) |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `ReportResults` schema |
| **Response Structure** | `{ "report_id": "uuid", "tests": [...] }` |
| **Test Object** | `{ "test_name", "result_value", "unit", "reference_range", "flag" }` |
| **Flag Values** | `normal`, `high`, `low`, `critical` |
| **Precondition** | Report must be in `verified` status (HTTP 409 if not) |
| **Error Responses** | 401 (unauthorized), 404 (not found), 409 (not verified) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_verified_results(report_id)` |

---

### 4. **Patient Contact Lookup API**

**Endpoint (GET)**: `/api/v1/patients/lookup`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Query Parameter** | `patient_id` (UUID, required) |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `PatientInfo` schema |
| **Response Fields** | `patient_id`, `name`, `phone`, `email`, `date_of_birth` (nullable), `gender` (nullable) |
| **Gender Enum** | `M`, `F`, `O` |
| **Error Responses** | 401 (unauthorized), 404 (patient not found) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_patient(patient_id)` |

---

### 5. **Secure Patient Report Access / Secure Link Generation**

**Endpoint (POST)**: `/api/v1/reports/{id}/secure-link`

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Path Parameter** | `id` (UUID, required) |
| **Authentication** | `X-Integration-Key` header |
| **Request Body** | `{ "patient_id": "uuid", "expires_in_hours": 24 (optional) }` |
| **Response (200)** | See `SecureLink` schema |
| **Response Fields** | `token`, `expires_at` (ISO 8601), `url` (full patient-facing URL) |
| **Error Responses** | 401 (unauthorized), 404 (not found) |
| **Purpose** | Generate single-use, time-limited token for patient to access report |
| **Flask Implementation** | [`services/report_access.py`](../services/report_access.py) - method `get_patient_facing_url(report)` |

**Public Access Endpoint (GET)**: `/api/v1/public/reports/access/{token}`
- **Security**: No authentication required
- **Path Parameter**: `token` (string, required)
- **Query Parameter**: `format` (enum: `json`, `pdf`, default: `pdf`)
- **Response (200)**: PDF binary or JSON report results
- **Response Headers**: `Content-Disposition: attachment; filename=...`
- **Error Responses**: 401 (invalid/expired token), 404 (report not found)

---

### 6. **Test Catalog API**

**Endpoint (GET)**: `/api/v1/tests/catalog`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `TestCatalog` schema |
| **Response Structure** | `{ "tests": [ ... ] }` |
| **Test Object Fields** | `test_id`, `name`, `description` (nullable), `price` (float), `duration_hours` (integer) |
| **Error Responses** | 401 (unauthorized) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_test_catalog()` |

---

### 7. **Branch / Location Availability API**

**Endpoint (GET)**: `/api/v1/branches/availability`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Query Parameter** | `city` (string, optional filter) |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `BranchAvailability` schema |
| **Response Structure** | `{ "branches": [ ... ] }` |
| **Branch Object** | `branch_id`, `name`, `location` (object), `is_open` (boolean), `working_hours` |
| **Location Object** | `city`, `address` |
| **Working Hours** | `open_at` (HH:MM), `close_at` (HH:MM) |
| **Error Responses** | 401 (unauthorized) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_branch_availability()` |

---

### 8. **Doctor Availability API**

**Endpoint (GET)**: `/api/v1/doctors/{id}/availability`

| Property | Value |
|----------|-------|
| **HTTP Method** | GET |
| **Path Parameter** | `id` (UUID, doctor ID) |
| **Query Parameters** | `from_date` (YYYY-MM-DD, optional), `to_date` (YYYY-MM-DD, optional) |
| **Authentication** | `X-Integration-Key` header |
| **Response (200)** | See `DoctorAvailability` schema |
| **Response Fields** | `doctor_id`, `name`, `specialization`, `available_slots` |
| **Slot Object** | `date` (YYYY-MM-DD), `start_time` (HH:MM), `end_time` (HH:MM) |
| **Error Responses** | 401 (unauthorized), 404 (doctor not found) |
| **Flask Implementation** | [`services/labos_client.py`](../services/labos_client.py) - method `get_doctor_availability(doctor_id)` |

---

### 9. **Doctor Appointment Booking API**

**Endpoint (POST)**: `/api/v1/bookings/doctor`

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Authentication** | `X-Integration-Key` header |
| **Request Body** | See `DoctorAppointmentRequest` schema |
| **Required Fields** | `doctor_id`, `patient_id`, `appointment_date`, `appointment_time` |
| **Optional Fields** | `notes` (string, nullable) |
| **Response (201)** | See `DoctorAppointmentResponse` schema |
| **Response Fields** | `appointment_id` (UUID), `status`, `confirmation_token` |
| **Status Values** | `confirmed`, `pending`, `cancelled` |
| **Error Responses** | 400 (invalid request), 401 (unauthorized), 409 (slot already booked) |
| **Flask Implementation** | [`services/booking_adapters.py`](../services/booking_adapters.py) - class `DoctorBookingService.create_booking()` |

---

### 10. **Lab Booking API**

**Endpoint (POST)**: `/api/v1/bookings/lab`

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Authentication** | `X-Integration-Key` header |
| **Request Body** | See `LabBookingRequest` schema |
| **Required Fields** | `patient_id`, `test_ids` (array, min 1), `branch_id` |
| **Optional Fields** | `preferred_date`, `preferred_time`, `notes` |
| **Response (201)** | See `LabBookingResponse` schema |
| **Response Fields** | `booking_id`, `status`, `appointment_date`, `appointment_time`, `confirmation_token` |
| **Status Values** | `confirmed`, `pending`, `cancelled` |
| **Error Responses** | 400 (invalid), 401 (unauthorized), 409 (slot unavailable) |
| **Flask Implementation** | [`services/booking_adapters.py`](../services/booking_adapters.py) - class `LabBookingService.create_booking()` |

---

### 11. **Customer Care Handoff API**

**Endpoint (POST)**: `/api/v1/customer-care/handoff`

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Authentication** | `X-Integration-Key` header |
| **Request Body** | See `CustomerCareHandoffRequest` schema |
| **Required Fields** | `patient_id`, `category`, `message` |
| **Optional Fields** | `contact_number` (nullable) |
| **Category Enum** | `billing`, `appointment`, `report_query`, `general` |
| **Message Max Length** | 1000 characters |
| **Response (201)** | See `CustomerCareHandoffResponse` schema |
| **Response Fields** | `ticket_id`, `status`, `assigned_to` (nullable) |
| **Status Values** | `created`, `assigned`, `in_progress`, `resolved` |
| **Error Responses** | 400 (invalid), 401 (unauthorized) |
| **Flask Implementation** | [`services/booking_adapters.py`](../services/booking_adapters.py) - class `CustomerCareService.create_request()` |

**Endpoint (GET)**: `/api/v1/customer-care/handoff`
- **Query Parameter**: `patient_id` (UUID, optional filter)
- **Response (200)**: Array of `CustomerCareHandoffResponse` objects
- **Error Responses**: 401 (unauthorized)

---

## Authentication & Headers

**Required Header on All Integration Endpoints**:
```
X-Integration-Key: <integration-key>
```

**Provided During Onboarding**:
- Integration key enables access to all `/api/v1/integrations/*` endpoints
- Non-integration endpoints (`/api/v1/reports/*`, `/api/v1/bookings/*`, etc.) use same header

**Security**: 
- All endpoints return 401 if header is missing or invalid
- Integration key should be stored in environment variables (never in source code)

---

## Error Response Format

All error responses follow this schema:

```json
{
  "error": "string",
  "message": "string",
  "details": { "...": "..." }
}
```

**Common Error Codes**:
- `400 Bad Request`: Invalid parameters or malformed request body
- `401 Unauthorized`: Missing or invalid `X-Integration-Key` header
- `404 Not Found`: Resource (report, patient, doctor, etc.) does not exist
- `409 Conflict`: Business logic conflict (e.g., slot already booked, report not verified)
- `500 Internal Server Error`: Unexpected server error

---

## Implementation Checklist

| Capability | Endpoint(s) | Flask File | Status |
|---|---|---|---|
| 1. Integration Test & Logs | POST `/api/v1/integrations/n8n/test`, GET `/api/v1/integrations/logs` | `labos_client.py` | ✅ READY |
| 2. Report Metadata | GET `/api/v1/integrations/reports/{id}/metadata` | `labos_client.py` | ✅ READY |
| 3. Verified Results | GET `/api/v1/integrations/reports/{id}/results` | `labos_client.py` | ✅ READY |
| 4. Patient Lookup | GET `/api/v1/patients/lookup` | `labos_client.py` | ✅ READY |
| 5. Secure Link Gen | POST `/api/v1/reports/{id}/secure-link` | `report_access.py` | ✅ READY |
| 6. Test Catalog | GET `/api/v1/tests/catalog` | `labos_client.py` | ✅ READY |
| 7. Branch Availability | GET `/api/v1/branches/availability` | `labos_client.py` | ✅ READY |
| 8. Doctor Availability | GET `/api/v1/doctors/{id}/availability` | `labos_client.py` | ✅ READY |
| 9. Doctor Booking | POST `/api/v1/bookings/doctor` | `booking_adapters.py` | ✅ READY |
| 10. Lab Booking | POST `/api/v1/bookings/lab` | `booking_adapters.py` | ✅ READY |
| 11. Customer Care | POST/GET `/api/v1/customer-care/handoff` | `booking_adapters.py` | ✅ READY |

---

## Integration Testing Strategy

### Unit Tests (Mock LabOS)
- Test each Flask client method with mocked responses
- Verify request formation (headers, paths, params)
- Verify response parsing and error handling
- Location: `tests/test_labos_client.py`

### Mock Tests (Synthetic LabOS Responses)
- Test webhook flow end-to-end with fabricated payloads
- Test report delivery, HMAC verification, idempotency
- Test booking workflows with fake IDs
- Location: `tests/test_report_flow_mock.py`

### Real LabOS Integration Tests (If Available)
- Only run if LabOS server is accessible at `http://localhost:8000`
- Use synthetic test data (real patient/doctor/branch IDs from test fixtures)
- Verify actual endpoint responses
- Location: `tests/test_labos_integration.py` (skipped if server unavailable)

---

## Report Flow Test (End-to-End)

```
LabOS report.available webhook
  ↓
Flask POST /webhook receives payload
  ↓
HMAC verification (X-Vyoma-Signature)
  ↓
Idempotency check (duplicate prevention)
  ↓
Patient lookup via LabOS (GET /api/v1/patients/lookup)
  ↓
Report metadata retrieval (GET /api/v1/integrations/reports/{id}/metadata)
  ↓
Verified results fetch (GET /api/v1/integrations/reports/{id}/results)
  ↓
Secure link generation (POST /api/v1/reports/{id}/secure-link)
  ↓
WhatsApp message delivery to patient with secure link
```

---

## Files Changed (Ready for Implementation)

1. **[services/labos_client.py](../services/labos_client.py)** - Core LabOS API client (8 methods)
2. **[services/report_access.py](../services/report_access.py)** - Secure link handling
3. **[services/booking_adapters.py](../services/booking_adapters.py)** - Booking orchestration (3 classes)
4. **[routes/webhook.py](../routes/webhook.py)** - Report flow webhook handler (if needed)
5. **[tests/test_labos_client.py](../tests/test_labos_client.py)** - Unit tests (new)
6. **[tests/test_labos_integration.py](../tests/test_labos_integration.py)** - Real integration tests (new)

