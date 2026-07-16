"""
Reset the database by dropping and recreating it with fresh seed data
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import asyncio
import sys

def drop_and_create_database():
    """Drop and recreate sis_chatbot database"""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="Mayur@2005",
            database="postgres"
        )
        
        # Set autocommit mode
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminate existing connections to the database
        print("🔌 Terminating existing connections...")
        cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'sis_chatbot'
            AND pid <> pg_backend_pid();
        """)
        
        # Drop database if exists
        print("🗑️  Dropping existing database...")
        cursor.execute("DROP DATABASE IF EXISTS sis_chatbot")
        print("✅ Database dropped")
        
        # Create fresh database
        print("📦 Creating fresh database...")
        cursor.execute("CREATE DATABASE sis_chatbot")
        print("✅ Database 'sis_chatbot' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return False

async def run_seed():
    """Import and run the seed script"""
    try:
        print("\n🌱 Running seed script...")
        from backend.seed import seed_database
        await seed_database()
        return True
    except Exception as e:
        print(f"❌ Error running seed script: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 60)
    print("DATABASE RESET UTILITY")
    print("=" * 60)
    print("\nThis will:")
    print("1. Drop the existing 'sis_chatbot' database")
    print("2. Create a fresh database")
    print("3. Run the seed script to populate with corrected data")
    print("\n⚠️  WARNING: All existing data will be lost!")
    
    # Step 1: Drop and recreate database
    if not drop_and_create_database():
        print("\n❌ Failed to reset database")
        sys.exit(1)
    
    # Step 2: Run seed script
    if not await run_seed():
        print("\n❌ Failed to seed database")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ DATABASE RESET COMPLETE")
    print("=" * 60)
    print("\nThe database now contains:")
    print("- Officer 1 (Arjun Kumar): Block B1 jurisdiction only")
    print("- Survey 145: Scheduled field visit (future)")
    print("- Survey 147: Overdue field visit (past)")
    print("- Survey 200, 201: Assigned to Officer 2 (not shown to Arjun)")

if __name__ == "__main__":
    asyncio.run(main())
