# VYOMA LABOS — n8n Integration Contract Documentation

## Overview

This document specifies the integration contract between **VYOMA LABOS** (System of Record) and **n8n** (Automation & Delivery Orchestrator).

```text
                  VYOMA LABOS
                      │
                      │ (report.available event)
                      ▼
                   n8n Webhook
                      │
          ┌───────────┼───────────┐
          │           │           │
   Fetch Report   Format Msg   WhatsApp API
   (M2M Auth)     (Optional AI)  (Delivery)
```

---

## 1. Safety & Architectural Principles

1. **LabOS = System of Record**: All clinical data, test results, verification records, and official PDF reports originate from and remain immutable inside LabOS.
2. **n8n = Automation Orchestrator**: Handles message templating, retry policies, and external API routing (WhatsApp Business API).
3. **AI Safety Boundary**:
   - AI MUST NOT approve or alter laboratory results.
   - AI MUST NOT modify reference ranges or diagnostic flags.
   - AI MUST NOT provide clinical diagnosis or prescribe treatments.
   - AI generates only communication-oriented summaries (e.g., reminding patient to consult their physician).
   - If AI fails or times out, report delivery falls back to a standard template without blocking delivery.
4. **Failure Isolation**: If n8n or WhatsApp services are offline, clinical operations (Verification, PDF Generation, PDF Download) operate completely unimpeded. Delivery failures are tracked as `Failed` in LabOS and can be manually retried by Admins.

---

## 2. Webhook Configuration & Security

- **Webhook Target**: `N8N_WEBHOOK_URL` (configured via environment variable).
- **HMAC-SHA256 Signature**: Every request body is signed using `N8N_WEBHOOK_SECRET`.
- **Header**:
  - `X-Vyoma-Signature`: `sha256=<hex_digest>`
  - `X-Vyoma-Event-ID`: Unique string (e.g. `evt_...`)
  - `X-Vyoma-Event-Type`: Event type identifier (e.g., `report.available` or `integration.test`)
  - `Content-Type`: `application/json`

### Signature Verification Example (n8n Code Node / JavaScript)

```javascript
const crypto = require('crypto');
const secret = $env.N8N_WEBHOOK_SECRET;
const signatureHeader = $input.item.json.headers['x-vyoma-signature'] || '';
const rawBody = JSON.stringify($input.item.json.body);

const expectedSig = 'sha256=' + crypto.createHmac('sha256', secret).update(rawBody).digest('hex');

if (signatureHeader !== expectedSig) {
  throw new Error('Unauthorized: Invalid HMAC signature');
}
```

---

## 3. Outbound Event Payload Schemas

### Primary Integration Event: `report.available`

Emitted asynchronously when a laboratory report PDF is generated and ready for delivery.

```json
{
  "event_id": "evt_9b1deb4d3b7d45678123456789abcdef",
  "event_type": "report.available",
  "event_version": "1.0",
  "timestamp": "2026-08-13T19:30:00.000Z",
  "organization_id": 1,
  "branch_id": 1,
  "report_id": 12,
  "report_number": "RPT-2026-00012",
  "order_id": 45,
  "patient_id": 102
}
```

### Connection Test Event: `integration.test`

Sent when an Admin clicks "Test n8n Connection" in the LabOS UI. Contains no patient medical data.

```json
{
  "event_id": "test_3a7b9c1d2e",
  "event_type": "integration.test",
  "event_version": "1.0",
  "timestamp": "2026-08-13T19:35:00.000Z",
  "organization_id": 1
}
```

---

## 4. Machine-to-Machine (M2M) Report Retrieval API

When n8n receives a `report.available` webhook, it fetches the official PDF file using the M2M authentication endpoint.

- **Endpoint**: `GET /api/v1/integrations/reports/{id}/download`
- **Authentication Header**: `X-Integration-Key: <N8N_INTEGRATION_KEY>`
- **Response**: `application/pdf` (binary stream)
- **Security Features**: Enforces tenant boundary isolation and audits all M2M report download requests under action `REPORT_DOWNLOADED`.

---

## 5. Expected n8n Workflow Contract

```text
Webhook Listener
  ↓
Validate Signature (HMAC-SHA256)
  ↓
Check event_id (Idempotency)
  ↓
Branch by event_type:
  ├─ integration.test ──► Return 200 OK
  └─ report.available ──► Continue
       ↓
  Fetch Report PDF (GET /api/v1/integrations/reports/{id}/download)
       ↓
  Format WhatsApp Message Template
       ↓
  (Optional) AI Assistance for Communication Summary (Fallback if error)
       ↓
  Send WhatsApp Message (WhatsApp Business API)
       ↓
  Return HTTP 200 OK to LabOS
```

---

## 6. Delivery Status & Error Codes

- **HTTP 200 / 201 / 202**: Successful delivery (`IntegrationDelivery` status marked `Sent`).
- **HTTP 5xx / Connection Timeout**: Retried up to `INTEGRATION_MAX_RETRIES` times (default 3 attempts with 15s timeout). If all retries fail, status is marked `Failed`.
- **HTTP 4xx**: Configuration or payload error (does NOT retry automatically). Marked `Failed`.
