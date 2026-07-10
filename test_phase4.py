"""
Phase 4 Testing Script
Tests RAG pipeline and chat functionality
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from backend.config import settings


class Phase4Tester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.access_token = None
        self.session_id = None
        
    async def test_ollama_connection(self):
        """Test Ollama is running and models are available"""
        print("\n[TEST 1] Ollama Connection")
        print("-" * 50)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=10.0)
                
                if response.status_code == 200:
                    models = response.json()
                    print(f"✓ Ollama connected")
                    print(f"  Available models: {len(models.get('models', []))}")
                    
                    # Check for required models
                    model_names = [m['name'] for m in models.get('models', [])]
                    
                    if 'llama3.1:8b' in model_names or any('llama3.1' in m for m in model_names):
                        print(f"  ✓ LLM model found")
                    else:
                        print(f"  ⚠ LLM model not found. Run: ollama pull llama3.1:8b")
                    
                    if 'nomic-embed-text' in model_names or any('nomic-embed-text' in m for m in model_names):
                        print(f"  ✓ Embedding model found")
                    else:
                        print(f"  ⚠ Embedding model not found. Run: ollama pull nomic-embed-text")
                    
                    return True
                else:
                    print(f"✗ Ollama returned status {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"✗ Ollama connection failed: {e}")
            print(f"  Make sure Ollama is running: ollama serve")
            return False
    
    async def test_chromadb(self):
        """Test ChromaDB is initialized and has documents"""
        print("\n[TEST 2] ChromaDB Initialization")
        print("-" * 50)
        
        try:
            from backend.services.chroma import get_collection_stats
            
            stats = get_collection_stats()
            print(f"✓ ChromaDB accessible")
            print(f"  Collection: {stats['collection_name']}")
            print(f"  Document count: {stats['document_count']}")
            print(f"  Status: {stats['status']}")
            
            if stats['document_count'] == 0:
                print(f"  ⚠ No documents ingested. Run: python backend/ingest.py")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ ChromaDB error: {e}")
            return False
    
    async def test_api_health(self):
        """Test API is running"""
        print("\n[TEST 3] API Health Check")
        print("-" * 50)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ API is healthy")
                    print(f"  Status: {data.get('data', {}).get('status')}")
                    return True
                else:
                    print(f"✗ API returned status {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            print(f"✗ API not accessible at {self.base_url}")
            print(f"  Start the API: uvicorn backend.main:app --reload")
            return False
        except Exception as e:
            print(f"✗ API health check failed: {e}")
            return False
    
    async def login(self):
        """Login and get access token"""
        print("\n[TEST 4] Authentication")
        print("-" * 50)
        
        try:
            async with httpx.AsyncClient() as client:
                # Try to login with default test credentials
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={
                        "email": "arjun.kumar@sis.tn.gov.in",
                        "password": "Test@1234"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data['data']['access_token']
                    print(f"✓ Login successful")
                    print(f"  Officer: {data['data']['officer_name']}")
                    return True
                else:
                    print(f"✗ Login failed: {response.status_code}")
                    print(f"  Create test officer first or update credentials")
                    return False
                    
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    async def create_chat_session(self):
        """Create a new chat session"""
        print("\n[TEST 5] Create Chat Session")
        print("-" * 50)
        
        if not self.access_token:
            print("✗ Not authenticated. Login first.")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/chat/sessions",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    self.session_id = data['data']['session_id']
                    print(f"✓ Session created")
                    print(f"  Session ID: {self.session_id}")
                    return True
                else:
                    print(f"✗ Session creation failed: {response.status_code}")
                    print(f"  Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"✗ Session creation error: {e}")
            return False
    
    async def test_chat_message(self, message: str, test_name: str):
        """Send a chat message and get response"""
        print(f"\n[TEST] {test_name}")
        print("-" * 50)
        print(f"Message: {message}")
        
        if not self.access_token or not self.session_id:
            print("✗ Not authenticated or no session. Complete previous tests first.")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/chat",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={
                        "message": message,
                        "session_id": self.session_id,
                        "language": "auto"
                    },
                    timeout=300.0  # Allow time for LLM response
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chat_data = data['data']
                    
                    print(f"✓ Response received")
                    print(f"  Language: {chat_data['language']}")
                    print(f"  Context used: {chat_data['context_used']}")
                    print(f"  Response time: {chat_data['response_time_ms']}ms")
                    print(f"\n  AI Response:")
                    print(f"  {chat_data['response'][:300]}...")
                    
                    return True
                else:
                    print(f"✗ Chat failed: {response.status_code}")
                    print(f"  Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"✗ Chat error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("PHASE 4 - RAG PIPELINE & CHAT API TESTING")
        print("=" * 60)
        
        # Infrastructure tests
        tests_passed = 0
        tests_total = 0
        
        tests_total += 1
        if await self.test_ollama_connection():
            tests_passed += 1
        
        tests_total += 1
        if await self.test_chromadb():
            tests_passed += 1
        
        tests_total += 1
        if await self.test_api_health():
            tests_passed += 1
        
        # Authentication tests
        tests_total += 1
        if await self.login():
            tests_passed += 1
        else:
            print("\n⚠ Skipping chat tests - authentication required")
            self.print_summary(tests_passed, tests_total)
            return
        
        tests_total += 1
        if await self.create_chat_session():
            tests_passed += 1
        else:
            print("\n⚠ Skipping chat tests - session creation required")
            self.print_summary(tests_passed, tests_total)
            return
        
        # Chat functionality tests
        chat_tests = [
            ("Show my pending applications", "Pending Applications Query"),
            ("What is the ISD workflow?", "Workflow Knowledge Query"),
            ("How many field visits do I need to schedule?", "Field Visit Query"),
            ("What documents are required for NISD?", "Document Requirements Query")
        ]
        
        for message, test_name in chat_tests:
            tests_total += 1
            if await self.test_chat_message(message, test_name):
                tests_passed += 1
            
            # Wait a bit between requests
            await asyncio.sleep(1)
        
        # Summary
        self.print_summary(tests_passed, tests_total)
    
    def print_summary(self, passed: int, total: int):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n✓ All tests passed! Phase 4 is working correctly.")
        elif passed >= total * 0.7:
            print("\n⚠ Some tests failed. Review the output above.")
        else:
            print("\n✗ Many tests failed. Check your setup:")
            print("  1. Ensure Ollama is running: ollama serve")
            print("  2. Run document ingestion: python backend/ingest.py")
            print("  3. Start the API: uvicorn backend.main:app --reload")
            print("  4. Create test officer account if needed")
        
        print("=" * 60)


async def main():
    """Main test function"""
    tester = Phase4Tester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
