
import os
import sys
from pathlib import Path
from pypdf import PdfReader
from google import genai

# Setup paths
pdf_path = r"c:\Users\meri\OneDrive - McHenry County College\Desktop\new-math-export_extracted\web_resources\Chapter 10 Note Packet (Key) (2).pdf"
html_path = r"c:\Users\meri\OneDrive - McHenry County College\Desktop\mosh\Chapter 10 Note Packet (Key) (2).html"

# Setup Gemini
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    api_key = input("Enter Gemini API Key: ").strip()

print(f"Using API Key: {api_key[:5]}...")
client = genai.Client(api_key=api_key)

def verify_page_text(page_num, pdf_text, html_content):
    prompt = f"""
    You are a Quality Assurance specialist. 
    Compare this original PDF text content with the converted HTML content.
    
    ORIGINAL PDF TEXT (Page {page_num}):
    {pdf_text}
    
    CONVERTED HTML CONTENT:
    {html_content}
    
    Task:
    1. Verify if the math concepts and text in the HTML match the PDF text.
    2. Check if the structure (headings, problem numbers) is preserved.
    3. Note that PDF text extraction might lose some formatting/math symbols, so be lenient on exact symbol matches, but look for key numbers/variables.
    4. Report missing content or major discrepancies.
    
    Return a brief summary of the accuracy for Page {page_num}.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        return f"Error verifying page {page_num}: {e}"

print(f"Verifying conversion for: {Path(pdf_path).name}")

# Read HTML
try:
    with open(html_path, 'r', encoding='utf-8') as f:
        html_text = f.read()
except FileNotFoundError:
    print(f"HTML file not found: {html_path}")
    sys.exit(1)

# Read PDF Text
print("Extracting PDF text...")
try:
    reader = PdfReader(pdf_path)
    print(f"PDF has {len(reader.pages)} pages")
except Exception as e:
    print(f"Could not read PDF: {e}")
    sys.exit(1)

reviews = []

# Check first 3 pages
for i in range(min(3, len(reader.pages))):
    page_num = i + 1
    print(f"Analyzing Page {page_num}...")
    
    pdf_text = reader.pages[i].extract_text()
    
    # Extract relevant HTML section
    marker = f"<!-- Page {page_num} -->"
    next_marker = f"<!-- Page {page_num+1} -->"
    
    start_idx = html_text.find(marker)
    if start_idx != -1:
        end_idx = html_text.find(next_marker)
        if end_idx == -1:
             end_idx = len(html_text)
        page_html = html_text[start_idx:end_idx]
    else:
        # Fallback based on content structure
        if page_num == 1:
             page_html = html_text[:3000] 
        else:
             page_html = "Content marker not found."
    
    review = verify_page_text(page_num, pdf_text, page_html)
    reviews.append(review)

print("\n" + "="*50)
print("VERIFICATION REPORT")
print("="*50)
for r in reviews:
    print(r)
    print("-" * 30)
