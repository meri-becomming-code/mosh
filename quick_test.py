import sys
sys.path.insert(0, r'c:\Users\mkasprak\Desktop\New folder\mosh')

import converter_utils
import os

# Test the specific PDF from the issue
pdf_path = r'C:\Users\mkasprak\Downloads\add-100-download for demo_extracted\web_resources\Python_Operators.pdf'

print("Testing PDF conversion...")
print(f"PDF: {os.path.basename(pdf_path)}")
print(f"Exists: {os.path.exists(pdf_path)}")

if os.path.exists(pdf_path):
    result, error = converter_utils.convert_pdf_to_html(pdf_path)
    if result:
        print(f"\n✓ SUCCESS! Generated: {result}")
        
        # Show snippet of output
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the body content
        start = content.find('<body>')
        end = content.find('</body>')
        if start != -1 and end != -1:
            body = content[start:end]
            # Count structures
            print(f"\nStructure Analysis:")
            print(f"  <p> tags: {body.count('<p>')}")
            print(f"  <ul> tags: {body.count('<ul>')}")
            print(f"  <li> tags: {body.count('<li>')}")
            print(f"  <h2> tags: {body.count('<h2>')}")
            print(f"  <h3> tags: {body.count('<h3>')}")
            
            # Show first 1000 chars of body
            print(f"\nFirst 1000 characters of body:")
            print(body[:1000])
    else:
        print(f"\n✗ ERROR: {error}")
else:
    print("\n✗ PDF file not found!")
