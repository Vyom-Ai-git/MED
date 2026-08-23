import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from app.core.security import get_password_hash, create_access_token
from app.models.organization import Organization
from app.models.branch import Branch
from app.models.user import User
from app.models.patient import Patient
from app.models.test import Test, TestParameter

# Prevent pytest from collecting SQLAlchemy models as test classes
Test.__test__ = False
TestParameter.__test__ = False

from app.models.order import Order, OrderItem
from app.models.sample import Sample, Result
from app.models.report import Report
from app.models.doctor import Doctor, DoctorScheduleSlot
from app.models.booking import DoctorAppointment, LabBooking
from app.models.customer_care import CustomerCareHandoff
from app.core.config import settings


@pytest.fixture
def test_setup(db):
    org = Organization(name="Test Org 11", code="ORG11")
    db.add(org)
    db.flush()

    branch = Branch(organization_id=org.id, name="Test Branch", code="BR11")
    db.add(branch)
    db.flush()

    admin = User(
        organization_id=org.id,
        branch_id=branch.id,
        name="Admin Eleven",
        email="admin11@vyoma.com",
        password_hash=get_password_hash("secret123"),
        role="admin",
    )
    db.add(admin)
    db.flush()

    patient = Patient(
        organization_id=org.id,
        patient_id="PAT-2026-9999",
        first_name="Alice",
        last_name="Wonderland",
        date_of_birth=date(1995, 4, 12),
        gender="female",
        phone="+91 99999 11111",
        email="alice@example.com",
        communication_preference="whatsapp",
        consent_operational=True,
    )
    db.add(patient)
    db.flush()

    test_obj = Test(
        organization_id=org.id,
        code="CBC",
        name="Complete Blood Count",
        category="Hematology",
        description="Fasting blood sample required",
        price=Decimal("400.00"),
        status="active",
    )
    test_obj.parameters.append(TestParameter(
        name="Hemoglobin", code="HB", unit="g/dL", reference_range="12-16", lower_limit=Decimal("12.0"), upper_limit=Decimal("16.0")
    ))
    db.add(test_obj)
    db.flush()

    order = Order(
        organization_id=org.id,
        branch_id=branch.id,
        patient_id=patient.id,
        ordering_user_id=admin.id,
        order_number="ORD-2026-99999",
        status="Verified",
        payment_status="Paid",
        subtotal=Decimal("400.00"),
        total_amount=Decimal("400.00"),
    )
    order.items.append(OrderItem(
        test_id=test_obj.id,
        test_name_snapshot=test_obj.name,
        test_code_snapshot=test_obj.code,
        unit_price=Decimal("400.00"),
        quantity=1,
        total=Decimal("400.00"),
        status="Verified",
    ))
    db.add(order)
    db.flush()

    sample = Sample(
        organization_id=org.id,
        branch_id=branch.id,
        order_id=order.id,
        sample_identifier="SMP-99999",
        sample_type="Blood",
        collection_status="Completed",
    )
    db.add(sample)
    db.flush()

    tr = Result(
        organization_id=org.id,
        sample_id=sample.id,
        order_item_id=order.items[0].id,
        test_id=test_obj.id,
        parameter_id=test_obj.parameters[0].id,
        raw_value="14.5",
        numeric_value=Decimal("14.5"),
        unit="g/dL",
        reference_low=Decimal("12.0"),
        reference_high=Decimal("16.0"),
        abnormal_flag="NORMAL",
        status="Verified",
        entered_by=admin.id,
    )
    db.add(tr)
    db.flush()

    report = Report(
        organization_id=org.id,
        branch_id=branch.id,
        order_id=order.id,
        patient_id=patient.id,
        report_number="RPT-2026-99999",
        status="Available",
        version=1,
        file_name="report_99999.pdf",
        file_path="storage/reports/report_99999.pdf",
        file_size=1024,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        page_count=2,
    )
    db.add(report)

    doc = Doctor(
        organization_id=org.id,
        branch_id=branch.id,
        doctor_code="DOC-999",
        name="Dr. Gregory House",
        specialty="Diagnostic Medicine",
        qualification="MD",
        phone="+91 98888 11111",
        email="house@hospital.org",
        consultation_fee=Decimal("1000.00"),
        is_active=True,
    )
    db.add(doc)
    db.flush()

    from datetime import time
    slot = DoctorScheduleSlot(
        doctor_id=doc.id,
        branch_id=branch.id,
        slot_date=date(2026, 8, 25),
        start_time=time(14, 0),
        end_time=time(14, 30),
        consultation_type="in_person",
        is_booked=False,
    )
    db.add(slot)
    db.commit()

    token = create_access_token(str(admin.id))

    return {
        "org": org,
        "branch": branch,
        "admin": admin,
        "patient": patient,
        "order": order,
        "report": report,
        "doctor": doc,
        "slot": slot,
        "token": token,
        "auth_headers": {"Authorization": f"Bearer {token}"},
    }



# Capability 1 & Outbound Webhooks
def test_report_available_webhook_service(db, test_setup):
    from app.services.integration import integration_service
    delivery = integration_service.dispatch_event(
        db,
        org_id=test_setup["org"].id,
        event_type="report.available",
        payload_data={
            "report_id": test_setup["report"].id,
            "report_number": test_setup["report"].report_number,
            "order_id": test_setup["order"].id,
            "patient_id": test_setup["patient"].id,
        }
    )
    assert delivery is not None
    assert delivery.event_type == "report.available"


