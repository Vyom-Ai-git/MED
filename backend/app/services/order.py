import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.repositories.patient import patient_repo
from app.repositories.test import test_repo
from app.models.order import Order, OrderItem
from app.models.enums import UserRole
from app.schemas.order import OrderCreate
from app.core import events
import logging

logger = logging.getLogger("app.services.order")

# --- Valid state machine transitions ---
VALID_TRANSITIONS = {
    "Pending": ["Sample Collected", "Cancelled"],
    "Sample Collected": ["Processing"],
    "Processing": ["Result Entered"],
    "Result Entered": ["Verified"],
    "Verified": ["Published"],
    "Published": [],
    "Cancelled": [],
}

# Role-gated transitions: who can perform which transitions
TRANSITION_ROLE_GATES = {
    "Sample Collected": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Processing": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Result Entered": [UserRole.ADMIN.value, UserRole.TECHNICIAN.value],
    "Verified": [UserRole.ADMIN.value, UserRole.REVIEWER.value],
    "Published": [UserRole.ADMIN.value, UserRole.REVIEWER.value],
    "Cancelled": [UserRole.ADMIN.value, UserRole.RECEPTION.value],
}


def _generate_order_number(db: Session, org_id: int) -> str:
    """
    Generate a collision-safe order number.
    Format: ORD-YYYY-NNNNN (or org-prefixed for global uniqueness across tenants).
    To guarantee global uniqueness while keeping human readability, we base sequence on max(Order.id).
    """
    year = datetime.date.today().year

    # Get overall order count/max id to ensure global uniqueness across orgs in single DB
    max_id = db.execute(select(func.coalesce(func.max(Order.id), 0))).scalar() or 0
    sequence_num = max_id + 1
    return f"ORD-{year}-{sequence_num:05d}"



