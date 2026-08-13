import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.organization import Organization
from app.models.branch import Branch
from app.models.user import User
from app.models.patient import Patient
from app.models.test import Test, TestParameter

# Prevent pytest from collecting the Test model as a test suite
Test.__test__ = False

from app.core.security import get_password_hash

def test_health_check(client: TestClient):
    """
    Test that the health endpoint returns status healthy.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_and_protected_routes(client: TestClient, db: Session):
    """
    Test authentication flow and access control.
    """
    # 1. Create a dummy organization and admin user
    org = Organization(name="Test Labs", code="TESTLAB")
    db.add(org)
    db.flush()
    
    branch = Branch(organization_id=org.id, name="Test Branch", code="TBR")
    db.add(branch)
    db.flush()
    
    user = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Test Admin",
        email="test_admin@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    db.add(user)
    db.commit()

    # 2. Try to access protected route without token (Should fail 401)
    response = client.get("/api/v1/users")
    assert response.status_code == 401

    # 3. Login with invalid password
    login_response = client.post("/api/v1/auth/login", json={
        "email": "test_admin@example.com",
        "password": "wrongpassword"
    })
    assert login_response.status_code == 401

    # 4. Login with valid password
    login_response = client.post("/api/v1/auth/login", json={
        "email": "test_admin@example.com",
        "password": "password123"
    })
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    token = data["access_token"]
    
    # 5. Access protected route with valid token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) == 1
    assert users_list[0]["email"] == "test_admin@example.com"


def test_organization_isolation(client: TestClient, db: Session):
    """
    Test multi-tenant isolation. Users from Org A must not see patients from Org B.
    """
    # Create Org A
    org_a = Organization(name="Org A Labs", code="ORGA")
    db.add(org_a)
    db.flush()
    branch_a = Branch(organization_id=org_a.id, name="Branch A", code="BRA")
    db.add(branch_a)
    db.flush()
    user_a = User(
        organization_id=org_a.id,
        branch_id=branch_a.id,
        name="User A",
        email="usera@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    db.add(user_a)
    patient_a = Patient(
        organization_id=org_a.id,
        patient_id="PAT-A",
        first_name="Alice",
        last_name="Patient",
        date_of_birth=datetime.date(1995, 1, 1),
        gender="female",
        phone="1111111111",
        consent_operational=True,
        consent_promotional=False
    )
    db.add(patient_a)

    # Create Org B
    org_b = Organization(name="Org B Labs", code="ORGB")
    db.add(org_b)
    db.flush()
    branch_b = Branch(organization_id=org_b.id, name="Branch B", code="BRB")
    db.add(branch_b)
    db.flush()
    user_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        name="User B",
        email="userb@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    db.add(user_b)
    patient_b = Patient(
        organization_id=org_b.id,
        patient_id="PAT-B",
        first_name="Bob",
        last_name="Patient",
        date_of_birth=datetime.date(1995, 1, 2),
        gender="male",
        phone="2222222222",
        consent_operational=True,
        consent_promotional=False
    )
    db.add(patient_b)
    
    db.commit()

    # Login as User A
    login_a = client.post("/api/v1/auth/login", json={"email": "usera@example.com", "password": "password123"})
    token_a = login_a.json()["access_token"]

    # Login as User B
    login_b = client.post("/api/v1/auth/login", json={"email": "userb@example.com", "password": "password123"})
    token_b = login_b.json()["access_token"]

    # Query patients as User A (should only see Alice)
    res_a = client.get("/api/v1/patients", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    patients_a = res_a.json()["items"]
    assert len(patients_a) == 1
    assert patients_a[0]["first_name"] == "Alice"

    # Query patients as User B (should only see Bob)
    res_b = client.get("/api/v1/patients", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    patients_b = res_b.json()["items"]
    assert len(patients_b) == 1
    assert patients_b[0]["first_name"] == "Bob"


def test_inactive_user_login(client: TestClient, db: Session):
    """
    Verify that inactive users cannot log in.
    """
    org = Organization(name="Inactive Lab", code="INACTIVE")
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        name="Inactive User",
        email="inactive@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="inactive"
    )
    db.add(user)
    db.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": "inactive@example.com",
        "password": "password123"
    })
    assert response.status_code == 401


def test_rbac_protection(client: TestClient, db: Session):
    """
    Verify that non-admins cannot manage users (403 Forbidden).
    """
    org = Organization(name="RBAC Lab", code="RBAC")
    db.add(org)
    db.flush()
    # Create technician user
    user = User(
        organization_id=org.id,
        name="Tech User",
        email="tech@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active"
    )
    db.add(user)
    db.commit()

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": "tech@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /users list (technician is denied, admin required)
    res = client.get("/api/v1/users", headers=headers)
    assert res.status_code == 403

    # Attempt to create patient as technician (technician is denied, admin/reception required)
    res_pat = client.post("/api/v1/patients", json={
        "first_name": "Test",
        "last_name": "Pat",
        "date_of_birth": "2000-01-01",
        "gender": "male",
        "phone": "9999999999",
        "organization_id": org.id
    }, headers=headers)
    assert res_pat.status_code == 403


def test_user_management_crud(client: TestClient, db: Session):
    """
    Test user CRUD actions (create, duplicate email checks, update, deactivate).
    """
    org = Organization(name="CRUD Lab", code="CRUD")
    db.add(org)
    db.flush()
    # Create admin
    admin = User(
        organization_id=org.id,
        name="Admin",
        email="admin_crud@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    db.add(admin)
    db.commit()

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": "admin_crud@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a user
    create_res = client.post("/api/v1/users", json={
        "name": "New Tech",
        "email": "newtech@example.com",
        "phone": "1234567890",
        "role": "technician",
        "password": "password123",
        "organization_id": org.id
    }, headers=headers)
    assert create_res.status_code == 201
    user_data = create_res.json()
    assert user_data["name"] == "New Tech"
    assert "password_hash" not in user_data  # Verify password_hash is never exposed
    assert "password" not in user_data

    # 2. Check duplicate email validation
    dup_res = client.post("/api/v1/users", json={
        "name": "Another Tech",
        "email": "newtech@example.com",
        "role": "technician",
        "password": "password123",
        "organization_id": org.id
    }, headers=headers)
    assert dup_res.status_code == 400

    # 3. Update user
    user_id = user_data["id"]
    update_res = client.patch(f"/api/v1/users/{user_id}", json={
        "name": "Updated Tech Name",
        "role": "reviewer"
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Tech Name"
    assert update_res.json()["role"] == "reviewer"

    # 4. Deactivate user
    deact_res = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "inactive"


def test_patient_management_endpoints(client: TestClient, db: Session):
    """
    Test patient registration, ID generation, duplicate warning triggers, bypasses,
    paginated search, and RBAC controls.
    """
    org = Organization(name="Patient Lab", code="PATLAB")
    db.add(org)
    db.flush()
    
    # 1. Create admin and technician users
    admin = User(
        organization_id=org.id,
        name="Admin User",
        email="admin_pat@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    tech = User(
        organization_id=org.id,
        name="Tech User",
        email="tech_pat@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active"
    )
    db.add_all([admin, tech])
    db.commit()

    # Login as Admin
    login_admin = client.post("/api/v1/auth/login", json={"email": "admin_pat@example.com", "password": "password123"})
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login as Tech
    login_tech = client.post("/api/v1/auth/login", json={"email": "tech_pat@example.com", "password": "password123"})
    tech_token = login_tech.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # 2. Register patient as Admin
    register_payload = {
        "first_name": "Rohan",
        "last_name": "Kumar",
        "date_of_birth": "1994-06-20",
        "gender": "male",
        "phone": "+91 99999 55555",
        "email": "rohan@example.com",
        "referring_provider": "Dr. Verma",
        "consent_operational": True,
        "consent_promotional": False,
        "organization_id": org.id
    }
    
    res = client.post("/api/v1/patients", json=register_payload, headers=admin_headers)
    assert res.status_code == 201
    patient_data = res.json()
    assert patient_data["first_name"] == "Rohan"
    assert "PAT-" in patient_data["patient_id"] # ID generated on backend
    assert patient_data["referring_provider"] == "Dr. Verma"
    assert patient_data["consent_operational"] is True
    assert patient_data["consent_promotional"] is False

    # 3. Attempt to register matching duplicate patient -> Should return 409 Conflict
    res_dup = client.post("/api/v1/patients", json=register_payload, headers=admin_headers)
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"]["message"]
    assert res_dup.json()["detail"]["existing_id"] == patient_data["id"]

    # 4. Force override duplicate check using ignore_duplicate flag
    register_payload["ignore_duplicate"] = True
    res_force = client.post("/api/v1/patients", json=register_payload, headers=admin_headers)
    assert res_force.status_code == 201
    assert res_force.json()["id"] != patient_data["id"]

    # 5. Search patient list (paginated search)
    search_res = client.get("/api/v1/patients?q=Rohan", headers=admin_headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 2
    assert len(search_data["items"]) == 2

    # 6. Tech role check (Technicians should be forbidden from registering or editing patients)
    res_tech_create = client.post("/api/v1/patients", json=register_payload, headers=tech_headers)
    assert res_tech_create.status_code == 403

    patient_id = patient_data["id"]
    res_tech_edit = client.patch(f"/api/v1/patients/{patient_id}", json={"first_name": "Rohan Edit"}, headers=tech_headers)
    assert res_tech_edit.status_code == 403


def test_test_catalog_endpoints(client: TestClient, db: Session):
    """
    Test test creation, parameter mappings (including critical values), paginated search,
    role protections, and catalog updates.
    """
    org = Organization(name="Test Catalog Lab", code="CATLAB")
    db.add(org)
    db.flush()
    
    # Create Admin & Tech users
    admin = User(
        organization_id=org.id,
        name="Admin",
        email="admin_test@example.com",
        password_hash=get_password_hash("password123"),
        role="admin",
        status="active"
    )
    tech = User(
        organization_id=org.id,
        name="Tech",
        email="tech_test@example.com",
        password_hash=get_password_hash("password123"),
        role="technician",
        status="active"
    )
    db.add_all([admin, tech])
    db.commit()

    # Login as Admin
    login_admin = client.post("/api/v1/auth/login", json={"email": "admin_test@example.com", "password": "password123"})
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login as Tech
    login_tech = client.post("/api/v1/auth/login", json={"email": "tech_test@example.com", "password": "password123"})
    tech_token = login_tech.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # 1. Create a Test with parameters
    test_payload = {
        "code": "GLU",
        "name": "Fasting Blood Glucose",
        "category": "Biochemistry",
        "description": "Fasting blood sugar analysis",
        "price": "180.00",
        "organization_id": org.id,
        "parameters": [
            {
                "name": "Glucose Value",
                "code": "FBS",
                "unit": "mg/dL",
                "data_type": "numeric",
                "reference_range": "70 - 100",
                "lower_limit": 70.0,
                "upper_limit": 100.0,
                "critical_low": 50.0,
                "critical_high": 250.0,
                "display_order": 1
            }
        ]
    }
    
    res = client.post("/api/v1/tests", json=test_payload, headers=admin_headers)
    assert res.status_code == 201
    test_data = res.json()
    assert test_data["name"] == "Fasting Blood Glucose"
    assert len(test_data["parameters"]) == 1
    assert test_data["parameters"][0]["critical_low"] == 50.0
    assert test_data["parameters"][0]["critical_high"] == 250.0

    # 2. Update catalog item and replace parameters
    test_id = test_data["id"]
    update_payload = {
        "price": "200.00",
        "parameters": [
            {
                "name": "Glucose Value Updated",
                "code": "FBS_UPD",
                "unit": "mg/dL",
                "data_type": "numeric",
                "reference_range": "70 - 110",
                "lower_limit": 70.0,
                "upper_limit": 110.0,
                "critical_low": 45.0,
                "critical_high": 300.0,
                "display_order": 1
            }
        ]
    }
    
    res_update = client.patch(f"/api/v1/tests/{test_id}", json=update_payload, headers=admin_headers)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert float(updated_data["price"]) == 200.0
    assert len(updated_data["parameters"]) == 1
    assert updated_data["parameters"][0]["name"] == "Glucose Value Updated"
    assert updated_data["parameters"][0]["code"] == "FBS_UPD"

    # 3. Technician role check (forbidden from creating or modifying tests)
    res_tech_create = client.post("/api/v1/tests", json=test_payload, headers=tech_headers)
    assert res_tech_create.status_code == 403

    res_tech_edit = client.patch(f"/api/v1/tests/{test_id}", json={"price": "250.00"}, headers=tech_headers)
    assert res_tech_edit.status_code == 403


# ── Phase 3: Order Management Tests ──────────────────────────────────────────

_fixture_counter = 0

def _setup_order_fixtures(client: TestClient, db: Session):
    """
    Create org, branch, admin, reception, technician, reviewer users, one patient, and tests.
    Uses a global counter to ensure unique org codes / emails / patient IDs across calls.
    """
    global _fixture_counter
    _fixture_counter += 1
    idx = _fixture_counter

    import datetime as dt
    from decimal import Decimal
    from app.core.security import get_password_hash

    org = Organization(name=f"Order Test Lab {idx}", code=f"ORDLAB{idx}")
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name=f"Order Branch {idx}", code=f"OBR{idx}")
    db.add(branch)
    db.flush()

    admin = User(organization_id=org.id, branch_id=branch.id, name=f"Order Admin {idx}",
                 email=f"order_admin_{idx}@testlab.com", password_hash=get_password_hash("pass123"),
                 role="admin", status="active")
    reception = User(organization_id=org.id, branch_id=branch.id, name=f"Order Reception {idx}",
                     email=f"order_reception_{idx}@testlab.com", password_hash=get_password_hash("pass123"),
                     role="reception", status="active")
    technician = User(organization_id=org.id, branch_id=branch.id, name=f"Order Tech {idx}",
                      email=f"order_tech_{idx}@testlab.com", password_hash=get_password_hash("pass123"),
                      role="technician", status="active")
    reviewer = User(organization_id=org.id, branch_id=branch.id, name=f"Order Reviewer {idx}",
                    email=f"order_reviewer_{idx}@testlab.com", password_hash=get_password_hash("pass123"),
                    role="reviewer", status="active")
    db.add_all([admin, reception, technician, reviewer])
    db.flush()

    patient = Patient(
        organization_id=org.id,
        patient_id=f"PAT-ORD-TEST-{idx:04d}",
        first_name="Order", last_name="Patient",
        date_of_birth=dt.date(1990, 1, 1),
        gender="male", phone=f"999000{idx:04d}",
    )
    db.add(patient)
    db.flush()

    test_cbc = Test(organization_id=org.id, code=f"CBC_ORD_{idx}", name="CBC Order Test",
                    category="Hematology", price=Decimal("500.00"), status="active")
    test_lipid = Test(organization_id=org.id, code=f"LIP_ORD_{idx}", name="Lipid Order Test",
                      category="Biochemistry", price=Decimal("800.00"), status="active")
    test_inactive = Test(organization_id=org.id, code=f"INA_ORD_{idx}", name="Inactive Test",
                         category="Other", price=Decimal("100.00"), status="inactive")
    db.add_all([test_cbc, test_lipid, test_inactive])
    db.flush()

    param_hb = TestParameter(test_id=test_cbc.id, name="Hemoglobin", code="HB", unit="g/dL", data_type="numeric", lower_limit=Decimal("12.00"), upper_limit=Decimal("16.00"), critical_low=Decimal("7.00"), critical_high=Decimal("20.00"), display_order=1)
    param_wbc = TestParameter(test_id=test_cbc.id, name="WBC Count", code="WBC", unit="10^3/uL", data_type="numeric", lower_limit=Decimal("4.00"), upper_limit=Decimal("11.00"), display_order=2)
    db.add_all([param_hb, param_wbc])
    db.commit()

    # Get auth headers
    def get_headers(email):
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "pass123"})
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return {
        "org": org, "branch": branch, "patient": patient,
        "admin": admin, "reception": reception, "tech": technician, "reviewer": reviewer,
        "test_cbc": test_cbc, "test_lipid": test_lipid, "test_inactive": test_inactive,
        "param_hb": param_hb, "param_wbc": param_wbc,
        "admin_headers": get_headers(f"order_admin_{idx}@testlab.com"),
        "reception_headers": get_headers(f"order_reception_{idx}@testlab.com"),
        "tech_headers": get_headers(f"order_tech_{idx}@testlab.com"),
        "reviewer_headers": get_headers(f"order_reviewer_{idx}@testlab.com"),
    }


def test_order_single_test_creation(client: TestClient, db: Session):
    """Valid single-test order — all values must be server-calculated."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0,
        "tax": 0.0,
        "payment_status": "Pending",
        "notes": "Single test order",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_number"].startswith("ORD-")
    assert float(data["subtotal"]) == 500.0
    assert float(data["total_amount"]) == 500.0
    assert float(data["discount"]) == 0.0
    assert data["status"] == "Pending"
    assert data["payment_status"] == "Pending"
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["test_name_snapshot"] == "CBC Order Test"
    assert item["test_code_snapshot"] == f"CBC_ORD_{f['org'].id}" or item["test_code_snapshot"].startswith("CBC_ORD_")
    assert float(item["unit_price"]) == 500.0
    assert item["quantity"] == 1
    assert float(item["total"]) == 500.0
    assert data["patient"]["first_name"] == "Order"


