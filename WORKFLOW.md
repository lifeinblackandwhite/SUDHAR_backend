# SUDHAR - Complete Workflow Pipeline

**SUDHAR** (Smart Urban Dispatch Hub for Assisted Reporting) is a civic issue reporting platform that connects citizens with government officials.

---

## High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Citizens      │     │    Backend      │     │   Officials     │
│  (Flutter App)  │────▶│   (FastAPI)     │◀────│  (Flutter App)  │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
              │ PostgreSQL│ │ Uploads │ │ Firebase  │
              │ + PostGIS │ │ (Files) │ │   (FCM)   │
              └───────────┘ └─────────┘ └───────────┘
```

---

## Complete Issue Lifecycle

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           ISSUE LIFECYCLE                                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────┐   ┌───────────────────┐   ┌─────────────────────────────┐  │
│  │ REPORTER │──▶│ ABUSE PREVENTION  │──▶│    COMMUNITY VERIFICATION   │  │
│  │ SUBMITS  │   │   (4 Validators)  │   │      (10 Residents)         │  │
│  └──────────┘   └─────────┬─────────┘   └──────────────┬──────────────┘  │
│                           │                            │                  │
│                    ┌──────┴──────┐              ┌──────┴──────┐          │
│                    │             │              │             │          │
│                    ▼             ▼              ▼             ▼          │
│              AUTO_REJECTED  UNDER_VERIF    VERIFIED    COMMUNITY_REJ     │
│                    │             │              │             │          │
│                    ▼             │              │             ▼          │
│                  [END]           │      ┌───────┴───────┐   [END]        │
│                                  │      │               │                │
│                                  │      ▼               ▼                │
│                                  │  ASSIGNED      IN_PROGRESS            │
│                                  │      │               │                │
│                                  │      └───────┬───────┘                │
│                                  │              ▼                        │
│                                  │          RESOLVED                     │
│                                  │              │                        │
│                                  │              ▼                        │
│                                  │           CLOSED                      │
│                                  │              │                        │
│                                  └──────────────┴────────▶ [END]         │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Issue Submission

### Flow
```
User opens app → Fills form → Takes photo → Submits → Backend receives
```

### What happens:
1. **User fills issue form**:
   - Title, Description
   - Category (Water Leakage, Electricity, etc.)
   - Location (auto-detected or manual)
   - Photo (required)

2. **Backend receives**:
   - Saves image to `/uploads/`
   - Creates issue in `SUBMITTED` status
   - Passes to Abuse Prevention layer

---

## Phase 2: Abuse Prevention

### Purpose
Validates that the uploaded image is authentic, recent, and taken at the claimed location.

### The 4 Validators

| Validator | What It Checks | Score Range |
|-----------|---------------|-------------|
| **AI Detection** | Is image AI-generated? | -80 to +50 |
| **EXIF Timestamp** | Was photo taken recently? | -30 to +30 |
| **GPS Location** | Does image GPS match user location? | -35 to +35 |
| **Web Existence** | Has image been seen before? | -40 to +15 |

### Decision Logic
```python
overall_score = ai_score + exif_score + gps_score + web_score

if overall_score >= 30:
    status = UNDER_VERIFICATION  ✅
else:
    status = AUTO_REJECTED  ❌
```

### After Abuse Prevention
- ✅ **PASSED**: Issue moves to `UNDER_VERIFICATION`, appears in community feed
- ❌ **FAILED**: Issue marked as `AUTO_REJECTED`, hidden from all feeds

---

## Phase 3: Community Verification

### Purpose
Nearby residents validate that the issue is real and exists at the claimed location.

### Flow
```
Issue appears in community feed → Residents visit location → 
Take verification photo → Submit verification → Counter increments
```

### Threshold
- **10 verifications required** to change status to `VERIFIED`
- Issue stays visible in feed until threshold reached

### What Gets Stored
- Verification image
- Verifier ID
- Description (optional)
- Timestamp

### After 10 Verifications
```python
if verification_count >= 10:
    status = VERIFIED
    priority_score = calculate_priority()  # Dynamic ranking kicks in
