import datetime
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pypdf import PdfReader

from app.models.organization import Organization
from app.models.branch import Branch
from app.models.user import User
from app.models.patient import Patient
from app.models.test import Test, TestParameter
from app.models.order import Order, OrderItem
from app.models.sample import Sample, Result
from app.models.report import Report
from app.models.integration import IntegrationDelivery
from app.models.audit import AuditLog

# Prevent pytest from collecting Test class as test suite
Test.__test__ = False

from app.core.security import get_password_hash
from app.core.config import settings
from app.services.report import report_service
from app.services.storage import storage_service

def setup_e2e_environment(db: Session):
    """Seed clean organization, branch, users, patient, test catalog for master E2E test."""
    org = Organization(name="E2E Master Laboratory", code="E2ELAB")
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name="Central E2E Branch", code="E2E1")
    db.add(branch)
    db.flush()

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="System Admin",
        email="admin_e2e@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    reviewer = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Pathologist Reviewer",
        email="reviewer_e2e@example.com",
        password_hash=get_password_hash("password123"),
        role="reviewer",
        status="active"
    )
    tech = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Lab Technician",
        email="tech_e2e@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active"
    )
    reception = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Receptionist Desk",
        email="reception_e2e@example.com",
        password_hash=get_password_hash("password123"),
        role="reception",
        status="active"
    )
    db.add_all([admin, reviewer, tech, reception])
    db.flush()

    test_obj = Test(
        organization_id=org.id,
        code="CBC",
        name="Complete Blood Count",
        category="Hematology",
        price=500.0,
        status="active"
    )
    db.add(test_obj)
    db.flush()

    param = TestParameter(
        test_id=test_obj.id,
        name="Hemoglobin",
        code="HGB",
        unit="g/dL",
        lower_limit=12.0,
        upper_limit=16.0,
        display_order=1
    )
    db.add(param)
    db.commit()

    return {
        "org": org,
        "branch": branch,
        "admin": admin,
        "reviewer": reviewer,
        "tech": tech,
        "reception": reception,
        "test": test_obj,
        "parameter": param
    }


def get_auth_headers(client: TestClient, email: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_patient_to_report_and_integration_e2e(client: TestClient, db: Session):
    """
    Master Acceptance Test:
    Patient -> Order -> Sample -> Result Entry -> Verification -> Report Generation -> PDF Text QA -> Audit -> n8n Integration Delivery
    """
    env = setup_e2e_environment(db)
    org_id = env["org"].id

    reception_headers = get_auth_headers(client, env["reception"].email)
    tech_headers = get_auth_headers(client, env["tech"].email)
    reviewer_headers = get_auth_headers(client, env["reviewer"].email)
    admin_headers = get_auth_headers(client, env["admin"].email)

    # 1. Reception Registers Patient
    pat_res = client.post("/api/v1/patients", json={
        "organization_id": org_id,
        "first_name": "Eleanor",
        "last_name": "Vance",
        "gender": "female",
        "date_of_birth": "1994-08-20",
        "phone": "+919811122233",
        "email": "eleanor@example.com"
    }, headers=reception_headers)
    assert pat_res.status_code == 201
    patient_id = pat_res.json()["id"]

    # 2. Reception Creates Test Order
    order_res = client.post("/api/v1/orders", json={
        "patient_id": patient_id,
        "selected_test_ids": [env["test"].id],
        "notes": "Routine checkup"
    }, headers=reception_headers)
    assert order_res.status_code == 201
    order_data = order_res.json()
    order_id = order_data["id"]
    order_number = order_data["order_number"]

    # 3. Technician Registers & Collects Sample
    sample_res = client.post("/api/v1/samples", json={
        "order_id": order_id,
        "sample_type": "Whole Blood",
        "priority": "Normal"
    }, headers=tech_headers)
    assert sample_res.status_code == 201
    sample_id = sample_res.json()["id"]

    collect_res = client.patch(f"/api/v1/samples/{sample_id}/status", json={"status": "Collected"}, headers=tech_headers)
    assert collect_res.status_code == 200

    # 4. Technician Starts Processing & Enters Results
    proc_res = client.patch(f"/api/v1/samples/{sample_id}/status", json={"status": "Processing"}, headers=tech_headers)
    assert proc_res.status_code == 200

    order_item_id = order_data["items"][0]["id"]

    # Submit results for verification
    submit_res = client.post(f"/api/v1/samples/{sample_id}/results/submit", json={
        "results": [
            {
                "order_item_id": order_item_id,
                "test_id": env["test"].id,
                "parameter_id": env["parameter"].id,
                "raw_value": "13.8",
                "notes": "Measured on automated counter"
            }
        ]
    }, headers=tech_headers)
    assert submit_res.status_code == 200

    # 5. Reviewer Verifies Results
    verify_res = client.post(f"/api/v1/verification/{sample_id}/approve", json={
        "reason": "Verified against baseline parameters"
    }, headers=reviewer_headers)
    assert verify_res.status_code == 200

    # 6. Admin Generates PDF Report (with n8n webhook mocked)
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status":"received"}'
    mock_client_instance.post.return_value = mock_response
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    mock_db = MagicMock(wraps=db)
    mock_db.close = MagicMock()

    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.test/webhook/e2e"), \
         patch.object(settings, "N8N_WEBHOOK_SECRET", "e2e_secret_key"), \
         patch("app.services.integration.SessionLocal", return_value=mock_db), \
         patch("app.services.integration.httpx.Client", return_value=mock_client_ctx):

        rpt_gen_res = client.post(f"/api/v1/reports/generate/{order_id}", headers=admin_headers)
        assert rpt_gen_res.status_code == 201
        report_data = rpt_gen_res.json()
        report_id = report_data["id"]
        report_number = report_data["report_number"]

        # 7. PDF Storage & Text Extraction QA
        download_res = client.get(f"/api/v1/reports/{report_id}/download", headers=admin_headers)
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/pdf"

        pdf_bytes = download_res.content
        assert len(pdf_bytes) > 0

        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) >= 1

        extracted_text = ""
        for pg in pdf_reader.pages:
            extracted_text += pg.extract_text() or ""

        # Content QA Checks
        assert "Eleanor Vance" in extracted_text or "ELEANOR" in extracted_text.upper()
        assert order_number in extracted_text
        assert report_number in extracted_text
        assert "13.8" in extracted_text
        assert "g/dL" in extracted_text

        # 8. Outbound Integration Verification
        delivery = db.query(IntegrationDelivery).filter(
            IntegrationDelivery.organization_id == org_id,
            IntegrationDelivery.event_type == "report.available"
        ).first()
        assert delivery is not None
        assert delivery.status == "Sent"
        assert delivery.response_status == 200

        # 9. Audit Trail Comprehensive Check
        audits = db.query(AuditLog).filter(AuditLog.organization_id == org_id).all()
        actions = [a.action for a in audits]
        assert "REPORT_DOWNLOADED" in actions
        assert "INTEGRATION_SENT" in actions


