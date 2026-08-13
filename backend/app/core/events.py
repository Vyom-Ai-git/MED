import logging
from typing import Callable, List, Dict, Any

logger = logging.getLogger("app.events")

# Event Registry maps event names to list of handlers
_event_registry: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

def subscribe(event_name: str, handler: Callable[[Dict[str, Any]], None]) -> None:
    """
    Subscribe a handler function to a specific event.
    """
    if event_name not in _event_registry:
        _event_registry[event_name] = []
    _event_registry[event_name].append(handler)
    logger.info(f"Subscribed handler {handler.__name__} to event: {event_name}")

def dispatch(event_name: str, payload: Dict[str, Any]) -> None:
    """
    Dispatch an event with a payload to all subscribed handlers.
    """
    logger.info(f"Dispatching event: {event_name} | Payload keys: {list(payload.keys())}")
    
    # In Phase 0, we simply log the event dispatch.
    # Future modules can register their listeners via subscribe()
    handlers = _event_registry.get(event_name, [])
    for handler in handlers:
        try:
            handler(payload)
        except Exception as e:
            logger.error(f"Error executing handler {handler.__name__} for event {event_name}: {str(e)}")

# Define event type constants for consistency
class EventTypes:
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_CANCELLED = "order.cancelled"
    SAMPLE_CREATED = "sample.created"
    SAMPLE_COLLECTED = "sample.collected"
    SAMPLE_PROCESSING_STARTED = "sample.processing_started"
    SAMPLE_COMPLETED = "sample.completed"
    SAMPLE_REJECTED = "sample.rejected"
    RESULT_ENTERED = "result.entered"
    RESULT_RETURNED_FOR_CORRECTION = "result.returned_for_correction"
    RESULT_VERIFIED = "result.verified"
    ORDER_VERIFIED = "order.verified"
    REPORT_GENERATED = "report.generated"
    REPORT_AVAILABLE = "report.available"


# Auto-subscribe domain event audit listener
try:
    from app.services.audit import domain_event_audit_listener
    for event_attr in dir(EventTypes):
        if not event_attr.startswith("__"):
            evt_val = getattr(EventTypes, event_attr)
            if isinstance(evt_val, str):
                subscribe(evt_val, domain_event_audit_listener)
except Exception as e:
    logger.warning(f"Could not auto-register audit listener: {str(e)}")

# Auto-subscribe integration dispatch listener for report.available
try:
    from app.services.integration import handle_report_available_event
    subscribe(EventTypes.REPORT_AVAILABLE, handle_report_available_event)
except Exception as e:
    logger.warning(f"Could not auto-register integration event listener: {str(e)}")

