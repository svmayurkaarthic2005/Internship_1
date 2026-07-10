"""
Setup verification script
Run this to verify the project structure and dependencies
"""
import sys
import os
from pathlib import Path

def check_directories():
    """Check if all required directories exist"""
    print("📁 Checking directory structure...")
    
    required_dirs = [
        "backend",
        "backend/routers",
        "backend/services",
        "backend/utils",
        "backend/documents",
        "backend/vectorstore",
        "frontend",
        "frontend/css",
        "frontend/js",
        "frontend/assets"
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists():
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} - MISSING")
            missing.append(dir_path)
    
    return len(missing) == 0

def check_files():
    """Check if all required files exist"""
    print("\n📄 Checking required files...")
    
    required_files = [
        "backend/main.py",
        "backend/config.py",
        "backend/database.py",
        "backend/models.py",
        "backend/schemas.py",
        "backend/dependencies.py",
        "backend/seed.py",
        "backend/routers/auth.py",
        "backend/routers/chat.py",
        "backend/routers/applications.py",
        "backend/routers/survey.py",
        "backend/services/auth_service.py",
        "backend/services/chatbot.py",
        "backend/services/rag.py",
        "backend/services/chroma.py",
        "backend/services/embeddings.py",
        "backend/services/postgres.py",
        "frontend/login.html",
        "frontend/chatbot.html",
        "frontend/css/variables.css",
        "frontend/css/global.css",
        "frontend/css/animations.css",
        "frontend/css/components.css",
        "frontend/css/chatbot.css",
        "frontend/css/responsive.css",
        "frontend/js/auth.js",
        "frontend/js/chat.js",
        "requirements.txt",
        ".env.example",
        "README.md"
    ]
    
    missing = []
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
            missing.append(file_path)
    
    return len(missing) == 0

def check_dependencies():
    """Check if dependencies can be imported"""
    print("\n📦 Checking Python dependencies...")
    
    dependencies = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pydantic", "Pydantic"),
        ("passlib", "Passlib"),
        ("jose", "Python-JOSE"),
    ]
    
    all_ok = True
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError:
            print(f"  ❌ {display_name} - NOT INSTALLED")
            all_ok = False
    
    return all_ok

def check_env():
    """Check if .env file exists"""
    print("\n🔐 Checking environment configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_example.exists():
        print(f"  ✅ .env.example exists")
    else:
        print(f"  ❌ .env.example missing")
        return False
    
    if env_file.exists():
        print(f"  ✅ .env file exists")
        print(f"  ℹ️  Remember to update SECRET_KEY and database credentials!")
    else:
        print(f"  ⚠️  .env file not found")
        print(f"  ℹ️  Run: cp .env.example .env")
        print(f"  ℹ️  Then update the values in .env")
    
    return True

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("SIS CHATBOT PORTAL - SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    checks = [
        ("Directory Structure", check_directories),
        ("Required Files", check_files),
        ("Python Dependencies", check_dependencies),
        ("Environment Config", check_env)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error during {name} check: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! You're ready to proceed.")
        print("\nNext steps:")
        print("1. Create PostgreSQL database: sis_db")
        print("2. Copy .env.example to .env and update values")
        print("3. Run: python -m backend.seed")
        print("4. Run: uvicorn backend.main:app --reload")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nIf dependencies are missing, run:")
        print("  pip install -r requirements.txt")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
