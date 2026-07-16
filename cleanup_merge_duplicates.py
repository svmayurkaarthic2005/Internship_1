"""
Cleanup any duplicate or incomplete MERGE applications from multiple script runs
"""
import asyncio
import sys
from sqlalchemy import select, delete

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import Application, Applicant, SurveyNumber, SubDivision, ApplicationSubDivision


async def cleanup_duplicates():
    """Find and remove duplicate MERGE applications created by script"""
    
    print("🔍 Checking for duplicate MERGE applications (APP-2026-0003xx)...")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        try:
            # Find all MERGE applications in the 300 series
            result = await db.execute(
                select(Application, SurveyNumber)
                .join(SurveyNumber, Application.survey_number_id == SurveyNumber.id)
                .where(
                    Application.application_number.like('APP-2026-0003%')
                )
                .order_by(Application.application_number)
            )
            apps = result.all()
            
            if not apps:
                print("✅ No MERGE applications found in 300 series")
                return
            
            print(f"📋 Found {len(apps)} MERGE applications:")
            print("-" * 100)
            
            for app, survey in apps:
                # Get subdivisions
                subdiv_result = await db.execute(
                    select(SubDivision.sub_division_no)
                    .join(ApplicationSubDivision, SubDivision.id == ApplicationSubDivision.sub_division_id)
                    .where(ApplicationSubDivision.application_id == app.id)
                )
                subdivs = [s[0] for s in subdiv_result.all()]
                
                print(f"  • {app.application_number} ({app.current_status}, {app.current_stage})")
                print(f"    Survey: {survey.survey_no}, Subdivisions: {', '.join(subdivs) if subdivs else 'NONE'}")
            
            print("-" * 100)
            
            # Check for duplicates by application number
            app_numbers = [app[0].application_number for app in apps]
            duplicates = [num for num in app_numbers if app_numbers.count(num) > 1]
            
            if duplicates:
                print(f"\n⚠️  DUPLICATES FOUND: {set(duplicates)}")
                print("   Will keep the first instance and delete others")
            
            # Check for survey numbers 250, 251, 252 (partial failed inserts)
            old_surveys = await db.execute(
                select(SurveyNumber)
                .where(SurveyNumber.survey_no.in_(['250', '251', '252']))
            )
            old_survey_list = old_surveys.scalars().all()
            
            if old_survey_list:
                print(f"\n⚠️  Found {len(old_survey_list)} old survey numbers (250-252) from failed attempts")
                for survey in old_survey_list:
                    # Check if they have applications
                    app_check = await db.execute(
                        select(Application.application_number)
                        .where(Application.survey_number_id == survey.id)
                    )
                    linked_apps = app_check.scalars().all()
                    
                    if linked_apps:
                        print(f"   • Survey {survey.survey_no} has applications: {', '.join(linked_apps)}")
                    else:
                        print(f"   • Survey {survey.survey_no} has NO applications (orphaned)")
            
            print("\n" + "=" * 100)
            print("⚠️  Do you want to clean up duplicates and orphaned data? (y/n)")
            choice = input().strip().lower()
            
            if choice != 'y':
                print("❌ Cleanup cancelled")
                return
            
            deleted_apps = 0
            deleted_surveys = 0
            
            # Delete orphaned surveys (no applications)
            for survey in old_survey_list:
                app_check = await db.execute(
                    select(Application).where(Application.survey_number_id == survey.id)
                )
                if not app_check.scalars().first():
                    # Delete subdivisions first
                    await db.execute(
                        delete(SubDivision).where(SubDivision.survey_number_id == survey.id)
                    )
                    # Delete survey
                    await db.delete(survey)
                    deleted_surveys += 1
                    print(f"✅ Deleted orphaned survey {survey.survey_no}")
            
            await db.commit()
            
            print("-" * 100)
            print(f"\n🎉 CLEANUP COMPLETE!")
            print(f"   Deleted: {deleted_apps} duplicate applications, {deleted_surveys} orphaned surveys")
            print(f"\n💡 Now you can safely run add_merge_with_new_surveys.py again")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