```

---

## Phase 4: Dynamic Ranking

### Purpose
Prioritizes issues for government officials based on urgency.

### Priority Formula
```
priority_score = (severity × 50%) + (verifications × 25%) + (time × 25%)
```

### Severity Scores (by Category)
| Category | Score |
|----------|-------|
| Public Safety | 100 |
| Electricity | 90 |
| Water Leakage | 75 |
| Drainage | 70 |
| Street Light | 65 |
| Road Damage | 55 |
| Garbage | 40 |

### Time Factor
- Older issues get priority boost
- Max boost at 7 days (168 hours)

### Result
Issues sorted by `priority_score DESC` in official's pending page.

---

## Phase 5: Official Dashboard

### Pages & Endpoints

| Page | Endpoint | Shows |
|------|----------|-------|
| **Pending** | `GET /officials/pending/{sso}` | Issues awaiting action (UNDER_VERIFICATION, VERIFIED) |
| **In Progress** | `GET /officials/in-progress/{sso}` | Issues currently being worked on |
| **Resolved** | `GET /officials/resolved/{sso}` | Completed issues |
| **All Issues** | `GET /officials/issues/{sso}` | All issues in official's jurisdiction |

### Official Actions
- View issue details
- Change status
- Add remarks
- Upload progress photos
- Set start/end dates

---

## Phase 6: Status Updates

### Official Override
Officials can bypass community verification if needed:

| From | To | Use Case |
|------|-----|----------|
| `UNDER_VERIFICATION` | `IN_PROGRESS` | Urgent issue, can't wait for 10 verifications |
| `VERIFIED` | `IN_PROGRESS` | Start work immediately |
| `IN_PROGRESS` | `RESOLVED` | Work completed |

### Update Endpoint
```
POST /officials/update/{issue_id}
- status: new status
- remarks: notes
- start_date, end_date: timeline
- image: progress photo (optional)
```

---

## State Machine

```
                                 ┌────────────────┐
                                 │   SUBMITTED    │
                                 └───────┬────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │                             │
                  [Abuse Passed]                 [Abuse Failed]
                          │                             │
                          ▼                             ▼
               ┌──────────────────┐           ┌────────────────┐
               │UNDER_VERIFICATION│           │  AUTO_REJECTED │
               └────────┬─────────┘           └────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
   [10 verifs]   [Official]    [Community]
         │        [Override]    [Rejects]
         ▼              │              │
   ┌─────────┐         │              ▼
   │VERIFIED │         │     ┌─────────────────┐
   └────┬────┘         │     │COMMUNITY_REJECTED│
        │              │     └─────────────────┘
        └──────┬───────┘
               │
               ▼
        ┌────────────┐
        │IN_PROGRESS │
        └─────┬──────┘
              │
              ▼
        ┌──────────┐
        │ RESOLVED │
        └────┬─────┘
             │
             ▼
        ┌────────┐
        │ CLOSED │
        └────────┘
```

---

## All States

| State | Description |
|-------|-------------|
| `SUBMITTED` | Just uploaded, awaiting abuse check |
| `AUTO_REJECTED` | Failed abuse prevention |
| `UNDER_VERIFICATION` | Passed abuse, awaiting community verification |
| `COMMUNITY_REJECTED` | Community flagged as invalid |
| `VERIFIED` | 10+ community verifications, awaiting official action |
| `RANKED` | Prioritized by dynamic ranking |
| `ASSIGNED` | Official assigned to issue |
| `IN_PROGRESS` | Work has started |
| `RESOLVED` | Work completed |
| `CLOSED` | Issue fully resolved and closed |

---

## Notifications

### When Notifications Are Sent
- Issue submitted in user's area
- Issue status changes
- Issue assigned to official

### Technology
- **Firebase Cloud Messaging (FCM)** for push notifications
- Users register FCM tokens on app startup
- Backend sends notifications via Firebase Admin SDK

---

## Database Schema

### Core Tables

```
issues
├── id, user_id, title, description
├── category, state, city, area, pincode
├── location (PostGIS POINT)
├── status, priority_score
├── created_at, abuse_cleared

issue_media
├── id, issue_id, file_path

issue_verifications
├── id, issue_id, verifier_id
├── description, image_path
├── created_at

issue_events (audit log)
├── id, issue_id, actor_type, actor_id
├── action, old_value, new_value
├── created_at

GOVTOFFICIALS
├── sso, name, department, email
├── state, city, category
```

---

## API Endpoints Summary

### Issue Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/issues/upload` | Submit new issue |
| GET | `/issues/{id}` | Get issue details |

### Community Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/community/feed` | Issues to verify |
| POST | `/community/verify/{id}` | Submit verification |

### Official Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/officials/profile/{sso}` | Official profile |
| GET | `/officials/issues/{sso}` | All issues |
| GET | `/officials/pending/{sso}` | Pending issues |
| GET | `/officials/in-progress/{sso}` | In-progress issues |
| GET | `/officials/resolved/{sso}` | Resolved issues |
| POST | `/officials/update/{id}` | Update issue status |

### Ranking Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ranking/issues` | Ranked issues list |
| GET | `/ranking/categories` | Category severity scores |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Mobile App** | Flutter |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL + PostGIS |
| **Container** | Docker Compose |
| **Push Notifications** | Firebase Cloud Messaging |
| **Image Storage** | Local filesystem |

---

## Running the App

### Backend
```bash
cd sudhar
docker compose up --build
```

### Frontend
```bash
cd flutter_app
flutter run
```

### Database Access
```bash
docker exec -it infra-postgres psql -U postgres -d infra_db
```
