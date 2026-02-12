import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Key starts with: {key[:10]}...")
try:
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('Say hello in one word')
    print(f"✅ SUCCESS! Response: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {e}")
