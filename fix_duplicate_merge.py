"""
Fix duplicate merge application by deleting APP-2024-000012
Since APP-2024-000004 is already approved and contains all the subdivisions,
the in_progress application APP-2024-000012 should be removed.
"""
import asyncio
import sys
from sqlalchemy import select, delete

sys.path.insert(0, 'c:/proj/nic_internship')

from backend.database import AsyncSessionLocal
from backend.models import Application, ApplicationSubDivision


async def fix_duplicate():
    """Delete the duplicate merge application APP-2024-000012"""
    
    print("🔧 Fixing duplicate merge application...")
    print("=" * 100)
    
    async with AsyncSessionLocal() as db:
        try:
            # Get the duplicate application
            result = await db.execute(
                select(Application).where(
                    Application.application_number == 'APP-2024-000012'
                )
            )
            app = result.scalar_one_or_none()
            
            if not app:
                print("❌ Application APP-2024-000012 not found")
                return
            
            print(f"📋 Found application: {app.application_number}")
            print(f"   Type: {app.application_type}")
            print(f"   Status: {app.current_status}")
            print(f"   Stage: {app.current_stage}")
            
            # Confirm deletion
            print(f"\n⚠️  This will DELETE application APP-2024-000012 and all related records")
            print(f"   Reason: It has overlapping subdivisions with approved app APP-2024-000004")
            
            # Delete related ApplicationSubDivision records first (cascade should handle this, but being explicit)
            await db.execute(
                delete(ApplicationSubDivision).where(
                    ApplicationSubDivision.application_id == app.id
                )
            )
            print(f"✅ Deleted related application_sub_divisions records")
            
            # Delete the application
            await db.delete(app)
            await db.commit()
            
            print(f"✅ Successfully deleted application APP-2024-000012")
            print(f"\n💡 The duplicate merge issue is now fixed!")
            print(f"   APP-2024-000004 (approved) remains with subdivisions 145/1A, 145/1B, 145/1C")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will permanently delete APP-2024-000012")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
        sys.exit(0)
    
    asyncio.run(fix_duplicate())
