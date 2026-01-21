# SUDHAR - Smart Urban Dispatch Hub for Assisted Reporting

A civic issue reporting platform that connects citizens with government officials for efficient resolution of urban infrastructure problems.

## Overview

SUDHAR enables residents to report civic issues (water leakage, street lights, road damage, etc.) with photo evidence. The system validates submissions, crowdsources verification from the community, and delivers prioritized work queues to government officials.

## Workflow Pipeline

```
Reporter → Abuse Prevention → Community Verification → Dynamic Ranking → Official Action → Resolution
```

### 1. Issue Submission
Citizens report issues with photos and location data via the mobile app.

### 2. Abuse Prevention (4 Validators)
- **AI Detection** - Rejects AI-generated images
- **EXIF Validation** - Ensures photo was taken recently
- **GPS Validation** - Matches image location to user location
- **Duplicate Detection** - Flags reused images

### 3. Community Verification
Nearby residents validate issues by visiting the location and submitting verification photos. **10 verifications** required for automatic promotion.

### 4. Dynamic Ranking
Issues are prioritized by:
- **Severity** (50%) - Category urgency (Public Safety > Garbage)
- **Verifications** (25%) - Community validation count
- **Age** (25%) - Older issues get priority boost

### 5. Official Dashboard
Government officials see issues sorted by priority and can:
- Override community verification for urgent issues
- Update status (In Progress → Resolved)
- Add remarks and progress photos

## Issue States

| State | Description |
|-------|-------------|
| `SUBMITTED` | Just uploaded, awaiting abuse check |
| `UNDER_VERIFICATION` | Passed abuse check, awaiting community validation |
| `VERIFIED` | 10+ community verifications received |
| `IN_PROGRESS` | Official working on resolution |
| `RESOLVED` | Work completed |
| `CLOSED` | Issue fully closed |

## Tech Stack

- **Mobile**: Flutter
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL + PostGIS
- **Notifications**: Firebase Cloud Messaging
- **Container**: Docker Compose

## Quick Start

```bash
# Start backend
docker compose up --build

# Access API docs
open http://localhost:8000/docs
```

## Documentation

- [Full Workflow Details](./WORKFLOW.md)
- [Abuse Prevention Layer](./backend/app/services/abuseprevention/README.md)
- [Dynamic Ranking System](./backend/dynamicranking/README.md)

## Project Structure

```
sudhar/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── core/           # State machine, transitions
│   │   ├── db/             # Models, database
│   │   └── services/       # Abuse prevention, audit logging
│   └── dynamicranking/     # Priority scoring module
├── uploads/                # Issue & verification images
├── docker-compose.yml
├── WORKFLOW.md             # Detailed workflow documentation
└── README.md
```