def test_correction_workflow_e2e(client: TestClient, db: Session):
    """Test full correction return -> technician edit -> resubmit -> verification pipeline."""
    env = setup_e2e_environment(db)
    tech_headers = get_auth_headers(client, env["tech"].email)
    reviewer_headers = get_auth_headers(client, env["reviewer"].email)
    reception_headers = get_auth_headers(client, env["reception"].email)

    # Setup patient & order
    p_id = client.post("/api/v1/patients", json={
        "organization_id": env["org"].id,
        "first_name": "Marcus", "last_name": "Brody", "gender": "male", "date_of_birth": "1980-01-01", "phone": "+919811122244"
    }, headers=reception_headers).json()["id"]

    o_res = client.post("/api/v1/orders", json={
        "patient_id": p_id, "selected_test_ids": [env["test"].id]
    }, headers=reception_headers).json()
    o_id = o_res["id"]
    order_item_id = o_res["items"][0]["id"]

    s_id = client.post("/api/v1/samples", json={"order_id": o_id, "sample_type": "Whole Blood"}, headers=tech_headers).json()["id"]
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Collected"}, headers=tech_headers)
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Processing"}, headers=tech_headers)

    # Tech enters value 25.0 (unrealistic high)
    client.post(f"/api/v1/samples/{s_id}/results/submit", json={
        "results": [{
            "order_item_id": order_item_id, "test_id": env["test"].id, "parameter_id": env["parameter"].id, "raw_value": "25.0"
        }]
    }, headers=tech_headers)

    # Reviewer returns for correction
    return_res = client.post(f"/api/v1/verification/{s_id}/return", json={
        "reason": "Value 25.0 exceeds plausible physiological range. Please re-run."
    }, headers=reviewer_headers)
    assert return_res.status_code == 200

    # Verify result status is Correction Required
    r_check = client.get(f"/api/v1/samples/{s_id}/results", headers=tech_headers).json()[0]
    assert r_check["status"] == "Correction Required"

    # Tech updates value to 14.0
    client.post(f"/api/v1/samples/{s_id}/results/submit", json={
        "results": [{
            "order_item_id": order_item_id, "test_id": env["test"].id, "parameter_id": env["parameter"].id, "raw_value": "14.0", "notes": "Re-run completed."
        }]
    }, headers=tech_headers)

    # Reviewer approves
    v_res = client.post(f"/api/v1/verification/{s_id}/approve", json={"reason": "Approved after re-run"}, headers=reviewer_headers)
    assert v_res.status_code == 200


