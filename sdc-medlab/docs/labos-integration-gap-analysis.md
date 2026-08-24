# VYOMA LabOS Flask Integration Gap Analysis

Date: 2026-08-17

## 1. Executive Summary

The current `sdc-medlab/` application is a solid Flask-based WhatsApp + AI POC, but it is not yet aligned with the LabOS integration architecture. It currently behaves like a standalone communication app with local MongoDB storage, direct PDF ingestion, and WhatsApp-triggered AI summaries. The new LabOS specification requires Flask to become a communication and automation layer only, with LabOS remaining the clinical system of record.

Primary conclusion:

- The current app is **partially reusable** for WhatsApp, conversation state, AI summary formatting, and basic deduplication.
- The current app is **missing** the LabOS event-driven webhook, HMAC verification, M2M report retrieval, LabOS-facing API contracts, and several booking/report delivery workflows.
- The current app is **not ready** for LabOS integration without adding a new adapter layer and replacing direct report intake with LabOS event consumption.

Overall readiness classification: **PARTIALLY READY, BLOCKED BY LABOS API CONTRACTS**

## 2. Existing Flask Architecture

Observed implementation:

- `app.py` creates a Flask app, registers `/health`, `/health/db`, `/health/meta`, `/webhook`, and `/api/reports`.
- `services/mongodb.py` acts as the data layer and creates MongoDB indexes.
- `services/whatsapp.py` wraps Meta Cloud API outbound sends.
- `services/gemini.py` wraps Gemini structured summary generation.
- `services/reports.py` stores PDFs locally, extracts text, caches summaries, and formats replies.
- `services/conversation.py` normalizes messages and drives the state machine.
- `routes/webhook.py` handles Meta webhook verification and report ingestion.

Assessment:

- Architecture is modular and usable as a base.
- There is no explicit LabOS adapter layer yet.
- There is no separate domain model layer for LabOS events or report snapshots.
- Flask currently owns report intake, which conflicts with the LabOS system-of-record rule.

## 3. Existing WhatsApp Implementation

What exists:

- WhatsApp outbound text sending.
- WhatsApp interactive button sending.
- Document sending support in the WhatsApp client.
- Template sending support in the WhatsApp client.
- Incoming webhook parsing for WhatsApp messages and status events.
- Message normalization for text, interactive, document, image, and audio payloads.
- Basic duplicate-message suppression using `processed_messages.message_id`.

What is missing or incomplete:

- No list-message UI.
- No delivery-status processing beyond logging.
- No retry-aware delivery orchestration.
- No secure report link generation through LabOS.
- No support for report-ready notification based on `report.available`.
- No persistent language flow tied to LabOS report sessions.

## 4. Existing AI Implementation

What exists:

- Gemini integration using `google-genai`.
- Structured JSON response validation using Pydantic.
- Summary caching per report and language.
- Simple medical safety prompt instructions.
- Emergency keyword detection on report text.

What is missing or risky:

- AI still works from extracted PDF text stored locally, not from a verified LabOS report contract.
- There is no deterministic post-processing guard that blocks unsafe content beyond prompt instructions and schema validation.
- There is no explicit critical-flag handling from LabOS as a hard stop.
- There is no guarantee that every summary is derived only from structured verified report data.
- There is no “AI failure must not block delivery” fallback tied to LabOS report events yet.

## 5. Existing Webhook Implementation

What exists:

- `GET /webhook` Meta verification using `hub.mode`, `hub.verify_token`, `hub.challenge`.
- `POST /webhook` for WhatsApp messages.
- `POST /api/reports` for direct report upload.

What is missing:

- No `POST /api/v1/webhooks/labos`.
- No HMAC-SHA256 verification using `X-Vyoma-Signature`.
- No raw-body signature verification.
- No LabOS event parsing.
- No event replay protection beyond WhatsApp message deduplication.
- No idempotency by `event_id`.

## 6. Existing Conversation / Chatbot Flow

Current state support:

- `idle`
- `awaiting_analyze`
- `awaiting_language`
- `analyzing`
- `awaiting_action`
- `booking`
- `doctor_consultation`
- `support`
- `emergency_halt`

What exists:

- Global commands: `menu`, `home`, `help`, `cancel`, `stop`, `restart`.
- Basic report analysis trigger.
- Basic booking/support/consultation branches.

What is missing:

