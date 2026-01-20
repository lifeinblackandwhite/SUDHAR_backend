"""
Test script for Dynamic Ranking module.
Verifies the ranking service works correctly with sample data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from dynamicranking.service import DynamicRankingService, RankedIssue
from dynamicranking.config import SEVERITY_SCORES, RankingConfig


def test_severity_scores():
    """Test that all categories have correct severity scores."""
    print("=" * 50)
    print("TEST 1: Severity Scores")
    print("=" * 50)
    
    expected_categories = [
        ('Public Safety', 100),
        ('Electricity', 90),
        ('Water Leakage', 75),
        ('Drainage', 70),
        ('Street Light', 65),
        ('Road Damage', 55),
        ('Garbage', 40),
        ('Other', 30),
    ]
    
    all_passed = True
    for category, expected_score in expected_categories:
        actual_score = RankingConfig.get_severity_score(category)
        status = "PASS" if actual_score == expected_score else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"  {status}: {category} = {actual_score} (expected {expected_score})")
    
    print(f"\n  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return all_passed


def test_priority_calculation():
    """Test priority score calculation."""
    print("\n" + "=" * 50)
    print("TEST 2: Priority Calculation")
    print("=" * 50)
    
    service = DynamicRankingService()
    
    # Test cases: (category, verifications, hours_old, expected_min, expected_max)
    test_cases = [
        ('Public Safety', 5, 2, 55, 70),     # High severity, some verifications, recent
        ('Electricity', 10, 24, 60, 80),     # High severity, max verifications
        ('Garbage', 0, 1, 15, 25),           # Low severity, no verifications, very recent
        ('Road Damage', 3, 168, 40, 55),     # Medium severity, some verifications, week old
    ]
    
    all_passed = True
    for category, verif, hours, min_score, max_score in test_cases:
        created_at = datetime.now() - timedelta(hours=hours)
        scores = service.calculate_priority_score(category, verif, created_at)
        priority = scores['priority_score']
        
        passed = min_score <= priority <= max_score
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        
        print(f"  {status}: {category} ({verif} verif, {hours}h old)")
        print(f"         Score: {priority:.1f} (expected {min_score}-{max_score})")
    
    print(f"\n  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return all_passed


def test_ranking_order():
    """Test that issues are ranked in correct order."""
    print("\n" + "=" * 50)
    print("TEST 3: Ranking Order")
    print("=" * 50)
    
    service = DynamicRankingService()
    
    # Create sample issues (should rank: Public Safety > Electricity > Street Light > Garbage)
    sample_issues = [
        {
            'id': 1,
            'category': 'Garbage',
            'description': 'Garbage pile near park',
            'status': 'Pending Verification',
            'created_at': datetime.now() - timedelta(hours=24)
        },
        {
            'id': 2,
            'category': 'Public Safety',
            'description': 'Broken railing on bridge',
            'status': 'Verified',
            'created_at': datetime.now() - timedelta(hours=12)
        },
        {
            'id': 3,
            'category': 'Street Light',
            'description': 'Street light not working',
            'status': 'Pending Verification',
            'created_at': datetime.now() - timedelta(hours=48)
        },
        {
            'id': 4,
            'category': 'Electricity',
            'description': 'Exposed wires on pole',
            'status': 'Pending Verification',
            'created_at': datetime.now() - timedelta(hours=6)
        },
    ]
    
    verification_counts = {1: 1, 2: 5, 3: 2, 4: 3}
    
    ranked = service.rank_issues(sample_issues, verification_counts)
    
    print("  Ranked order:")
    for issue in ranked:
        print(f"    #{issue.priority_rank}: {issue.category} (score: {issue.priority_score:.1f})")
    
    # Verify Public Safety is #1 (highest severity + verified status bonus)
    passed = ranked[0].category == 'Public Safety'
    print(f"\n  Public Safety ranked first: {'PASS' if passed else 'FAIL'}")
    
    # Verify Garbage is last (lowest severity)
    passed2 = ranked[-1].category == 'Garbage'
    print(f"  Garbage ranked last: {'PASS' if passed2 else 'FAIL'}")
    
    return passed and passed2


def test_status_multipliers():
    """Test that status multipliers work correctly."""
    print("\n" + "=" * 50)
    print("TEST 4: Status Multipliers")
    print("=" * 50)
    
    service = DynamicRankingService()
    created_at = datetime.now() - timedelta(hours=24)
    
    # Same issue, different statuses
    pending = service.calculate_priority_score('Road Damage', 3, created_at, 'Pending Verification')
    verified = service.calculate_priority_score('Road Damage', 3, created_at, 'Verified')
    in_progress = service.calculate_priority_score('Road Damage', 3, created_at, 'In Progress')
    
    print(f"  Pending Verification: {pending['priority_score']:.1f}")
    print(f"  Verified: {verified['priority_score']:.1f} (1.2x bonus)")
    print(f"  In Progress: {in_progress['priority_score']:.1f} (0.8x)")
    
    passed = verified['priority_score'] > pending['priority_score'] > in_progress['priority_score']
    print(f"\n  Verified > Pending > In Progress: {'PASS' if passed else 'FAIL'}")
    
    return passed


def test_api_import():
    """Test that API router can be imported."""
    print("\n" + "=" * 50)
    print("TEST 5: API Import Compatibility")
    print("=" * 50)
    
    try:
        from dynamicranking.api import router
        print(f"  Router imported: PASS")
        print(f"  Router prefix: {router.prefix}")
        print(f"  Routes: {len(router.routes)}")
        return True
    except Exception as e:
        print(f"  Router import FAILED: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "#" * 50)
    print("#  DYNAMIC RANKING MODULE TESTS")
    print("#" * 50)
    
    tests = [
        ("Severity Scores", test_severity_scores),
        ("Priority Calculation", test_priority_calculation),
        ("Ranking Order", test_ranking_order),
        ("Status Multipliers", test_status_multipliers),
        ("API Import", test_api_import),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  {status}: {name}")
    
    print("\n" + "=" * 50)
    print(f"OVERALL: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 50 + "\n")
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
