"""
Test script to verify IBM Watson services configuration.
"""
from app.config import Config

def main():
    print("=" * 70)
    print("FINSY AGENT - IBM WATSON SERVICES CONFIGURATION STATUS")
    print("=" * 70)
    
    # Check configuration
    missing = Config.validate()
    
    print("\n📋 SERVICE STATUS:")
    print("-" * 70)
    
    # NLU
    nlu_status = "✅ ENABLED" if Config.ENABLE_NLU else "❌ DISABLED"
    print(f"Natural Language Understanding: {nlu_status}")
    if Config.ENABLE_NLU:
        print(f"  └─ URL: {Config.NLU_URL}")
        print(f"  └─ API Key: {'***' + Config.NLU_API_KEY[-8:] if Config.NLU_API_KEY else 'NOT SET'}")
    
    # Cloudant
    cloudant_status = "✅ ENABLED" if Config.USE_CLOUDANT else "❌ DISABLED"
    print(f"\nCloudant Database: {cloudant_status}")
    if Config.USE_CLOUDANT:
        print(f"  └─ URL: {Config.CLOUDANT_URL}")
        print(f"  └─ API Key: {'***' + Config.CLOUDANT_API_KEY[-8:] if Config.CLOUDANT_API_KEY else 'NOT SET'}")
        print(f"  └─ Database: {Config.CLOUDANT_DB_NAME}")
    
    # Speech Services
    speech_status = "✅ ENABLED" if Config.ENABLE_SPEECH else "❌ DISABLED"
    print(f"\nSpeech Services: {speech_status}")
    if Config.ENABLE_SPEECH:
        stt_ok = "✅" if Config.STT_API_KEY and Config.STT_URL else "⚠️"
        print(f"  └─ Speech-to-Text: {stt_ok}")
        if Config.STT_URL:
            print(f"      └─ URL: {Config.STT_URL}")
        tts_ok = "✅" if Config.TTS_API_KEY and Config.TTS_URL else "⚠️ Not configured"
        print(f"  └─ Text-to-Speech: {tts_ok}")
    
    # Orchestrate
    orchestrate_status = "✅ ENABLED" if Config.ENABLE_ORCHESTRATE else "❌ DISABLED"
    print(f"\nwatsonx Orchestrate: {orchestrate_status}")
    if Config.ENABLE_ORCHESTRATE:
        print(f"  └─ URL: {Config.ORCHESTRATE_URL}")
        print(f"  └─ API Key: {'***' + Config.ORCHESTRATE_API_KEY[-8:] if Config.ORCHESTRATE_API_KEY else 'NOT SET'}")
    
    # watsonx.ai
    watsonx_status = "✅ ENABLED" if Config.ENABLE_WATSONX else "❌ DISABLED"
    print(f"\nwatsonx.ai: {watsonx_status}")
    if Config.ENABLE_WATSONX:
        print(f"  └─ URL: {Config.WATSONX_URL}")
        print(f"  └─ Project ID: {Config.WATSONX_PROJECT_ID or '⚠️ NOT SET'}")
    
    print("\n" + "=" * 70)
    print("⚙️  CONFIGURATION VALIDATION:")
    print("-" * 70)
    
    if missing:
        print(f"❌ Missing required configuration:")
        for item in missing:
            print(f"   - {item}")
    else:
        print("✅ All required configuration is present!")
    
    print("=" * 70)
    
    # Try to connect to services
    print("\n🔌 TESTING SERVICE CONNECTIONS:")
    print("-" * 70)
    
    # Test NLU
    if Config.ENABLE_NLU:
        try:
            from app.nlu_service import nlu_service
            if nlu_service.connect():
                print("✅ NLU Service: Connected")
            else:
                print("⚠️ NLU Service: Failed to connect")
        except Exception as e:
            print(f"❌ NLU Service: Error - {str(e)[:60]}")
    
    # Test Speech
    if Config.ENABLE_SPEECH:
        try:
            from app.speech_service import speech_service
            if speech_service.connect():
                stt_msg = "✅" if speech_service.is_stt_connected() else "⚠️"
                tts_msg = "✅" if speech_service.is_tts_connected() else "⚠️"
                print(f"{stt_msg} Speech-to-Text: {'Connected' if speech_service.is_stt_connected() else 'Not connected'}")
                print(f"{tts_msg} Text-to-Speech: {'Connected' if speech_service.is_tts_connected() else 'Not connected'}")
            else:
                print("⚠️ Speech Services: Failed to connect")
        except Exception as e:
            print(f"❌ Speech Services: Error - {str(e)[:60]}")
    
    # Test Cloudant
    if Config.USE_CLOUDANT:
        try:
            from app.cloudant_client import cloudant_client
            if cloudant_client.connect():
                print("✅ Cloudant Database: Connected")
            else:
                print("⚠️ Cloudant Database: Failed to connect")
        except Exception as e:
            print(f"❌ Cloudant Database: Error - {str(e)[:60]}")
    
    print("=" * 70)
    print("\n✨ Configuration check complete!")
    print("\nFor detailed setup information, see: docs/IBM_WATSON_SETUP.md\n")

if __name__ == "__main__":
    main()