- No explicit session object with `session_id`, `selected_option`, and timeout handling.
- No formal chatbot state machine for LabOS-driven report arrival.
- No greeting intent detection for casual openers.
- No natural-language intent routing for Manglish / Malayalam transliterated input.
- No back/confirm/change flows for booking.
- No comprehensive state recovery for old sessions.

## 7. Existing Booking Functionality

What exists:

- Local MongoDB collections for appointments, doctor consultations, and support requests.
- Duplicate prevention at a basic phone/status level.
- Simple confirmation text responses.

What is missing:

- No integration to LabOS booking APIs.
- No real doctor availability API.
- No date/time selection flow.
- No slot availability checks.
- No explicit confirmation step before booking.
- No branch/location selection.
- No home sample collection flow.
- No lab test catalog integration.
- No payment or secure booking orchestration.

## 8. Existing Report Delivery Functionality

What exists:

- Direct `POST /api/reports` upload.
- Local PDF storage in `storage/reports/`.
- PDF text extraction and summary caching.
- WhatsApp notification that a report is ready.
- “Analyze with AI” reply flow.

What is missing:

- No LabOS `report.available` webhook.
- No official report retrieval from LabOS M2M endpoint.
- No secure report URL generation.
- No patient-name/report-number lookup from LabOS.
- No guarantee that the official PDF remains the only source of truth.
- No explicit “View Report” LabOS-backed access flow.
- No separation between official LabOS PDF and Flask-side cached copies.

## 9. Existing Authentication / Security

What exists:

- `REPORT_INGEST_API_KEY` protection for `POST /api/reports`.
- Meta webhook verification token check.
- Environment-variable-based secrets.
- Basic safe error handling on many routes.

What is missing or weak:

- No HMAC signature verification for LabOS webhooks.
- No tenant/organization isolation.
- No strict replay protection for LabOS event delivery.
- No formal authorization for LabOS M2M calls besides the expected integration key concept.
- No rate limiting.
- No request fingerprinting or audit trail for webhook origin.
- No explicit secret redaction policy enforcement in code beyond not printing obvious values.

## 10. Existing Database / Data Model

Current collections:

- `processed_messages`
- `conversation_state`
- `reports`
- `appointments`
- `doctor_consultations`
- `support_requests`
- `event_logs`

Assessment:

- The database is a standalone MongoDB application store.
- It is not a second clinical system of record, which is good.
- However, it currently stores full PDFs locally and report metadata directly from ingestion, which conflicts with the LabOS-only clinical authority model.
- No tenant isolation is visible in the current data model.
- No LabOS event store exists.

## 11. LabOS Integration Requirements

LabOS-side capabilities the Flask app depends on:

- `POST /api/v1/webhooks/labos` for `report.available`.
- `GET /api/v1/integrations/reports/{report_id}/download` for official PDF retrieval.
- `X-Integration-Key` support for M2M authentication.
- `X-Vyoma-Signature` support for webhook HMAC verification.
- Patient detail lookup API.
- Report metadata lookup API.
- Doctor availability API.
- Lab booking API.
- Test catalog API.
- Branch/location availability API.

These are required because the current Flask app does not provide authoritative clinical or booking data.

## 12. Feature-by-Feature Gap Analysis

