"""
audit_service.py — Append admin actions to the admin_audit_log table.
Caller commits the session; this helper only adds + flushes.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit_log import AdminAuditLog


async def log_admin_action(
    db: AsyncSession,
    admin_user_id: uuid.UUID,
    action: str,
    target_user_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> AdminAuditLog:
    """Append a single audit log entry.

    Args:
        db: Active async session.
        admin_user_id: The admin who performed the action.
        action: Short verb-ish identifier (e.g. "plan_changed", "overrides_updated").
        target_user_id: User who was acted upon. Null for actions that don't target a user.
        details: Arbitrary JSON payload — typically {"before": ..., "after": ...}.

    Returns:
        The persisted AdminAuditLog row (flushed but not committed).
    """
    entry = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        target_user_id=target_user_id,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry
