import sys
sys.path.insert(0, r'c:\Users\mkasprak\Desktop\New folder\mosh')

import converter_utils
import os
import shutil

pdf_path = r'C:\Users\mkasprak\Downloads\add-100-download for demo_extracted\web_resources\Python_Operators.pdf'
old_html = pdf_path.replace('.pdf', '.html')
backup_html = pdf_path.replace('.pdf', '_BEFORE.html')

print("COMPARISON TEST")
print("="*60)

# 1. Backup the old file
if os.path.exists(old_html):
    shutil.copy2(old_html, backup_html)
    print(f"\n1. Backed up OLD version to:")
    print(f"   {backup_html}")
    
    with open(old_html, 'r', encoding='utf-8') as f:
        old_content = f.read()
    print(f"\n   OLD file stats:")
    print(f"   - Lines: {old_content.count(chr(10))}")
    print(f"   - <p> tags: {old_content.count('<p>')}")
    print(f"   - <ul> tags: {old_content.count('<ul>')}")
    print(f"   - <li> tags: {old_content.count('<li>')}")

# 2. Reconvert with NEW code
print(f"\n2. Reconverting with IMPROVED code...")
if os.path.exists(pdf_path):
    result, error = converter_utils.convert_pdf_to_html(pdf_path)
    if result:
        print(f"   ✓ Generated: {os.path.basename(result)}")
        
        with open(result, 'r', encoding='utf-8') as f:
            new_content = f.read()
        print(f"\n   NEW file stats:")
        print(f"   - Lines: {new_content.count(chr(10))}")
        print(f"   - <p> tags: {new_content.count('<p>')}")
        print(f"   - <ul> tags: {new_content.count('<ul>')}")
        print(f"   - <li> tags: {new_content.count('<li>')}")
        
        print(f"\n3. COMPARISON:")
        print(f"   BEFORE (old code): {backup_html}")
        print(f"   AFTER (new code):  {result}")
        print(f"\n   Open both files to see the difference!")
    else:
        print(f"   ✗ ERROR: {error}")
else:
    print(f"   ✗ PDF not found!")
