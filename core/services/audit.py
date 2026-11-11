from typing import Any, Dict, Optional
from core.models import AuditLog


def log_audit(
    actor,
    action: str,
    instance: Any,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None
) -> AuditLog:
    """
    Records an immutable audit event for compliance and operational tracking.
    """
    model_name = instance._meta.label if hasattr(instance, '_meta') else str(type(instance).__name__)
    object_id = str(getattr(instance, 'pk', ''))
    object_repr = str(instance)[:255]

    return AuditLog.objects.create(
        actor=actor if (actor and actor.is_authenticated) else None,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes or {},
        ip_address=ip_address,
        request_id=request_id or ''
    )

