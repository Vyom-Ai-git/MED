import datetime
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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

# Prevent pytest from collecting the Test model as a test suite
Test.__test__ = False

from app.core.security import get_password_hash
from app.core.config import settings
from app.services.integration import (
    integration_service,
    compute_hmac_signature,
    verify_hmac_signature,
    handle_report_available_event,
)
from app.services.report import report_service


def setup_test_environment(db: Session):
    """Utility helper to seed a clean organization with users across roles, tests, and order."""
    org = Organization(name="Phase 9 Test Lab", code="P9LAB")
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name="Main Branch", code="MAIN")
    db.add(branch)
    db.flush()

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Admin User",
        email="admin_p9@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    reviewer = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Reviewer User",
        email="reviewer_p9@example.com",
        password_hash=get_password_hash("password123"),
        role="reviewer",
        status="active"
    )
    tech = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Tech User",
        email="tech_p9@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active"
    )
    reception = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Reception User",
        email="reception_p9@example.com",
        password_hash=get_password_hash("password123"),
        role="reception",
        status="active"
    )
    db.add_all([admin, reviewer, tech, reception])
    db.flush()

    patient = Patient(
        organization_id=org.id,
        patient_id="PAT-P9-001",
        first_name="Jane",
        last_name="Doe",
        gender="female",
        date_of_birth=datetime.date(1990, 5, 15),
        phone="+919876543210"
    )
    db.add(patient)
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
    db.flush()

    order = Order(
        organization_id=org.id,
        branch_id=branch.id,
        order_number="ORD-P9-00001",
        patient_id=patient.id,
        status="Verified",
        ordering_user_id=admin.id
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        test_id=test_obj.id,
        test_name_snapshot="Complete Blood Count",
        test_code_snapshot="CBC",
        unit_price=500.0,
        total=500.0
    )
    db.add(item)
    db.flush()

    sample = Sample(
        organization_id=org.id,
        branch_id=branch.id,
        order_id=order.id,
        sample_identifier="SMP-P9-00001",
        sample_type="Whole Blood",
        collection_status="Completed",
        collected_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(sample)
    db.flush()

    result = Result(
        organization_id=org.id,
        sample_id=sample.id,
        order_item_id=item.id,
        test_id=test_obj.id,
        parameter_id=param.id,
        raw_value="14.2",
        unit="g/dL",
        status="Verified",
        verified_by=reviewer.id,
        verified_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(result)
    db.commit()

    return {
        "org": org,
        "branch": branch,
        "admin": admin,
        "reviewer": reviewer,
        "tech": tech,
        "reception": reception,
        "patient": patient,
        "order": order,
        "sample": sample,
        "result": result
    }


def get_token(client: TestClient, email: str, password: str = "password123") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_security_signature_computation_and_verification():
    """Test HMAC-SHA256 signature generation and validation logic."""
    secret = "test_webhook_secret_key_123"
    body_bytes = b'{"event_id":"evt_001","event_type":"report.available"}'

    sig = compute_hmac_signature(body_bytes, secret)
    assert sig != ""
    assert len(sig) == 64  # SHA256 hex digest length

    # Verify matching signature succeeds
    assert verify_hmac_signature(body_bytes, secret, sig) is True
    assert verify_hmac_signature(body_bytes, secret, f"sha256={sig}") is True

    # Verify mismatched secret or tampered body fails
    assert verify_hmac_signature(body_bytes, "wrong_secret", sig) is False
    assert verify_hmac_signature(b'{"tampered":true}', secret, sig) is False
    assert verify_hmac_signature(body_bytes, secret, "") is False


def test_m2m_report_download_security(client: TestClient, db: Session):
    """Test Machine-to-Machine (M2M) authentication header enforcement for report retrieval."""
    env = setup_test_environment(db)
    org_id = env["org"].id
    order_id = env["order"].id

    # Set M2M integration key in settings
    with patch.object(settings, "N8N_INTEGRATION_KEY", "secret_m2m_key_999"):
        # Generate report
        report = report_service.generate_report_for_order(db, order_id=order_id, org_id=org_id)

        # 1. Missing X-Integration-Key -> 401 Unauthorized
        res_no_key = client.get(f"/api/v1/integrations/reports/{report.id}/download")
        assert res_no_key.status_code == 401

        # 2. Invalid X-Integration-Key -> 401 Unauthorized
        res_bad_key = client.get(
            f"/api/v1/integrations/reports/{report.id}/download",
            headers={"X-Integration-Key": "wrong_key_123"}
        )
        assert res_bad_key.status_code == 401

        # 3. Valid X-Integration-Key -> 200 OK (PDF response)
        res_valid = client.get(
            f"/api/v1/integrations/reports/{report.id}/download",
            headers={"X-Integration-Key": "secret_m2m_key_999"}
        )
        assert res_valid.status_code == 200
        assert res_valid.headers["content-type"] == "application/pdf"

        # Check M2M audit log
        audit = db.query(AuditLog).filter(
            AuditLog.organization_id == org_id,
            AuditLog.action == "REPORT_DOWNLOADED",
            AuditLog.entity_id == str(report.id)
        ).first()
        assert audit is not None
        assert audit.metadata_json.get("source") == "m2m_n8n_integration"


def test_report_available_e2e_integration_flow(client: TestClient, db: Session):
    """Test full E2E report generation -> report.available event -> webhook dispatch -> IntegrationDelivery Sent."""
    env = setup_test_environment(db)
    org_id = env["org"].id
    order_id = env["order"].id

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status":"received"}'
    mock_client_instance.post.return_value = mock_response
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    mock_db = MagicMock(wraps=db)
    mock_db.close = MagicMock()

    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.test/webhook/report-available"), \
         patch.object(settings, "N8N_WEBHOOK_SECRET", "test_secret_123"), \
         patch("app.services.integration.SessionLocal", return_value=mock_db), \
         patch("app.services.integration.httpx.Client", return_value=mock_client_ctx):

        # Generate report
        report = report_service.generate_report_for_order(db, order_id=order_id, org_id=org_id)

        # Verify n8n webhook POST was called
        assert mock_client_instance.post.called is True

        # Verify IntegrationDelivery record exists in DB
        delivery = db.query(IntegrationDelivery).filter(
            IntegrationDelivery.organization_id == org_id,
            IntegrationDelivery.event_type == "report.available"
        ).first()
        assert delivery is not None
        assert delivery.status == "Sent"
        assert delivery.attempts == 1
        assert delivery.response_status == 200

        # Verify INTEGRATION_SENT audit record
        audit = db.query(AuditLog).filter(
            AuditLog.organization_id == org_id,
            AuditLog.action == "INTEGRATION_SENT"
        ).first()
        assert audit is not None


def test_n8n_outage_resilience(client: TestClient, db: Session):
    """
    Test n8n Outage Resilience:
    If n8n is offline (HTTP 500 or ConnectionError), LabOS MUST still generate report,
    mark report Available, record IntegrationDelivery as Failed, and allow downloading report.
    """
    env = setup_test_environment(db)
    org_id = env["org"].id
    order_id = env["order"].id
    admin_token = get_token(client, env["admin"].email)

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = '{"error":"Internal n8n outage"}'
    mock_client_instance.post.return_value = mock_response
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    mock_db = MagicMock(wraps=db)
    mock_db.close = MagicMock()

    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.test/webhook/down"), \
         patch.object(settings, "N8N_WEBHOOK_SECRET", "test_secret_123"), \
         patch("app.services.integration.SessionLocal", return_value=mock_db), \
         patch("app.services.integration.httpx.Client", return_value=mock_client_ctx):

        # Generate report
        report = report_service.generate_report_for_order(db, order_id=order_id, org_id=org_id)
        report_id = report.id

        # 1. Report is STILL successfully created & Available!
        report_db = db.query(Report).filter(Report.id == report_id).first()
        assert report_db is not None
        assert report_db.status == "Available"

        # 2. Integration delivery status is recorded as Failed
        delivery = db.query(IntegrationDelivery).filter(
            IntegrationDelivery.organization_id == org_id,
            IntegrationDelivery.event_type == "report.available"
        ).first()
        assert delivery is not None
        assert delivery.status == "Failed"
        assert delivery.response_status == 500

        # 3. Report is STILL fully downloadable in LabOS UI/API
        download_res = client.get(
            f"/api/v1/reports/{report_id}/download",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/pdf"


def test_idempotency_duplicate_event_handling(client: TestClient, db: Session):
    """Test idempotency: duplicate event dispatch with same event_id is skipped if already Sent."""
    env = setup_test_environment(db)
    org_id = env["org"].id

    mock_client_instance = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client_instance.post.return_value = mock_resp
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.test/webhook"), \
         patch("app.services.integration.httpx.Client", return_value=mock_client_ctx):

        event_id = "evt_fixed_idempotency_test"
        payload = {"report_id": 1, "order_id": 1, "patient_id": 1}

        # First dispatch
        del1 = integration_service.dispatch_event(
            db, org_id=org_id, event_type="report.available", payload_data=payload, event_id_override=event_id
        )
        assert del1.status == "Sent"
        assert mock_client_instance.post.call_count == 1

        # Second dispatch with SAME event_id
        del2 = integration_service.dispatch_event(
            db, org_id=org_id, event_type="report.available", payload_data=payload, event_id_override=event_id
        )
        assert del2.status == "Sent"
        # Verify HTTP post was NOT called a second time due to idempotency guard
        assert mock_client_instance.post.call_count == 1


def test_admin_manual_retry(client: TestClient, db: Session):
    """Test Admin manual retry capability for a failed delivery."""
    env = setup_test_environment(db)
    org_id = env["org"].id
    admin_token = get_token(client, env["admin"].email)

    # Create a failed delivery record
    failed_delivery = IntegrationDelivery(
        organization_id=org_id,
        event_id="evt_failed_001",
        event_type="report.available",
        destination="https://n8n.test/webhook",
        status="Failed",
        attempts=3,
        response_status=500,
        error_message="HTTP 500: Server error",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(failed_delivery)
    db.commit()

    mock_client_instance = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client_instance.post.return_value = mock_resp
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.test/webhook"), \
         patch("app.services.integration.httpx.Client", return_value=mock_client_ctx):

        # Trigger manual retry via Admin endpoint
        retry_res = client.post(
            f"/api/v1/integrations/logs/{failed_delivery.id}/retry",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert retry_res.status_code == 200
        assert retry_res.json()["status"] == "Sent"


def test_rbac_integration_access(client: TestClient, db: Session):
    """Test RBAC: Admin allowed, non-admin roles (Reviewer, Tech, Reception) forbidden (403)."""
    env = setup_test_environment(db)

    admin_token = get_token(client, env["admin"].email)
    reviewer_token = get_token(client, env["reviewer"].email)
    tech_token = get_token(client, env["tech"].email)
    reception_token = get_token(client, env["reception"].email)

    # Admin -> 200 OK
    res_admin = client.get("/api/v1/integrations", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200

    # Non-Admin roles -> 403 Forbidden
    for t_name, token in [("Reviewer", reviewer_token), ("Technician", tech_token), ("Reception", reception_token)]:
        res = client.get("/api/v1/integrations", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, f"Expected 403 for role {t_name}, got {res.status_code}"

        res_test = client.post("/api/v1/integrations/n8n/test", headers={"Authorization": f"Bearer {token}"})
        assert res_test.status_code == 403

        res_logs = client.get("/api/v1/integrations/logs", headers={"Authorization": f"Bearer {token}"})
        assert res_logs.status_code == 403


def test_tenant_isolation_integration_logs(client: TestClient, db: Session):
    """Test tenant boundary isolation for integration logs and retries."""
    env1 = setup_test_environment(db)

    # Create Org 2 & Admin 2
    org2 = Organization(name="Tenant 2 Lab", code="TEN2")
    db.add(org2)
    db.flush()

    admin2 = User(
        organization_id=org2.id,
        name="Admin Org 2",
        email="admin_org2@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    db.add(admin2)
    db.commit()

    token1 = get_token(client, env1["admin"].email)
    token2 = get_token(client, admin2.email)

    # Create delivery record in Org 1
    del1 = IntegrationDelivery(
        organization_id=env1["org"].id,
        event_id="evt_org1_001",
        event_type="report.available",
        destination="https://n8n.test/webhook",
        status="Failed",
        attempts=1,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(del1)
    db.commit()

    # Admin 2 attempts to retry Org 1 delivery -> 404 Not Found (isolated)
    retry_cross = client.post(
        f"/api/v1/integrations/logs/{del1.id}/retry",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert retry_cross.status_code == 404

    # Admin 2 gets logs -> Org 1 logs are excluded
    logs_res = client.get("/api/v1/integrations/logs", headers={"Authorization": f"Bearer {token2}"})
    assert logs_res.status_code == 200
    assert logs_res.json()["total"] == 0
