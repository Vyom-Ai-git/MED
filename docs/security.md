# VYOMA LABOS — Security Architecture & Hardening Guide

## 1. Authentication & JWT Security

- **Algorithm**: HS256 with strong server-side secret (`JWT_SECRET`).
- **Token Claims**: Subject (`sub`: `user_id`), Organization (`org_id`), Role (`role`), Expiration (`exp`).
- **Production Requirement**: `JWT_SECRET` must be set via environment variable with a minimum 32-character random string. Insecure default secrets cause application startup failure in production mode (`ENVIRONMENT=production`).

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | Admin | Reviewer | Technician | Reception | M2M Integration |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **System Settings & Users** | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Integration Logs & Retry** | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Audit Logs** | ✓ | Partial | ✗ | ✗ | ✗ |
| **Patient Registration** | ✓ | ✗ | ✗ | ✓ | ✗ |
| **Order Creation** | ✓ | ✗ | ✗ | ✓ | ✗ |
| **Sample Collection** | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Result Entry** | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Verification & Approval** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Report Generation** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Report PDF Download** | ✓ | ✓ | ✓ | ✓ | ✗ |
| **M2M Report Download** | ✗ | ✗ | ✗ | ✗ | ✓ (`X-Integration-Key`) |

---

## 3. Multi-Tenant Boundary Isolation

- All data models (`Patient`, `Order`, `Sample`, `Result`, `Report`, `AuditLog`, `IntegrationDelivery`) enforce `organization_id` foreign key constraints.
- Every API route extracts `organization_id` from the authenticated user token and enforces tenant scoping at repository/database query level.
- Cross-tenant data access attempts return `HTTP 404 Not Found` or `HTTP 403 Forbidden`.

---

## 4. Integration & HMAC Signature Security

- **Outbound Webhooks**: Requests sent to `N8N_WEBHOOK_URL` are signed using HMAC-SHA256 based on `N8N_WEBHOOK_SECRET`.
- **Signature Header**: `X-Vyoma-Signature: sha256=<hex_digest>`.
- **M2M Authentication**: n8n report retrieval requires header `X-Integration-Key` matching server environment secret `N8N_INTEGRATION_KEY`.
- **Secret Isolation**: Secrets (`N8N_WEBHOOK_SECRET`, `N8N_INTEGRATION_KEY`, `JWT_SECRET`) are server-side only and NEVER returned in frontend API responses.

---

## 5. Security Hardening Features

- **Security Headers Middleware**: Sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 1; mode=block`.
- **Error Information Masking**: Database exceptions (`SQLAlchemyError`) and unhandled exceptions are caught by global exception handlers returning sanitized messages without stack traces, database schema details, or raw SQL queries.
- **Audit Logging**: Sensitive operations log IP address, user agent, timestamp, action type, entity ID, and metadata JSON.
