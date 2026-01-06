from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import IssueEvent

async def log_event(
    db: AsyncSession,
    *,
    issue_id: int,
    actor_type: str,
    actor_id: str | None,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None
):
    event = IssueEvent(
        issue_id=issue_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(event)
