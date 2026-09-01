import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.schemas.patient import PatientCreate

class DuplicatePatientError(Exception):
    def __init__(self, message: str, existing_id: int):
        super().__init__(message)
        self.existing_id = existing_id

class PatientService:
    def create_patient(
        self, 
        db: Session, 
        patient_in: PatientCreate, 
        org_id: int, 
        ignore_duplicate: bool = False
    ) -> Patient:
        patient_data = patient_in.model_dump()
        patient_data["organization_id"] = org_id
        
        # Remove frontend-only control fields if present
        patient_data.pop("ignore_duplicate", None)

        # 1. Duplicate check (first name, last name, DOB, and phone)
        first_name = patient_data.get("first_name")
        last_name = patient_data.get("last_name")
        date_of_birth = patient_data.get("date_of_birth")
        phone = patient_data.get("phone")

        if not ignore_duplicate:
            existing = db.query(Patient).filter(
                Patient.organization_id == org_id,
                Patient.first_name == first_name,
                Patient.last_name == last_name,
                Patient.date_of_birth == date_of_birth,
                Patient.phone == phone
            ).first()
            if existing:
                raise DuplicatePatientError(
                    "A patient with similar name, date of birth, and phone number already exists.",
                    existing.id
                )

        # 2. Sequential Patient ID generation: PAT-YYYYMMDD-XXXX
        today = datetime.date.today()
        today_str = today.strftime("%Y%m%d")
        
        # Count patient rows created today within this organization
        count_today = db.query(func.count(Patient.id)).filter(
            Patient.organization_id == org_id,
            Patient.patient_id.like(f"PAT-{today_str}-%")
        ).scalar()
        
        sequence_num = count_today + 1
        patient_data["patient_id"] = f"PAT-{today_str}-{sequence_num:04d}"
        
        db_obj = Patient(**patient_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

patient_service = PatientService()
