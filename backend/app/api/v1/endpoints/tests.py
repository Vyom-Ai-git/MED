from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.schemas.test import TestCreate, TestResponse, TestUpdate, TestListResponse
from app.repositories.test import test_repo
from app.models.test import Test, TestParameter
from app.api.deps import get_current_user, get_current_user_or_m2m, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.tests")

@router.get("", response_model=TestListResponse)
def get_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_m2m),
    q: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Search and list tests in the catalog (paginated, filtered by category/status).
    All authenticated staff can view the catalog.
    """
    items, total = test_repo.search_tests(
        db, 
        org_id=current_user.organization_id, 
        q=q, 
        category=category, 
        status=status,
        page=page, 
        page_size=page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/catalog", response_model=dict)
def get_test_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_m2m),
    q: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Get full active test catalog with preparation guidelines (fasting), turnaround times (TAT), and pricing.
    """
    items, total = test_repo.search_tests(
        db, 
        org_id=current_user.organization_id, 
        q=q, 
        category=category, 
        status="active",
        page=1, 
        page_size=100
    )

    catalog_items = []
    for test in items:
        params_summary = []
        for p in test.parameters:
            params_summary.append({
                "name": p.name,
                "code": p.code,
                "unit": p.unit,
                "reference_range": p.reference_range,
            })
        
        catalog_items.append({
            "id": test.id,
            "code": test.code,
            "name": test.name,
            "category": test.category,
            "description": test.description,
            "price": float(test.price),
            "status": test.status,
            "fasting_required": "fasting" in (test.description or "").lower(),
            "turnaround_time": "24 Hours",
            "parameters_count": len(test.parameters),
            "parameters": params_summary,
        })

    return {
        "items": catalog_items,
        "total": total,
    }


@router.post("", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def create_test(
    test_in: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create a new test in the catalog (ADMIN only).
    """
    if test_in.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a test for another organization"
        )
    
    # Check duplicate code
    existing_test = test_repo.get_by_code(db, org_id=current_user.organization_id, code=test_in.code)
    if existing_test:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A test with code '{test_in.code}' already exists in your organization"
        )
        
    db_obj = Test(
        organization_id=test_in.organization_id,
        code=test_in.code,
        name=test_in.name,
        category=test_in.category,
        description=test_in.description,
        price=test_in.price,
        status="active"
    )
    
    if test_in.parameters:
        for p in test_in.parameters:
            db_obj.parameters.append(
                TestParameter(
                    name=p.name,
                    code=p.code,
                    unit=p.unit,
                    data_type=p.data_type,
                    reference_range=p.reference_range,
                    lower_limit=p.lower_limit,
                    upper_limit=p.upper_limit,
                    critical_low=p.critical_low,
                    critical_high=p.critical_high,
                    ref_gender=p.ref_gender,
                    ref_age_min=p.ref_age_min,
                    ref_age_max=p.ref_age_max,
                    ref_context=p.ref_context,
                    critical_config=p.critical_config,
                    display_order=p.display_order
                )
            )
            
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/{id}", response_model=TestResponse)
def get_test(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed catalog settings of a specific test.
    """
    test = test_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or belongs to another organization"
        )
    return test

@router.patch("/{id}", response_model=TestResponse)
def update_test(
    id: int,
    test_in: TestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update a test details and its parameters catalog configuration (ADMIN only).
    """
    test = test_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found in your organization"
        )
        
    update_data = test_in.model_dump(exclude_unset=True)
    # Extract parameters directly from test_in to keep them as Pydantic objects
    parameters_in = test_in.parameters
    if "parameters" in update_data:
        update_data.pop("parameters")
    
    # Update core attributes
    for field in update_data:
        setattr(test, field, update_data[field])
        
    # Overwrite/replace parameters if provided
    if parameters_in is not None:
        test.parameters.clear()
        for p in parameters_in:
            test.parameters.append(
                TestParameter(
                    name=p.name,
                    code=p.code,
                    unit=p.unit,
                    data_type=p.data_type,
                    reference_range=p.reference_range,
                    lower_limit=p.lower_limit,
                    upper_limit=p.upper_limit,
                    critical_low=p.critical_low,
                    critical_high=p.critical_high,
                    ref_gender=p.ref_gender,
                    ref_age_min=p.ref_age_min,
                    ref_age_max=p.ref_age_max,
                    ref_context=p.ref_context,
                    critical_config=p.critical_config,
                    display_order=p.display_order
                )
            )
            
    db.add(test)
    db.commit()
    db.refresh(test)
    return test
