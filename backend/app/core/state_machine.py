from app.core.issue_states import IssueState
from app.core.issue_transitions import is_valid_transition
from fastapi import HTTPException

def enforce_transition(
    *,
    current_state: IssueState,
    next_state: IssueState,
    actor_role: str,
    has_evidence: bool = False
):
    # 1️⃣ Structural check
    if not is_valid_transition(current_state, next_state):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current_state} → {next_state}"
        )

    # 2️⃣ Role enforcement
    ROLE_RULES = {
        IssueState.ASSIGNED: {"official"},
        IssueState.IN_PROGRESS: {"official"},
        IssueState.RESOLVED: {"official"},
        IssueState.CLOSED: {"system"},
    }

    allowed_roles = ROLE_RULES.get(next_state)
    if allowed_roles and actor_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this transition"
        )

    # 3️⃣ Evidence enforcement
    if next_state in {IssueState.IN_PROGRESS, IssueState.RESOLVED} and not has_evidence:
        raise HTTPException(
            status_code=400,
            detail="Proof image required for this transition"
        )

    return True