def test_result_locking_after_verification(client: TestClient, db: Session):
    """Verify that verified results cannot be altered by a Technician (HTTP 409 Conflict)."""
    env = setup_e2e_environment(db)
    tech_headers = get_auth_headers(client, env["tech"].email)
    reviewer_headers = get_auth_headers(client, env["reviewer"].email)
    reception_headers = get_auth_headers(client, env["reception"].email)

    p_id = client.post("/api/v1/patients", json={
        "organization_id": env["org"].id,
        "first_name": "Locking", "last_name": "Test", "gender": "male", "date_of_birth": "1992-03-12", "phone": "+919811122255"
    }, headers=reception_headers).json()["id"]

    o_res = client.post("/api/v1/orders", json={"patient_id": p_id, "selected_test_ids": [env["test"].id]}, headers=reception_headers).json()
    o_id = o_res["id"]
    order_item_id = o_res["items"][0]["id"]

    s_id = client.post("/api/v1/samples", json={"order_id": o_id, "sample_type": "Whole Blood"}, headers=tech_headers).json()["id"]
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Collected"}, headers=tech_headers)
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Processing"}, headers=tech_headers)

    client.post(f"/api/v1/samples/{s_id}/results/submit", json={
        "results": [{
            "order_item_id": order_item_id, "test_id": env["test"].id, "parameter_id": env["parameter"].id, "raw_value": "15.0"
        }]
    }, headers=tech_headers)
    client.post(f"/api/v1/verification/{s_id}/approve", json={"reason": "Approved"}, headers=reviewer_headers)

    r_id = client.get(f"/api/v1/samples/{s_id}/results", headers=tech_headers).json()[0]["id"]

    # Attempt technician edit on verified result -> 400 or 409 Conflict
    edit_res = client.post(f"/api/v1/samples/{s_id}/results/submit", json={
        "results": [{
            "order_item_id": order_item_id, "test_id": env["test"].id, "parameter_id": env["parameter"].id, "raw_value": "99.0"
        }]
    }, headers=tech_headers)
    assert edit_res.status_code in (400, 409)


def test_report_generation_idempotency(client: TestClient, db: Session):
    """Calling report generation twice on the same verified order returns the existing report."""
    env = setup_e2e_environment(db)
    admin_headers = get_auth_headers(client, env["admin"].email)
    reviewer_headers = get_auth_headers(client, env["reviewer"].email)
    tech_headers = get_auth_headers(client, env["tech"].email)
    reception_headers = get_auth_headers(client, env["reception"].email)

    p_id = client.post("/api/v1/patients", json={
        "organization_id": env["org"].id,
        "first_name": "Idem", "last_name": "Potent", "gender": "female", "date_of_birth": "1995-10-10", "phone": "+919811122266"
    }, headers=reception_headers).json()["id"]

    o_res = client.post("/api/v1/orders", json={"patient_id": p_id, "selected_test_ids": [env["test"].id]}, headers=reception_headers).json()
    o_id = o_res["id"]
    order_item_id = o_res["items"][0]["id"]

    s_id = client.post("/api/v1/samples", json={"order_id": o_id, "sample_type": "Whole Blood"}, headers=tech_headers).json()["id"]
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Collected"}, headers=tech_headers)
    client.patch(f"/api/v1/samples/{s_id}/status", json={"status": "Processing"}, headers=tech_headers)
    client.post(f"/api/v1/samples/{s_id}/results/submit", json={
        "results": [{
            "order_item_id": order_item_id, "test_id": env["test"].id, "parameter_id": env["parameter"].id, "raw_value": "13.5"
        }]
    }, headers=tech_headers)
    client.post(f"/api/v1/verification/{s_id}/approve", json={"reason": "Ok"}, headers=reviewer_headers)

    # First report generation -> 201 Created
    res1 = client.post(f"/api/v1/reports/generate/{o_id}", headers=admin_headers)
    assert res1.status_code == 201
    rpt1_num = res1.json()["report_number"]

    # Second report generation -> returns existing report (201 or 200)
    res2 = client.post(f"/api/v1/reports/generate/{o_id}", headers=admin_headers)
    assert res2.status_code in (200, 201)
    rpt2_num = res2.json()["report_number"]

    assert rpt1_num == rpt2_num


def test_health_and_readiness_probes(client: TestClient):
    """Test GET /api/v1/health and GET /api/v1/health/ready endpoints."""
    h_res = client.get("/api/v1/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    r_res = client.get("/api/v1/health/ready")
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "ready"