def test_order_multi_test_creation(client: TestClient, db: Session):
    """Valid multi-test order — subtotal must be sum of all selected tests."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id, f["test_lipid"].id],
        "discount": 100.0,
        "tax": 0.0,
        "payment_status": "Paid",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["subtotal"]) == 1300.0   # 500 + 800
    assert float(data["discount"]) == 100.0
    assert float(data["total_amount"]) == 1200.0  # 1300 - 100
    assert data["payment_status"] == "Paid"
    assert len(data["items"]) == 2


def test_order_reception_can_create(client: TestClient, db: Session):
    """Reception role must be allowed to create orders."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["reception_headers"])
    assert resp.status_code == 201


def test_order_technician_cannot_create(client: TestClient, db: Session):
    """Technician must NOT be able to create orders."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["tech_headers"])
    assert resp.status_code == 403


def test_order_reviewer_cannot_create(client: TestClient, db: Session):
    """Reviewer must NOT be able to create orders."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["reviewer_headers"])
    assert resp.status_code == 403


def test_order_patient_not_found(client: TestClient, db: Session):
    """Non-existent patient must return 400."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": 999999,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 400


def test_order_test_not_found(client: TestClient, db: Session):
    """Non-existent test ID must return 400."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [999999],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 400


def test_order_inactive_test_rejected(client: TestClient, db: Session):
    """Inactive test must be rejected with 400."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_inactive"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 400
    assert "not active" in resp.json()["detail"].lower()


def test_order_no_tests_rejected(client: TestClient, db: Session):
    """Empty test list must return 422 (Pydantic min_length=1)."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 422


