from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Key starts with: {key[:10]}...")
try:
    client = genai.Client(api_key=key)
    # ✅ ПРАВИЛЬНА МОДЕЛЬ (з аналізу Cursor)
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents='Say hello in one word'
    )
    print(f"✅ SUCCESS! Response: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
