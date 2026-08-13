# VYOMA LABOS — API Overview & Integration Reference

## OpenAPI Documentation

When the FastAPI server is running (`uvicorn app.main:app --port 8000`), interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/api/v1/docs`
- **ReDoc**: `http://localhost:8000/api/v1/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/v1/openapi.json`

---

## Primary API Endpoints

### 1. Health & Probes
- `GET /api/v1/health`: Fast liveness check.
- `GET /api/v1/health/ready`: Readiness check verifying database and storage availability.

### 2. Authentication & Users
- `POST /api/v1/auth/login`: Authenticate staff credentials, return JWT access token.
- `GET /api/v1/users`: List organization staff users (Admin only).
- `POST /api/v1/users`: Create new staff account (Admin only).

### 3. Patients & Tests
- `GET /api/v1/patients`: Paginated, searchable patient registry (Tenant isolated).
- `POST /api/v1/patients`: Create patient record.
- `GET /api/v1/tests`: Test catalog listing.

### 4. Orders & Samples
- `GET /api/v1/orders`: Orders list and search.
- `POST /api/v1/orders`: Create new laboratory order.
- `GET /api/v1/samples`: Samples tracker.
- `POST /api/v1/samples/{id}/collect`: Mark sample collected.
- `POST /api/v1/samples/{id}/start-processing`: Mark sample processing.

### 5. Results & Verification
- `POST /api/v1/samples/results/{id}`: Enter/update result value (Technician).
- `POST /api/v1/samples/{id}/submit-results`: Submit sample results for review.
- `POST /api/v1/verification/{id}/verify`: Pathologist sign-off & verify order (Reviewer).
- `POST /api/v1/verification/{id}/return-correction`: Return result for correction (Reviewer).

### 6. Reports & PDF Storage
- `GET /api/v1/reports`: Generated reports registry.
- `POST /api/v1/reports/generate/{order_id}`: Generate PDF report for verified order.
- `GET /api/v1/reports/{id}/download`: Secure PDF report download.

### 7. Integrations (n8n & M2M)
- `GET /api/v1/integrations`: Integration configuration status and delivery counters (Admin).
- `POST /api/v1/integrations/n8n/test`: Dispatch safe test event (`integration.test`) to n8n (Admin).
- `GET /api/v1/integrations/logs`: Paginated outbound delivery logs (Admin).
- `POST /api/v1/integrations/logs/{id}/retry`: Manually retry failed delivery (Admin).
- `GET /api/v1/integrations/reports/{id}/download`: Machine-to-Machine (M2M) PDF report retrieval requiring `X-Integration-Key` header.
