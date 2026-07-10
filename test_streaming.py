"""
Test script to verify streaming endpoint is working
"""
import asyncio
import httpx
import json

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_MESSAGE = "What is ISD?"


async def test_stream():
    """Test the streaming endpoint"""
    
    print("=" * 60)
    print("Testing Streaming Endpoint")
    print("=" * 60)
    
    # First, login to get a token
    print("\n1. Logging in...")
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={
                "employee_id": "SIS001",
                "password": "password123"
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            return
        
        login_data = login_response.json()
        access_token = login_data["data"]["access_token"]
        print(f"✓ Login successful, got token")
        
        # Create a session
        print("\n2. Creating chat session...")
        session_response = await client.post(
            f"{API_BASE_URL}/api/v1/chat/sessions",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if session_response.status_code != 201:
            print(f"❌ Session creation failed: {session_response.status_code}")
            print(session_response.text)
            return
        
        session_data = session_response.json()
        session_id = session_data["data"]["session_id"]
        print(f"✓ Session created: {session_id}")
        
        # Test streaming endpoint
        print(f"\n3. Testing streaming with message: '{TEST_MESSAGE}'")
        print("-" * 60)
        
        async with client.stream(
            "POST",
            f"{API_BASE_URL}/api/v1/chat/stream",
            json={
                "message": TEST_MESSAGE,
                "session_id": session_id,
                "language": "auto"
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        ) as response:
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print()
            
            if response.status_code != 200:
                error_text = await response.aread()
                print(f"❌ Stream failed: {error_text.decode()}")
                return
            
            print("Streaming response:")
            print("-" * 60)
            
            full_response = ""
            chunk_count = 0
            
            async for chunk in response.aiter_bytes():
                chunk_count += 1
                chunk_text = chunk.decode('utf-8')
                
                # Parse SSE format
                for line in chunk_text.split('\n\n'):
                    line = line.strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            content = data.get('content', '')
                            full_response += content
                            print(content, end='', flush=True)
                        except json.JSONDecodeError as e:
                            print(f"\n⚠️  JSON decode error: {e}")
                            print(f"   Raw line: {line[:100]}")
            
            print()
            print("-" * 60)
            print(f"\n✓ Stream complete!")
            print(f"   Total chunks: {chunk_count}")
            print(f"   Response length: {len(full_response)} characters")
            
            if not full_response:
                print("\n❌ WARNING: No content received!")
            else:
                print("\n✓ Content received successfully")


if __name__ == "__main__":
    asyncio.run(test_stream())
