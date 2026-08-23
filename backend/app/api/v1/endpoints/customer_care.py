from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
import logging

from app.core.database import get_db
from app.models.customer_care import CustomerCareHandoff
from app.models.patient import Patient
from app.models.order import Order
from app.schemas.customer_care import (
    CustomerCareHandoffCreate,
    CustomerCareHandoffResponse,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.customer_care")


@router.post("/handoff", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_customer_care_handoff(
    handoff_in: CustomerCareHandoffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a customer care escalation/handoff ticket (Capability 11).
    """
    org_id = current_user.organization_id

    patient_name = None
    patient_phone = None
    if handoff_in.patient_id:
        patient = db.query(Patient).filter(Patient.id == handoff_in.patient_id, Patient.organization_id == org_id).first()
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name}"
            patient_phone = patient.phone

    order_num = None
    if handoff_in.order_id:
        order = db.query(Order).filter(Order.id == handoff_in.order_id, Order.organization_id == org_id).first()
        if order:
            order_num = order.order_number

    ticket_num = f"TKT-2026-{secrets.randbelow(89999) + 10000}"
    ticket = CustomerCareHandoff(
        organization_id=org_id,
        ticket_number=ticket_num,
        patient_id=handoff_in.patient_id,
        order_id=handoff_in.order_id,
        channel=handoff_in.channel,
        category=handoff_in.category,
        priority=handoff_in.priority,
        summary=handoff_in.summary,
        conversation_transcript=handoff_in.conversation_transcript,
        status="Open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "id": ticket.id,
        "organization_id": ticket.organization_id,
        "ticket_number": ticket.ticket_number,
        "patient_id": ticket.patient_id,
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "order_id": ticket.order_id,
        "order_number": order_num,
        "channel": ticket.channel,
        "category": ticket.category,
        "priority": ticket.priority,
        "summary": ticket.summary,
        "conversation_transcript": ticket.conversation_transcript,
        "status": ticket.status,
        "assigned_agent_id": ticket.assigned_agent_id,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }


@router.get("/handoff", response_model=dict)
def list_customer_care_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    """
    List customer-care handoff tickets with optional status/priority filtering.
    """
    query = db.query(CustomerCareHandoff).filter(
        CustomerCareHandoff.organization_id == current_user.organization_id
    )

    if status:
        query = query.filter(CustomerCareHandoff.status == status)
    if priority:
        query = query.filter(CustomerCareHandoff.priority == priority)

    tickets = query.order_by(CustomerCareHandoff.created_at.desc()).all()
    results = []

    for t in tickets:
        p_name = None
        p_phone = None
        if t.patient_id:
            p = db.query(Patient).filter(Patient.id == t.patient_id).first()
            if p:
                p_name = f"{p.first_name} {p.last_name}"
                p_phone = p.phone

        o_num = None
        if t.order_id:
            o = db.query(Order).filter(Order.id == t.order_id).first()
            if o:
                o_num = o.order_number

        results.append({
            "id": t.id,
            "ticket_number": t.ticket_number,
            "patient_id": t.patient_id,
            "patient_name": p_name,
            "patient_phone": p_phone,
            "order_id": t.order_id,
            "order_number": o_num,
            "channel": t.channel,
            "category": t.category,
            "priority": t.priority,
            "summary": t.summary,
            "status": t.status,
            "created_at": t.created_at,
        })

    return {"items": results, "total": len(results)}
