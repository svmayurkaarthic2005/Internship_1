"""
Check for duplicate applications using the same subdivisions
Business Rule: If a subdivision is in an active application (pending/in_progress),
it cannot be used in another application until the first one is completed.
"""
import asyncio
import sys
from sqlalchemy import select, and_, or_
from collections import defaultdict

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import Application, ApplicationSubDivision, SubDivision, SurveyNumber


async def check_conflicts():
    """Find applications with conflicting subdivisions"""
    
    print("🔍 Checking for subdivision conflicts across all applications...")
    print("=" * 120)
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all ACTIVE applications (pending/in_progress) with their subdivisions
            result = await db.execute(
                select(
                    Application.id,
                    Application.application_number,
                    Application.application_type,
                    Application.current_status,
                    Application.current_stage,
                    Application.survey_number_id,
                    SurveyNumber.survey_no,
                    ApplicationSubDivision.sub_division_id,
                    SubDivision.sub_division_no
                )
                .join(ApplicationSubDivision, Application.id == ApplicationSubDivision.application_id)
                .join(SubDivision, ApplicationSubDivision.sub_division_id == SubDivision.id)
                .join(SurveyNumber, Application.survey_number_id == SurveyNumber.id)
                .where(
                    or_(
                        Application.current_status == 'pending',
                        Application.current_status == 'in_progress',
                        Application.current_status == 'approved'  # Include approved to catch any issues
                    )
                )
                .order_by(Application.application_number, SubDivision.sub_division_no)
            )
            
            rows = result.all()
            
            if not rows:
                print("✅ No active applications found")
                return
            
            print(f"📊 Found {len(rows)} subdivision assignments in active applications")
            
            # Group by application
            app_data = defaultdict(lambda: {
                "app_number": "",
                "type": "",
                "status": "",
                "stage": "",
                "survey_no": "",
                "survey_id": None,
                "subdivisions": set()
            })
            
            for app_id, app_num, app_type, status, stage, survey_id, survey_no, subdiv_id, subdiv_no in rows:
                app_data[app_id]["app_number"] = app_num
                app_data[app_id]["type"] = app_type
                app_data[app_id]["status"] = status
                app_data[app_id]["stage"] = stage
                app_data[app_id]["survey_no"] = survey_no
                app_data[app_id]["survey_id"] = survey_id
                app_data[app_id]["subdivisions"].add((subdiv_id, subdiv_no))
            
            # Find conflicts: same subdivision in multiple applications
            print(f"\n🔍 Analyzing {len(app_data)} applications for conflicts...")
            print("-" * 120)
            
            conflicts_found = []
            apps_list = list(app_data.items())
            
            for i, (app_id1, data1) in enumerate(apps_list):
                for app_id2, data2 in apps_list[i+1:]:
                    # Check for overlapping subdivisions
                    subdiv_ids1 = {sid for sid, _ in data1["subdivisions"]}
                    subdiv_ids2 = {sid for sid, _ in data2["subdivisions"]}
                    overlap = subdiv_ids1 & subdiv_ids2
                    
                    if overlap:
                        # Found conflict!
                        overlapping_names = [name for sid, name in data1["subdivisions"] if sid in overlap]
                        conflicts_found.append({
                            "app1": data1["app_number"],
                            "type1": data1["type"],
                            "status1": data1["status"],
                            "stage1": data1["stage"],
                            "survey1": data1["survey_no"],
                            "subdivs1": [name for _, name in sorted(data1["subdivisions"])],
                            "app2": data2["app_number"],
                            "type2": data2["type"],
                            "status2": data2["status"],
                            "stage2": data2["stage"],
                            "survey2": data2["survey_no"],
                            "subdivs2": [name for _, name in sorted(data2["subdivisions"])],
                            "overlap": sorted(overlapping_names)
                        })
            
            if not conflicts_found:
                print("\n✅ NO CONFLICTS FOUND!")
                print("   All applications have unique subdivision assignments.")
                print("   ✓ Business rule validated: No subdivision is used in multiple active applications.")
                return
            
            # Display conflicts
            print(f"\n❌ FOUND {len(conflicts_found)} CONFLICT(S):")
            print("=" * 120)
            
            for idx, conflict in enumerate(conflicts_found, 1):
                print(f"\n🔴 CONFLICT #{idx}:")
                print(f"   ┌─ Application 1: {conflict['app1']}")
                print(f"   │  Type: {conflict['type1']}, Status: {conflict['status1']}, Stage: {conflict['stage1']}")
                print(f"   │  Survey No: {conflict['survey1']}")
                print(f"   │  Subdivisions: {', '.join(conflict['subdivs1'])}")
                print(f"   │")
                print(f"   └─ Application 2: {conflict['app2']}")
                print(f"      Type: {conflict['type2']}, Status: {conflict['status2']}, Stage: {conflict['stage2']}")
                print(f"      Survey No: {conflict['survey2']}")
                print(f"      Subdivisions: {', '.join(conflict['subdivs2'])}")
                print(f"")
                print(f"      ⚠️  OVERLAPPING SUBDIVISIONS: {', '.join(conflict['overlap'])}")
                print("-" * 120)
            
            print(f"\n💡 RECOMMENDATIONS:")
            print(f"   1. Keep the application with earliest submission date or higher priority status")
            print(f"   2. Reject/cancel the duplicate application")
            print(f"   3. Or modify subdivisions to be non-overlapping")
            print(f"   4. Business rule: One subdivision = One active application only")
            
            print(f"\n📋 SUMMARY:")
            print(f"   Total Applications Checked: {len(app_data)}")
            print(f"   Conflicts Found: {len(conflicts_found)}")
            print(f"   Status: {'🔴 DATA INTEGRITY ISSUE' if conflicts_found else '✅ CLEAN'}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_conflicts())
