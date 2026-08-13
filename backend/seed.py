import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.branch import Branch
from app.models.user import User
from app.models.patient import Patient
from app.models.test import Test, TestParameter
from app.models.order import Order, OrderItem
from app.models.sample import Sample, Result
from app.models.result_verification import ResultVerification
from app.models.report import Report
from app.models.audit import AuditLog
from app.models.integration import IntegrationDelivery

def seed_data():
    print("Seeding development-only demo data...")
    db = SessionLocal()
    try:
        # Check if database has already been seeded
        if db.query(Organization).first():
            print("Database already contains data, skipping seed.")
            return

        # 1. Create Demo Organization
        org = Organization(
            name="Vyoma Diagnostics",
            code="VYOMA",
            contact_info={"email": "info@vyoma.com", "phone": "+91 99999 88888", "website": "www.vyoma.com"},
            status="active"
        )
        db.add(org)
        db.flush() # Populate org.id
        print(f"Created Organization: {org.name} (ID: {org.id})")

        # 2. Create Demo Branch
        branch = Branch(
            organization_id=org.id,
            name="Bengaluru Main Lab",
            code="BLR-MAIN",
            address={"street": "100 Feet Rd, Indiranagar", "city": "Bengaluru", "state": "Karnataka", "zip": "560038"},
            contact_info={"phone": "+91 80 4444 5555"},
            status="active"
        )
        db.add(branch)
        db.flush()
        print(f"Created Branch: {branch.name} (ID: {branch.id})")

        # 3. Create Users
        admin_user = User(
            organization_id=org.id,
            branch_id=branch.id,
            name="Vivek Admin",
            email="admin@vyoma.com",
            phone="+91 98765 43210",
            password_hash=get_password_hash("admin123"),
            role="admin",
            status="active"
        )
        
        reception_user = User(
            organization_id=org.id,
            branch_id=branch.id,
            name="Ravi Reception",
            email="reception@vyoma.com",
            phone="+91 98765 43211",
            password_hash=get_password_hash("reception123"),
            role="reception",
            status="active"
        )
        
        technician_user = User(
            organization_id=org.id,
            branch_id=branch.id,
            name="Sarah Tech",
            email="tech@vyoma.com",
            phone="+91 98765 43212",
            password_hash=get_password_hash("tech123"),
            role="technician",
            status="active"
        )
        
        reviewer_user = User(
            organization_id=org.id,
            branch_id=branch.id,
            name="Dr. Anand Reviewer",
            email="reviewer@vyoma.com",
            phone="+91 98765 43213",
            password_hash=get_password_hash("reviewer123"),
            role="reviewer",
            status="active"
        )
        
        db.add_all([admin_user, reception_user, technician_user, reviewer_user])
        db.flush()
        print(f"Created Users (Admin: {admin_user.email}, Reception: {reception_user.email}, Tech: {technician_user.email}, Reviewer: {reviewer_user.email})")

        # 4. Create Tests and Parameters
        # CBC
        cbc = Test(
            organization_id=org.id,
            code="CBC",
            name="Complete Blood Count",
            category="Hematology",
            description="Analyzes cellular components of blood including RBC, WBC, and Platelets.",
            price=Decimal("350.00"),
            status="active"
        )
        cbc.parameters.append(TestParameter(name="Hemoglobin", code="HB", unit="g/dL", data_type="numeric", reference_range="13.5 - 17.5", lower_limit=Decimal("13.5"), upper_limit=Decimal("17.5"), critical_low=Decimal("7.0"), critical_high=Decimal("20.0"), display_order=1))
        cbc.parameters.append(TestParameter(name="White Blood Cells (WBC)", code="WBC", unit="10^3/uL", data_type="numeric", reference_range="4.0 - 11.0", lower_limit=Decimal("4.0"), upper_limit=Decimal("11.0"), critical_low=Decimal("2.0"), critical_high=Decimal("30.0"), display_order=2))
        cbc.parameters.append(TestParameter(name="Platelet Count", code="PLT", unit="10^3/uL", data_type="numeric", reference_range="150 - 450", lower_limit=Decimal("150"), upper_limit=Decimal("450"), critical_low=Decimal("50.0"), critical_high=Decimal("800.0"), display_order=3))
        
        # HbA1c
        hba1c = Test(
            organization_id=org.id,
            code="HBA1C",
            name="Glycated Hemoglobin (HbA1c)",
            category="Diabetology",
            description="Evaluates long-term glycemic control over approximately 3 months.",
            price=Decimal("450.00"),
            status="active"
        )
        hba1c.parameters.append(TestParameter(name="HbA1c", code="HBA1C", unit="%", data_type="numeric", reference_range="4.0 - 5.6", lower_limit=Decimal("4.0"), upper_limit=Decimal("5.6"), critical_high=Decimal("9.0"), display_order=1))

        # Lipid Profile
        lipid = Test(
            organization_id=org.id,
            code="LIPID",
            name="Lipid Profile",
            category="Biochemistry",
            description="Assesses risk of cardiovascular disease by measuring blood lipids.",
            price=Decimal("650.00"),
            status="active"
        )
        lipid.parameters.append(TestParameter(name="Total Cholesterol", code="CHOL", unit="mg/dL", data_type="numeric", reference_range="< 200", upper_limit=Decimal("200.00"), critical_high=Decimal("300.00"), display_order=1))
        lipid.parameters.append(TestParameter(name="HDL Cholesterol", code="HDL", unit="mg/dL", data_type="numeric", reference_range="> 40", lower_limit=Decimal("40.00"), critical_low=Decimal("20.00"), display_order=2))
        lipid.parameters.append(TestParameter(name="LDL Cholesterol", code="LDL", unit="mg/dL", data_type="numeric", reference_range="< 100", upper_limit=Decimal("100.00"), critical_high=Decimal("190.00"), display_order=3))
        lipid.parameters.append(TestParameter(name="Triglycerides", code="TG", unit="mg/dL", data_type="numeric", reference_range="< 150", upper_limit=Decimal("150.00"), critical_high=Decimal("500.00"), display_order=4))

        db.add_all([cbc, hba1c, lipid])
        db.flush()
        print("Created Test Catalog and parameters.")

        # 5. Create Demo Patients
        jane = Patient(
            organization_id=org.id,
            patient_id="PAT-2026-0001",
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 5, 15),
            gender="female",
            phone="+91 98888 77777",
            email="jane.doe@example.com",
            address={"street": "Apt 4B, Central Vista", "city": "Bengaluru"},
            emergency_contact={"name": "Richard Doe", "phone": "+91 98888 77770", "relation": "husband"},
            referring_provider="Dr. Amit Shah",
            communication_preference="whatsapp",
            consent_operational=True,
            consent_promotional=False
        )
        
        john = Patient(
            organization_id=org.id,
            patient_id="PAT-2026-0002",
            first_name="John",
            last_name="Smith",
            date_of_birth=date(1985, 11, 23),
            gender="male",
            phone="+91 97777 66666",
            email="john.smith@example.com",
            address={"street": "Plot 54, Sector 7", "city": "Bengaluru"},
            emergency_contact={"name": "Mary Smith", "phone": "+91 97777 66660", "relation": "wife"},
            referring_provider="Self",
            communication_preference="email",
            consent_operational=True,
            consent_promotional=True
        )
        
        db.add_all([jane, john])
        db.flush()
        print(f"Created Patients ({jane.first_name} {jane.last_name}, {john.first_name} {john.last_name})")

        # 6. Create Demo Orders with Phase 3 schema (snapshots, subtotal, notes)
        # Order 1: Jane — CBC + HbA1c — Multi-test, Paid
        cbc_price = Decimal(str(cbc.price))
        hba1c_price = Decimal(str(hba1c.price))
        lipid_price = Decimal(str(lipid.price))

        subtotal1 = cbc_price + hba1c_price
        order1 = Order(
            organization_id=org.id,
            branch_id=branch.id,
            patient_id=jane.id,
            ordering_user_id=admin_user.id,
            order_number="ORD-2026-00001",
            status="Pending",
            payment_status="Paid",
            subtotal=subtotal1,
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total_amount=subtotal1,
            notes="Routine annual checkup panel",
        )
        order1.items.append(OrderItem(
            test_id=cbc.id,
            test_name_snapshot=cbc.name,
            test_code_snapshot=cbc.code,
            unit_price=cbc_price,
            quantity=1,
            discount=Decimal("0.00"),
            total=cbc_price,
            status="Pending",
        ))
        order1.items.append(OrderItem(
            test_id=hba1c.id,
            test_name_snapshot=hba1c.name,
            test_code_snapshot=hba1c.code,
            unit_price=hba1c_price,
            quantity=1,
            discount=Decimal("0.00"),
            total=hba1c_price,
            status="Pending",
        ))

        # Order 2: John — Lipid Profile — Single test, Pending payment, Verified status
        order2 = Order(
            organization_id=org.id,
            branch_id=branch.id,
            patient_id=john.id,
            ordering_user_id=admin_user.id,
            order_number="ORD-2026-00002",
            status="Verified",
            payment_status="Pending",
            subtotal=lipid_price,
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total_amount=lipid_price,
            notes="Fasting lipid panel — patient fasted 12 hours",
        )
        order2.items.append(OrderItem(
            test_id=lipid.id,
            test_name_snapshot=lipid.name,
            test_code_snapshot=lipid.code,
            unit_price=lipid_price,
            quantity=1,
            discount=Decimal("0.00"),
            total=lipid_price,
            status="Verified",
        ))

        # Order 3: Jane — CBC with discount — Cancelled order
        order3 = Order(
            organization_id=org.id,
            branch_id=branch.id,
            patient_id=jane.id,
            ordering_user_id=admin_user.id,
            order_number="ORD-2026-00003",
            status="Cancelled",
            payment_status="Pending",
            subtotal=cbc_price,
            discount=Decimal("50.00"),
            tax=Decimal("0.00"),
            total_amount=max(Decimal("0.00"), cbc_price - Decimal("50.00")),
            notes="Cancelled: patient rescheduled",
        )
        order3.items.append(OrderItem(
            test_id=cbc.id,
            test_name_snapshot=cbc.name,
            test_code_snapshot=cbc.code,
            unit_price=cbc_price,
            quantity=1,
            discount=Decimal("50.00"),
            total=max(Decimal("0.00"), cbc_price - Decimal("50.00")),
            status="Pending",
        ))

        db.add_all([order1, order2, order3])
        db.commit()
        print("Created Phase 3 laboratory orders (multi-test, paid, cancelled) successfully.")
        print("--- SEED COMPLETED SUCCESSFULLY ---")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