def test_order_discount_exceeds_subtotal_rejected(client: TestClient, db: Session):
    """Discount greater than subtotal must be rejected."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 999.0,  # > 500 subtotal
        "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 400
    assert "discount" in resp.json()["detail"].lower()


def test_order_tenant_isolation(client: TestClient, db: Session):
    """Admin from org A must not be able to see orders from org B."""
    f = _setup_order_fixtures(client, db)
    # Create order under org A
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    # Create a second org with its own admin — use counter for uniqueness
    other_idx = _fixture_counter + 1000  # offset to avoid collision with fixture counter
    org2 = Organization(name=f"Other Lab {other_idx}", code=f"OTHERLAB{other_idx}")
    db.add(org2)
    db.flush()
    branch2 = Branch(organization_id=org2.id, name=f"Other Branch {other_idx}", code=f"OBR2_{other_idx}")
    db.add(branch2)
    db.flush()
    from app.core.security import get_password_hash
    admin2 = User(organization_id=org2.id, branch_id=branch2.id, name=f"Other Admin {other_idx}",
                  email=f"other_admin_{other_idx}@testlab.com", password_hash=get_password_hash("pass123"),
                  role="admin", status="active")
    db.add(admin2)
    db.commit()
    resp2 = client.post("/api/v1/auth/login", json={"email": f"other_admin_{other_idx}@testlab.com", "password": "pass123"})
    other_headers = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

    # Attempt to get org A order from org B admin — must 404
    get_resp = client.get(f"/api/v1/orders/{order_id}", headers=other_headers)
    assert get_resp.status_code == 404



def test_order_cancel_pending(client: TestClient, db: Session):
    """A Pending order can be cancelled by admin."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    cancel_resp = client.patch(f"/api/v1/orders/{order_id}/cancel", headers=f["admin_headers"])
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "Cancelled"


