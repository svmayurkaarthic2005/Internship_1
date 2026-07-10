"""
Test speech transcription directly
"""
import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.speech_service import get_speech_service

async def test_speech_service():
    """Test if speech service can initialize"""
    try:
        print("🧪 Testing Speech Service...")
        print("=" * 60)
        
        # Get service
        service = get_speech_service()
        
        # Initialize
        print("\n📦 Loading Faster-Whisper model...")
        print("   (First time will download ~150MB, please wait...)")
        service.initialize()
        
        print(f"\n✅ Model loaded successfully!")
        print(f"   - Model size: {service.model_size}")
        print(f"   - Device: {service.device}")
        print(f"   - Compute Type: {service.compute_type}")
        print(f"   - Model object: {type(service.model)}")
        
        # Test with a dummy audio file (if exists)
        test_audio_path = "test_audio.wav"
        if os.path.exists(test_audio_path):
            print(f"\n🎤 Testing transcription with {test_audio_path}...")
            result = service.transcribe_audio(test_audio_path)
            print(f"✅ Transcription result:")
            print(f"   Text: \"{result['text']}\"")
            print(f"   Language: {result['language']}")
            print(f"   Confidence: {result['language_probability']:.2%}")
        else:
            print(f"\nℹ️  No test audio file found at {test_audio_path}")
            print("   To test transcription, create a test audio file:")
            print("   - Record a .wav file")
            print("   - Save as test_audio.wav in this directory")
            print("   - Run this script again")
        
        print("\n" + "=" * 60)
        print("✅ Speech service is working correctly!")
        print("\nYou can now:")
        print("1. Start the backend: python -m uvicorn backend.main:app --reload")
        print("2. Test voice input in the chatbot")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nDetails:")
        import traceback
        traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Troubleshooting:")
        print("=" * 60)
        
        error_str = str(e).lower()
        
        if "ffmpeg" in error_str or "ffprobe" in error_str:
            print("\n🔧 FFmpeg is not installed or not in PATH")
            print("\nTo install FFmpeg:")
            print("  Windows: choco install ffmpeg  OR  download from ffmpeg.org")
            print("  Mac: brew install ffmpeg")
            print("  Linux: sudo apt install ffmpeg")
            
        elif "connection" in error_str or "network" in error_str:
            print("\n🌐 Network error - model download failed")
            print("Check your internet connection and try again")
            
        elif "permission" in error_str:
            print("\n🔒 Permission error")
            print("Try running with appropriate permissions")
            
        else:
            print("\n❓ Unknown error")
            print("Please check the error details above")
            print("\nYou can also try:")
            print("  1. pip install --upgrade faster-whisper")
            print("  2. pip install ffmpeg-python")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_speech_service())
    sys.exit(0 if success else 1)
