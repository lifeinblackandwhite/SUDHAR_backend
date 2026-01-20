"""
FastAPI routes for Dynamic Ranking.

Provides endpoints for government officials to get ranked issues.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from .service import DynamicRankingService, RankedIssue, get_category_severities
from .config import RankingConfig, SEVERITY_SCORES

router = APIRouter(prefix="/ranking", tags=["Dynamic Ranking"])


@router.get("/issues", response_model=None)
async def get_ranked_issues(
    limit: int = Query(50, ge=1, le=100, description="Maximum issues to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = None  # Inject via Depends(get_db) in main app
):
    """
    Get issues ranked by priority for government officials.
    
    Returns issues sorted by priority score (highest first).
    
    Priority is calculated from:
    - **Severity** (50%): Based on category (fire hazard > pothole)
    - **Verifications** (25%): More citizen verifications = higher priority
    - **Time** (25%): Older issues get priority boost
    """
    try:
        service = DynamicRankingService(db_session=db)
        
        ranked_issues = await service.get_ranked_issues_from_db(
            limit=limit,
            offset=offset,
            state=state,
            city=city,
            category=category
        )
        
        return {
            'success': True,
            'count': len(ranked_issues),
            'data': [issue.to_dict() for issue in ranked_issues],
            'meta': {
                'weights': {
                    'severity': RankingConfig.WEIGHT_SEVERITY,
                    'verifications': RankingConfig.WEIGHT_VERIFICATIONS,
                    'time': RankingConfig.WEIGHT_TIME
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_category_severity_scores():
    """
    Get severity scores for all categories.
    
    Useful for understanding how different issue types are prioritized.
    """
    return {
        'success': True,
        'data': get_category_severities(),
        'description': 'Severity scores (0-100). Higher = more urgent.'
    }


@router.get("/config")
async def get_ranking_config():
    """
    Get current ranking configuration.
    
    Shows the weights and thresholds used in priority calculation.
    """
    return {
        'success': True,
        'data': {
            'weights': {
                'severity': RankingConfig.WEIGHT_SEVERITY,
                'verifications': RankingConfig.WEIGHT_VERIFICATIONS,
                'time': RankingConfig.WEIGHT_TIME
            },
            'thresholds': {
                'max_verifications_for_score': RankingConfig.MAX_VERIFICATIONS_FOR_SCORE,
                'time_decay_hours': RankingConfig.TIME_DECAY_HOURS
            },
            'status_multipliers': RankingConfig.STATUS_MULTIPLIERS
        }
    }


@router.post("/calculate")
async def calculate_priority(
    category: str = Query(..., description="Issue category"),
    verification_count: int = Query(0, ge=0, description="Number of verifications"),
    hours_since_created: float = Query(0, ge=0, description="Hours since issue was created"),
    status: str = Query("Pending Verification", description="Issue status")
):
    """
    Calculate priority score for a hypothetical issue.
    
    Useful for testing and understanding the ranking algorithm.
    """
    service = DynamicRankingService()
    
    # Create a datetime from hours ago
    created_at = datetime.now() - timedelta(hours=hours_since_created)
    
    scores = service.calculate_priority_score(
        category=category,
        verification_count=verification_count,
        created_at=created_at,
        status=status
    )
    
    return {
        'success': True,
        'data': {
            'category': category,
            'input': {
                'verification_count': verification_count,
                'hours_since_created': hours_since_created,
                'status': status
            },
            'scores': {
                'severity_score': round(scores['severity_score'], 2),
                'verification_score': round(scores['verification_score'], 2),
                'time_score': round(scores['time_score'], 2),
                'priority_score': round(scores['priority_score'], 2)
            }
        }
    }
