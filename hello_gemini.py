"""hello_gemini.py — Smallest possible Gemini API call. Verifies the key works."""
import os
from google import genai

if not os.environ.get("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY is not set.")
    print("Run: export GOOGLE_API_KEY='your-key-here'")
    exit(1)

client = genai.Client()  # picks up GOOGLE_API_KEY from the environment automatically

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say 'Hello, red teamer!' and nothing else.",
)

print(response.text)

