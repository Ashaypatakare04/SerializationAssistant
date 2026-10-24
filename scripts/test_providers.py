import asyncio
import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx
from backend.app.core.config import settings
from backend.app.providers.openai_provider import OpenAIProvider
from backend.app.providers.stability_provider import StabilityProvider
from backend.app.providers.gemini_provider import GeminiProvider

async def test_openai():
    print("[*] Testing OpenAI connectivity...")
    provider = OpenAIProvider()
    print("    Configured:", provider.is_configured())
    # Test models endpoint or simple prompt
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {provider.api_key}"}
            )
            print(f"    OpenAI Models HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                print("    [OK] OpenAI API Key is valid and authenticated!")
            else:
                print(f"    [FAIL] OpenAI Error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"    [ERROR] OpenAI request exception: {e}")

async def test_stability():
    print("[*] Testing Stability AI connectivity...")
    provider = StabilityProvider()
    print("    Configured:", provider.is_configured())
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Check account balance or user info endpoint
            resp = await client.get(
                "https://api.stability.ai/v1/user/balance",
                headers={"Authorization": f"Bearer {provider.api_key}"}
            )
            print(f"    Stability AI Balance HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                balance_data = resp.json()
                print(f"    [OK] Stability AI Key is valid! Credits: {balance_data.get('credits', 'N/A')}")
            else:
                print(f"    [FAIL] Stability Error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"    [ERROR] Stability request exception: {e}")

async def test_gemini():
    print("[*] Testing Google Gemini connectivity...")
    provider = GeminiProvider()
    print("    Configured:", provider.is_configured())
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={provider.api_key}"
            resp = await client.get(url)
            print(f"    Gemini Models HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                print("    [OK] Google Gemini API Key is valid and authenticated!")
            else:
                print(f"    [FAIL] Gemini Error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"    [ERROR] Gemini request exception: {e}")

async def main():
    print("==========================================")
    print("API PROVIDER CONNECTIVITY SMOKE TEST")
    print("==========================================")
    await test_openai()
    print()
    await test_stability()
    print()
    await test_gemini()
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
