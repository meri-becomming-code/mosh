import sys
sys.path.insert(0, r'c:\Users\mkasprak\Desktop\New folder\mosh')

import converter_utils
import os

pdf_path = r'C:\Users\mkasprak\Downloads\add-100-download for demo_extracted\web_resources\Python_Operators.pdf'

print("Converting PDF with IMPROVED code...")
print(f"PDF: {os.path.basename(pdf_path)}")

if os.path.exists(pdf_path):
    result, error = converter_utils.convert_pdf_to_html(pdf_path)
    if result:
        print(f"\n✓ SUCCESS! Generated: {result}")
        print("\nNow compare:")
        print(f"  OLD (before improvements): {pdf_path.replace('.pdf', '.html')}")
        print(f"  NEW (after improvements):  {result}")
    else:
        print(f"\n✗ ERROR: {error}")
else:
    print("\n✗ PDF not found!")
    print(f"Path: {pdf_path}")
