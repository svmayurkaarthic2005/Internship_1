"""
Add sample MERGE applications with strict validation:
1. No duplicate subdivisions across any applications
2. Survey numbers used for MERGE cannot have active ISD/NISD applications
3. All subdivisions in a MERGE must belong to the same survey number
4. Proper workflow: Only one application per survey at a time
"""
import asyncio
import sys
from datetime import date, timedelta
from sqlalchemy import select, and_, or_
from collections import defaultdict

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import (
    Application, Applicant, SISOfficer, SurveyNumber, 
    SubDivision, ApplicationSubDivision
)


async def check_conflicts(db, survey_id, subdivision_ids):
    """
    Check if subdivisions or survey number have conflicts with existing applications
    Returns (has_conflict, message)
    """
    # Check if any of these subdivisions are already in use
    result = await db.execute(
        select(Application.application_number, Application.current_status, Application.current_stage)
        .join(ApplicationSubDivision, Application.id == ApplicationSubDivision.application_id)
        .where(
            and_(
                ApplicationSubDivision.sub_division_id.in_(subdivision_ids),
                Application.current_status.in_(['pending', 'in_progress'])
            )
        )
    )
    existing_apps = result.all()
    
    if existing_apps:
        return True, f"Subdivisions already in use by: {', '.join(a[0] for a in existing_apps)}"
    
    # Check if this survey number has any active ISD/NISD applications
    result = await db.execute(
        select(Application.application_number, Application.application_type, Application.current_status)
        .where(
            and_(
                Application.survey_number_id == survey_id,
                Application.application_type.in_(['ISD', 'NISD']),
                Application.current_status.in_(['pending', 'in_progress'])
            )
        )
    )
    active_apps = result.all()
    
    if active_apps:
        return True, f"Survey has active {active_apps[0][1]} application: {active_apps[0][0]}"
    
    return False, "OK"


async def get_available_subdivisions(db):
    """
    Find survey numbers with multiple subdivisions that are NOT in any active application
    Returns list of (survey_number, available_subdivisions)
    """
    print("🔍 Scanning for available survey numbers with multiple subdivisions...")
    
    # Get all survey numbers with their subdivisions
    result = await db.execute(
        select(SurveyNumber.id, SurveyNumber.survey_no, SubDivision.id, SubDivision.sub_division_no)
        .join(SubDivision, SurveyNumber.id == SubDivision.survey_number_id)
        .order_by(SurveyNumber.survey_no, SubDivision.sub_division_no)
    )
    rows = result.all()
    
    # Group by survey number
    survey_subdivs = defaultdict(list)
    for survey_id, survey_no, subdiv_id, subdiv_no in rows:
        survey_subdivs[survey_id].append({
            'survey_no': survey_no,
            'subdiv_id': subdiv_id,
            'subdiv_no': subdiv_no
        })
    
    # Filter: only surveys with 2+ subdivisions
    candidates = []
    for survey_id, subdivs in survey_subdivs.items():
        if len(subdivs) >= 2:
            # Check if ANY subdivision is in use
            subdiv_ids = [s['subdiv_id'] for s in subdivs]
            has_conflict, msg = await check_conflicts(db, survey_id, subdiv_ids)
            
            if not has_conflict:
                candidates.append({
                    'survey_id': survey_id,
                    'survey_no': subdivs[0]['survey_no'],
                    'subdivisions': subdivs
                })
    
    return candidates


async def add_merge_applications():
    """Add MERGE applications with proper validation"""
    
    print("🚀 Adding MERGE applications with conflict checking...")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        try:
            # Get Arjun Kumar (or first officer)
            officer_result = await db.execute(
                select(SISOfficer).where(SISOfficer.email == 'arjun.kumar@sis.tn.gov.in')
            )
            officer = officer_result.scalar_one_or_none()
            
            if not officer:
                print("⚠️  Arjun Kumar not found, using first available officer...")
                officer = (await db.execute(select(SISOfficer).limit(1))).scalar_one_or_none()
            
            if not officer:
                print("❌ ERROR: No officers found in database")
                return
            
            print(f"✅ Assigning to officer: {officer.name} ({officer.email})")
            
            # Find available survey numbers
            available = await get_available_subdivisions(db)
            
            if len(available) < 3:
                print(f"❌ ERROR: Need at least 3 available survey numbers, found only {len(available)}")
                print("   Cannot create safe MERGE applications without conflicts")
                return
            
            print(f"✅ Found {len(available)} survey numbers available for MERGE")
            print("-" * 100)
            
            # Create 3 MERGE applications
            merge_apps = [
                {
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
                        "reason": "commercial_consolidation"
                    },
                    "subdivisions_count": 3,  # Merge 3 subdivisions
                    "priority": False
                },
                {
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
                        "reason": "trust_consolidation"
                    },
                    "subdivisions_count": 2,  # Merge 2 subdivisions
                    "priority": False
                },
                {
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
                        "days_ago": 5,
                        "reason": "housing_development"
                    },
                    "subdivisions_count": 2,  # Merge 2 subdivisions
                    "priority": True  # Priority merge
                }
            ]
            
            inserted_count = 0
            
            for idx, data in enumerate(merge_apps):
                if idx >= len(available):
                    print(f"⚠️  Skipping application - no more available surveys")
                    break
                
                survey_data = available[idx]
                survey_id = survey_data['survey_id']
                survey_no = survey_data['survey_no']
                subdivs = survey_data['subdivisions'][:data['subdivisions_count']]
                
                if len(subdivs) < data['subdivisions_count']:
                    print(f"⚠️  Skipping {data['application']['number']} - not enough subdivisions")
                    continue
                
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
                    survey_number_id=survey_id,
                    applicant_id=applicant.id,
                    assigned_officer_id=officer.id,
                    current_status=data["application"]["status"],
                    current_stage=data["application"]["stage"],
                    submission_date=submission_date,
                    is_overdue=(data["application"]["days_ago"] > 15),
                    priority_flag=data["priority"],
                    declared_reason=data["application"]["reason"]
                )
                db.add(application)
                await db.flush()
                
                # Link subdivisions
                for subdiv in subdivs:
                    app_subdiv = ApplicationSubDivision(
                        application_id=application.id,
                        sub_division_id=subdiv['subdiv_id']
                    )
                    db.add(app_subdiv)
                
                subdiv_names = ', '.join(s['subdiv_no'] for s in subdivs)
                priority_str = " [PRIORITY]" if data["priority"] else ""
                print(f"✅ {data['application']['number']} - {data['applicant']['name']}")
                print(f"   Survey: {survey_no}, Subdivisions: {subdiv_names}{priority_str}")
                print(f"   Status: {data['application']['status']}, Stage: {data['application']['stage']}")
                
                inserted_count += 1
            
            # Commit all changes
            await db.commit()
            
            print("-" * 100)
            print(f"\n🎉 SUCCESS! Inserted {inserted_count} MERGE applications")
            print(f"   ✓ No subdivision conflicts")
            print(f"   ✓ No survey number conflicts with ISD/NISD")
            print(f"   ✓ All applications assigned to {officer.name}")
            print(f"\n💡 Restart backend and test with: 'show merge applications'")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_merge_applications())
