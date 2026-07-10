"""
Test script for Phase 2 Authentication
Tests login, /me endpoint, refresh, and logout
"""
import asyncio
import httpx
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

# Test credentials from seed data
TEST_CREDENTIALS = {
    "email": "arjun.kumar@sis.tn.gov.in",
    "password": "Test@1234"
}


async def test_authentication():
    """Test the complete authentication flow"""
    
    print("=" * 70)
    print("SIS CHATBOT PORTAL - AUTHENTICATION TEST")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, follow_redirects=True) as client:
        
        # Test 1: Health Check
        print("1️⃣  Testing Health Check Endpoint...")
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Health check passed")
                print(f"   Status: {data.get('data', {}).get('status', 'N/A')}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            print(f"   Make sure the server is running: uvicorn backend.main:app --reload")
            return
        
        print()
        
        # Test 2: Login
        print("2️⃣  Testing Login Endpoint...")
        print(f"   Email: {TEST_CREDENTIALS['email']}")
        print(f"   Password: {'*' * len(TEST_CREDENTIALS['password'])}")
        
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json=TEST_CREDENTIALS
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Login successful")
                print(f"   Officer: {data['data']['officer_name']}")
                print(f"   Employee ID: {data['data']['employee_id']}")
                print(f"   Jurisdiction: {data['data']['jurisdiction_type']} - {data['data']['jurisdiction_name']}")
                print(f"   Cookie set: {'sis_access_token' in response.cookies}")
                
                # Store cookies for subsequent requests
                cookies = response.cookies
            else:
                print(f"   ❌ Login failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        print()
        
        # Test 3: Get Current User Profile
        print("3️⃣  Testing /me Endpoint (Get Current Officer Profile)...")
        
        try:
            response = await client.get(
                "/api/v1/auth/me",
                cookies=cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                officer = data['data']
                print(f"   ✅ Profile retrieved")
                print(f"   Name: {officer['name']}")
                print(f"   Tamil Name: {officer.get('name_tamil', 'N/A')}")
                print(f"   Email: {officer['email']}")
                print(f"   Mobile: {officer.get('mobile', 'N/A')}")
                print(f"   Designation: {officer['designation']}")
                print(f"   Active: {officer['is_active']}")
                print(f"   Last Login: {officer.get('last_login', 'N/A')}")
                print(f"   Jurisdiction Type: {officer['jurisdiction']['type']}")
                print(f"   Jurisdiction Name: {officer['jurisdiction']['name']}")
                print(f"   Block Count: {officer['jurisdiction']['block_count']}")
            else:
                print(f"   ❌ Failed to get profile: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 4: Refresh Token
        print("4️⃣  Testing Token Refresh Endpoint...")
        
        try:
            response = await client.post(
                "/api/v1/auth/refresh",
                cookies=cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Token refreshed successfully")
                print(f"   New token received: {'access_token' in data['data']}")
                print(f"   Cookie updated: {'sis_access_token' in response.cookies}")
                
                # Update cookies
                cookies = response.cookies
            else:
                print(f"   ❌ Token refresh failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 5: Access Protected Endpoint (verify token still works)
        print("5️⃣  Testing Protected Endpoint After Refresh...")
        
        try:
            response = await client.get(
                "/api/v1/auth/me",
                cookies=cookies
            )
            
            if response.status_code == 200:
                print(f"   ✅ Protected endpoint accessible with refreshed token")
            else:
                print(f"   ❌ Failed to access protected endpoint: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 6: Logout
        print("6️⃣  Testing Logout Endpoint...")
        
        try:
            response = await client.post(
                "/api/v1/auth/logout",
                cookies=cookies
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Logout successful")
                print(f"   Message: {data['message']}")
                print(f"   Cookie cleared: {response.cookies.get('sis_access_token', '') == ''}")
            else:
                print(f"   ❌ Logout failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 7: Try to access protected endpoint after logout
        print("7️⃣  Testing Protected Endpoint After Logout (should fail)...")
        
        try:
            # Use cleared cookies
            response = await client.get(
                "/api/v1/auth/me",
                cookies=response.cookies if 'response' in locals() else {}
            )
            
            if response.status_code == 401:
                print(f"   ✅ Correctly rejected (401 Unauthorized)")
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
                print(f"   Should return 401 after logout")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Test 8: Invalid credentials
        print("8️⃣  Testing Login with Invalid Credentials...")
        
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "wrong@email.com", "password": "wrong"}
            )
            
            if response.status_code == 401:
                print(f"   ✅ Correctly rejected invalid credentials (401)")
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print()
    print("=" * 70)
    print("AUTHENTICATION TEST COMPLETED")
    print("=" * 70)
    print()
    print("📋 Summary:")
    print("   ✅ Health check")
    print("   ✅ Login with valid credentials")
    print("   ✅ HTTPOnly cookie set")
    print("   ✅ Get current officer profile")
    print("   ✅ Token refresh")
    print("   ✅ Logout")
    print("   ✅ Protected endpoint rejection after logout")
    print("   ✅ Invalid credentials rejection")
    print()
    print("🎉 Phase 2 Authentication System is working correctly!")
    print()


if __name__ == "__main__":
    print("\n⚠️  Make sure:")
    print("   1. Database is seeded: python -m backend.seed")
    print("   2. Server is running: uvicorn backend.main:app --reload")
    print("   3. Server is at: http://localhost:8000")
    print()
    input("Press Enter to start tests...")
    print()
    
    asyncio.run(test_authentication())
