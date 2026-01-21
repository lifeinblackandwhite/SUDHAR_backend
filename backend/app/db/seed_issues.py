"""
Seed script to populate issues table with sample data at different states.
Run: docker exec infra-backend python -m app.db.seed_issues
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text
from geoalchemy2 import WKTElement
from app.db.database import AsyncSessionLocal
from app.db.models import Issue, IssueMedia
from app.core.issue_states import IssueState


# Bengaluru coordinates for sample locations
BENGALURU_LOCATIONS = [
    (12.9716, 77.5946, "Koramangala"),   # Koramangala
    (12.9352, 77.6245, "HSR Layout"),     # HSR Layout
    (12.9698, 77.7500, "Whitefield"),     # Whitefield
    (12.9279, 77.6271, "BTM Layout"),     # BTM Layout
    (12.9850, 77.5533, "Malleshwaram"),   # Malleshwaram
    (13.0358, 77.5970, "Yelahanka"),      # Yelahanka
    (12.9063, 77.5857, "Jayanagar"),      # Jayanagar
    (12.9121, 77.6446, "Madiwala"),       # Madiwala
    (12.9783, 77.6408, "Indiranagar"),    # Indiranagar
    (12.9141, 77.6011, "JP Nagar"),       # JP Nagar
]


async def seed_issues():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(text("SELECT COUNT(*) FROM issues"))
        count = result.scalar()
        
        if count > 0:
            print(f"⚠️  Issues table already has {count} records. Clearing and re-seeding...")
            await session.execute(text("DELETE FROM issue_media"))
            await session.execute(text("DELETE FROM issue_verifications"))
            await session.execute(text("DELETE FROM issue_events"))
            await session.execute(text("DELETE FROM issues"))
            await session.commit()

        issues = [
            # ============ SUBMITTED (just created, awaiting abuse check) ============
            Issue(
                user_id="test_user_001",
                title="Broken streetlight near bus stop",
                description="The streetlight near the bus stop on 5th Main Road has been broken for a week. It's very dark and unsafe at night.",
                category="Street Light",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[0][2],
                pincode="560034",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[0][1]} {BENGALURU_LOCATIONS[0][0]})", srid=4326),
                status=IssueState.SUBMITTED.value,
                abuse_cleared=False,
                priority_score=0.0
            ),
            
            # ============ UNDER_VERIFICATION (passed abuse, awaiting community) ============
            Issue(
                user_id="test_user_002",
                title="Garbage dump overflowing",
                description="The garbage collection point near the park is overflowing. It hasn't been cleared for 4 days and is causing a stench.",
                category="Garbage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[1][2],
                pincode="560102",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[1][1]} {BENGALURU_LOCATIONS[1][0]})", srid=4326),
                status=IssueState.UNDER_VERIFICATION.value,
                abuse_cleared=True,
                priority_score=0.0
            ),
            Issue(
                user_id="test_user_003",
                title="Open drain near school",
                description="There's an open drain near the government school that poses a safety hazard for children.",
                category="Drainage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[2][2],
                pincode="560066",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[2][1]} {BENGALURU_LOCATIONS[2][0]})", srid=4326),
                status=IssueState.UNDER_VERIFICATION.value,
                abuse_cleared=True,
                priority_score=0.0
            ),
            
            # ============ VERIFIED (community verified, awaiting ranking) ============
            Issue(
                user_id="test_user_004",
                title="Major pothole on main road",
                description="A large pothole has developed on the main road near the temple. Multiple vehicles have been damaged.",
                category="Road Damage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[3][2],
                pincode="560029",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[3][1]} {BENGALURU_LOCATIONS[3][0]})", srid=4326),
                status=IssueState.VERIFIED.value,
                abuse_cleared=True,
                priority_score=0.0
            ),
            Issue(
                user_id="test_user_005",
                title="Water main leak flooding street",
                description="A water main has burst and is flooding the entire street. Water is being wasted continuously.",
                category="Water Leakage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[4][2],
                pincode="560003",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[4][1]} {BENGALURU_LOCATIONS[4][0]})", srid=4326),
                status=IssueState.VERIFIED.value,
                abuse_cleared=True,
                priority_score=0.0
            ),

            # ============ RANKED (priority score calculated) ============
            Issue(
                user_id="test_user_006",
                title="Dangerous electrical wire hanging low",
                description="An electrical wire is hanging dangerously low near the children's playground. Immediate attention required!",
                category="Electricity",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[5][2],
                pincode="560064",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[5][1]} {BENGALURU_LOCATIONS[5][0]})", srid=4326),
                status=IssueState.RANKED.value,
                abuse_cleared=True,
                priority_score=85.5  # High priority
            ),
            Issue(
                user_id="test_user_007",
                title="Broken traffic signal",
                description="The traffic signal at the main junction is not working, causing traffic chaos during peak hours.",
                category="Public Safety",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[6][2],
                pincode="560041",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[6][1]} {BENGALURU_LOCATIONS[6][0]})", srid=4326),
                status=IssueState.RANKED.value,
                abuse_cleared=True,
                priority_score=72.3  # Medium-high priority
            ),
            Issue(
                user_id="test_user_008",
                title="Garbage not collected for a week",
                description="Garbage at our lane has not been collected for over a week. Health hazard.",
                category="Garbage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[7][2],
                pincode="560068",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[7][1]} {BENGALURU_LOCATIONS[7][0]})", srid=4326),
                status=IssueState.RANKED.value,
                abuse_cleared=True,
                priority_score=45.8  # Medium priority
            ),

            # ============ IN_PROGRESS (official working on it) ============
            Issue(
                user_id="test_user_009",
                title="Road resurfacing needed",
                description="The entire stretch of road from the circle to the market needs resurfacing. Very bumpy ride.",
                category="Road Damage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[8][2],
                pincode="560038",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[8][1]} {BENGALURU_LOCATIONS[8][0]})", srid=4326),
                status=IssueState.IN_PROGRESS.value,
                abuse_cleared=True,
                priority_score=68.2
            ),
            Issue(
                user_id="test_user_010",
                title="Blocked drainage causing flooding",
                description="The main drainage is blocked causing water logging during rains. Cars getting stuck.",
                category="Drainage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[9][2],
                pincode="560078",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[9][1]} {BENGALURU_LOCATIONS[9][0]})", srid=4326),
                status=IssueState.IN_PROGRESS.value,
                abuse_cleared=True,
                priority_score=55.0
            ),

            # ============ RESOLVED (work completed) ============
            Issue(
                user_id="test_user_011",
                title="Streetlight repaired",
                description="Streetlight at 3rd cross was not working. [RESOLVED: Replaced bulb and wiring]",
                category="Street Light",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[0][2],
                pincode="560034",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[0][1]} {BENGALURU_LOCATIONS[0][0]})", srid=4326),
                status=IssueState.RESOLVED.value,
                abuse_cleared=True,
                priority_score=35.0
            ),
            Issue(
                user_id="test_user_012",
                title="Pothole fixed on service road",
                description="Large pothole on service road. [RESOLVED: Filled with asphalt]",
                category="Road Damage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[1][2],
                pincode="560102",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[1][1]} {BENGALURU_LOCATIONS[1][0]})", srid=4326),
                status=IssueState.RESOLVED.value,
                abuse_cleared=True,
                priority_score=42.0
            ),

            # ============ CLOSED (fully complete) ============
            Issue(
                user_id="test_user_013",
                title="Water leakage - Fixed",
                description="Water pipe leaking near metro station. [CLOSED: Pipe replaced, no further leakage]",
                category="Water Leakage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[2][2],
                pincode="560066",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[2][1]} {BENGALURU_LOCATIONS[2][0]})", srid=4326),
                status=IssueState.CLOSED.value,
                abuse_cleared=True,
                priority_score=28.0
            ),

            # ============ AUTO_REJECTED (failed abuse check) ============
            Issue(
                user_id="test_user_014",
                title="Test spam issue",
                description="This issue was auto-rejected due to abuse detection.",
                category="Other",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[3][2],
                pincode="560029",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[3][1]} {BENGALURU_LOCATIONS[3][0]})", srid=4326),
                status=IssueState.AUTO_REJECTED.value,
                abuse_cleared=False,
                priority_score=0.0
            ),

            # ============ COMMUNITY_REJECTED (community voted down) ============
            Issue(
                user_id="test_user_015",
                title="False report - no issue found",
                description="Community verified this issue doesn't exist at the specified location.",
                category="Garbage",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[4][2],
                pincode="560003",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[4][1]} {BENGALURU_LOCATIONS[4][0]})", srid=4326),
                status=IssueState.COMMUNITY_REJECTED.value,
                abuse_cleared=True,
                priority_score=0.0
            ),

            # ============ COMMUNITY_REVIEW (tie in votes, needs more review) ============
            Issue(
                user_id="test_user_016",
                title="Possible illegal construction",
                description="Building appears to be encroaching on public land. Community opinions are divided.",
                category="Other",
                state="Karnataka",
                city="Bengaluru",
                area=BENGALURU_LOCATIONS[5][2],
                pincode="560064",
                location=WKTElement(f"POINT({BENGALURU_LOCATIONS[5][1]} {BENGALURU_LOCATIONS[5][0]})", srid=4326),
                status=IssueState.COMMUNITY_REVIEW.value,
                abuse_cleared=True,
                priority_score=0.0
            ),
        ]

        session.add_all(issues)
        await session.commit()
        
        # Refresh to get IDs
        for issue in issues:
            await session.refresh(issue)
        
        # Add sample images for each issue
        # Using placeholder URLs that represent typical civic issue images
        sample_images = {
            "Street Light": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
            "Garbage": "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=800",
            "Drainage": "https://images.unsplash.com/photo-1584824486509-112e4181ff6b?w=800",
            "Road Damage": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=800",
            "Water Leakage": "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=800",
            "Electricity": "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=800",
            "Public Safety": "https://images.unsplash.com/photo-1509390144018-eeaf65052242?w=800",
            "Other": "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=800",
        }
        
        issue_media_entries = []
        for issue in issues:
            # Get appropriate sample image for category
            image_url = sample_images.get(issue.category, sample_images["Other"])
            
            issue_media_entries.append(
                IssueMedia(
                    issue_id=issue.id,
                    file_path=image_url
                )
            )
            
            # Add a second image for some issues (RANKED and IN_PROGRESS)
            if issue.status in [IssueState.RANKED.value, IssueState.IN_PROGRESS.value]:
                issue_media_entries.append(
                    IssueMedia(
                        issue_id=issue.id,
                        file_path=f"{image_url}&q=80"  # Slightly different URL for variety
                    )
                )
        
        session.add_all(issue_media_entries)
        await session.commit()
        
        print(f"✅ Seeded {len(issues)} issues across all states:")
        print(f"📸 Added {len(issue_media_entries)} sample images")
        
        # Count by status
        status_counts = {}
        for issue in issues:
            status_counts[issue.status] = status_counts.get(issue.status, 0) + 1
        
        for status, count in sorted(status_counts.items()):
            print(f"   {status}: {count}")


if __name__ == "__main__":
    asyncio.run(seed_issues())