| Requirement | Existing | Partial | Missing | Needs LabOS API | Action |
|---|---:|---:|---:|---:|---|
| LabOS webhook `POST /api/v1/webhooks/labos` |  |  | X | X | Add new webhook route |
| `report.available` event handling |  |  | X | X | Parse and dispatch event |
| HMAC-SHA256 `X-Vyoma-Signature` |  |  | X | X | Verify raw body signature |
| Event `event_id` idempotency | X |  |  |  | Store processed event IDs |
| Replay protection |  |  | X |  | Reject duplicate signatures/events |
| M2M report download |  |  | X | X | Fetch official PDF from LabOS |
| `X-Integration-Key` auth |  |  | X | X | Add authenticated LabOS client |
| Report delivery via WhatsApp | X |  |  |  | Rewire to event-driven delivery |
| PDF handling | X |  |  |  | Remove Flask as source of truth |
| English summary | X |  |  |  | Keep, but drive from verified data |
| Malayalam summary | X |  |  |  | Keep, but drive from verified data |
| AI fallback | X |  |  |  | Keep deterministic fallback text |
| Critical-result safety |  | X |  | X | Add hard stop from LabOS flags |
| Greeting intent |  | X |  |  | Add intent detection |
| Main menu | X |  |  |  | Preserve and refine |
| Doctor consultation |  | X |  | X | Replace local stub with API flow |
| Date selection |  |  | X | X | Add availability-driven UX |
| Time selection |  |  | X | X | Add availability-driven UX |
| Appointment confirmation |  |  | X | X | Add confirm/change/cancel flow |
| Unavailable slot handling |  |  | X | X | Require live availability |
| Lab booking |  | X |  | X | Move to LabOS booking API |
| Test selection |  |  | X | X | Pull from LabOS catalog |
| Home collection |  |  | X | X | Add provider/API contract |
| Lab visit |  |  | X | X | Add branch/location API |
| Customer care | X |  |  |  | Preserve basic routing |
| Human handoff | X |  |  |  | Improve with ticketing integration |
| Natural-language intent detection |  | X |  |  | Add structured intent layer |
| Malayalam/Manglish input |  |  | X |  | Add language/intent normalization |
| Language persistence | X |  |  |  | Tighten session persistence |
| Back / Cancel / Main Menu | X |  |  |  | Preserve and expand per state |
| Session timeout |  |  | X |  | Add TTL/expiry handling |
| Duplicate booking protection | X |  |  |  | Replace with API-safe idempotency |
| WhatsApp interactive buttons | X |  |  |  | Preserve |
| WhatsApp list messages |  |  | X |  | Add for larger menus |
| Conversation state machine | X |  |  |  | Formalize and document |
| Audit / logging | X |  |  |  | Expand for LabOS events |
| Tenant isolation |  |  | X | X | Add org/branch scoping |
| Error handling | X |  |  |  | Preserve and harden |
| LabOS outage handling |  |  | X | X | Add retry/fallback paths |
| WhatsApp outage handling |  | X |  |  | Add queue/retry policy |
| AI outage handling | X |  |  |  | Keep deterministic fallback |

## 13. Required API Contracts

The Flask app needs these confirmed or designed with LabOS:

- LabOS event webhook schema for `report.available`.
- Webhook signature secret and HMAC canonicalization rules.
- Report metadata fetch endpoint.
- Official report download endpoint.
- Patient contact lookup endpoint.
- Doctor availability endpoint.
- Appointment creation endpoint.
- Lab test catalog endpoint.
- Branch/location availability endpoint.
- Customer-care handoff endpoint or ticketing API.

If any of these do not already exist, they are blocking dependencies and must be defined by the LabOS team.

## 14. Security Gaps

High priority gaps:

- Missing HMAC verification for LabOS webhooks.
- Missing replay protection by `event_id`.
- No tenant or branch isolation in the Flask data model.
- No explicit rate limiting.
- No guaranteed secret redaction policy for all logs.
- Current report ingestion endpoint is not LabOS-authenticated M2M integration.

Medium priority gaps:

- No structured audit event for each LabOS request/response.
- No fail-closed behavior for malformed LabOS webhook payloads.
- No strict separation between official LabOS PDF and local cache copies.

## 15. AI Safety Gaps

Current safety strengths:

- Prompt instructions discourage diagnosis and prescriptions.
- Output schema validation exists.
- Emergency keyword detection exists.

Current safety gaps:

- No deterministic enforcement of LabOS critical flags.
- No content-based post-filter that rejects unsafe model output.
- No proof that AI only sees verified LabOS data.
- No explicit anti-hallucination layer that prevents guesses about appointments, prices, or availability.
- No policy layer that routes serious/critical findings directly to safe escalation text.

## 16. WhatsApp UX Gaps

Current UX is functional but not yet aligned with the LabOS spec:

- No greeting-first main menu flow.
- No list-message menus.
- No state-specific back/cancel/restart recovery in every branch.
- No persistent language UX across sessions.
- No secure report view link.
- No formal report-ready flow that waits for language choice before summary.

## 17. Booking Gaps

Doctor booking gaps:

- No live availability source.
- No date/time selection logic.
- No explicit confirm/change/cancel step.
- No failure path for slot contention.

Lab booking gaps:

- No test catalog integration.
- No branch/location availability.
- No home collection address/time flow.
- No payment handoff integration.

## 18. Report Delivery Gaps

Current app behavior:

- Accepts direct PDF upload.
- Sends a “report ready” WhatsApp message.
- Allows summary generation from the uploaded file.

Required LabOS behavior:

- Receive event from LabOS, not direct report upload as the primary path.
- Fetch the official report from LabOS M2M download endpoint.
- Use LabOS report metadata and critical flags.
- Offer report access and summaries without modifying the PDF.

