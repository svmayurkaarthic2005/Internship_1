"""
Add MERGE applications by creating new survey numbers and subdivisions
This ensures NO conflicts with existing applications
"""
import asyncio
import sys
from datetime import date, timedelta
from sqlalchemy import select

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import (
    Application, Applicant, SISOfficer, SurveyNumber, 
    SubDivision, ApplicationSubDivision, Block
)


async def add_merge_with_new_surveys():
    """Add MERGE applications with new survey numbers and subdivisions"""
    
    print("🚀 Creating new survey numbers and MERGE applications...")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        try:
            # Get Arjun Kumar
            officer_result = await db.execute(
                select(SISOfficer).where(SISOfficer.email == 'arjun.kumar@sis.tn.gov.in')
            )
            officer = officer_result.scalar_one_or_none()
            
            if not officer:
                print("⚠️  Arjun Kumar not found, using first available officer...")
                officer = (await db.execute(select(SISOfficer).limit(1))).scalar_one_or_none()
            
            if not officer:
                print("❌ ERROR: No officers found")
                return
            
            print(f"✅ Assigning to officer: {officer.name} ({officer.email})")
            
            # Get a block for the survey numbers
            block = (await db.execute(select(Block).limit(1))).scalar_one_or_none()
            if not block:
                print("❌ ERROR: No blocks found in database")
                return
            
            print(f"✅ Using block: {block.block_name}")
            print("-" * 100)
            
            # Create 3 MERGE applications with new survey numbers
            merge_data = [
                {
                    "survey_no": "350",
                    "subdivisions": ["350/1A", "350/1B", "350/1C"],
                    "applicant": {
                        "name": "Selvam Industries Ltd",
                        "mobile": "9876543300",
                        "email": "selvam.ind@example.com",
                        "address": "Industrial Estate, Guindy",
                        "aadhaar_last4": "4567"
                    },
                    "application": {
                        "number": "APP-2026-000301",
                        "status": "pending",
                        "stage": "SIS",
                        "days_ago": 12,
                        "is_overdue": False,
                        "priority_flag": False,
                        "reason": "commercial_consolidation"
                    },
                    "description": "Merging 3 plots for industrial expansion"
                },
                {
                    "survey_no": "351",
                    "subdivisions": ["351/2A", "351/2B"],
                    "applicant": {
                        "name": "Ramanathan Trust",
                        "mobile": "9876543301",
                        "email": "ramanathan.trust@example.com",
                        "address": "Temple Street, Mylapore",
                        "aadhaar_last4": "8901"
                    },
                    "application": {
                        "number": "APP-2026-000302",
                        "status": "in_progress",
                        "stage": "SIS",
                        "days_ago": 8,
                        "is_overdue": False,
                        "priority_flag": False,
                        "reason": "trust_consolidation"
                    },
                    "description": "Trust property consolidation"
                },
                {
                    "survey_no": "352",
                    "subdivisions": ["352/A", "352/B"],
                    "applicant": {
                        "name": "Kumar Housing Co-op",
                        "mobile": "9876543302",
                        "email": "kumar.coop@example.com",
                        "address": "T Nagar, Chennai",
                        "aadhaar_last4": "2345"
                    },
                    "application": {
                        "number": "APP-2026-000303",
                        "status": "pending",
                        "stage": "SIS",
                        "days_ago": 18,
                        "is_overdue": True,
                        "priority_flag": True,
                        "reason": "housing_development"
                    },
                    "description": "Housing development project - PRIORITY & OVERDUE"
                }
            ]
            
            inserted_count = 0
            
            for data in merge_data:
                # Create survey number
                survey = SurveyNumber(
                    block_id=block.id,
                    survey_no=data["survey_no"],
                    total_area_sqm=5000.0,
                    land_type="urban_residential",
                    has_encroachment=False,
                    has_litigation=False
                )
                db.add(survey)
                await db.flush()
                
                print(f"\n📍 Created Survey No: {data['survey_no']}")
                
                # Create subdivisions
                subdivision_ids = []
                for subdiv_no in data["subdivisions"]:
                    subdivision = SubDivision(
                        survey_number_id=survey.id,
                        sub_division_no=subdiv_no,
                        area_sqm=1500.0,
                        status='active'
                    )
                    db.add(subdivision)
                    await db.flush()
                    subdivision_ids.append(subdivision.id)
                    print(f"   ├─ Subdivision: {subdiv_no}")
                
                # Create applicant
                applicant = Applicant(
                    name=data["applicant"]["name"],
                    mobile=data["applicant"]["mobile"],
                    email=data["applicant"]["email"],
                    address=data["applicant"]["address"],
                    aadhaar_last4=data["applicant"]["aadhaar_last4"]
                )
                db.add(applicant)
                await db.flush()
                
                # Create MERGE application
                submission_date = date.today() - timedelta(days=data["application"]["days_ago"])
                application = Application(
                    application_number=data["application"]["number"],
                    application_type="MERGE",
                    survey_number_id=survey.id,
                    applicant_id=applicant.id,
                    assigned_officer_id=officer.id,
                    current_status=data["application"]["status"],
                    current_stage=data["application"]["stage"],
                    submission_date=submission_date,
                    is_overdue=data["application"]["is_overdue"],
                    priority_flag=data["application"]["priority_flag"],
                    declared_reason=data["application"]["reason"]
                )
                db.add(application)
                await db.flush()
                
                # Link subdivisions to application
                for subdiv_id in subdivision_ids:
                    app_subdiv = ApplicationSubDivision(
                        application_id=application.id,
                        sub_division_id=subdiv_id
                    )
                    db.add(app_subdiv)
                
                status_flags = []
                if data["application"]["is_overdue"]:
                    status_flags.append("OVERDUE")
                if data["application"]["priority_flag"]:
                    status_flags.append("PRIORITY")
                
                flag_str = f" [{', '.join(status_flags)}]" if status_flags else ""
                
                print(f"   └─ ✅ {data['application']['number']} - {data['applicant']['name']}{flag_str}")
                print(f"      {data['description']}")
                print(f"      Status: {data['application']['status']}, Merging {len(data['subdivisions'])} subdivisions")
                
                inserted_count += 1
            
            # Commit all changes
            await db.commit()
            
            print("-" * 100)
            print(f"\n🎉 SUCCESS! Created:")
            print(f"   ✓ 3 new survey numbers (350, 351, 352)")
            print(f"   ✓ 7 new subdivisions")
            print(f"   ✓ 3 MERGE applications (1 overdue + priority, 2 normal)")
            print(f"   ✓ All assigned to {officer.name}")
            print(f"   ✓ NO conflicts with existing applications")
            print(f"\n💡 Application breakdown:")
            print(f"   • APP-2026-000301: Normal MERGE (3 subdivisions)")
            print(f"   • APP-2026-000302: In Progress (2 subdivisions)")
            print(f"   • APP-2026-000303: Priority + Overdue (2 subdivisions)")
            print(f"\n🔄 Restart backend and test with:")
            print(f"   - 'show merge applications'")
            print(f"   - 'show high priority applications'")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_merge_with_new_surveys())
