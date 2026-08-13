import pytest
import datetime
from datetime import timezone, timedelta
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
from app.models.audit import AuditLog
from app.core.security import get_password_hash

# Prevent pytest from collecting Test or TestParameter model as a test suite
Test.__test__ = False
TestParameter.__test__ = False


def _get_auth_headers(client: TestClient, email: str, password: str = "password123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_summary_and_empty_states(client: TestClient, db: Session):
    """
    Test dashboard endpoints on an empty/fresh organization.
    Ensures correct zero values and null TAT metrics.
    """
    # Setup Organization and Admin
    org = Organization(name="Empty Lab Org", code="EMPTYLAB")
    db.add(org)
    db.flush()

    admin = User(
        organization_id=org.id,
        name="Empty Admin",
        email="empty_admin@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active",
    )
    db.add(admin)
    db.commit()

    headers = _get_auth_headers(client, "empty_admin@example.com")

    # 1. Summary API
    res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_patients"] == 0
    assert data["orders_today"] == 0
    assert data["samples_today"] == 0
    assert data["pending_verification"] == 0
    assert data["critical_results"] == 0
    assert data["reports_available"] == 0

    # 2. Workload API
    res = client.get("/api/v1/dashboard/workload?range_type=7days", headers=headers)
    assert res.status_code == 200
    workload = res.json()
    assert workload["range_type"] == "7days"
    assert len(workload["orders"]) == 7
    assert workload["sample_status"]["total_samples"] == 0
    assert workload["priority_workload"]["normal_count"] == 0

    # 3. TAT API
    res = client.get("/api/v1/dashboard/tat", headers=headers)
    assert res.status_code == 200
    tat = res.json()
    assert tat["sample_to_result"]["average_minutes"] is None
    assert tat["sample_to_result"]["sample_count"] == 0
    assert tat["result_to_verification"]["average_minutes"] is None
    assert tat["verification_to_report"]["average_minutes"] is None

    # 4. Critical Results API
    res = client.get("/api/v1/dashboard/critical", headers=headers)
    assert res.status_code == 200
    assert res.json()["total_count"] == 0

    # 5. Verification Queue API
    res = client.get("/api/v1/dashboard/verification-queue", headers=headers)
    assert res.status_code == 200
    assert res.json()["total_count"] == 0

    # 6. Activity API
    res = client.get("/api/v1/dashboard/activity", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json()["activities"], list)

    # 7. Recent Reports API
    res = client.get("/api/v1/dashboard/recent-reports", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["reports"]) == 0


def test_dashboard_real_data_and_tenant_isolation(client: TestClient, db: Session):
    """
    Test dashboard with real records across two organizations to ensure tenant isolation
    and accurate metric aggregation.
    """
    # 1. Setup Organization A with Admin, Reviewer, Technician, Reception
    org_a = Organization(name="Alpha Lab", code="ALPHA")
    db.add(org_a)
    db.flush()

    user_admin_a = User(
        organization_id=org_a.id,
        name="Admin A",
        email="admin_a@alpha.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active",
    )
    user_rev_a = User(
        organization_id=org_a.id,
        name="Reviewer A",
        email="reviewer_a@alpha.com",
        password_hash=get_password_hash("password123"),
        role="reviewer",
        status="active",
    )
    user_tech_a = User(
        organization_id=org_a.id,
        name="Tech A",
        email="tech_a@alpha.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active",
    )
    user_rec_a = User(
        organization_id=org_a.id,
        name="Rec A",
        email="rec_a@alpha.com",
        password_hash=get_password_hash("password123"),
        role="reception",
        status="active",
    )
    db.add_all([user_admin_a, user_rev_a, user_tech_a, user_rec_a])

    # 2. Setup Organization B
    org_b = Organization(name="Beta Lab", code="BETA")
    db.add(org_b)
    db.flush()

    user_admin_b = User(
        organization_id=org_b.id,
        name="Admin B",
        email="admin_b@beta.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active",
    )
    db.add(user_admin_b)
    db.commit()

    # Create Patient, Test, Order, Sample, Result for Org A
    now = datetime.datetime.now(timezone.utc)
    patient_a = Patient(
        organization_id=org_a.id,
        patient_id="PAT-ALPHA-001",
        first_name="Jane",
        last_name="Doe",
        date_of_birth=datetime.date(1990, 5, 15),
        gender="female",
        phone="1234567890",
    )
    db.add(patient_a)
    db.flush()

    test_a = Test(
        organization_id=org_a.id,
        code="GLU",
        name="Fasting Glucose",
        category="Biochemistry",
        price=250.00,
    )
    db.add(test_a)
    db.flush()

    param_a = TestParameter(
        test_id=test_a.id,
        name="Glucose",
        code="GLU",
        unit="mg/dL",
        lower_limit=70.0,
        upper_limit=100.0,
        critical_low=50.0,
        critical_high=400.0,
    )

    db.add(param_a)
    db.flush()

    order_a = Order(
        organization_id=org_a.id,
        patient_id=patient_a.id,
        order_number="ORD-ALPHA-001",
        status="Sample Collected",
        total_amount=250.00,
    )
    db.add(order_a)
    db.flush()

    item_a = OrderItem(
        order_id=order_a.id,
        test_id=test_a.id,
        test_name_snapshot="Fasting Glucose",
        test_code_snapshot="GLU",
        unit_price=250.00,
        total=250.00,
    )
    db.add(item_a)
    db.flush()

    sample_a = Sample(
        organization_id=org_a.id,
        order_id=order_a.id,
        sample_identifier="SMP-ALPHA-001",
        sample_type="Serum",
        collection_status="Processing",
        priority="Urgent",
        collected_at=now - timedelta(hours=2),
    )
    db.add(sample_a)
    db.flush()

    result_a = Result(
        organization_id=org_a.id,
        sample_id=sample_a.id,
        order_item_id=item_a.id,
        test_id=test_a.id,
        parameter_id=param_a.id,
        numeric_value=45.0, # Critical low
        unit="mg/dL",
        reference_low=70.0,
        reference_high=100.0,
        abnormal_flag="LOW",
        critical_flag=True,
        status="Entered",
        entered_at=now - timedelta(hours=1),
    )
    db.add(result_a)

    # Audit log for Org A
    audit_a = AuditLog(
        organization_id=org_a.id,
        user_id=user_tech_a.id,
        action="RESULT_ENTERED",
        entity_type="Result",
        entity_id=str(result_a.id),
        description="Technician entered glucose result",
    )
    db.add(audit_a)
    db.commit()

    # 3. Verify Org A Admin sees metrics
    headers_a = _get_auth_headers(client, "admin_a@alpha.com")
    res_summary = client.get("/api/v1/dashboard/summary", headers=headers_a)
    assert res_summary.status_code == 200
    data_a = res_summary.json()
    assert data_a["total_patients"] == 1
    assert data_a["orders_today"] == 1
    assert data_a["samples_today"] == 1
    assert data_a["samples_processing"] == 1
    assert data_a["samples_urgent"] == 1
    assert data_a["pending_verification"] == 1
    assert data_a["critical_results"] == 1

    # Verify Critical Widget for Org A
    res_crit = client.get("/api/v1/dashboard/critical", headers=headers_a)
    assert res_crit.status_code == 200
    crit_data = res_crit.json()
    assert crit_data["total_count"] == 1
    assert crit_data["critical_results"][0]["sample_identifier"] == "SMP-ALPHA-001"
    assert crit_data["critical_results"][0]["critical_flag"] is True

    # Verify Verification Queue Widget for Org A
    res_vqueue = client.get("/api/v1/dashboard/verification-queue", headers=headers_a)
    assert res_vqueue.status_code == 200
    vq_data = res_vqueue.json()
    assert vq_data["total_count"] == 1
    assert vq_data["queue"][0]["has_critical"] is True
    assert "Fasting Glucose" in vq_data["queue"][0]["tests"]

    # Verify TAT metric for Org A (sample_to_result = ~60 mins)
    res_tat = client.get("/api/v1/dashboard/tat", headers=headers_a)
    assert res_tat.status_code == 200
    tat_data = res_tat.json()
    assert tat_data["sample_to_result"]["sample_count"] == 1
    assert tat_data["sample_to_result"]["average_minutes"] is not None
    assert 55.0 <= tat_data["sample_to_result"]["average_minutes"] <= 65.0

    # 4. TENANT ISOLATION CHECK: Org B Admin should see ZERO metrics for Org A
    headers_b = _get_auth_headers(client, "admin_b@beta.com")
    res_summary_b = client.get("/api/v1/dashboard/summary", headers=headers_b)
    assert res_summary_b.status_code == 200
    data_b = res_summary_b.json()
    assert data_b["total_patients"] == 0
    assert data_b["orders_today"] == 0
    assert data_b["samples_today"] == 0
    assert data_b["critical_results"] == 0
    assert data_b["pending_verification"] == 0

    res_crit_b = client.get("/api/v1/dashboard/critical", headers=headers_b)
    assert res_crit_b.status_code == 200
    assert res_crit_b.json()["total_count"] == 0

    # 5. Role checking: Reviewer, Technician, Reception can all access summary endpoint safely
    headers_rev = _get_auth_headers(client, "reviewer_a@alpha.com")
    res_rev = client.get("/api/v1/dashboard/summary", headers=headers_rev)
    assert res_rev.status_code == 200

    headers_tech = _get_auth_headers(client, "tech_a@alpha.com")
    res_tech = client.get("/api/v1/dashboard/summary", headers=headers_tech)
    assert res_tech.status_code == 200

    headers_rec = _get_auth_headers(client, "rec_a@alpha.com")
    res_rec = client.get("/api/v1/dashboard/summary", headers=headers_rec)
    assert res_rec.status_code == 200
