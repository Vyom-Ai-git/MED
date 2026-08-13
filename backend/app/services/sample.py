import datetime
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from typing import List, Optional, Dict, Any
import logging

from app.models.sample import Sample, Result
from app.models.order import Order, OrderItem
from app.models.test import Test, TestParameter
from app.models.enums import UserRole
from app.schemas.sample import SampleCreate, ResultValueIn
from app.repositories.order import order_repo
from app.repositories.sample import sample_repo
from app.core import events

logger = logging.getLogger("app.services.sample")

# Sample State Machine
VALID_SAMPLE_TRANSITIONS = {
    "Registered": ["Collected", "Cancelled", "Rejected"],
    "Collected": ["Processing", "Cancelled", "Rejected"],
    "Processing": ["Completed", "Rejected"],
    "Completed": [],
    "Rejected": ["Recollection Required"],
    "Recollection Required": [],
    "Cancelled": [],
}

SAMPLE_ROLE_GATES = {
    "Collected": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Processing": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Completed": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Rejected": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Cancelled": [UserRole.ADMIN.value, UserRole.RECEPTION.value],
}


def _generate_sample_identifier(db: Session, org_id: int) -> str:
    """
    Generate unique human-readable sample identifier: SMP-YYYYMMDD-NNNNN.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    max_id = db.execute(select(func.coalesce(func.max(Sample.id), 0))).scalar() or 0
    seq = max_id + 1
    return f"SMP-{today_str}-{seq:05d}"


class SampleService:
    def create_sample(self, db: Session, sample_in: SampleCreate, org_id: int, user_id: int) -> Sample:
        # 1. Verify Order exists & belongs to org
        order = order_repo.get_with_details(db, organization_id=org_id, id=sample_in.order_id)
        if not order:
            raise ValueError(f"Order ID {sample_in.order_id} not found in your organization")

        if order.status == "Cancelled":
            raise ValueError("Cannot create a sample for a cancelled order")

        sample_identifier = _generate_sample_identifier(db, org_id)

        sample = Sample(
            organization_id=org_id,
            branch_id=order.branch_id,
            order_id=order.id,
            sample_identifier=sample_identifier,
            sample_type=sample_in.sample_type,
            priority=sample_in.priority,
            collection_status="Registered",
            notes=sample_in.notes,
        )

        try:
            db.add(sample)
            db.commit()
            db.refresh(sample)
        except Exception as e:
            db.rollback()
            logger.error(f"Sample creation failed: {e}")
            raise ValueError("Database error while registering sample") from e

        events.dispatch("sample.created", {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "order_id": order.id,
            "organization_id": org_id,
            "user_id": user_id,
        })

        return sample

    def transition_status(self, db: Session, sample: Sample, target_status: str, user_role: str, user_id: int) -> Sample:
        allowed = VALID_SAMPLE_TRANSITIONS.get(sample.collection_status, [])
        if target_status not in allowed:
            raise ValueError(f"Cannot transition sample from '{sample.collection_status}' to '{target_status}'")

        required_roles = SAMPLE_ROLE_GATES.get(target_status, [])
        if required_roles and user_role not in required_roles:
            raise PermissionError(f"Role '{user_role}' cannot perform transition to '{target_status}'")

        now = datetime.datetime.now(datetime.timezone.utc)
        sample.collection_status = target_status

        if target_status == "Collected":
            sample.collected_at = now
            sample.collected_by = user_id
            events.dispatch(events.EventTypes.SAMPLE_COLLECTED, {
                "sample_id": sample.id, "sample_identifier": sample.sample_identifier,
                "order_id": sample.order_id, "organization_id": sample.organization_id, "user_id": user_id
            })
            # Also transition order status if Pending
            if sample.order and sample.order.status == "Pending":
                sample.order.status = "Sample Collected"
                db.add(sample.order)

        elif target_status == "Processing":
            sample.processing_started_at = now
            events.dispatch("sample.processing_started", {
                "sample_id": sample.id, "sample_identifier": sample.sample_identifier,
                "order_id": sample.order_id, "organization_id": sample.organization_id, "user_id": user_id
            })
            if sample.order and sample.order.status in ["Pending", "Sample Collected"]:
                sample.order.status = "Processing"
                db.add(sample.order)

        elif target_status == "Completed":
            sample.processing_completed_at = now
            events.dispatch("sample.completed", {
                "sample_id": sample.id, "sample_identifier": sample.sample_identifier,
                "order_id": sample.order_id, "organization_id": sample.organization_id, "user_id": user_id
            })

        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample

    def reject_sample(self, db: Session, sample: Sample, reason: str, user_role: str, user_id: int) -> Sample:
        if user_role not in [UserRole.ADMIN.value, UserRole.TECHNICIAN.value]:
            raise PermissionError("Only Admin and Technician can reject samples")

        if sample.collection_status in ["Completed", "Cancelled"]:
            raise ValueError(f"Cannot reject sample with status '{sample.collection_status}'")

        sample.collection_status = "Rejected"
        sample.rejection_reason = reason
        sample.recollection_required = True

        db.add(sample)
        db.commit()
        db.refresh(sample)

        events.dispatch("sample.rejected", {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "order_id": sample.order_id,
            "organization_id": sample.organization_id,
            "reason": reason,
            "user_id": user_id,
        })
        events.dispatch("sample.recollection_required", {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "order_id": sample.order_id,
            "organization_id": sample.organization_id,
        })
        return sample

    def save_draft_results(
        self, db: Session, sample: Sample, items: List[ResultValueIn], org_id: int, user_id: int
    ) -> List[Result]:
        """
        Save partial draft results for parameters.
        Does not enforce mandatory parameter completion.
        """
        saved_results = []
        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            for item in items:
                res = self._upsert_result(db, sample, item, status="Draft", org_id=org_id, user_id=user_id, now=now)
                saved_results.append(res)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Save draft results transaction failed: {e}")
            raise ValueError(f"Error saving draft results: {str(e)}") from e

        events.dispatch("result.draft_saved", {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "organization_id": org_id,
            "user_id": user_id,
        })
        return saved_results

    def submit_results(
        self, db: Session, sample: Sample, items: List[ResultValueIn], org_id: int, user_id: int
    ) -> List[Result]:
        """
        Validate all mandatory test parameters, calculate abnormal/critical flags, snapshot ranges,
        save results with status="Entered", and transition Order status to "Result Entered".
        """
        # Validate that all parameters for tests in this order item exist in the submission
        order_items = sample.order.items if sample.order else []
        required_params = []
        for oi in order_items:
            if oi.test:
                for param in oi.test.parameters:
                    required_params.append((oi.id, oi.test_id, param))

        submitted_param_keys = {(i.order_item_id, i.parameter_id) for i in items if i.raw_value and i.raw_value.strip() != ""}

        missing_names = []
        for oi_id, test_id, param in required_params:
            if (oi_id, param.id) not in submitted_param_keys:
                missing_names.append(f"{param.name} ({param.code})")

        if missing_names:
            raise ValueError(f"Cannot submit incomplete results. Missing required parameters: {', '.join(missing_names)}")

        saved_results = []
        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            for item in items:
                res = self._upsert_result(db, sample, item, status="Entered", org_id=org_id, user_id=user_id, now=now)
                saved_results.append(res)

            # Update sample status to Completed if processing
            if sample.collection_status in ["Registered", "Collected", "Processing"]:
                sample.collection_status = "Completed"
                sample.processing_completed_at = now
                db.add(sample)

            # Update order status to Result Entered
            if sample.order and sample.order.status in ["Pending", "Sample Collected", "Processing"]:
                sample.order.status = "Result Entered"
                db.add(sample.order)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Submit results transaction failed: {e}")
            raise ValueError(str(e)) from e

        events.dispatch(events.EventTypes.RESULT_ENTERED, {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "order_id": sample.order_id,
            "organization_id": org_id,
            "user_id": user_id,
        })
        events.dispatch("result.entered", {
            "sample_id": sample.id,
            "sample_identifier": sample.sample_identifier,
            "order_id": sample.order_id,
            "organization_id": org_id,
            "user_id": user_id,
        })
        return saved_results

    def _upsert_result(
        self, db: Session, sample: Sample, item: ResultValueIn, status: str, org_id: int, user_id: int, now: datetime.datetime
    ) -> Result:
        # Load parameter definition
        param = db.query(TestParameter).filter(TestParameter.id == item.parameter_id).first()
        if not param:
            raise ValueError(f"Parameter ID {item.parameter_id} not found")

        # Validate data type
        val_str = (item.raw_value or "").strip()
        num_val: Optional[Decimal] = None
        txt_val: Optional[str] = val_str if val_str else None

        if val_str:
            if param.data_type == "numeric":
                try:
                    num_val = Decimal(val_str)
                except (InvalidOperation, ValueError):
                    raise ValueError(f"Invalid numeric value '{val_str}' for parameter '{param.name}'")

        # Calculate Abnormal & Critical Flags deterministically
        abnormal_flag = "NORMAL"
        critical_flag = False

        if num_val is not None and param.data_type == "numeric":
            # Reference range flags
            if param.lower_limit is not None and num_val < param.lower_limit:
                abnormal_flag = "LOW"
            elif param.upper_limit is not None and num_val > param.upper_limit:
                abnormal_flag = "HIGH"

            # Critical range flags
            if param.critical_low is not None and num_val <= param.critical_low:
                critical_flag = True
            elif param.critical_high is not None and num_val >= param.critical_high:
                critical_flag = True

        # Check existing result record
        existing = db.query(Result).filter(
            Result.organization_id == org_id,
            Result.sample_id == sample.id,
            Result.order_item_id == item.order_item_id,
            Result.parameter_id == item.parameter_id,
        ).first()

        if existing:
            if existing.status == "Verified":
                raise ValueError("Cannot edit a result that has already been Verified.")
            existing.raw_value = val_str
            existing.numeric_value = num_val
            existing.text_value = txt_val
            existing.unit = param.unit
            existing.reference_low = param.lower_limit
            existing.reference_high = param.upper_limit
            existing.abnormal_flag = abnormal_flag
            existing.critical_flag = critical_flag
            existing.status = status
            existing.entered_by = user_id
            existing.entered_at = now
            db.add(existing)
            return existing
        else:
            new_res = Result(
                organization_id=org_id,
                sample_id=sample.id,
                order_item_id=item.order_item_id,
                test_id=item.test_id,
                parameter_id=item.parameter_id,
                raw_value=val_str,
                numeric_value=num_val,
                text_value=txt_val,
                unit=param.unit,
                reference_low=param.lower_limit,
                reference_high=param.upper_limit,
                abnormal_flag=abnormal_flag,
                critical_flag=critical_flag,
                status=status,
                entered_by=user_id,
                entered_at=now,
            )
            db.add(new_res)
            return new_res


sample_service = SampleService()