# Capability 2: Report Metadata
def test_report_metadata(client, test_setup):
    res = client.get(
        f"/api/v1/reports/{test_setup['report'].id}/metadata",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_number"] == "RPT-2026-99999"
    assert data["patient_name"] == "Alice Wonderland"
    assert data["verification_status"] == "Verified"


# Capability 3: Verified Report Data / Results
def test_verified_report_results(client, test_setup):
    res = client.get(
        f"/api/v1/reports/{test_setup['report'].id}/results",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["report_number"] == "RPT-2026-99999"
    assert len(data["results"]) == 1
    assert data["results"][0]["parameter_name"] == "Hemoglobin"
    assert data["results"][0]["result_value"] == "14.5"


# Capability 4: Patient Communication / Contact Lookup
def test_patient_contact_lookup(client, test_setup):
    res = client.get(
        f"/api/v1/patients/lookup?phone={test_setup['patient'].phone}",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == "PAT-2026-9999"
    assert data["communication_preference"] == "whatsapp"


# Capability 5: Patient-Facing Secure Report Access
def test_patient_secure_report_access(client, test_setup, db):
    from app.services.storage import storage_service
    saved_path, _, _ = storage_service.save_file(b"%PDF-1.4 Mock PDF Content", "reports/report_99999.pdf")
    test_setup["report"].file_path = saved_path
    db.commit()

    # Generate secure link
    gen_res = client.post(
        f"/api/v1/reports/{test_setup['report'].id}/secure-link?expires_in_hours=24",
        headers=test_setup["auth_headers"],
    )
    assert gen_res.status_code == 200
    token_data = gen_res.json()
    secure_token = token_data["secure_token"]

    db.expire_all()

    # Public patient access
    pub_res = client.get(f"/api/v1/public/reports/access/{secure_token}")
    assert pub_res.status_code == 200
    assert pub_res.headers["content-type"] == "application/pdf"
    assert b"%PDF-1.4 Mock PDF Content" in pub_res.content


# Capability 6: Test Catalog
def test_test_catalog(client, test_setup):
    res = client.get(
        "/api/v1/tests/catalog",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["code"] == "CBC"
    assert data["items"][0]["fasting_required"] is True


# Capability 7: Branch & Location Availability
def test_branch_availability(client, test_setup):
    res = client.get(
        "/api/v1/branches/availability",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["code"] == "BR11"
    assert "Diagnostic Testing" in data[0]["services_offered"]


# Capability 8: Doctor Availability
def test_doctor_availability(client, test_setup):
    res = client.get(
        f"/api/v1/doctors/{test_setup['doctor'].id}/availability",
        headers=test_setup["auth_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["doctor_name"] == "Dr. Gregory House"
    assert len(data["available_slots"]) == 1


# Capability 9: Doctor Appointment Booking
def test_doctor_appointment_booking(client, test_setup):
    res = client.post(
        "/api/v1/bookings/doctor",
        headers=test_setup["auth_headers"],
        json={
            "patient_id": test_setup["patient"].id,
            "doctor_id": test_setup["doctor"].id,
            "slot_id": test_setup["slot"].id,
            "branch_id": test_setup["branch"].id,
            "appointment_date": "2026-08-25",
            "start_time": "14:00:00",
            "end_time": "14:30:00",
            "consultation_type": "in_person",
            "notes": "Patient complains of fatigue",
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["doctor_name"] == "Dr. Gregory House"
    assert data["status"] == "Scheduled"
    assert data["booking_number"].startswith("APT-2026-")


# Capability 10: Lab Booking (Home Sample Collection & Walk-in)
def test_lab_booking(client, test_setup):
    res = client.post(
        "/api/v1/bookings/lab",
        headers=test_setup["auth_headers"],
        json={
            "patient_id": test_setup["patient"].id,
            "branch_id": test_setup["branch"].id,
            "booking_type": "home_collection",
            "preferred_date": "2026-08-26",
            "preferred_slot": "08:00 AM - 10:00 AM",
            "address": {"street": "742 Evergreen Terrace", "city": "Springfield"},
            "tests_requested": ["CBC", "HbA1c"],
            "notes": "Ring doorbell twice",
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["booking_type"] == "home_collection"
    assert data["status"] == "Pending"
    assert data["booking_number"].startswith("LBK-2026-")


# Capability 11: Customer Care Handoff
def test_customer_care_handoff(client, test_setup):
    res = client.post(
        "/api/v1/customer-care/handoff",
        headers=test_setup["auth_headers"],
        json={
            "patient_id": test_setup["patient"].id,
            "order_id": test_setup["order"].id,
            "channel": "whatsapp",
            "category": "report_query",
            "priority": "high",
            "summary": "Urgent request for verified blood result",
            "conversation_transcript": [
                {"sender": "patient", "text": "Is my report ready?"},
                {"sender": "bot", "text": "Escalating to human agent."},
            ],
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["ticket_number"].startswith("TKT-2026-")
    assert data["priority"] == "high"
    assert data["status"] == "Open"

    # List tickets
    list_res = client.get(
        "/api/v1/customer-care/handoff",
        headers=test_setup["auth_headers"],
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
