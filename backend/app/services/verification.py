import logging
import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.sample import Sample, Result
from app.models.result_verification import ResultVerification
from app.models.order import Order
from app.models.user import User
from app.core.events import dispatch

logger = logging.getLogger("app.services.verification")

class VerificationService:
    def approve_sample_results(
        self, db: Session, sample: Sample, org_id: int, reviewer_id: int, reason: Optional[str] = None
    ) -> List[Result]:
        """
        Approve all results recorded for a sample.
        Transitions eligible results from 'Entered' or 'Under Review' to 'Verified'.
        Creates ResultVerification audit records.
        If all results across the sample's order are verified, transitions Order to 'Verified'.
        Emits result.verified and order.verified / report.ready events.
        """
        results = db.query(Result).filter(
            Result.organization_id == org_id,
            Result.sample_id == sample.id
        ).all()

        if not results:
            raise ValueError(f"No results found for sample {sample.sample_identifier}")

        # Check if any result is not in an approvable state
        for r in results:
            if r.status not in ["Entered", "Under Review"]:
                if r.status == "Verified":
                    continue  # Already verified
                raise ValueError(f"Cannot approve result in state '{r.status}'. Results must be Submitted/Entered before approval.")

        now = datetime.datetime.now(datetime.timezone.utc)
        approved_results = []

        try:
            for r in results:
                if r.status != "Verified":
                    r.status = "Verified"
                    r.verified_by = reviewer_id
                    r.verified_at = now
                    db.add(r)

                    # Add verification audit history
                    audit = ResultVerification(
                        organization_id=org_id,
                        sample_id=sample.id,
                        result_id=r.id,
                        action="Approved",
                        performed_by=reviewer_id,
                        reason=reason or "Approved by authorized reviewer",
                        created_at=now
                    )
                    db.add(audit)
                    approved_results.append(r)

            # Check overall order verification status across all samples/order_items
            order = sample.order
            if order:
                # Check if all results for this order are Verified
                all_order_results = db.query(Result).filter(
                    Result.organization_id == org_id,
                    Result.sample_id.in_([s.id for s in order.samples])
                ).all()

                if all_order_results and all(r.status == "Verified" for r in all_order_results):
                    order.status = "Verified"
                    db.add(order)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Approve sample results transaction failed: {e}")
            raise ValueError(f"Approval failed: {str(e)}") from e

        # Emit verification events
        for r in approved_results:
            dispatch("result.verified", {
                "result_id": r.id,
                "sample_id": sample.id,
                "order_id": sample.order_id,
                "organization_id": org_id,
                "verified_by": reviewer_id,
                "verified_at": now.isoformat(),
            })

        if sample.order and sample.order.status == "Verified":
            dispatch("order.verified", {
                "order_id": sample.order.id,
                "order_number": sample.order.order_number,
                "organization_id": org_id,
                "verified_at": now.isoformat(),
            })
            dispatch("report.ready", {
                "order_id": sample.order.id,
                "order_number": sample.order.order_number,
                "organization_id": org_id,
            })

        return results

    def return_sample_results_for_correction(
        self, db: Session, sample: Sample, org_id: int, reviewer_id: int, reason: str
    ) -> List[Result]:
        """
        Return sample results to technician for correction.
        Requires a non-empty reason.
        Transitions results from 'Entered' / 'Under Review' to 'Correction Required'.
        Records reviewer reason and creates ResultVerification audit record.
        Emits result.returned_for_correction event.
        """
        if not reason or not reason.strip():
            raise ValueError("Correction reason is required when returning results for correction.")

        results = db.query(Result).filter(
            Result.organization_id == org_id,
            Result.sample_id == sample.id
        ).all()

        if not results:
            raise ValueError(f"No results found for sample {sample.sample_identifier}")

        for r in results:
            if r.status == "Verified":
                raise ValueError("Cannot return verified results for correction.")

        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            for r in results:
                r.status = "Correction Required"
                r.correction_reason = reason.strip()
                db.add(r)

                audit = ResultVerification(
                    organization_id=org_id,
                    sample_id=sample.id,
                    result_id=r.id,
                    action="Returned for Correction",
                    performed_by=reviewer_id,
                    reason=reason.strip(),
                    created_at=now
                )
                db.add(audit)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Return for correction transaction failed: {e}")
            raise ValueError(f"Return for correction failed: {str(e)}") from e

        dispatch("result.returned_for_correction", {
            "sample_id": sample.id,
            "order_id": sample.order_id,
            "organization_id": org_id,
            "returned_by": reviewer_id,
            "reason": reason.strip(),
        })

        return results

    def get_verification_history(self, db: Session, org_id: int, sample_id: int) -> List[ResultVerification]:
        """
        Get complete verification history for a sample specimen.
        """
        return db.query(ResultVerification).filter(
            ResultVerification.organization_id == org_id,
            ResultVerification.sample_id == sample_id
        ).order_by(ResultVerification.created_at.asc()).all()


verification_service = VerificationService()
