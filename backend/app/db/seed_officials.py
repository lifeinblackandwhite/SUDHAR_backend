"""
Seed script to populate the govt_officials table with initial data.

Run this script to add government officials to the database:
    python -m app.db.seed_officials
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal, engine, Base
from app.db.models import GovtOfficial


async def seed_govt_officials():
    """Seed the database with government officials."""
    
    async with AsyncSessionLocal() as session:
        # Check if data already exists
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(GovtOfficial.sso)))
        count = result.scalar()
        
        if count > 0:
            print(f"Database already has {count} officials. Skipping seed.")
            return
        
        govt_officials = [
            # =======================
            # Karnataka – Bengaluru
            # =======================
            GovtOfficial(
                sso="SSO3001",
                name="Rajesh Gowda",
                department="Bruhat Bengaluru Mahanagara Palike (BBMP)",
                email="rajesh.gowda@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Garbage"
            ),
            GovtOfficial(
                sso="SSO3002",
                name="Shilpa Rao",
                department="Public Works Department (PWD)",
                email="shilpa.rao@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Road Damage"
            ),
            GovtOfficial(
                sso="SSO3003",
                name="Mahesh Kulkarni",
                department="Bangalore Electricity Supply Company (BESCOM)",
                email="mahesh.kulkarni@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Electricity"
            ),
            GovtOfficial(
                sso="SSO3004",
                name="Ananya Shetty",
                department="Bangalore Water Supply and Sewerage Board (BWSSB)",
                email="ananya.shetty@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Water Leakage"
            ),
            GovtOfficial(
                sso="SSO3005",
                name="Ramesh Naik",
                department="BBMP Storm Water Drain Department",
                email="ramesh.naik@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Drainage"
            ),
            GovtOfficial(
                sso="SSO3006",
                name="Sumanth Rao",
                department="BBMP Street Lighting Division",
                email="sumanth.rao@karnataka.gov.in",
                state="Karnataka",
                city="Bengaluru",
                category="Street Light"
            ),

            # =======================
            # Karnataka – Other Cities
            # =======================
            GovtOfficial(
                sso="SSO3007",
                name="Prakash Naik",
                department="City Municipal Corporation",
                email="prakash.naik@karnataka.gov.in",
                state="Karnataka",
                city="Mangaluru",
                category="Garbage"
            ),
            GovtOfficial(
                sso="SSO3008",
                name="Vinay Deshpande",
                department="Public Works Department (PWD)",
                email="vinay.deshpande@karnataka.gov.in",
                state="Karnataka",
                city="Hubballi",
                category="Road Damage"
            ),
            GovtOfficial(
                sso="SSO3009",
                name="Kavya Joshi",
                department="City Municipal Council",
                email="kavya.joshi@karnataka.gov.in",
                state="Karnataka",
                city="Mysuru",
                category="Public Safety"
            ),
            GovtOfficial(
                sso="SSO3010",
                name="Raghavendra Patil",
                department="Hubli Electricity Supply Company (HESCOM)",
                email="raghavendra.patil@karnataka.gov.in",
                state="Karnataka",
                city="Belagavi",
                category="Electricity"
            ),

            # =======================
            # Nearby States
            # =======================
            GovtOfficial(
                sso="SSO3101",
                name="Satish Rao",
                department="Greater Hyderabad Municipal Corporation (GHMC)",
                email="satish.rao@telangana.gov.in",
                state="Telangana",
                city="Hyderabad",
                category="Drainage"
            ),
            GovtOfficial(
                sso="SSO3102",
                name="Pooja Menon",
                department="Greater Chennai Corporation",
                email="pooja.menon@tn.gov.in",
                state="Tamil Nadu",
                city="Chennai",
                category="Garbage"
            ),

            # =======================
            # Major Cities
            # =======================
            GovtOfficial(
                sso="SSO3201",
                name="Neha Malhotra",
                department="Municipal Corporation of Delhi",
                email="neha.malhotra@delhi.gov.in",
                state="Delhi",
                city="New Delhi",
                category="Public Safety"
            ),
            GovtOfficial(
                sso="SSO3202",
                name="Imran Khan",
                department="Brihanmumbai Municipal Corporation (BMC)",
                email="imran.khan@maharashtra.gov.in",
                state="Maharashtra",
                city="Mumbai",
                category="Other"
            ),
        ]

        session.add_all(govt_officials)
        await session.commit()
        print(f"Successfully seeded {len(govt_officials)} government officials!")


if __name__ == "__main__":
    asyncio.run(seed_govt_officials())
