"""
Find duplicate MERGE applications that reference the same subdivisions
"""
import asyncio
import sys
from sqlalchemy import select, func, and_
from collections import defaultdict

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import Application, ApplicationSubDivision, SubDivision


async def find_duplicates():
    """Find MERGE applications with overlapping subdivisions"""
    
    print("🔍 Searching for duplicate MERGE applications...")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all MERGE applications with their subdivisions
            result = await db.execute(
                select(
                    Application.id,
                    Application.application_number,
                    Application.current_status,
                    Application.survey_number_id,
                    ApplicationSubDivision.sub_division_id,
                    SubDivision.sub_division_no
                )
                .join(ApplicationSubDivision, Application.id == ApplicationSubDivision.application_id)
                .join(SubDivision, ApplicationSubDivision.sub_division_id == SubDivision.id)
                .where(Application.application_type == 'MERGE')
                .order_by(Application.application_number, SubDivision.sub_division_no)
            )
            
            rows = result.all()
            
            if not rows:
                print("✅ No MERGE applications found")
                return
            
            # Group by application
            app_subdivisions = defaultdict(lambda: {"app_number": "", "status": "", "survey_id": None, "subdivisions": set()})
            
            for app_id, app_num, status, survey_id, subdiv_id, subdiv_no in rows:
                app_subdivisions[app_id]["app_number"] = app_num
                app_subdivisions[app_id]["status"] = status
                app_subdivisions[app_id]["survey_id"] = survey_id
                app_subdivisions[app_id]["subdivisions"].add((subdiv_id, subdiv_no))
            
            # Find duplicates
            print(f"\n📋 Found {len(app_subdivisions)} MERGE applications:")
            print("-" * 100)
            
            duplicates_found = []
            apps_list = list(app_subdivisions.items())
            
            for i, (app_id1, data1) in enumerate(apps_list):
                for app_id2, data2 in apps_list[i+1:]:
                    # Check if same survey number
                    if data1["survey_id"] != data2["survey_id"]:
                        continue
                    
                    # Check for overlapping subdivisions
                    subdiv_ids1 = {sid for sid, _ in data1["subdivisions"]}
                    subdiv_ids2 = {sid for sid, _ in data2["subdivisions"]}
                    overlap = subdiv_ids1 & subdiv_ids2
                    
                    if overlap:
                        # Found duplicate!
                        overlapping_names = [name for sid, name in data1["subdivisions"] if sid in overlap]
                        duplicates_found.append({
                            "app1": data1["app_number"],
                            "status1": data1["status"],
                            "subdivs1": [name for _, name in sorted(data1["subdivisions"])],
                            "app2": data2["app_number"],
                            "status2": data2["status"],
                            "subdivs2": [name for _, name in sorted(data2["subdivisions"])],
                            "overlap": sorted(overlapping_names)
                        })
            
            if not duplicates_found:
                print("\n✅ No duplicate MERGE applications found!")
                print("   All merge applications have unique subdivision sets.")
                return
            
            print(f"\n⚠️  FOUND {len(duplicates_found)} DUPLICATE MERGE APPLICATION(S):")
            print("=" * 100)
            
            for idx, dup in enumerate(duplicates_found, 1):
                print(f"\n❌ DUPLICATE #{idx}:")
                print(f"   Application 1: {dup['app1']} (Status: {dup['status1']})")
                print(f"      Subdivisions: {', '.join(dup['subdivs1'])}")
                print(f"   Application 2: {dup['app2']} (Status: {dup['status2']})")
                print(f"      Subdivisions: {', '.join(dup['subdivs2'])}")
                print(f"   🔴 OVERLAPPING: {', '.join(dup['overlap'])}")
                print("-" * 100)
            
            print(f"\n💡 RECOMMENDATION:")
            print(f"   - Keep the APPROVED/COMPLETED application")
            print(f"   - Delete or modify the PENDING one")
            print(f"   - Or update subdivisions to be non-overlapping")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(find_duplicates())
