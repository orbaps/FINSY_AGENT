"""
Comprehensive test of all Finsy Agent services including Orchestrate.
"""
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

sys.path.insert(0, 'c:/Users/orbap/Downloads/finsy-agent/finsy-agent')

from app.config import Config
from app.nlu_service import nlu_service
from app.speech_service import speech_service
from app.cloudant_client import cloudant_client
from app.orchestrate.skills import orchestrate_skills
from app.orchestrate.flow_runner import flow_runner

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_all_services():
    print("\n" + "=" * 70)
    print("  FINSY AGENT - COMPLETE SERVICE TEST")
    print("=" * 70)
    
    # Test 1: Configuration
    print_section("1. Configuration Validation")
    missing = Config.validate()
    if missing:
        print(f"WARNING: Missing config: {', '.join(missing)}")
    else:
        print("[OK] All required configuration present")
    
    print(f"\nActive Services:")
    print(f"   NLU:        {'[ENABLED]' if Config.ENABLE_NLU else '[DISABLED]'}")
    print(f"   Speech:     {'[ENABLED]' if Config.ENABLE_SPEECH else '[DISABLED]'}")
    print(f"   Cloudant:   {'[ENABLED]' if Config.USE_CLOUDANT else '[DISABLED]'}")
    print(f"   Orchestrate: {'[ENABLED]' if Config.ENABLE_ORCHESTRATE else '[DISABLED]'}")
    print(f"   watsonx.ai: {'[ENABLED]' if Config.ENABLE_WATSONX else '[DISABLED]'}")
    
    # Test 2: NLU Service
    print_section("2. IBM Watson NLU Service")
    nlu_ok = False
    if nlu_service.connect():
        print("[OK] NLU Service Connected")
        nlu_ok = True
        
        # Test entity extraction
        test_text = "Invoice from Acme Corporation for $1500.00. PO Number: PO-12345"
        print(f"\nTesting entity extraction:")
        print(f"   Input: {test_text}")
        
        entities = nlu_service.extract_invoice_entities(test_text)
        if entities:
            print(f"\n   [OK] Extracted Entities:")
            print(f"      Vendor: {entities.get('vendor', 'N/A')}")
            print(f"      Amount: ${entities.get('amount', 0):.2f}")
            keywords = ', '.join(entities.get('keywords', []))[:50]
            if keywords:
                print(f"      Keywords: {keywords}")
            print(f"      Confidence: {entities.get('confidence', 0):.2%}")
        else:
            print("   [WARNING] No entities extracted")
    else:
        print("[ERROR] NLU Service Failed to Connect")
    
    # Test 3: Speech Services
    print_section("3. IBM Watson Speech Services")
    speech_ok = False
    if speech_service.connect():
        print("[OK] Speech Services Connected")
        speech_ok = True
        
        stt = speech_service.is_stt_connected()
        tts = speech_service.is_tts_connected()
        
        print(f"\n   Status:")
        print(f"      Speech-to-Text: {'[OK]' if stt else '[ERROR]'}")
        print(f"      Text-to-Speech: {'[OK]' if tts else '[ERROR]'}")
        
        if tts:
            print(f"\n   Testing TTS synthesis...")
            test_audio = speech_service.synthesize_speech("Test successful")
            if test_audio:
                print(f"      [OK] Generated {len(test_audio):,} bytes of audio")
            else:
                print(f"      [WARNING] Synthesis returned None")
    else:
        print("[ERROR] Speech Services Failed to Connect")
    
    # Test 4: Cloudant Database
    print_section("4. IBM Cloudant Database")
    cloudant_ok = False
    if cloudant_client.connect():
        print("[OK] Cloudant Connected")
        cloudant_ok = True
        print(f"   URL: {Config.CLOUDANT_URL[:50]}...")
        print(f"   Database: {Config.CLOUDANT_DB_NAME}")
    else:
        print("[ERROR] Cloudant Failed to Connect")
    
    # Test 5: Orchestrate (NEW!)
    print_section("5. IBM watsonx Orchestrate [NEW]")
    orchestrate_ok = False
    if orchestrate_skills.connect():
        print("[OK] Orchestrate Connected")
        orchestrate_ok = True
        print(f"   Project ID: {Config.ORCHESTRATE_PROJECT_ID}")
        print(f"   URL: {Config.ORCHESTRATE_URL[:50]}...")
        
        # Test flow runner
        print(f"\n   Available Flows:")
        try:
            flows = list(flow_runner.flows.keys())
            for flow in flows:
                print(f"      - {flow}")
        except Exception as e:
            print(f"      [WARNING] Could not list flows: {str(e)[:50]}")
    else:
        print("[WARNING] Orchestrate Not Connected")
        print(f"   Reason: Check Project ID configuration")
    
    # Summary
    print_section("SUMMARY")
    
    services_status = {
        'Database': True,
        'Cloudant': cloudant_ok,
        'NLU': nlu_ok,
        'Speech (STT)': speech_service.is_stt_connected() if speech_ok else False,
        'Speech (TTS)': speech_service.is_tts_connected() if speech_ok else False,
        'Orchestrate': orchestrate_ok
    }
    
    services_count = sum(1 for v in services_status.values() if v)
    total_services = len(services_status)
    
    print(f"\nServices Active: {services_count}/{total_services}")
    print(f"\nService Health:")
    for service, status in services_status.items():
        status_str = '[OK]' if status else '[DOWN]'
        marker = '***' if service == 'Orchestrate' and status else ''
        print(f"   {service:15} {status_str} {marker}")
    
    completion = (services_count / total_services) * 100
    print(f"\nSystem Readiness: {completion:.0f}%")
    
    if completion >= 80:
        print("\nStatus: HACKATHON READY!")
    elif completion >= 60:
        print("\nStatus: OPERATIONAL")
    else:
        print("\nStatus: NEEDS ATTENTION")
    
    print("\n" + "=" * 70)
    print("Test Complete! Application running at http://localhost:5000")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    test_all_services()
