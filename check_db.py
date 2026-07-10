# -*- coding: utf-8 -*-
"""
Comprehensive PostgreSQL connectivity and service folder check
"""
import asyncio
import sys
import os

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"


async def test_asyncpg_direct():
    """Test 1: Direct asyncpg connection"""
    print("\n" + "="*55)
    print("TEST 1: Direct asyncpg connection")
    print("="*55)
    try:
        import asyncpg
        print(f"  {INFO} asyncpg version: {asyncpg.__version__}")
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=5432,
            user='postgres',
            password='Mayur@2005',
            database='sis_chatbot'
        )
        version = await conn.fetchval('SELECT version()')
        print(f"  {PASS} Connected!")
        print(f"         Server : {version[:65]}")

        # List tables with row counts
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        print(f"\n  {PASS} Tables in 'sis_chatbot' ({len(tables)} total):")
        print(f"  {'Table Name':<40} {'Rows':>8}")
        print(f"  {'-'*40} {'------':>8}")
        for t in tables:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t["tablename"]}"')
            print(f"  {t['tablename']:<40} {count:>8}")

        # Quick SELECT test
        db_name = await conn.fetchval('SELECT current_database()')
        db_user = await conn.fetchval('SELECT current_user')
        print(f"\n  {INFO} Current DB   : {db_name}")
        print(f"  {INFO} Current User : {db_user}")

        await conn.close()
        print(f"\n  {PASS} Connection closed cleanly")
        return True

    except ImportError:
        print(f"  {FAIL} asyncpg not installed")
        return False
    except Exception as e:
        print(f"  {FAIL} {type(e).__name__}: {e}")
        return False


def test_psycopg2_sync():
    """Test 2: Synchronous psycopg2 connection"""
    print("\n" + "="*55)
    print("TEST 2: Synchronous psycopg2 connection")
    print("="*55)
    try:
        import psycopg2
        print(f"  {INFO} psycopg2 version: {psycopg2.__version__}")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            user='postgres',
            password='Mayur@2005',
            dbname='sis_chatbot'
        )
        cur = conn.cursor()
        cur.execute("SELECT version()")
        ver = cur.fetchone()[0]
        print(f"  {PASS} Connected via psycopg2!")
        print(f"         Server : {ver[:65]}")

        cur.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'")
        tbl_count = cur.fetchone()[0]
        print(f"  {PASS} Public tables: {tbl_count}")

        cur.close()
        conn.close()
        print(f"  {PASS} Connection closed cleanly")
        return True
    except ImportError:
        print(f"  {FAIL} psycopg2 not installed (run: pip install psycopg2-binary)")
        return False
    except Exception as e:
        print(f"  {FAIL} {type(e).__name__}: {e}")
        return False


def check_services_folder():
    """Test 3: Inspect the services/ folder"""
    print("\n" + "="*55)
    print("TEST 3: Services folder inspection (backend/services/)")
    print("="*55)
    services_path = os.path.join(os.path.dirname(__file__), 'backend', 'services')

    if not os.path.exists(services_path):
        print(f"  {FAIL} Folder not found: {services_path}")
        return

    files = [f for f in os.listdir(services_path) if f.endswith('.py') and f != '__pycache__']
    print(f"  {INFO} Found {len(files)} Python files in backend/services/:\n")

    for fname in sorted(files):
        fpath = os.path.join(services_path, fname)
        size = os.path.getsize(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Count async def + def (skip __init__ and private)
        all_funcs = [l.strip() for l in lines if l.strip().startswith(('async def ', 'def '))]
        classes = [l.strip() for l in lines if l.strip().startswith('class ')]

        print(f"  >> {fname}")
        print(f"     Size     : {size:,} bytes  |  Lines: {len(lines)}")
        print(f"     Classes  : {len(classes)}  |  Functions: {len(all_funcs)}")
        if all_funcs:
            for fn in all_funcs[:10]:
                name = fn.split('(')[0].replace('async def ', '').replace('def ', '').strip()
                is_async = fn.startswith('async')
                tag = 'async' if is_async else 'sync '
                print(f"       [{tag}] {name}()")
            if len(all_funcs) > 10:
                print(f"       ... +{len(all_funcs)-10} more")
        print()


async def main():
    print("=" * 55)
    print("  SIS-Chatbot -- DB Connectivity & Services Audit")
    print("=" * 55)

    r1 = await test_asyncpg_direct()
    r2 = test_psycopg2_sync()
    check_services_folder()

    print("=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print(f"  asyncpg (async)   : {'PASS' if r1 else 'FAIL'}")
    print(f"  psycopg2 (sync)   : {'PASS' if r2 else 'FAIL'}")
    print(f"  Services folder   : Inspected")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
