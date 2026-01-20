"""
Government Official routes for SSO login and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import GovtOfficial

router = APIRouter(prefix="/officials", tags=["Government Officials"])


@router.get("/profile/{sso}")
async def get_official_profile(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch government official profile by SSO ID.
    Called after SSO login to display profile info in UI.
    """
    result = await db.execute(
        select(GovtOfficial).where(GovtOfficial.sso == sso)
    )
    official = result.scalar()

    if not official:
        raise HTTPException(
            status_code=404,
            detail=f"Official with SSO '{sso}' not found"
        )

    return {
        "sso": official.sso,
        "name": official.name,
        "department": official.department,
        "email": official.email,
        "state": official.state,
        "city": official.city,
        "category": official.category
    }


@router.get("/verify-sso/{sso}")
async def verify_sso(
    sso: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify if SSO exists in the system.
    Used during login to validate credentials.
    """
    result = await db.execute(
        select(GovtOfficial.sso).where(GovtOfficial.sso == sso)
    )
    exists = result.scalar() is not None

    return {
        "sso": sso,
        "valid": exists
    }
