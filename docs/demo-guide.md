# VYOMA LABOS — Client Demonstration & QA Script

This document provides a step-by-step demonstration script for walking stakeholders through the completed VYOMA LABOS system.

> [!WARNING]
> All accounts and data below are **DEVELOPMENT / DEMO ONLY**. No real patient medical data is used.

---

## 1. Demo Credentials

| Role | Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@vyoma.com` | `admin123` | System settings, user management, audit logs, n8n config, report generation |
| **Reviewer** | `reviewer@vyoma.com` | `reviewer123` | Verification queue, result sign-off, correction return, report viewing |
| **Technician** | `tech@vyoma.com` | `tech123` | Sample collection, worklist, result entry, correction re-entry |
| **Reception** | `reception@vyoma.com` | `reception123` | Patient registration, order creation, report lookup |

---

## 2. Primary End-to-End Client Demo Scenario

### Step 1: Patient Registration & Order Creation (Reception)
1. Sign in as Reception (`reception@vyoma.com`).
2. Navigate to **Patients** (`/patients`) -> Click **Register Patient**.
3. Register synthetic patient: *Sarah Connor*, DOB: `1985-05-12`, Phone: `+91 98765 43210`.
4. Navigate to **Orders** (`/orders/new`).
5. Select *Sarah Connor*, pick tests (e.g. *Complete Blood Count (CBC)* and *Lipid Profile*).
6. Submit Order -> System creates Order Number (e.g. `ORD-2026-00010`).

### Step 2: Sample Collection & Processing (Technician)
1. Sign in as Technician (`tech@vyoma.com`).
2. Navigate to **Samples Tracker** (`/samples`) -> Locate order `ORD-2026-00010`.
3. Click **Collect Sample** (Status becomes `Collected`).
4. Click **Start Processing** (Status becomes `Processing`).
5. Navigate to **Technician Worklist** (`/worklist`) -> Click **Enter Results**.
6. Enter values:
   - Hemoglobin: `13.5 g/dL` (Normal)
   - Cholesterol: `185 mg/dL` (Normal)
7. Click **Submit Results for Review**.

### Step 3: Result Verification & Reviewer Sign-Off (Reviewer)
1. Sign in as Reviewer (`reviewer@vyoma.com`).
2. Navigate to **Verification Queue** (`/verification`).
3. Open sample verification detail -> Inspect parameter values, reference ranges, and abnormal flags.
4. Click **Verify & Sign-Off**.
5. System marks results `Verified` and Order status transitions to `Verified`.

### Step 4: Report Generation & PDF Download (Admin)
1. Sign in as Admin (`admin@vyoma.com`).
2. Navigate to **Reports Registry** (`/reports`).
3. Click **Generate PDF Report** for the verified order.
4. Click **Download / View PDF** -> Verify generated PDF header, patient details, results table, reference ranges, and pathologist verification sign-off.

### Step 5: Audit Trail & Automation Logs (Admin)
1. Navigate to **Audit Trail** (`/audit`). Verify logs for `PATIENT_CREATED`, `ORDER_CREATED`, `RESULT_SUBMITTED`, `RESULT_APPROVED`, `REPORT_GENERATED`, and `REPORT_DOWNLOADED`.
2. Navigate to **n8n Integration** (`/settings/integrations`) -> Click **View Delivery Logs**.
3. Verify outbound `report.available` event delivery record and status.

---

## 3. Secondary Demo Scenarios

### Scenario A: Critical Result Alerting
- Enter a critical result value (e.g. Hemoglobin: `5.0 g/dL` - Critical Low).
- Show prominent **CRITICAL** alert badge on Technician Worklist, Reviewer Verification Queue, and Dashboard.
- Show critical flag preserved in official PDF report.

### Scenario B: Correction Workflow & Audit Traceability
- Reviewer returns result for correction with reason (e.g. *"Plausibility check required"*).
- Technician receives sample back in worklist under status `Correction Required`.
- Technician re-enters corrected value with explanation.
- Reviewer approves -> Audit trail records full correction history and reason.

### Scenario C: n8n Outage Resilience Demonstration
- Simulate n8n webhook target offline.
- Generate report -> Report is created successfully and available for immediate PDF download in LabOS.
- Integration delivery record is marked `Failed`.
- When n8n comes online, Admin clicks **Retry** in `/settings/integrations/logs` -> Delivery status updates to `Sent`.
