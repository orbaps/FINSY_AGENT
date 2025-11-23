"""Quick verification that .env is loaded correctly"""
import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("🔧 ENVIRONMENT VARIABLES VERIFICATION")
print("="*60)

services = {
    "NLU": ("NLU_API_KEY", "NLU_URL", "ENABLE_NLU"),
    "Cloudant": ("CLOUDANT_API_KEY", "CLOUDANT_URL", "USE_CLOUDANT"),
    "Speech-to-Text": ("STT_API_KEY", "STT_URL", "ENABLE_SPEECH"),
    "Orchestrate": ("ORCHESTRATE_API_KEY", "ORCHESTRATE_URL", "ENABLE_ORCHESTRATE"),
}

for name, keys in services.items():
    print(f"\n{name}:")
    for key in keys:
        value = os.getenv(key)
        if key.endswith("_KEY"):
            status = f"✅ Set (***{value[-8:]})" if value else "❌ Not set"
        elif key.startswith("ENABLE_") or key.startswith("USE_"):
            status = f"✅ {value}" if value else "❌ Not set"
        else:
            status = f"✅ {value[:50]}..." if value and len(value) > 50 else f"✅ {value}" if value else "❌ Not set"
        print(f"  {key}: {status}")

print("\n" + "="*60)
print("✅ Environment file loaded successfully!")
print("="*60 + "\n")