def test_order_technician_cannot_cancel(client: TestClient, db: Session):
    """Technician cannot cancel an order."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    order_id = create_resp.json()["id"]

    cancel_resp = client.patch(f"/api/v1/orders/{order_id}/cancel", headers=f["tech_headers"])
    assert cancel_resp.status_code == 403


def test_order_payment_update(client: TestClient, db: Session):
    """Payment status can be updated to Paid by admin."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    order_id = create_resp.json()["id"]

    pay_resp = client.patch(f"/api/v1/orders/{order_id}/payment",
                            json={"payment_status": "Paid"}, headers=f["admin_headers"])
    assert pay_resp.status_code == 200
    assert pay_resp.json()["payment_status"] == "Paid"


def test_order_invalid_payment_status(client: TestClient, db: Session):
    """Invalid payment_status must be rejected."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    order_id = create_resp.json()["id"]

    pay_resp = client.patch(f"/api/v1/orders/{order_id}/payment",
                            json={"payment_status": "InvalidStatus"}, headers=f["admin_headers"])
    assert pay_resp.status_code == 400


def test_order_state_machine_valid_transition(client: TestClient, db: Session):
    """Valid Pending → Cancelled state transition must succeed."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    order_id = create_resp.json()["id"]

    tr_resp = client.put(f"/api/v1/orders/{order_id}/status",
                         json={"status": "Cancelled"}, headers=f["admin_headers"])
    assert tr_resp.status_code == 200
    assert tr_resp.json()["status"] == "Cancelled"


