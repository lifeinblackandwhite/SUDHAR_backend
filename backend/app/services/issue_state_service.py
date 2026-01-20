from fastapi import HTTPException
from app.core.issue_transitions import is_valid_transition
from app.core.issue_states import IssueState

# =========================================================
# CENTRAL ISSUE STATE TRANSITION SERVICE
# =========================================================
# RULES:
# - ONLY validates + mutates issue.status
# - NO database writes
# - NO logging
# - NO notifications
# =========================================================

def change_issue_state(
    *,
    issue,
    new_state: IssueState,
):
    current_state = IssueState(issue.status)

    if not is_valid_transition(current_state, new_state):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current_state.value} → {new_state.value}"
        )

    issue.status = new_state.value
