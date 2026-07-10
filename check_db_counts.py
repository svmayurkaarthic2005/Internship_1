import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from backend.database import engine

async def check():
    tables = [
        'districts','taluks','towns','wards','blocks',
        'survey_numbers','sub_divisions',
        'owners','survey_ownership',
        'sis_officers','officer_jurisdictions',
        'applicants','applications',
        'application_sub_divisions','application_documents',
        'workflow_history','field_visits','patta_transfers',
        'chat_sessions','chat_messages'
    ]
    print("\n=== DB ROW COUNTS ===")
    async with engine.connect() as conn:
        for t in tables:
            r = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
            print(f"  {t:35s}: {r.scalar()}")
    await engine.dispose()

asyncio.run(check())
