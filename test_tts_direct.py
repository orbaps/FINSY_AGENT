"""
Test Text-to-Speech service directly without going through the API.
"""
import sys
sys.path.insert(0, 'c:/Users/orbap/Downloads/finsy-agent/finsy-agent')

from app.speech_service import speech_service
from app.config import Config

def test_tts():
    print("=" * 70)
    print("Testing IBM Text-to-Speech Service")
    print("=" * 70)
    
    # Connect to service
    print("\n1. Connecting to Speech services...")
    if speech_service.connect():
        print("   ✅ Connected to Speech services")
    else:
        print("   ❌ Failed to connect")
        return
    
    # Check TTS status
    print("\n2. Checking Text-to-Speech status...")
    if speech_service.is_tts_connected():
        print("   ✅ Text-to-Speech is connected")
    else:
        print("   ❌ Text-to-Speech is not connected")
        return
    
    # Synthesize speech
    print("\n3. Synthesizing test speech...")
    text = "Hello! This is a test of the IBM Watson Text-to-Speech service for the Finsy Agent application."
    
    try:
        audio = speech_service.synthesize_speech(text)
        
        if audio:
            # Save to file
            with open("test_tts_output.wav", "wb") as f:
                f.write(audio)
            
            print(f"   ✅ Speech synthesized successfully!")
            print(f"   📁 Audio saved to: test_tts_output.wav")
            print(f"   📊 Audio size: {len(audio)} bytes")
        else:
            print("   ❌ Synthesis returned None")
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 70)
    print("✨ Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    test_tts()
