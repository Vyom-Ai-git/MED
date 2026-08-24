# LabOS Flask Integration

## Architecture

Flask is the communication and automation layer.
LabOS remains the clinical system of record.
WhatsApp is the delivery channel.
AI is used only for patient-friendly communication.

## Webhook

- `POST /api/v1/webhooks/labos`
- Validates `X-Vyoma-Signature`
- Uses HMAC-SHA256 over the raw request body
- Rejects missing or invalid signatures
- Rejects malformed payloads

## Idempotency

- Event IDs are stored in `labos_events`
- Duplicate `event_id` values are not processed twice
- Duplicate events return a safe success response

## M2M Report Download

- The LabOS client downloads reports from the LabOS M2M endpoint
- Authentication uses `X-Integration-Key`
- Transient errors can be retried using configured limits
- Permanent auth/not-found errors are not retried

## Report Flow

1. LabOS emits `report.available`
2. Flask validates the signature
3. Flask checks event idempotency
4. Flask retrieves the official PDF from LabOS
5. Flask identifies the patient phone if available
6. Flask caches only the minimum required communication metadata
7. Flask sends a WhatsApp report-ready message
8. The patient chooses English or Malayalam
9. Flask returns a deterministic summary or safe fallback

## AI Safety

- AI is not used for diagnosis
- AI is not used to change the official PDF
- Critical results use deterministic escalation text
- Missing structured data falls back to safe templates

## Language Flow

- English
- Malayalam
- Language selection is persisted in conversation state
- The conversation can later be changed back to English or reset

## WhatsApp Flow

- Interactive buttons are used for the report flow
- Legacy menu handling remains available
- The report-ready message offers:
  - View Report
  - English
  - Malayalam

## Booking Adapters

The following adapters exist as contracts only:

- `DoctorBookingService`
- `LabBookingService`

They currently raise configuration errors until LabOS booking APIs are defined.

## Customer Care

- Local support requests remain available
- A future external ticketing API can be added without changing the conversation model

## Environment Variables

- `LABOS_BASE_URL`
- `LABOS_INTEGRATION_KEY`
- `LABOS_WEBHOOK_SECRET`
- `LABOS_TIMEOUT_SECONDS`
- `LABOS_MAX_RETRIES`
- `SESSION_TIMEOUT_MINUTES`

## Error Handling

- Missing phone/contact records return `WAITING_FOR_LABOS_API`
- Missing report metadata uses event data only
- Missing report download data marks the event failed
- Missing LabOS contracts raise clear configuration or contract errors

## Testing

The repository includes:

- existing legacy POC tests
- new LabOS webhook and idempotency tests
- new report delivery and critical-safety tests

## Pending LabOS Contracts

The following are still required from LabOS:

- patient-facing report access URL API
- report metadata API
- verified structured result API
- doctor availability API
- lab booking API
- test catalog API
- branch availability API
- patient lookup API when phone is not present in the event
