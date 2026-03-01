import sys
import google.genai as genai
import time
from pathlib import Path

# Need to load actual API key since 'fake' won't work hitting the real API.
import json
config = json.load(open(r'c:\Users\mered\OneDrive\Desktop\mosh-1\toolkit_config.json'))
api_key = config.get('gemini_api_key', '')
if not api_key:
    # Try getting it from Jeanie AI... wait jeanie_ai is config based
    sys.path.insert(0, r'c:\Users\mered\OneDrive\Desktop\mosh-1')
    import jeanie_ai
    # jeanie ai reads from toolkit_config.json as well.
    print("No API key")
    sys.exit()

client = genai.Client(api_key=api_key)

doc_path = r'c:\Users\mered\Downloads\new-math-export (1)_extracted\web_resources\Chapter 3 Note Packet (Key) (4).docx'

f = client.files.upload(file=doc_path)
print("Uploaded", f.name)

while True:
    f = client.files.get(name=f.name)
    if f.state.name == 'ACTIVE':
        break
    time.sleep(2)

response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=['Convert this document exactly to accessible HTML. Return only the raw HTML body content.', f]
)

print(response.text[:1000])
