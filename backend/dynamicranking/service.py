"""
Dynamic Ranking Service for SUDHAR.

Calculates priority scores for issues to help government officials
prioritize their workload based on:
1. Severity Score - Based on issue category
2. Verification Count - How many citizens verified the issue
3. Time Factor - How long the issue has been pending
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .config import RankingConfig, SEVERITY_SCORES

logger = logging.getLogger(__name__)


@dataclass
class RankedIssue:
    """An issue with its calculated ranking score."""
    
    # Original issue data
    id: int
    category: str
    description: str
    status: str
    created_at: datetime
    location: Optional[Dict[str, float]] = None
    
    # Ranking components
    severity_score: float = 0.0
    verification_score: float = 0.0
    time_score: float = 0.0
    
    # Final ranking
    priority_score: float = 0.0
    priority_rank: int = 0
    
    # Additional data
    verification_count: int = 0
    age_hours: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'category': self.category,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'location': self.location,
            'ranking': {
                'priority_score': round(self.priority_score, 2),
                'priority_rank': self.priority_rank,
                'severity_score': round(self.severity_score, 2),
                'verification_score': round(self.verification_score, 2),
                'time_score': round(self.time_score, 2),
            },
            'verification_count': self.verification_count,
            'age_hours': round(self.age_hours, 1)
        }


class DynamicRankingService:
    """
    Service for calculating dynamic priority rankings of issues.
    
    The ranking formula is:
        priority_score = (severity * W1) + (verifications * W2) + (time * W3)
    
    Where W1, W2, W3 are configurable weights that sum to 1.0
    """
    
    def __init__(self, db_session=None, config: RankingConfig = None):
        """
        Initialize the ranking service.
        
        Args:
            db_session: Async database session
            config: Ranking configuration (uses defaults if None)
        """
        self.db = db_session
        self.config = config or RankingConfig()
    
    def calculate_priority_score(
        self,
        category: str,
        verification_count: int,
        created_at: datetime,
        status: str = 'Pending Verification'
    ) -> Dict[str, float]:
        """
        Calculate priority score for a single issue.
        
        Args:
            category: Issue category
            verification_count: Number of verifications
            created_at: When the issue was created
            status: Current status
            
        Returns:
            Dict with individual scores and final priority
        """
        # 1. Severity Score (0-100 based on category)
        severity_score = RankingConfig.get_severity_score(category)
        
        # 2. Verification Score (0-100 based on count)
        # More verifications = higher priority, capped at max
        normalized_verifications = min(
            verification_count, 
            self.config.MAX_VERIFICATIONS_FOR_SCORE
        )
        verification_score = (
            normalized_verifications / self.config.MAX_VERIFICATIONS_FOR_SCORE
        ) * 100
        
        # 3. Time Score (0-100 based on age)
        # Older issues get higher priority (up to a cap)
        now = datetime.now()
        if created_at.tzinfo:
            # Handle timezone-aware datetime
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age_hours = (now - created_at).total_seconds() / 3600
        normalized_age = min(age_hours, self.config.TIME_DECAY_HOURS)
        time_score = (normalized_age / self.config.TIME_DECAY_HOURS) * 100
        
        # 4. Calculate weighted final score
        priority_score = (
            (severity_score * self.config.WEIGHT_SEVERITY) +
            (verification_score * self.config.WEIGHT_VERIFICATIONS) +
            (time_score * self.config.WEIGHT_TIME)
        )
        
        # 5. Apply status multiplier
        status_multiplier = self.config.STATUS_MULTIPLIERS.get(status, 1.0)
        priority_score *= status_multiplier
        
        # Clamp to valid range
        priority_score = max(
            self.config.MIN_SCORE,
            min(self.config.MAX_SCORE, priority_score)
        )
        
        return {
            'severity_score': severity_score,
            'verification_score': verification_score,
            'time_score': time_score,
            'priority_score': priority_score,
            'age_hours': age_hours
        }
    
    def rank_issues(
        self,
        issues: List[Dict[str, Any]],
        verification_counts: Dict[int, int] = None
    ) -> List[RankedIssue]:
        """
        Rank a list of issues by priority.
        
        Args:
            issues: List of issue dictionaries with id, category, status, created_at
            verification_counts: Optional dict mapping issue_id -> verification count
            
        Returns:
            List of RankedIssue objects sorted by priority (highest first)
        """
        verification_counts = verification_counts or {}
        ranked_issues = []
        
        for issue in issues:
            issue_id = issue.get('id')
            category = issue.get('category', 'other')
            status = issue.get('status', 'Pending Verification')
            created_at = issue.get('created_at')
            
            # Skip resolved/rejected issues
            if status in ('Resolved', 'Rejected'):
                continue
            
            # Parse datetime if string
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Get verification count
            v_count = verification_counts.get(issue_id, 0)
            
            # Calculate scores
            scores = self.calculate_priority_score(
                category=category,
                verification_count=v_count,
                created_at=created_at,
                status=status
            )
            
            # Create ranked issue
            ranked_issue = RankedIssue(
                id=issue_id,
                category=category,
                description=issue.get('description', ''),
                status=status,
                created_at=created_at,
                location=issue.get('location'),
                severity_score=scores['severity_score'],
                verification_score=scores['verification_score'],
                time_score=scores['time_score'],
                priority_score=scores['priority_score'],
                verification_count=v_count,
                age_hours=scores['age_hours']
            )
            
            ranked_issues.append(ranked_issue)
        
        # Sort by priority score (highest first)
        ranked_issues.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Assign ranks
        for i, issue in enumerate(ranked_issues):
            issue.priority_rank = i + 1
        
        return ranked_issues
    
    async def get_ranked_issues_from_db(
        self,
        limit: int = 50,
        offset: int = 0,
        state: str = None,
        city: str = None,
        category: str = None
    ) -> List[RankedIssue]:
        """
        Get ranked issues directly from database.
        
        Args:
            limit: Maximum number of issues to return
            offset: Pagination offset
            state: Filter by state
            city: Filter by city
            category: Filter by category
            
        Returns:
            List of RankedIssue objects
        """
        if not self.db:
            raise ValueError("Database session required")
        
        from sqlalchemy import select, func, text
        from sqlalchemy.orm import selectinload
        
        # This would need to be adapted to your actual ORM setup
        # Building dynamic query
        query = """
            SELECT 
                i.id,
                i.category,
                i.description,
                i.status,
                i.created_at,
                i.state,
                i.city,
                ST_X(i.location::geometry) as longitude,
                ST_Y(i.location::geometry) as latitude,
                COUNT(CASE WHEN e.action = 'VERIFIED' THEN 1 END) as verification_count
            FROM issues i
            LEFT JOIN issue_events e ON i.id = e.issue_id
            WHERE i.status NOT IN ('Resolved', 'Rejected')
        """
        
        params = {}
        
        if state:
            query += " AND i.state = :state"
            params['state'] = state
        
        if city:
            query += " AND i.city = :city"
            params['city'] = city
            
        if category:
            query += " AND i.category = :category"
            params['category'] = category
        
        query += " GROUP BY i.id ORDER BY i.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        # Execute query
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        # Convert to issues list
        issues = []
        verification_counts = {}
        
        for row in rows:
            issue = {
                'id': row.id,
                'category': row.category,
                'description': row.description,
                'status': row.status,
                'created_at': row.created_at,
                'location': {
                    'latitude': row.latitude,
                    'longitude': row.longitude
                } if row.latitude else None
            }
            issues.append(issue)
            verification_counts[row.id] = row.verification_count or 0
        
        # Rank issues
        return self.rank_issues(issues, verification_counts)


def get_category_severities() -> Dict[str, int]:
    """Get all category severity scores for reference."""
    return SEVERITY_SCORES.copy()
