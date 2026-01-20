"""
Dynamic Ranking Package for SUDHAR.

Provides dynamic priority ranking of issues for government officials based on:
1. Severity Score - Category-based severity (e.g., fire hazards > potholes)
2. Verification Count - Number of user verifications
3. Time Factor - Age of report (older reports get priority boost)
"""

from .service import DynamicRankingService, RankedIssue
from .config import SEVERITY_SCORES, RankingConfig
from .ws_routes import broadcast_ranking_update

__version__ = '1.0.0'

__all__ = [
    'DynamicRankingService',
    'RankedIssue',
    'SEVERITY_SCORES',
    'RankingConfig',
    'broadcast_ranking_update',
]
