async def evaluate_verification(issue_id, db):
    confirms = await db.execute(
        "SELECT COUNT(*) FROM issue_verifications WHERE issue_id=:id AND vote=true",
        {"id": issue_id}
    )
    denies = await db.execute(
        "SELECT COUNT(*) FROM issue_verifications WHERE issue_id=:id AND vote=false",
        {"id": issue_id}
    )

    if denies.scalar() >= 3:
        return IssueState.COMMUNITY_REJECTED
    if confirms.scalar() >= 3:
        return IssueState.VERIFIED
    return None
