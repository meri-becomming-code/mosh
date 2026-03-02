import re
import urllib.parse
import os

def check_link(link_html, old_filename, new_base):
    old_base, old_ext = os.path.splitext(old_filename)
    
    # Fuzzy escape: handles spaces as either spaces or %20
    e_old_base = re.escape(old_base).replace(r'\ ', r'(?:\ |%20)')
    e_old_ext = re.escape(old_ext)
    
    # Pattern includes optional prefix and optional query params
    pattern = rf'href="([^"]*/)?{e_old_base}{e_old_ext}(\?[^"]*)?"'
    
    print(f"Testing: {link_html}")
    print(f"Pattern: {pattern}")
    
    match = re.search(pattern, link_html, re.IGNORECASE)
    if match:
        result = re.sub(pattern, rf'href="\1{new_base}.html\2"', link_html, flags=re.IGNORECASE)
        print(f"MATCH! Result: {result}")
        return True
    else:
        print("NO MATCH")
        return False

# Test cases
new_base = "Syllabus"

# Case 1: Simple space
check_link('href="My Syllabus.docx"', "My Syllabus.docx", new_base)

# Case 2: URL encoded
check_link('href="My%20Syllabus.docx"', "My Syllabus.docx", new_base)

# Case 3: With prefix and query params
check_link('href="$IMS-CC-FILEBASE$/Uploaded%20Media/My%20Syllabus.docx?canvas_qs=1"', "My Syllabus.docx", new_base)

# Case 4: Mismatched (Syllabus2)
check_link('href="My Syllabus2.docx"', "My Syllabus.docx", new_base)
