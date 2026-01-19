from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.issue_transitions import is_valid_transition
from app.core.issue_states import IssueState
from app.services.notification_service import NotificationService
from app.services.audit_logger import log_event


# ✅ MUST be async
async def change_issue_state(
    *,
    issue,
    new_state: IssueState,
    db: AsyncSession,
    actor_type: str,
    actor_id: str | None = None
):
    # 🔒 Enforce state machine
    if not is_valid_transition(issue.status, new_state):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {issue.status} → {new_state}"
        )

    old_state = issue.status
    issue.status = new_state

    # 🧾 Audit log
    await log_event(
        db=db,
        issue_id=issue.id,
        actor_type=actor_type,
        actor_id=actor_id,
        action="STATE_CHANGED",
        old_value=old_state,
        new_value=new_state
    )

    # 🔔 Trigger notifications on specific transitions
    if new_state == IssueState.UNDER_VERIFICATION:
        await NotificationService().notify_community(issue)

    if new_state == IssueState.VERIFIED:
        await NotificationService().notify_department(issue)

    if new_state == IssueState.RESOLVED:
        await NotificationService().notify_resolution(issue)

    return issue
