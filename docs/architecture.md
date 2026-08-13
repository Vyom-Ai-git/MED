# VYOMA LABOS — Complete System Architecture Specification

## Executive System Overview

**VYOMA LABOS** is a multi-tenant Clinical Laboratory Information System (LIS) built to manage clinical laboratory operations with auditability, role-based access control, tenant boundary enforcement, and integration capability.

```text
                                VYOMA LABOS
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
   Next.js Frontend           FastAPI Core Service           PostgreSQL DB
   (TypeScript/Tailwind)       (Python 3.14 / Pydantic)      (Multi-Tenant)
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     │
                             report.available
                                     │
                                     ▼
                            n8n Automation Engine
                                ┌────┼────┐
                                │    │    │
                             WhatsApp AI Other
```

---

## 1. Architectural Principles & Boundaries

1. **System of Record (LabOS)**: LabOS is the sole immutable clinical system of record. Test results, reference ranges, verifications, and official PDF laboratory reports originate and reside strictly within LabOS.
2. **Automation & Orchestration Layer (n8n)**: n8n handles outbound delivery logic, message templating, retry queuing, and external API calls (e.g. WhatsApp Business API).
3. **AI Safety Boundary**:
   - AI is strictly an optional assistance layer for WhatsApp patient-facing communication formatting.
   - AI **MUST NOT**:
     - Approve laboratory results
     - Modify result values or flags
     - Alter reference ranges
     - Diagnose patients or prescribe treatment
     - Modify official PDF report files
4. **Failure Isolation**: If n8n or WhatsApp services are unavailable or error out, clinical operations (Verification, Report Generation, PDF Downloads, Dashboard metrics) remain fully functional inside LabOS.

---

## 2. Core Functional Modules

```text
Phases 0–9 Module Overview:

Phase 0: Foundation & Core System Configuration
Phase 1: Authentication, Multi-Tenancy & RBAC
Phase 2: Patient Registry & Test Catalog Management
Phase 3: Test Order Management & Billing Breakdown
Phase 4: Sample Tracker & Result Processing Worklist
Phase 5: Reviewer Verification & Correction Workflow
Phase 6: Report PDF Generation & File Storage
Phase 7: Comprehensive Audit Trail & Security Hardening
Phase 8: Laboratory Dashboard & Operational Analytics
Phase 9: n8n + WhatsApp + AI Integration Boundary
```

---

## 3. Data Flow Lifecycle

```text
1. Patient Registration  (Reception)   ──► Patient Record
2. Order Creation        (Reception)   ──► Verified Order Items & Pricing
3. Sample Registration   (Technician)  ──► Barcoded Sample Tracking
4. Sample Processing     (Technician)  ──► Sample Status: Processing
5. Result Entry          (Technician)  ──► Result Status: Draft / Entered
6. Reviewer Verification (Reviewer)    ──► Verified Result & Order Status: Verified
7. Report Generation     (Admin/System)──► PDF File Generated & SHA-256 Checksum Stored
8. Audit & Event         (System)      ──► Audit Event Log & report.available Event Emitted
9. Outbound Integration  (n8n Engine)  ──► Webhook Dispatched (HMAC Signed)
10. Delivery Channel     (WhatsApp)    ──► Patient Report Notification
```

---

## 4. Key Security Specifications

- **Authentication**: JWT Access tokens (HS256) with expiration and role assertions.
- **Tenant Isolation**: Every database query scopes access by `organization_id` derived from authenticated user token.
- **HMAC-SHA256 Signatures**: Outbound webhooks are signed using server secret `N8N_WEBHOOK_SECRET` producing header `X-Vyoma-Signature`.
- **Machine-to-Machine Auth**: n8n report retrieval uses `X-Integration-Key` header matching `N8N_INTEGRATION_KEY`.
