# Dynamic Ranking Layer

The dynamic ranking system calculates **priority scores** for issues to help government officials prioritize their workload. Issues with higher scores appear first in the dashboard.

---

## Priority Formula

```
priority_score = (severity × 50%) + (verifications × 25%) + (time × 25%)
```

Each component is scored 0-100, then weighted and combined. Final score is clamped to 0-100 range.

---

## The 3 Ranking Factors

### 1. Severity Score (50% weight)

Based on issue **category** - more dangerous/urgent categories score higher.

| Category | Score | Priority Level |
|----------|-------|----------------|
| Public Safety | 100 | 🔴 Critical |
| Electricity | 90 | 🔴 Critical |
| Water Leakage | 75 | 🟠 High |
| Drainage | 70 | 🟠 High |
| Street Light | 65 | 🟡 Medium |
| Road Damage | 55 | 🟡 Medium |
| Garbage | 40 | 🟢 Lower |
| Other | 30 | 🟢 Lower |

**Logic:** A fire hazard or exposed electrical wire is more urgent than a pothole.

---

### 2. Verification Score (25% weight)

Based on how many **community members verified** the issue. More verifications = higher confidence = higher priority.

```python
verification_score = (verifications / max_verifications) × 100
```

| Verifications | Score |
|---------------|-------|
| 0 | 0 |
| 2 | 20 |
| 5 | 50 |
| 10+ | 100 (capped) |

**Logic:** Issues verified by more citizens are more likely to be real and widespread.

---

### 3. Time Score (25% weight)

**Older issues get priority boost** - prevents issues from being forgotten.

```python
time_score = (age_hours / max_hours) × 100
```

| Age | Score |
|-----|-------|
| < 1 hour | ~0.6 |
| 24 hours | ~14 |
| 72 hours (3 days) | ~43 |
| 168 hours (7 days) | 100 (capped) |

**Logic:** An issue pending for a week needs attention more than one reported an hour ago.

---

## Status Multipliers

Issues get bonus/penalty based on current status:

| Status | Multiplier | Effect |
|--------|------------|--------|
| Verified | ×1.2 | +20% boost ✅ |
| Pending Verification | ×1.0 | Normal |
| In Progress | ×0.8 | -20% (already being worked on) |
| Resolved | ×0.0 | Hidden from lists |
| Rejected | ×0.0 | Hidden from lists |

---

## Example Calculations

### Example 1: Urgent New Issue
```
Category: Public Safety (severity = 100)
Verifications: 5 (score = 50)
Age: 2 hours (score = 1.2)
Status: Verified (multiplier = 1.2)

priority = ((100 × 0.5) + (50 × 0.25) + (1.2 × 0.25)) × 1.2
         = (50 + 12.5 + 0.3) × 1.2
         = 75.36
```

### Example 2: Old Low-Priority Issue
```
Category: Garbage (severity = 40)
Verifications: 2 (score = 20)
Age: 7 days (score = 100)
Status: Pending (multiplier = 1.0)

priority = (40 × 0.5) + (20 × 0.25) + (100 × 0.25)
         = 20 + 5 + 25
         = 50
```

### Example 3: Critical Verified Issue
```
Category: Electricity (severity = 90)
Verifications: 8 (score = 80)
Age: 1 day (score = 14)
Status: Verified (multiplier = 1.2)

priority = ((90 × 0.5) + (80 × 0.25) + (14 × 0.25)) × 1.2
         = (45 + 20 + 3.5) × 1.2
         = 82.2
```

---

## When Ranking Happens

```
Issue Created → Abuse Prevention Passed → UNDER_VERIFICATION
                                               ↓
                              Community submits verifications
                                               ↓
                              2nd verification submitted
                                               ↓
                    ┌──────────────────────────────────────┐
                    │ Status → VERIFIED                    │
                    │ priority_score = calculated & stored │
                    └──────────────────────────────────────┘
                                               ↓
                    Pending page shows issues sorted by priority_score DESC
```

---

## Configuration

Settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `WEIGHT_SEVERITY` | 0.50 | Weight for category severity |
| `WEIGHT_VERIFICATIONS` | 0.25 | Weight for verification count |
| `WEIGHT_TIME` | 0.25 | Weight for issue age |
| `MAX_VERIFICATIONS_FOR_SCORE` | 10 | Cap for verification scoring |
| `TIME_DECAY_HOURS` | 168 | Max hours for time scoring (7 days) |
| `MIN_SCORE` | 0 | Minimum possible score |
| `MAX_SCORE` | 100 | Maximum possible score |

Weights can be customized via environment variables:
```bash
RANKING_WEIGHT_SEVERITY=0.50
RANKING_WEIGHT_VERIFICATIONS=0.25
RANKING_WEIGHT_TIME=0.25
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ranking/issues` | GET | Get ranked issues with filters (state, city, category) |
| `/ranking/categories` | GET | Get severity scores for all categories |
| `/ranking/config` | GET | Get current ranking configuration |
| `/ranking/calculate` | POST | Test priority calculation with custom values |

### Example: Get Ranked Issues
```bash
curl "http://localhost:8000/ranking/issues?city=Bengaluru&category=Water%20Leakage"
```

### Example: Test Calculation
```bash
curl -X POST "http://localhost:8000/ranking/calculate?category=Electricity&verification_count=5&hours_since_created=24"
```

---

## File Structure

```
dynamicranking/
├── __init__.py         # Package exports
├── api.py              # FastAPI routes
├── config.py           # Severity scores & weights
├── service.py          # DynamicRankingService class
├── test_ranking.py     # Unit tests
└── README.md           # This file
```

---

## Usage in Code

### Calculate Priority Score
```python
from dynamicranking.service import DynamicRankingService

service = DynamicRankingService()
scores = service.calculate_priority_score(
    category="Water Leakage",
    verification_count=3,
    created_at=issue.created_at,
    status="Verified"
)

print(scores['priority_score'])  # e.g., 62.5
```

### Rank Multiple Issues
```python
issues = [
    {"id": 1, "category": "Electricity", "status": "Verified", "created_at": ...},
    {"id": 2, "category": "Garbage", "status": "Verified", "created_at": ...},
]
verification_counts = {1: 5, 2: 2}

ranked = service.rank_issues(issues, verification_counts)
# Returns list sorted by priority_score DESC
```

---

## Testing

Run the test suite:
```bash
cd /path/to/backend
python -m dynamicranking.test_ranking
```

Tests cover:
- Severity score lookups
- Priority calculation accuracy
- Ranking order correctness
- Status multiplier effects
- API import compatibility
