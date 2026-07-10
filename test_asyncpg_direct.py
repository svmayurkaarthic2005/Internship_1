"""Test asyncpg connection directly"""
import asyncio
import asyncpg

async def test_connection():
    try:
        # Try direct connection with explicit parameters
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=5432,
            user='postgres',
            password='Mayur@2005',
            database='sis_chatbot',
            ssl=False
        )
        
        # Test query
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Direct asyncpg connection successful! Result: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Direct asyncpg connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
