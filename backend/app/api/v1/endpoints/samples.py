from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.core.database import get_db
from app.schemas.sample import (
    SampleCreate,
    SampleResponse,
    SampleListResponse,
    SampleReject,
    SampleStatusUpdate,
    SampleResultsResponse,
    ResultDraftSaveIn,
    ResultSubmitIn,
    ResultResponse,
)
from app.repositories.sample import sample_repo
from app.services.sample import sample_service
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.samples")


@router.get("", response_model=SampleListResponse)
def get_samples(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = Query(None, description="Search by sample ID, order number, patient name/phone"),
    status: Optional[str] = Query(None, description="Filter by collection status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    sample_type: Optional[str] = Query(None, description="Filter by sample type"),
    order_id: Optional[int] = Query(None, description="Filter by order ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Paginated, searchable sample tracker and worklist endpoint. Tenant isolated.
    """
    items, total = sample_repo.search_samples(
        db,
        org_id=current_user.organization_id,
        q=q,
        status=status,
        priority=priority,
        sample_type=sample_type,
        order_id=order_id,
        page=page,
        page_size=page_size,
    )
    
    # Format order summary for each sample response
    response_items = []
    for s in items:
        resp = SampleResponse.model_validate(s)
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
            resp.order = {
                "id": s.order.id,
                "order_number": s.order.order_number,
                "created_at": s.order.created_at,
                "patient": pat_summary,
                "tests": tests_list,
            }
        response_items.append(resp)

    return {"items": response_items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
def create_sample(
    sample_in: SampleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TECHNICIAN, UserRole.RECEPTION)),
):
    """
    Register a new sample for an existing laboratory order.
    """
    try:
        sample = sample_service.create_sample(
            db, sample_in=sample_in, org_id=current_user.organization_id, user_id=current_user.id
        )
        return sample_repo.get_by_id(db, org_id=current_user.organization_id, id=sample.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{id}", response_model=SampleResponse)
def get_sample(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get sample details by ID. Tenant isolated.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    resp = SampleResponse.model_validate(sample)
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
        resp.order = {
            "id": sample.order.id,
            "order_number": sample.order.order_number,
            "created_at": sample.order.created_at,
            "patient": pat_summary,
            "tests": tests_list,
        }
    return resp


@router.patch("/{id}/status", response_model=SampleResponse)
def update_sample_status(
    id: int,
    status_in: SampleStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TECHNICIAN)),
):
    """
    Transition sample collection/processing status. Admin and Technician only.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    try:
        updated = sample_service.transition_status(
            db, sample=sample, target_status=status_in.status, user_role=current_user.role, user_id=current_user.id
        )
        return sample_repo.get_by_id(db, org_id=current_user.organization_id, id=updated.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{id}/reject", response_model=SampleResponse)
def reject_sample(
    id: int,
    reject_in: SampleReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TECHNICIAN)),
):
    """
    Reject sample specimen and trigger recollection foundation. Admin & Technician only.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    try:
        updated = sample_service.reject_sample(
            db, sample=sample, reason=reject_in.rejection_reason, user_role=current_user.role, user_id=current_user.id
        )
        return sample_repo.get_by_id(db, org_id=current_user.organization_id, id=updated.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{id}/results", response_model=List[ResultResponse])
def get_sample_results(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all results recorded for a sample.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    results = sample_repo.get_results_by_sample(db, org_id=current_user.organization_id, sample_id=id)
    res_list = []
    for r in results:
        resp = ResultResponse.model_validate(r)
        if r.parameter:
            resp.parameter_name = r.parameter.name
            resp.parameter_code = r.parameter.code
            resp.data_type = r.parameter.data_type
        res_list.append(resp)
    return res_list


@router.post("/{id}/results/draft", response_model=List[ResultResponse])
def save_draft_results(
    id: int,
    draft_in: ResultDraftSaveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TECHNICIAN)),
):
    """
    Save partial draft results for a sample. Does not require complete parameter entry.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    try:
        results = sample_service.save_draft_results(
            db, sample=sample, items=draft_in.results, org_id=current_user.organization_id, user_id=current_user.id
        )
        res_list = []
        for r in results:
            resp = ResultResponse.model_validate(r)
            if r.parameter:
                resp.parameter_name = r.parameter.name
                resp.parameter_code = r.parameter.code
                resp.data_type = r.parameter.data_type
            res_list.append(resp)
        return res_list
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{id}/results/submit", response_model=List[ResultResponse])
def submit_results(
    id: int,
    submit_in: ResultSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TECHNICIAN)),
):
    """
    Submit completed laboratory results. Validates mandatory test parameters, calculates flags,
    and updates sample/order states.
    """
    sample = sample_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

    try:
        results = sample_service.submit_results(
            db, sample=sample, items=submit_in.results, org_id=current_user.organization_id, user_id=current_user.id
        )
        res_list = []
        for r in results:
            resp = ResultResponse.model_validate(r)
            if r.parameter:
                resp.parameter_name = r.parameter.name
                resp.parameter_code = r.parameter.code
                resp.data_type = r.parameter.data_type
            res_list.append(resp)
        return res_list
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
