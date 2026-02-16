
import os
from google import genai

key = "AIzaSyBmi28or6Mcw1NUq1A2tm2Cv-jsg3U3cBc"
client = genai.Client(api_key=key)

print("Listing available models...")
try:
    for model in client.models.list(config={"page_size": 100}):
        print(f"- {model.name}")
except Exception as e:
    print(f"Error: {e}")