## 19. Missing Tests

Already covered today:

- Meta webhook verification success/failure.
- Empty POST handling.
- Text message routing.
- Duplicate WhatsApp message suppression.
- Analyze button language prompt.
- Cached summary behavior.
- AI failure fallback.
- Support and booking basics.

Still missing for LabOS integration:

- HMAC signature verification.
- Raw-body replay/modified payload rejection.
- `report.available` webhook handling.
- M2M report download.
- idempotent event processing by `event_id`.
- critical-flag escalation.
- LabOS outage handling.
- WhatsApp send failure retry or failure logging.
- booking slot contention.
- natural-language intent detection.
- Malayalam/Manglish input routing.
- session timeout expiry.

## 20. Recommended Implementation Order

1. Define LabOS webhook and M2M API contracts.
2. Add `POST /api/v1/webhooks/labos` with HMAC verification.
3. Add `event_id` idempotency storage and replay protection.
4. Add LabOS report retrieval and official PDF handling.
5. Replace direct report ingestion as the primary workflow with `report.available`.
6. Refine the chatbot state machine for report, booking, and support flows.
7. Add availability-driven booking adapters for doctor and lab booking.
8. Add deterministic critical-flag and safety escalation logic.
9. Expand tests for webhook security, booking, delivery, and outage behavior.

## 21. Dependencies on the LabOS FastAPI Developer

The Flask team needs LabOS-side confirmation for:

- Event schema for `report.available`.
- Raw-body signing secret and canonicalization format.
- Report download endpoint path and authentication.
- Patient metadata lookup endpoint.
- Doctor availability API.
- Appointment creation API.
- Lab catalog and branch availability APIs.
- Customer-care handoff/ticket API.
- Error response formats and retry guidance.

## 22. Risks / Breaking Changes

Key risks:

- Moving from direct report upload to event-driven report delivery changes the operational flow.
- Existing tests assume local PDF ingestion and will need to be updated.
- Conversation state will need to become more formal to support LabOS-driven sessions.
- LabOS outage handling must be defined so patient messaging does not break delivery.
- Local stored PDFs should become cache-only or temporary, not authoritative.

## 23. Final Readiness Classification

Overall:

- Flask communication layer: **PARTIALLY READY**
- LabOS integration: **BLOCKED BY LABOS API**
- WhatsApp delivery: **PARTIALLY READY**
- AI summary: **PARTIALLY READY**
- Booking flows: **MISSING / BLOCKED BY LABOS API**
- Security posture for LabOS webhooks: **MISSING**

Final verdict:

**The current app is reusable as a foundation, but it is not yet LabOS-integrated.**

## Concise Summary

1. What already works

- Flask app bootstrap and health endpoints.
- Meta webhook verification.
- WhatsApp send/receive basics.
- MongoDB persistence and deduplication.
- Gemini summary generation with caching.
- Basic support/booking conversation branches.

2. What needs to be changed

- Replace direct report ingestion as the main workflow.
- Add LabOS webhook, HMAC, and event idempotency.
- Move report retrieval to LabOS M2M download.
- Add booking and customer-care adapter flows.
- Add stronger safety and intent handling.

3. What can be reused

- Flask app structure.
- WhatsApp client.
- MongoDB layer.
- Conversation/state machinery.
- AI summary formatting and caching patterns.

4. What must be added

- LabOS event webhook.
- HMAC verification.
- Event replay protection.
- Report retrieval from LabOS.
- LabOS booking/customer-care adapters.
- Better UX states and list-message menus.

5. What APIs are required from LabOS

- `POST /api/v1/webhooks/labos`
- `GET /api/v1/integrations/reports/{report_id}/download`
- patient lookup API
- doctor availability API
- appointment booking API
- lab catalog API
- branch availability API
- customer care / ticket API

6. What credentials are required

- `LABOS_INTEGRATION_KEY`
- webhook signing secret for `X-Vyoma-Signature`
- WhatsApp Cloud API token and phone number ID
- AI API key and model

7. Recommended implementation sequence

- Define LabOS contracts.
- Implement signed webhook ingestion.
- Add idempotent event processing.
- Add official report retrieval.
- Rework chatbot/report flows.
- Add booking adapters.
- Expand tests.

8. Critical security issues

- Missing LabOS HMAC verification.
- Missing replay protection.
- No tenant isolation.
- No deterministic enforcement of critical flags.
- No formal LabOS event audit trail.
