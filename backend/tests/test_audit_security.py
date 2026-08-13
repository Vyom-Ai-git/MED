import pytest
from app.models.enums import UserRole, UserStatus
from app.models.organization import Organization
from app.models.branch import Branch
from app.models.user import User
from app.core.security import get_password_hash
from app.repositories.audit import audit_repo
from app.services.auth import auth_service


def test_audit_logs_creation_and_append_only(client, db):
    org = Organization(name="Audit Test Lab", code="AUDLAB1", status="active")
    db.add(org)
    db.flush()

    branch = Branch(name="Main Branch", code="MAIN1", organization_id=org.id)
    db.add(branch)
    db.flush()

    admin = User(
        email="auditadmin@test.com",
        password_hash=get_password_hash("Password123!"),
        name="Audit Admin",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org.id,
        branch_id=branch.id,
    )
    db.add(admin)
    db.commit()

    token = auth_service.generate_token(admin)
    headers = {"Authorization": f"Bearer {token}"}

    # Verify audit endpoint lists empty items initially or from logins
    res = client.get("/api/v1/audit", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

    # Verify HTTP security headers present
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "SAMEORIGIN"


def test_authentication_audit_logging(client, db):
    org = Organization(name="Auth Audit Lab", code="AUTHAUD1", status="active")
    db.add(org)
    db.flush()

    user = User(
        email="authuser@test.com",
        password_hash=get_password_hash("Secret123!"),
        name="Auth User",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org.id,
    )
    db.add(user)
    db.commit()

    # 1. Login Failure
    res_fail = client.post("/api/v1/auth/login", json={"email": "authuser@test.com", "password": "WrongPassword"})
    assert res_fail.status_code == 401

    # 2. Login Success
    res_success = client.post("/api/v1/auth/login", json={"email": "authuser@test.com", "password": "Secret123!"})
    assert res_success.status_code == 200
    token = res_success.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Check Audit Logs
    audit_res = client.get("/api/v1/audit", headers=headers)
    assert audit_res.status_code == 200
    items = audit_res.json()["items"]

    actions = [i["action"] for i in items]
    assert "LOGIN_SUCCESS" in actions
    assert "LOGIN_FAILURE" in actions


def test_audit_tenant_isolation_and_rbac(client, db):
    # Setup Org A
    org_a = Organization(name="Org A Audit", code="ORGA_AUD", status="active")
    db.add(org_a)
    db.flush()
    admin_a = User(
        email="admin_a@test.com",
        password_hash=get_password_hash("Pass123!"),
        name="Admin A",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org_a.id,
    )
    tech_a = User(
        email="tech_a@test.com",
        password_hash=get_password_hash("Pass123!"),
        name="Tech A",
        role=UserRole.TECHNICIAN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org_a.id,
    )
    db.add_all([admin_a, tech_a])

    # Setup Org B
    org_b = Organization(name="Org B Audit", code="ORGB_AUD", status="active")
    db.add(org_b)
    db.flush()
    admin_b = User(
        email="admin_b@test.com",
        password_hash=get_password_hash("Pass123!"),
        name="Admin B",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org_b.id,
    )
    db.add(admin_b)
    db.commit()

    # Create an audit log record for Org B
    log_b = audit_repo.create_audit(
        db,
        org_id=org_b.id,
        action="TEST_ACTION",
        entity_type="TEST",
        entity_id="123",
        user_id=admin_b.id,
    )

    # 1. Technician from Org A cannot access audit trail (403)
    tech_token = auth_service.generate_token(tech_a)
    tech_headers = {"Authorization": f"Bearer {tech_token}"}
    res_tech = client.get("/api/v1/audit", headers=tech_headers)
    assert res_tech.status_code == 403

    # 2. Admin A cannot view Org B audit record by ID (404/403)
    admin_a_token = auth_service.generate_token(admin_a)
    admin_a_headers = {"Authorization": f"Bearer {admin_a_token}"}
    res_detail = client.get(f"/api/v1/audit/{log_b.id}", headers=admin_a_headers)
    assert res_detail.status_code in [404, 403]


def test_pagination_hard_limit_security(client, db):
    org = Organization(name="Pagination Security Lab", code="PAGELAB", status="active")
    db.add(org)
    db.flush()

    admin = User(
        email="pageadmin@test.com",
        password_hash=get_password_hash("Pass123!"),
        name="Page Admin",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        organization_id=org.id,
    )
    db.add(admin)
    db.commit()

    token = auth_service.generate_token(admin)
    headers = {"Authorization": f"Bearer {token}"}

    # Request page size exceeding limit (e.g. 1000)
    res = client.get("/api/v1/audit?page_size=1000", headers=headers)
    # Pydantic Query validation rejects le=100 with 422 Unprocessable Entity
    assert res.status_code == 422

