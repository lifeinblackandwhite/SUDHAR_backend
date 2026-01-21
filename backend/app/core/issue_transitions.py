from app.core.issue_states import IssueState

ISSUE_TRANSITIONS = {
    IssueState.SUBMITTED: {
        IssueState.AUTO_REJECTED,
        IssueState.UNDER_VERIFICATION,
    },
    IssueState.UNDER_VERIFICATION: {
        IssueState.COMMUNITY_REJECTED,
        IssueState.VERIFIED,
        IssueState.AUTO_REJECTED,
        IssueState.COMMUNITY_REVIEW,
        IssueState.IN_PROGRESS,  # Official override - skip community verification
    },
    IssueState.VERIFIED: {
        IssueState.RANKED,
        IssueState.ASSIGNED,
        IssueState.IN_PROGRESS,  # Official can directly start work
    },
    IssueState.ASSIGNED: {
        IssueState.IN_PROGRESS,
    },
    IssueState.IN_PROGRESS: {
        IssueState.RESOLVED,
    },
    IssueState.RESOLVED: {
        IssueState.CLOSED,
    },
    IssueState.RANKED: {
        IssueState.ASSIGNED,
        IssueState.IN_PROGRESS,  # Official can directly start work
    },
    IssueState.COMMUNITY_REVIEW: {
        IssueState.VERIFIED,
        IssueState.COMMUNITY_REJECTED,
    },
}


def is_valid_transition(current, next_):
    return next_ in ISSUE_TRANSITIONS.get(current, set())


