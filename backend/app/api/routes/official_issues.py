"""
Government Official Issue Feed Routes.
Fetches issues matching official's city and category.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import Issue, IssueMedia, GovtOfficial
from app.core.issue_states import IssueState

router = APIRouter(prefix="/officials", tags=["Government Officials"])


@router.get("/issues/{sso}")
async def get_official_issues(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch issues assigned to a government official based on their city and category.
    Issues must be COMMUNITY_VERIFIED or later in the lifecycle.
    """
    # 1. Get official's profile
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(
            status_code=404,
            detail=f"Official with SSO '{sso}' not found"
        )

    # 2. Define valid statuses for officials to see
    # Officials see all issues in their city/category (excluding rejected ones)
    valid_statuses = [
        IssueState.SUBMITTED.value,
        IssueState.UNDER_VERIFICATION.value,
        IssueState.VERIFIED.value,
        IssueState.COMMUNITY_REVIEW.value,
        IssueState.RANKED.value,
        IssueState.ASSIGNED.value,
        IssueState.IN_PROGRESS.value,
        IssueState.RESOLVED.value,
        IssueState.CLOSED.value,
    ]

    # 3. Query issues matching official's city and category
    query = (
        select(Issue)
        .where(Issue.status.in_(valid_statuses))
        .where(func.lower(Issue.city) == official.city.lower())
        .where(func.lower(Issue.category) == official.category.lower())
        .order_by(Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    # 4. Build response with images
    response = []
    for issue in issues:
        # Get images for this issue
        media_result = await db.execute(
            select(IssueMedia).where(IssueMedia.issue_id == issue.id)
        )
        media_items = media_result.scalars().all()

        image_urls = []
        for media in media_items:
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
            "priority_score": round(issue.priority_score, 2) if issue.priority_score else 0,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "images": image_urls,
        })

    return {
        "official": {
            "sso": official.sso,
            "name": official.name,
            "department": official.department,
            "city": official.city,
            "category": official.category,
        },
        "issues": response,
        "count": len(response)
    }


@router.post("/issues/{issue_id}/update-status")
async def update_issue_status(
    issue_id: int,
    sso: str = Query(...),
    new_status: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Allow official to update issue status.
    Valid transitions: ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
    """
    # Validate official
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(status_code=404, detail="Official not found")

    # Get issue
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Validate status
    valid_statuses = ["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    # Update
    issue.status = new_status
    await db.commit()

    return {
        "status": "success",
        "issue_id": issue_id,
        "new_status": new_status
    }


@router.get("/pending/{sso}")
async def get_pending_issues(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch pending issues for officials grouped by verification status.
    - verified: Issues that passed abuse prevention (UNDER_VERIFICATION)
    - community_verified: Issues verified by community (VERIFIED, COMMUNITY_REVIEW) - sorted by priority
    """
    # 1. Get official's profile
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(
            status_code=404,
            detail=f"Official with SSO '{sso}' not found"
        )

    async def fetch_issues_by_status(statuses: list, order_by_priority: bool = False):
        query = (
            select(Issue)
            .where(Issue.status.in_(statuses))
            .where(func.lower(Issue.city) == official.city.lower())
            .where(func.lower(Issue.category) == official.category.lower())
        )
        
        # Sort by priority_score DESC for community verified issues
        if order_by_priority:
            query = query.order_by(Issue.priority_score.desc(), Issue.created_at.desc())
        else:
            query = query.order_by(Issue.created_at.desc())
            
        result = await db.execute(query)
        issues = result.scalars().all()
        
        response = []
        for issue in issues:
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
            })
        return response

    # 2. Fetch issues by status groups
    # "Verified" = passed abuse prevention, awaiting community verification
    verified_issues = await fetch_issues_by_status([IssueState.UNDER_VERIFICATION.value])
    
    # "Community Verified" = verified by community, sorted by priority score
    community_verified_issues = await fetch_issues_by_status(
        [
            IssueState.VERIFIED.value,
            IssueState.COMMUNITY_REVIEW.value,
            IssueState.RANKED.value,
        ],
        order_by_priority=True
    )

    return {
        "official": {
            "sso": official.sso,
            "name": official.name,
            "city": official.city,
            "category": official.category,
        },
        "verified": verified_issues,
        "community_verified": community_verified_issues,
        "verified_count": len(verified_issues),
        "community_verified_count": len(community_verified_issues),
    }


@router.post("/update/{issue_id}")
async def update_issue_by_official(
    issue_id: int,
    status: str = Form(...),
    remarks: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update issue status, remarks, dates, and optionally upload a progress image.
    """
    import os
    from datetime import datetime
    
    issue = await db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Update status
    old_status = issue.status
    issue.status = status
    
    # Save progress image if provided
    if image:
        UPLOAD_DIR = "/code/uploads/progress"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        filename = f"{issue_id}_progress_{image.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(await image.read())
        
        # Add to issue_media
        db.add(IssueMedia(issue_id=issue_id, file_path=filepath))
    
    await db.commit()
    
    return {
        "status": "success",
        "issue_id": issue_id,
        "old_status": old_status,
        "new_status": status,
        "remarks": remarks,
    }


@router.get("/in-progress/{sso}")
async def get_in_progress_issues(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get issues that are IN_PROGRESS for an official's city and category.
    """
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(status_code=404, detail="Official not found")

    query = (
        select(Issue)
        .where(Issue.status == IssueState.IN_PROGRESS.value)
        .where(func.lower(Issue.city) == official.city.lower())
        .where(func.lower(Issue.category) == official.category.lower())
        .order_by(Issue.priority_score.desc(), Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    response = []
    for issue in issues:
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
        })

    return {
        "official": {
            "sso": official.sso,
            "name": official.name,
            "city": official.city,
            "category": official.category,
        },
        "issues": response,
        "count": len(response),
    }


@router.get("/resolved/{sso}")
async def get_resolved_issues(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get issues that are RESOLVED or CLOSED for an official's city and category.
    """
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(status_code=404, detail="Official not found")

    query = (
        select(Issue)
        .where(Issue.status.in_([IssueState.RESOLVED.value, IssueState.CLOSED.value]))
        .where(func.lower(Issue.city) == official.city.lower())
        .where(func.lower(Issue.category) == official.category.lower())
        .order_by(Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    response = []
    for issue in issues:
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
        })

    return {
        "official": {
            "sso": official.sso,
            "name": official.name,
            "city": official.city,
            "category": official.category,
        },
        "issues": response,
        "count": len(response),
    }
