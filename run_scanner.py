import os
import json
import re
from bs4 import BeautifulSoup
import sys

# --- Configuration ---
BAD_ALT_TEXT = ['image', 'photo', 'picture', 'spacer', 'undefined', 'null']
BAD_LINK_TEXT = ['click here', 'here', 'read more', 'link', 'more info', 'info']

def get_context(tag, length=100):
    """Returns the surrounding characters of a tag for context."""
    # This is a rough approximation since BS4 deconstructs the tree.
    # We will just return the parent text.
    parent = tag.parent
    if parent:
        text = parent.get_text(separator=' ', strip=True)
        return text[:length] + "..." if len(text) > length else text
    return ""

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # 1. Check Images
    for img in soup.find_all('img'):
        alt = img.get('alt', '').strip().lower()
        src = img.get('src', '')
        filename = os.path.basename(src).lower()
        
        issue_type = None
        reason = None
        
        if 'alt' not in img.attrs:
            issue_type = "missing_alt"
            reason = "Missing alt attribute"
        elif alt in BAD_ALT_TEXT:
            issue_type = "bad_alt"
            reason = f"Generic alt text: '{alt}'"
        elif alt == filename or alt == filename.replace('-', ' ').replace('_', ' '):
            issue_type = "filename_alt"
            reason = "Filename used as alt text"
        elif "[fix_me]" in alt:
             issue_type = "marker_found"
             reason = "Previous remediation marker found"

        if issue_type:
            return {
                "file": filepath,
                "found": True,
                "type": "image",
                "issue": issue_type,
                "reason": reason,
                "tag_str": str(img),
                "src": src,
                "current_alt": img.get('alt', ''),
                "context": get_context(img)
            }

    # 2. Check Links
    for a in soup.find_all('a'):
        text = a.get_text(strip=True).lower()
        href = a.get('href', '')
        
        issue_type = None
        reason = None
        
        if text in BAD_LINK_TEXT:
            issue_type = "bad_link_text"
            reason = f"Vague link text: '{text}'"
        
        # Check for marker in text
        if "[fix_me]" in text or "[ada fix" in text:
             issue_type = "marker_found"
             reason = "Remediation marker found in link"

        if issue_type:
            return {
                "file": filepath,
                "found": True,
                "type": "link",
                "issue": issue_type,
                "reason": reason,
                "tag_str": str(a),
                "href": href,
                "current_text": a.get_text(strip=True),
                "context": get_context(a)
            }
            
    return None

def main(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                result = scan_file(path)
                if result:
                    print(json.dumps(result, indent=2))
                    return # Stop after first find
    
    # If nothing found
    print(json.dumps({"found": False}, indent=2))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = os.getcwd()
    main(target)
