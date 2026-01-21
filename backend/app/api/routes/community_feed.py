from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Issue, IssueMedia, IssueVerification
from app.core.issue_states import IssueState

router = APIRouter(prefix="/community", tags=["Community"])


@router.get("/feed")
async def resident_issue_feed(
    state: str,
    city: str,
    pincode: str,
    category: str,  # REQUIRED
    db: AsyncSession = Depends(get_db)
):
    # Get issues
    query = (
        select(Issue)
        .where(Issue.status == IssueState.UNDER_VERIFICATION.value)
        .where(Issue.abuse_cleared.is_(True))
        .where(func.lower(Issue.city) == city.lower())
        .where(func.lower(Issue.state) == state.lower())
        .where(Issue.pincode == pincode)
        .where(func.lower(Issue.category) == category.lower())
        .order_by(Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    # Build response with images
    response = []
    for issue in issues:
        # Get images for this issue
        media_result = await db.execute(
            select(IssueMedia).where(IssueMedia.issue_id == issue.id)
        )
        media_items = media_result.scalars().all()
        
        # Convert file paths to URLs
        image_urls = []
        for media in media_items:
            # Extract filename from path like "/code/uploads/1_image.jpg"
            filename = media.file_path.split("/")[-1]
            image_urls.append(f"/uploads/{filename}")
        
        response.append({
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "state": issue.state,
            "city": issue.city,
            "area": issue.area,
            "pincode": issue.pincode,
            "status": issue.status,
            "created_at": issue.created_at,
            "images": image_urls,  # Added images
        })

    return response


@router.get("/my-issues/{user_id}")
async def get_my_issues(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all issues that the user has either:
    - Reported (user_id matches issue.user_id)
    - Verified (user_id matches issue_verifications.verifier_id)
    
    Returns issues with role indicator (reported/verified) and current status.
    """
    
    # Get issues reported by user
    reported_query = select(Issue).where(Issue.user_id == user_id)
    reported_result = await db.execute(reported_query)
    reported_issues = reported_result.scalars().all()
    
    # Get issue IDs verified by user
    verified_query = (
        select(IssueVerification.issue_id)
        .where(IssueVerification.verifier_id == user_id)
        .distinct()
    )
    verified_result = await db.execute(verified_query)
    verified_issue_ids = [row[0] for row in verified_result.fetchall()]
    
    # Get verified issues
    verified_issues = []
    if verified_issue_ids:
        verified_issues_query = select(Issue).where(Issue.id.in_(verified_issue_ids))
        verified_issues_result = await db.execute(verified_issues_query)
        verified_issues = verified_issues_result.scalars().all()
    
    # Build response
    response = []
    seen_ids = set()
    
    # Add reported issues
    for issue in reported_issues:
        media_result = await db.execute(
            select(IssueMedia).where(IssueMedia.issue_id == issue.id)
        )
        media_items = media_result.scalars().all()
        image_urls = [f"/uploads/{m.file_path.split('/')[-1]}" for m in media_items]
        
        # Check if user also verified this issue
        role = "reported"
        if issue.id in verified_issue_ids:
            role = "reported_and_verified"
        
        response.append({
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "state": issue.state,
            "city": issue.city,
            "area": issue.area,
            "pincode": issue.pincode,
            "status": issue.status,
            "priority_score": round(issue.priority_score, 2) if issue.priority_score else 0,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "images": image_urls,
            "role": role,
        })
        seen_ids.add(issue.id)
    
    # Add verified-only issues (not reported by user)
    for issue in verified_issues:
        if issue.id in seen_ids:
            continue
        
        media_result = await db.execute(
            select(IssueMedia).where(IssueMedia.issue_id == issue.id)
        )
        media_items = media_result.scalars().all()
        image_urls = [f"/uploads/{m.file_path.split('/')[-1]}" for m in media_items]
        
        response.append({
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "state": issue.state,
            "city": issue.city,
            "area": issue.area,
            "pincode": issue.pincode,
            "status": issue.status,
            "priority_score": round(issue.priority_score, 2) if issue.priority_score else 0,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "images": image_urls,
            "role": "verified",
        })
    
    # Sort by created_at descending
    response.sort(key=lambda x: x['created_at'] or '', reverse=True)
    
    return {
        "user_id": user_id,
        "total": len(response),
        "reported_count": len([r for r in response if 'reported' in r['role']]),
        "verified_count": len([r for r in response if 'verified' in r['role']]),
        "issues": response,
    }
