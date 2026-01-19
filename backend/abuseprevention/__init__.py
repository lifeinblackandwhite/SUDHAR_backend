"""
SUDHAR Abuse Prevention Package

This package provides comprehensive abuse prevention and verification
functionality for the SUDHAR backend system.
"""

from .middleware import AbusePreventionLayer, ReportVerificationManager
from .notifications import NotificationManager
from .database import initialize_database, create_abuse_prevention_tables

__version__ = '1.0.0'
__all__ = [
    'AbusePreventionLayer',
    'ReportVerificationManager', 
    'NotificationManager',
    'initialize_database',
    'create_abuse_prevention_tables'
]