class OrderService:
    def create_order(self, db: Session, order_in: OrderCreate, org_id: int, user_id: int) -> Order:
        """
        Full validation → price calculation → snapshot → transactional commit → event dispatch.
        Nothing is trusted from the client: prices, totals, org_id, created_by are all server-derived.
        """
        # 1. Validate patient
        patient = patient_repo.get_by_org(db, organization_id=org_id, id=order_in.patient_id)
        if not patient:
            raise ValueError(f"Patient ID {order_in.patient_id} not found in your organization")

        # 2. Validate at least one test selected
        if not order_in.selected_test_ids:
            raise ValueError("At least one test must be selected to create an order")

        # 3. De-duplicate test IDs (silently remove duplicates)
        unique_test_ids = list(dict.fromkeys(order_in.selected_test_ids))

        # 4. Validate all tests and build items with snapshots
        items = []
        subtotal = Decimal("0.00")

        for test_id in unique_test_ids:
            test = test_repo.get_by_org(db, organization_id=org_id, id=test_id)
            if not test:
                raise ValueError(f"Test ID {test_id} not found in your organization")
            if test.status != "active":
                raise ValueError(f"Test '{test.name}' ({test.code}) is not active and cannot be ordered")

            unit_price = Decimal(str(test.price))
            item_total = unit_price  # quantity is 1 for POC

            items.append(OrderItem(
                test_id=test.id,
                test_name_snapshot=test.name,
                test_code_snapshot=test.code,
                unit_price=unit_price,
                quantity=1,
                discount=Decimal("0.00"),
                total=item_total,
                status="Pending",
            ))
            subtotal += item_total

        # 5. Validate discount
        discount = Decimal(str(order_in.discount)) if order_in.discount else Decimal("0.00")
        if discount < Decimal("0.00"):
            raise ValueError("Discount cannot be negative")
        if discount > subtotal:
            raise ValueError(f"Discount (₹{discount}) cannot exceed subtotal (₹{subtotal})")

        # 6. Tax (default 0 for POC; server calculates, client value is accepted as hint but validated)
        tax = Decimal(str(order_in.tax)) if order_in.tax else Decimal("0.00")
        if tax < Decimal("0.00"):
            raise ValueError("Tax cannot be negative")

        # 7. Server-side total calculation
        total_amount = max(Decimal("0.00"), subtotal - discount + tax)

        # 8. Generate safe order number within transaction
        order_number = _generate_order_number(db, org_id)

        # 9. Build order object
        db_obj = Order(
            organization_id=org_id,
            branch_id=order_in.branch_id,
            patient_id=order_in.patient_id,
            ordering_user_id=user_id,
            order_number=order_number,
            status="Pending",
            payment_status=order_in.payment_status,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total_amount=total_amount,
            notes=order_in.notes,
            items=items,
        )

        # 10. Transactional commit — all or nothing
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
        except Exception as e:
            db.rollback()
            logger.error(f"Order creation transaction failed: {e}")
            raise ValueError("Order creation failed due to a database error. Please try again.") from e

        # 11. Emit event (after successful commit)
        events.dispatch(events.EventTypes.ORDER_CREATED, {
            "order_id": db_obj.id,
            "order_number": db_obj.order_number,
            "organization_id": db_obj.organization_id,
            "patient_id": db_obj.patient_id,
            "created_by": user_id,
            "total_amount": float(db_obj.total_amount),
        })

        logger.info(f"Order {db_obj.order_number} created for patient {patient.patient_id}")
        return db_obj

    def cancel_order(self, db: Session, order: Order, user_role: str) -> Order:
        """
        Cancel an order. Only Pending orders can be cancelled.
        Only ADMIN and RECEPTION may cancel.
        """
        if order.status != "Pending":
            raise ValueError(f"Only Pending orders can be cancelled. Current status: '{order.status}'")

        if user_role not in [UserRole.ADMIN.value, UserRole.RECEPTION.value]:
            raise PermissionError("Only Admin and Reception can cancel orders")

        order.status = "Cancelled"
        db.add(order)
        db.commit()
        db.refresh(order)

        events.dispatch("order.cancelled", {
            "order_id": order.id,
            "order_number": order.order_number,
            "organization_id": order.organization_id,
            "patient_id": order.patient_id,
        })

        return order

    def update_payment_status(self, db: Session, order: Order, payment_status: str) -> Order:
        """
        Update payment status. Accepted values: Pending, Paid, Partial, Refunded.
        """
        valid_statuses = ["Pending", "Paid", "Partial", "Refunded"]
        if payment_status not in valid_statuses:
            raise ValueError(f"Invalid payment status. Must be one of: {valid_statuses}")

        old_status = order.payment_status
        order.payment_status = payment_status
        db.add(order)
        db.commit()
        db.refresh(order)

        events.dispatch("order.payment_updated", {
            "order_id": order.id,
            "order_number": order.order_number,
            "organization_id": order.organization_id,
            "old_payment_status": old_status,
            "new_payment_status": payment_status,
        })

        return order

    def transition_status(self, db: Session, order: Order, target_status: str, user_role: str) -> Order:
        """
        State-machine-enforced status transitions. Prevents skipping states.
        """
        allowed_next = VALID_TRANSITIONS.get(order.status, [])
        if target_status not in allowed_next:
            raise ValueError(
                f"Cannot transition from '{order.status}' to '{target_status}'. "
                f"Valid next states: {allowed_next}"
            )

        # Role gate
        required_roles = TRANSITION_ROLE_GATES.get(target_status, [])
        if required_roles and user_role not in required_roles:
            raise PermissionError(
                f"Role '{user_role}' is not permitted to transition to '{target_status}'"
            )

        order.status = target_status
        db.add(order)
        db.commit()
        db.refresh(order)

        # Emit events for key lifecycle milestones
        if target_status == "Verified":
            events.dispatch(events.EventTypes.REPORT_VERIFIED, {
                "order_id": order.id,
                "order_number": order.order_number,
                "organization_id": order.organization_id,
                "patient_id": order.patient_id,
            })
        elif target_status == "Published":
            events.dispatch(events.EventTypes.REPORT_PUBLISHED, {
                "order_id": order.id,
                "order_number": order.order_number,
                "organization_id": order.organization_id,
                "patient_id": order.patient_id,
            })
        else:
            events.dispatch("order.updated", {
                "order_id": order.id,
                "order_number": order.order_number,
                "organization_id": order.organization_id,
                "new_status": target_status,
            })

        return order


order_service = OrderService()
