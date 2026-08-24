# SDC MedLab

Production-style Flask POC for WhatsApp-based lab report intake and AI summary delivery.

## Architecture

- `app.py`: Flask entrypoint and app factory
- `routes/webhook.py`: Meta webhook verification, inbound webhook handling, and report intake
- `services/mongodb.py`: MongoDB collections, indexes, state helpers, and event logging
- `services/whatsapp.py`: WhatsApp Cloud API sender
- `services/gemini.py`: Gemini analysis and structured output validation
- `services/reports.py`: Report storage, PDF extraction, intake, and summary formatting
- `services/conversation.py`: Normalization, deduplication, routing, booking, support, and language flow
- `services/safety.py`: Emergency detection and safe-failure messaging
- `prompts/medical_report_prompt.txt`: medical summary system prompt

## Installation

```powershell
cd sdc-medlab
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

- `MONGODB_URI`
- `MONGODB_DATABASE`
- `META_VERIFY_TOKEN`
- `META_ACCESS_TOKEN`
- `META_PHONE_NUMBER_ID`
- `META_API_VERSION`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `APP_ENV`
- `PORT`
- `TEST_MODE`
- `TEST_PHONE_NUMBER`
- `REPORT_INGEST_API_KEY`
- `REPORT_MAX_FILE_MB`
- `REPORT_STORAGE_DIR`

Never commit `.env`.

## MongoDB Setup

Use a MongoDB instance you control, including a free-compatible tier.

Collections created by the app:

- `processed_messages`
- `conversation_state`
- `reports`
- `appointments`
- `doctor_consultations`
- `support_requests`
- `event_logs`

Indexes are created by the application on startup when a real client is supplied.

## Meta WhatsApp Setup

1. Create or reuse a Meta Cloud API WhatsApp app.
2. Set the webhook callback URL to your public HTTPS endpoint:
   - `https://YOUR_DOMAIN/webhook`
3. Set the verify token to `META_VERIFY_TOKEN`.
4. Subscribe the app to the WhatsApp messages webhook field.
5. Configure `META_ACCESS_TOKEN` and `META_PHONE_NUMBER_ID`.

Webhook verification:

- `GET /webhook`
- requires `hub.mode=subscribe`
- requires `hub.verify_token == META_VERIFY_TOKEN`
- returns the raw `hub.challenge`

## Gemini Setup

1. Create a Gemini API key.
2. Set `GEMINI_API_KEY`.
3. Set `GEMINI_MODEL` to the model you want to use.
4. Keep the model configurable through the environment.

The app asks Gemini for strict JSON and validates the response before sending anything to the patient.

## Cloudflare Tunnel

Use Cloudflare Tunnel to expose localhost over HTTPS:

```powershell
cloudflared tunnel --url http://localhost:5000
```

Use the generated HTTPS URL as the Meta webhook callback.

## Run

```powershell
python app.py
```

Production-style WSGI:

```powershell
gunicorn app:app
```

Do not use Flask debug mode in production.

## Report Ingestion Example

`POST /api/reports` requires `X-API-Key: REPORT_INGEST_API_KEY`.

Example using multipart form-data:

```powershell
curl -X POST "http://localhost:5000/api/reports" `
  -H "X-API-Key: ingest-key" `
  -F "phone=919999999999" `
  -F "patient_id=P001" `
  -F "report_id=RPT-001" `
  -F "report_type=lab" `
  -F "report_date=2026-08-13" `
  -F "pdf_file=@report.pdf"
```

After a successful intake, the app sends a WhatsApp interactive message with:

- View Report
- Analyze with AI
- Book Test

## Testing the Analyze Button

1. Ingest a report for a real WhatsApp phone number.
2. Send the report-ready notification.
3. Tap `Analyze with AI`.
4. The app asks for language selection.
5. Choose English or Malayalam.
6. The app looks up the linked report, extracts text, calls Gemini, validates the JSON, caches the summary, and sends the result back on WhatsApp.

## Local Test Procedure

```powershell
cd sdc-medlab
.venv\Scripts\Activate.ps1
pytest
```

## Troubleshooting

- If webhook verification fails, confirm `META_VERIFY_TOKEN`.
- If report analysis fails, confirm `GEMINI_API_KEY` and `GEMINI_MODEL`.
- If WhatsApp sends fail, confirm `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, and phone permissions.
- If MongoDB health fails, confirm `MONGODB_URI`.
- If PDF extraction returns empty text, the file may be image-only or malformed.

## Security Notes

- Secrets are read from environment variables.
- No access tokens are logged.
- Inbound webhooks use deduplication.
- Report intake requires an API key.
- Failed AI analysis returns a safe message and does not fabricate values.
- The app is not HIPAA compliant by default.

## POC Limitations

- Local filesystem storage is only for the POC.
- Booking and consultation flows are lightweight and intentionally simple.
- PDF extraction cannot recover text from image-only scans without OCR.
- Rendering, queueing, and background jobs are not included.

## Production Migration Notes

- Move report PDFs to durable object storage.
- Put webhook processing behind a queue if traffic grows.
- Add OCR for scanned PDFs.
- Add structured consent and audit logging.
- Add stronger RBAC, monitoring, and backups.
- Review legal, privacy, and compliance obligations before production use.