def test_order_state_machine_invalid_skip(client: TestClient, db: Session):
    """Skipping states must be rejected (Pending → Published is invalid)."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    create_resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
    order_id = create_resp.json()["id"]

    tr_resp = client.put(f"/api/v1/orders/{order_id}/status",
                         json={"status": "Published"}, headers=f["admin_headers"])
    assert tr_resp.status_code == 400


def test_order_unique_numbers(client: TestClient, db: Session):
    """Multiple orders must have unique order numbers."""
    f = _setup_order_fixtures(client, db)
    order_numbers = set()
    for _ in range(3):
        payload = {
            "patient_id": f["patient"].id,
            "selected_test_ids": [f["test_cbc"].id],
            "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
        }
        resp = client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])
        assert resp.status_code == 201
        order_numbers.add(resp.json()["order_number"])
    assert len(order_numbers) == 3, "All order numbers must be unique"


def test_order_search_and_pagination(client: TestClient, db: Session):
    """Order registry must support pagination and status filter."""
    f = _setup_order_fixtures(client, db)
    # Create 2 orders
    for _ in range(2):
        payload = {
            "patient_id": f["patient"].id,
            "selected_test_ids": [f["test_cbc"].id],
            "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
        }
        client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])

    resp = client.get("/api/v1/orders?page=1&page_size=10", headers=f["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2

    # Filter by status
    resp_filtered = client.get("/api/v1/orders?status=Pending", headers=f["admin_headers"])
    assert resp_filtered.status_code == 200
    for order in resp_filtered.json()["items"]:
        assert order["status"] == "Pending"


def test_patient_orders_endpoint(client: TestClient, db: Session):
    """Patient orders endpoint must return orders filtered by patient."""
    f = _setup_order_fixtures(client, db)
    payload = {
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }
    client.post("/api/v1/orders", json=payload, headers=f["admin_headers"])

    resp = client.get(f"/api/v1/orders/patient/{f['patient'].id}", headers=f["admin_headers"])
    assert resp.status_code == 200
    orders = resp.json()
    assert len(orders) >= 1
    for order in orders:
        assert "order_number" in order
        assert "status" in order


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — SAMPLE MANAGEMENT & RESULT ENTRY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_sample_creation_and_identifier(client: TestClient, db: Session):
    """Sample registration creates a unique SMP- identifier linked to order."""
    f = _setup_order_fixtures(client, db)
    # Create order first
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    order_id = ord_resp.json()["id"]

    # Register sample
    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id,
        "sample_type": "Blood",
        "priority": "Urgent",
        "notes": "Fast track sample"
    }, headers=f["tech_headers"])
    assert smp_resp.status_code == 201
    s_data = smp_resp.json()
    assert s_data["sample_identifier"].startswith("SMP-")
    assert s_data["sample_type"] == "Blood"
    assert s_data["priority"] == "Urgent"
    assert s_data["collection_status"] == "Registered"
    assert s_data["recollection_required"] is False


def test_sample_state_machine(client: TestClient, db: Session):
    """State transition: Registered → Collected → Processing → Completed."""
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id,
        "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    order_id = ord_resp.json()["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Normal"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    # Transition to Collected
    col_resp = client.patch(f"/api/v1/samples/{smp_id}/status", json={"status": "Collected"}, headers=f["tech_headers"])
    assert col_resp.status_code == 200
    assert col_resp.json()["collection_status"] == "Collected"
    assert col_resp.json()["collected_at"] is not None

    # Transition to Processing
    prc_resp = client.patch(f"/api/v1/samples/{smp_id}/status", json={"status": "Processing"}, headers=f["tech_headers"])
    assert prc_resp.status_code == 200
    assert prc_resp.json()["collection_status"] == "Processing"
    assert prc_resp.json()["processing_started_at"] is not None

    # Invalid transition (Processing cannot jump to Registered)
    inv_resp = client.patch(f"/api/v1/samples/{smp_id}/status", json={"status": "Registered"}, headers=f["tech_headers"])
    assert inv_resp.status_code == 400


def test_sample_rejection(client: TestClient, db: Session):
    """Sample rejection marks status Rejected and recollection_required True."""
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    order_id = ord_resp.json()["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Serum", "priority": "Normal"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    rej_resp = client.post(f"/api/v1/samples/{smp_id}/reject", json={
        "rejection_reason": "Hemolyzed specimen"
    }, headers=f["tech_headers"])
    assert rej_resp.status_code == 200
    r_data = rej_resp.json()
    assert r_data["collection_status"] == "Rejected"
    assert r_data["rejection_reason"] == "Hemolyzed specimen"
    assert r_data["recollection_required"] is True


def test_result_draft_and_submission_flags(client: TestClient, db: Session):
    """Save draft -> Submit completed results with LOW/HIGH and CRITICAL flags."""
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    ord_data = ord_resp.json()
    order_id = ord_data["id"]
    order_item_id = ord_data["items"][0]["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Normal"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    # 1. Save partial draft (only HB)
    draft_payload = {
        "results": [
            {
                "parameter_id": f["param_hb"].id,
                "order_item_id": order_item_id,
                "test_id": f["test_cbc"].id,
                "raw_value": "6.5"  # Critical low (< 7.0)
            }
        ]
    }
    d_resp = client.post(f"/api/v1/samples/{smp_id}/results/draft", json=draft_payload, headers=f["tech_headers"])
    assert d_resp.status_code == 200
    d_results = d_resp.json()
    assert len(d_results) == 1
    assert d_results[0]["status"] == "Draft"
    assert d_results[0]["abnormal_flag"] == "LOW"
    assert d_results[0]["critical_flag"] is True

    # 2. Attempt submit without WBC parameter (should fail 400 incomplete)
    sub_fail = client.post(f"/api/v1/samples/{smp_id}/results/submit", json=draft_payload, headers=f["tech_headers"])
    assert sub_fail.status_code == 400
    assert "missing required parameters" in sub_fail.json()["detail"].lower()

    # 3. Submit full results with WBC
    full_payload = {
        "results": [
            {
                "parameter_id": f["param_hb"].id,
                "order_item_id": order_item_id,
                "test_id": f["test_cbc"].id,
                "raw_value": "6.5"
            },
            {
                "parameter_id": f["param_wbc"].id,
                "order_item_id": order_item_id,
                "test_id": f["test_cbc"].id,
                "raw_value": "14.5"  # High (> 11.0)
            }
        ]
    }
    sub_resp = client.post(f"/api/v1/samples/{smp_id}/results/submit", json=full_payload, headers=f["tech_headers"])
    assert sub_resp.status_code == 200
    sub_results = sub_resp.json()
    assert len(sub_results) == 2
    for r in sub_results:
        assert r["status"] == "Entered"
        if r["parameter_id"] == f["param_wbc"].id:
            assert r["abnormal_flag"] == "HIGH"
            assert r["critical_flag"] is False

    # Check sample and order status updated to Completed / Result Entered
    s_check = client.get(f"/api/v1/samples/{smp_id}", headers=f["tech_headers"])
    assert s_check.json()["collection_status"] == "Completed"


def test_result_reception_forbidden(client: TestClient, db: Session):
    """Reception role cannot submit laboratory results."""
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    order_id = ord_resp.json()["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Normal"
    }, headers=f["reception_headers"])
    smp_id = smp_resp.json()["id"]

    # Reception tries to save draft result -> 403
    draft_payload = {"results": []}
    res = client.post(f"/api/v1/samples/{smp_id}/results/draft", json=draft_payload, headers=f["reception_headers"])
    assert res.status_code == 403


def test_verification_workflow_and_rbac(client: TestClient, db: Session):
    """
    Test Phase 5 Verification Queue, Reviewer approval, RBAC authorization,
    auditing, and Order status transition to Verified upon completion.
    """
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    ord_data = ord_resp.json()
    order_id = ord_data["id"]
    order_item_id = ord_data["items"][0]["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Normal"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    full_payload = {
        "results": [
            {"parameter_id": f["param_hb"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "14.2"},
            {"parameter_id": f["param_wbc"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "7.5"}
        ]
    }
    client.post(f"/api/v1/samples/{smp_id}/results/submit", json=full_payload, headers=f["tech_headers"])

    # 1. Technician tries to approve -> 403
    tech_app = client.post(f"/api/v1/verification/{smp_id}/approve", json={"reason": "Self approve"}, headers=f["tech_headers"])
    assert tech_app.status_code == 403

    # 2. Reception tries to access queue -> 403
    rec_queue = client.get("/api/v1/verification", headers=f["reception_headers"])
    assert rec_queue.status_code == 403

    # 3. Reviewer queries queue -> 200
    rev_queue = client.get("/api/v1/verification", headers=f["reviewer_headers"])
    assert rev_queue.status_code == 200
    q_data = rev_queue.json()
    assert q_data["total"] >= 1
    assert q_data["pending_count"] >= 1

    # 4. Reviewer approves results -> 200
    rev_app = client.post(f"/api/v1/verification/{smp_id}/approve", json={"reason": "Clinical review verified"}, headers=f["reviewer_headers"])
    assert rev_app.status_code == 200
    verified_results = rev_app.json()
    assert all(r["status"] == "Verified" for r in verified_results)
    assert verified_results[0]["verified_by"] == f["reviewer"].id

    # 5. Check order status transitioned to Verified
    order_chk = client.get(f"/api/v1/orders/{order_id}", headers=f["reviewer_headers"])
    assert order_chk.json()["status"] == "Verified"


def test_result_locking_and_correction_flow(client: TestClient, db: Session):
    """
    Test returning results for correction, editing by technician, resubmitting,
    and enforcing locking once verified.
    """
    f = _setup_order_fixtures(client, db)
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    ord_data = ord_resp.json()
    order_id = ord_data["id"]
    order_item_id = ord_data["items"][0]["id"]

    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Urgent"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    full_payload = {
        "results": [
            {"parameter_id": f["param_hb"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "14.2"},
            {"parameter_id": f["param_wbc"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "7.5"}
        ]
    }
    client.post(f"/api/v1/samples/{smp_id}/results/submit", json=full_payload, headers=f["tech_headers"])

    # 1. Reviewer attempts to return for correction WITHOUT reason -> 422
    ret_empty = client.post(f"/api/v1/verification/{smp_id}/return", json={"reason": ""}, headers=f["reviewer_headers"])
    assert ret_empty.status_code == 422

    # 2. Reviewer returns for correction WITH reason -> 200
    ret_ok = client.post(f"/api/v1/verification/{smp_id}/return", json={"reason": "Re-check WBC count"}, headers=f["reviewer_headers"])
    assert ret_ok.status_code == 200
    ret_results = ret_ok.json()
    assert all(r["status"] == "Correction Required" for r in ret_results)
    assert ret_results[0]["correction_reason"] == "Re-check WBC count"

    # 3. Technician edits result and resubmits
    corrected_payload = {
        "results": [
            {"parameter_id": f["param_hb"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "14.2"},
            {"parameter_id": f["param_wbc"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "8.0"}
        ]
    }
    resub_resp = client.post(f"/api/v1/samples/{smp_id}/results/submit", json=corrected_payload, headers=f["tech_headers"])
    assert resub_resp.status_code == 200
    assert all(r["status"] == "Entered" for r in resub_resp.json())

    # 4. Reviewer approves
    client.post(f"/api/v1/verification/{smp_id}/approve", json={"reason": "Approved post-correction"}, headers=f["reviewer_headers"])

    # 5. Technician attempts to modify locked verified result -> 400
    edit_locked = client.post(f"/api/v1/samples/{smp_id}/results/submit", json=corrected_payload, headers=f["tech_headers"])
    assert edit_locked.status_code == 400
    assert "cannot edit a result that has already been verified" in edit_locked.json()["detail"].lower()


def test_report_generation_pdf_content_and_security(client: TestClient, db: Session):
    """
    Test Phase 6 PDF report generation, content validation, unverified order rejection,
    idempotency, PDF download security, and tenant isolation.
    """
    f = _setup_order_fixtures(client, db)
    
    # 1. Create order
    ord_resp = client.post("/api/v1/orders", json={
        "patient_id": f["patient"].id, "selected_test_ids": [f["test_cbc"].id],
        "discount": 0.0, "tax": 0.0, "payment_status": "Pending",
    }, headers=f["admin_headers"])
    ord_data = ord_resp.json()
    order_id = ord_data["id"]
    order_item_id = ord_data["items"][0]["id"]

    # 2. Register sample & submit results
    smp_resp = client.post("/api/v1/samples", json={
        "order_id": order_id, "sample_type": "Blood", "priority": "Normal"
    }, headers=f["tech_headers"])
    smp_id = smp_resp.json()["id"]

    full_payload = {
        "results": [
            {"parameter_id": f["param_hb"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "14.2"},
            {"parameter_id": f["param_wbc"].id, "order_item_id": order_item_id, "test_id": f["test_cbc"].id, "raw_value": "7.5"}
        ]
    }
    client.post(f"/api/v1/samples/{smp_id}/results/submit", json=full_payload, headers=f["tech_headers"])

    # 3. Attempt report generation BEFORE verification -> 409 Conflict
    unv_gen = client.post(f"/api/v1/reports/generate/{order_id}", headers=f["reviewer_headers"])
    assert unv_gen.status_code == 409
    assert "only verified orders" in unv_gen.json()["detail"].lower()

    # 4. Reviewer approves results -> Order becomes Verified
    client.post(f"/api/v1/verification/{smp_id}/approve", json={"reason": "Approved"}, headers=f["reviewer_headers"])

    # 5. Generate Report -> 201 Created
    gen_resp = client.post(f"/api/v1/reports/generate/{order_id}", headers=f["reviewer_headers"])
    assert gen_resp.status_code == 201
    rpt_data = gen_resp.json()
    assert rpt_data["report_number"].startswith("RPT-")
    assert rpt_data["status"] == "Available"
    assert rpt_data["file_size"] > 0
    assert len(rpt_data["checksum"]) == 64  # SHA-256 length

    report_id = rpt_data["id"]

    # 6. Test Idempotency: second call returns existing report
    gen_dup = client.post(f"/api/v1/reports/generate/{order_id}", headers=f["reviewer_headers"])
    assert gen_dup.status_code == 201
    assert gen_dup.json()["id"] == report_id

    # 7. Download PDF file
    dl_resp = client.get(f"/api/v1/reports/{report_id}/download", headers=f["reviewer_headers"])
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert len(dl_resp.content) > 0

    # Parse PDF content with pypdf
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(dl_resp.content))
    assert len(reader.pages) >= 1
    page_text = reader.pages[0].extract_text()
    assert rpt_data["report_number"] in page_text
    assert "Hemoglobin" in page_text or "14.2" in page_text

    # 8. Tenant Isolation check: Create Org B & User B, login, and attempt to download Report -> 404
    org_b = Organization(name="Tenant Isolation Lab", code="TENISO_LAB", status="active")
    db.add(org_b)
    db.flush()
    user_b = User(
        email="tenant_user_b@isolation.com",
        password_hash=get_password_hash("pass123"),
        name="Tenant User B",
        role="reviewer",
        status="active",
        organization_id=org_b.id,
    )
    db.add(user_b)
    db.commit()

    login_b = client.post("/api/v1/auth/login", json={"email": "tenant_user_b@isolation.com", "password": "pass123"})
    token_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    
    iso_dl = client.get(f"/api/v1/reports/{report_id}/download", headers=token_b)
    assert iso_dl.status_code == 404





