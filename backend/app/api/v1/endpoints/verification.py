from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, func
from typing import Optional, List
import logging
import datetime

from app.core.database import get_db
from app.schemas.sample import (
    SampleResponse,
    ResultResponse,
    ResultVerificationCreate,
    ResultVerificationResponse,
    VerificationQueueItem,
    VerificationQueueListResponse,
)
from app.models.sample import Sample, Result
from app.models.result_verification import ResultVerification
from app.models.order import Order
from app.models.patient import Patient
from app.models.user import User
from app.repositories.sample import sample_repo
from app.services.verification import verification_service
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole

router = APIRouter()
logger = logging.getLogger("app.api.verification")


@router.get("", response_model=VerificationQueueListResponse)
def get_verification_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
    q: Optional[str] = Query(None, description="Search by patient name/id, sample ID, order number"),
    result_status: Optional[str] = Query(None, description="Filter by status: Entered, Under Review, Verified, Correction Required"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    critical_only: Optional[bool] = Query(False, description="Filter to critical results only"),
    abnormal_only: Optional[bool] = Query(False, description="Filter to abnormal results only"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Verification Queue endpoint for Reviewers and Admins. Tenant isolated.
    Returns samples with entered/submitted results awaiting verification.
    """
    org_id = current_user.organization_id

    # Compute summary metrics for reviewer dashboard cards
    all_results_q = db.query(Result).filter(Result.organization_id == org_id)
    pending_count = all_results_q.filter(Result.status.in_(["Entered", "Under Review"])).distinct(Result.sample_id).count()
    critical_count = all_results_q.filter(Result.critical_flag == True, Result.status.in_(["Entered", "Under Review"])).distinct(Result.sample_id).count()
    correction_count = all_results_q.filter(Result.status == "Correction Required").distinct(Result.sample_id).count()

    today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    verified_today_count = all_results_q.filter(Result.status == "Verified", Result.verified_at >= today_start).distinct(Result.sample_id).count()

    # Query samples that have results
    query = db.query(Sample).join(Result, Result.sample_id == Sample.id).filter(Sample.organization_id == org_id)

    if result_status:
        query = query.filter(Result.status == result_status)
    else:
        # Default queue view: show Entered, Under Review, or Correction Required
        query = query.filter(Result.status.in_(["Entered", "Under Review", "Correction Required"]))

    if priority:
        query = query.filter(Sample.priority == priority)

    if critical_only:
        query = query.filter(Result.critical_flag == True)

    if abnormal_only:
        query = query.filter(Result.abnormal_flag.in_(["LOW", "HIGH"]))

    if q:
        term = f"%{q}%"
        query = query.join(Sample.order).join(Order.patient).filter(
            or_(
                Sample.sample_identifier.ilike(term),
                Order.order_number.ilike(term),
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.patient_id.ilike(term),
                Patient.phone.ilike(term),
            )
        )

    # Distinct sample IDs
    query = query.distinct(Sample.id)
    total = query.count()

    samples = (
        query.options(
            joinedload(Sample.order).joinedload(Order.patient),
            joinedload(Sample.order).joinedload(Order.items),
        )
        .order_by(desc(Sample.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    queue_items = []
    for s in samples:
        s_resp = SampleResponse.model_validate(s)
        if s.order:
            tests_list = [item.test_name_snapshot for item in s.order.items]
            pat_summary = None
            if s.order.patient:
                pat_summary = {
                    "id": s.order.patient.id,
                    "patient_id": s.order.patient.patient_id,
                    "first_name": s.order.patient.first_name,
                    "last_name": s.order.patient.last_name,
                    "phone": s.order.patient.phone,
                    "gender": s.order.patient.gender,
                    "date_of_birth": str(s.order.patient.date_of_birth),
                }
            s_resp.order = {
                "id": s.order.id,
                "order_number": s.order.order_number,
                "created_at": s.order.created_at,
                "patient": pat_summary,
                "tests": tests_list,
            }

        # Load sample results
        results = sample_repo.get_results_by_sample(db, org_id=org_id, sample_id=s.id)
        res_list = []
        has_critical = False
        has_abnormal = False
        statuses = set()

        for r in results:
            resp = ResultResponse.model_validate(r)
            if r.parameter:
                resp.parameter_name = r.parameter.name
                resp.parameter_code = r.parameter.code
                resp.data_type = r.parameter.data_type
            if r.critical_flag:
                has_critical = True
            if r.abnormal_flag in ["LOW", "HIGH"]:
                has_abnormal = True
            statuses.add(r.status)
            res_list.append(resp)

        # Status summary string
        if "Correction Required" in statuses:
            status_summary = "Correction Required"
        elif "Entered" in statuses or "Under Review" in statuses:
            status_summary = "Pending Review"
        elif all(st == "Verified" for st in statuses):
            status_summary = "Verified"
        else:
            status_summary = "Draft"

        # Load verification audit history for sample
        verifications = verification_service.get_verification_history(db, org_id=org_id, sample_id=s.id)
        ver_list = []
        for v in verifications:
            v_resp = ResultVerificationResponse.model_validate(v)
            if v.actor:
                v_resp.performed_by_name = f"{v.actor.name} ({v.actor.role})"
            ver_list.append(v_resp)

        queue_items.append(
            VerificationQueueItem(
                sample=s_resp,
                results=res_list,
                verifications=ver_list,
                has_critical=has_critical,
                has_abnormal=has_abnormal,
                status_summary=status_summary,
            )
        )

    return {
        "items": queue_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pending_count": pending_count,
        "critical_count": critical_count,
        "correction_count": correction_count,
        "verified_today_count": verified_today_count,
    }


@router.get("/{id}", response_model=VerificationQueueItem)
def get_verification_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER, UserRole.TECHNICIAN)),
):
    """
    Get detailed verification record for a sample specimen.
    Reviewer, Admin, and Technician (for correction review) access.
    """
    org_id = current_user.organization_id
    sample = sample_repo.get_by_id(db, org_id=org_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    s_resp = SampleResponse.model_validate(sample)
    if sample.order:
        tests_list = [item.test_name_snapshot for item in sample.order.items]
        pat_summary = None
        if sample.order.patient:
            pat_summary = {
                "id": sample.order.patient.id,
                "patient_id": sample.order.patient.patient_id,
                "first_name": sample.order.patient.first_name,
                "last_name": sample.order.patient.last_name,
                "phone": sample.order.patient.phone,
                "gender": sample.order.patient.gender,
                "date_of_birth": str(sample.order.patient.date_of_birth),
            }
        s_resp.order = {
            "id": sample.order.id,
            "order_number": sample.order.order_number,
            "created_at": sample.order.created_at,
            "patient": pat_summary,
            "tests": tests_list,
        }

    results = sample_repo.get_results_by_sample(db, org_id=org_id, sample_id=id)
    res_list = []
    has_critical = False
    has_abnormal = False
    statuses = set()

    for r in results:
        resp = ResultResponse.model_validate(r)
        if r.parameter:
            resp.parameter_name = r.parameter.name
            resp.parameter_code = r.parameter.code
            resp.data_type = r.parameter.data_type
        if r.critical_flag:
            has_critical = True
        if r.abnormal_flag in ["LOW", "HIGH"]:
            has_abnormal = True
        statuses.add(r.status)
        res_list.append(resp)

    if "Correction Required" in statuses:
        status_summary = "Correction Required"
    elif "Entered" in statuses or "Under Review" in statuses:
        status_summary = "Pending Review"
    elif all(st == "Verified" for st in statuses):
        status_summary = "Verified"
    else:
        status_summary = "Draft"

    verifications = verification_service.get_verification_history(db, org_id=org_id, sample_id=id)
    ver_list = []
    for v in verifications:
        v_resp = ResultVerificationResponse.model_validate(v)
        if v.actor:
            v_resp.performed_by_name = f"{v.actor.name} ({v.actor.role})"
        ver_list.append(v_resp)

    return VerificationQueueItem(
        sample=s_resp,
        results=res_list,
        verifications=ver_list,
        has_critical=has_critical,
        has_abnormal=has_abnormal,
        status_summary=status_summary,
    )


@router.post("/{id}/approve", response_model=List[ResultResponse])
def approve_sample_results(
    id: int,
    body: Optional[ResultVerificationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """
    Approve laboratory results for a sample. Admin and Reviewer only.
    Technicians are denied (HTTP 403).
    """
    org_id = current_user.organization_id
    sample = sample_repo.get_by_id(db, org_id=org_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    reason = body.reason if body else None
    try:
        approved_results = verification_service.approve_sample_results(
            db, sample=sample, org_id=org_id, reviewer_id=current_user.id, reason=reason
        )
        res_list = []
        for r in approved_results:
            resp = ResultResponse.model_validate(r)
            if r.parameter:
                resp.parameter_name = r.parameter.name
                resp.parameter_code = r.parameter.code
                resp.data_type = r.parameter.data_type
            res_list.append(resp)
        return res_list
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{id}/return", response_model=List[ResultResponse])
def return_sample_results_for_correction(
    id: int,
    body: ResultVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """
    Return sample results to technician for correction. Admin and Reviewer only.
    Requires a non-empty reason. Technicians are denied (HTTP 403).
    """
    org_id = current_user.organization_id
    sample = sample_repo.get_by_id(db, org_id=org_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    if not body.reason or not body.reason.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Correction reason is required.")

    try:
        returned_results = verification_service.return_sample_results_for_correction(
            db, sample=sample, org_id=org_id, reviewer_id=current_user.id, reason=body.reason
        )
        res_list = []
        for r in returned_results:
            resp = ResultResponse.model_validate(r)
            if r.parameter:
                resp.parameter_name = r.parameter.name
                resp.parameter_code = r.parameter.code
                resp.data_type = r.parameter.data_type
            res_list.append(resp)
        return res_list
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
