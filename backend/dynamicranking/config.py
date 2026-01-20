"""
Configuration for Dynamic Ranking.

Defines severity scores for different issue categories and ranking weights.
"""

import os
from typing import Dict


# Severity scores by category (1-100 scale)
# Higher score = more urgent/dangerous = higher priority
SEVERITY_SCORES: Dict[str, int] = {
    # Critical - Life/Safety threatening (80-100)
    'Public Safety': 100,
    'public_safety': 100,
    'Electricity': 90,
    'electricity': 90,
    
    # High - Infrastructure affecting daily life (60-79)
    'Water Leakage': 75,
    'water_leakage': 75,
    'Drainage': 70,
    'drainage': 70,
    'Street Light': 65,
    'street_light': 65,
    
    # Medium - Road/Transport issues (40-59)
    'Road Damage': 55,
    'road_damage': 55,
    
    # Lower - Sanitation/Other (20-39)
    'Garbage': 40,
    'garbage': 40,
    'Other': 30,
    'other': 30,
    
    # Default for unknown categories
    'unknown': 30
}


class RankingConfig:
    """Configuration for dynamic ranking calculation."""
    
    # Weights for each factor in final score (must sum to 1.0)
    WEIGHT_SEVERITY = float(os.getenv('RANKING_WEIGHT_SEVERITY', 0.50))
    WEIGHT_VERIFICATIONS = float(os.getenv('RANKING_WEIGHT_VERIFICATIONS', 0.25))
    WEIGHT_TIME = float(os.getenv('RANKING_WEIGHT_TIME', 0.25))
    
    # Verification scoring
    MAX_VERIFICATIONS_FOR_SCORE = int(os.getenv('MAX_VERIFICATIONS_FOR_SCORE', 10))
    # After this many verifications, score maxes out
    
    # Time scoring
    TIME_DECAY_HOURS = int(os.getenv('TIME_DECAY_HOURS', 168))  # 7 days
    # Issues older than this get maximum time boost
    
    # Score normalization
    MIN_SCORE = 0
    MAX_SCORE = 100
    
    # Status multipliers (issues with certain statuses may be deprioritized)
    STATUS_MULTIPLIERS = {
        'Pending Verification': 1.0,
        'Verified': 1.2,  # Verified issues get priority
        'In Progress': 0.8,  # Already being worked on
        'Resolved': 0.0,  # Don't show resolved
        'Rejected': 0.0,  # Don't show rejected
    }
    
    @classmethod
    def get_severity_score(cls, category: str) -> int:
        """
        Get severity score for a category.
        
        Args:
            category: Issue category string
            
        Returns:
            Severity score (0-100)
        """
        # Normalize category to lowercase with underscores
        normalized = category.lower().replace(' ', '_').replace('-', '_')
        return SEVERITY_SCORES.get(normalized, SEVERITY_SCORES['other'])
