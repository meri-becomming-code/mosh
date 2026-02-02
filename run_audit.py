# Created by Dr. Meri Kasprak.
# Dedicated to the academic community to make the world a slightly better, more accessible place.
# Released freely under the GNU GPLv3 License. USE AT YOUR OWN RISK.

import os
import json
import re
from bs4 import BeautifulSoup

# --- Helper Functions (Math & Logic) ---
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6: return None
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_luminance(rgb):
    rag = []
    for c in rgb:
        c = c / 255.0
        if c <= 0.03928: rag.append(c / 12.92)
        else: rag.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * rag[0] + 0.7152 * rag[1] + 0.0722 * rag[2]

def get_contrast_ratio(hex1, hex2):
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    if not rgb1 or not rgb2: return None
    lum1 = get_luminance(rgb1)
    lum2 = get_luminance(rgb2)
    return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)

# --- Check Functions ---

def check_style_contrast(tag):
    """Calculates WCAG AA Contrast Ratio."""
    style = tag.get('style', '').lower()
    if not style: return None
    fg_match = re.search(r'(?:^|[\s;])color:\s*(#[0-9a-fA-F]{3,6})', style)
    bg_match = re.search(r'background-color:\s*(#[0-9a-fA-F]{3,6})', style)
    # DEBUG
    # print(f"Checking style: {style}")
    
    if fg_match and bg_match:
        rgb1 = hex_to_rgb(fg_match.group(1))
        rgb2 = hex_to_rgb(bg_match.group(1))
        
        ratio = get_contrast_ratio(fg_match.group(1), bg_match.group(1))
        
        if ratio and ratio < 4.5:
            return f"Contrast Fail ({ratio:.2f}:1) {fg_match.group(1)} on {bg_match.group(1)}"
    return None

def check_headings(soup):
    issues = []
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if not headings: return ["No headings found."]
    
    first_level = int(headings[0].name[1])
    if first_level > 2: issues.append(f"Starts with H{first_level} (Should be H2)")
    
    last_level = first_level
    for h in headings[1:]:
        curr_level = int(h.name[1])
        if curr_level > last_level + 1:
            issues.append(f"Skipped level: H{last_level} -> H{curr_level}")
        last_level = curr_level
    return issues

    # Simplify result if empty
    if not results["technical"] and not results["subjective"]:
        return None
    return results

def check_viewport(soup):
    """Reflow Check: Ensures <meta name='viewport'> exists."""
    meta = soup.find('meta', attrs={'name': 'viewport'})
    if not meta:
        return "Missing <meta name='viewport'> (Fails WCAG Reflow/Mobile)"
    content = meta.get('content', '').lower()
    if 'width=device-width' not in content:
        return "Viewport meta tag missing 'width=device-width'"
    return None

def check_reflow_styles(tag):
    """Checks for fixed width containers > 320px."""
    style = tag.get('style', '').lower()
    if not style: return None
    
    # Check 1: fixed width > 320px
    width_match = re.search(r'\bwidth:\s*(\d+)px', style)
    if width_match:
        px = int(width_match.group(1))
        if px > 320:
            return f"Fixed width {px}px (Risk of Reflow Fail on Mobile)"
            
    # Check 2: Justified text
    if "text-align: justify" in style or "text-align:justify" in style:
        return "Avoid 'text-align: justify' (Panorama/Dyslexia Issue)"
        
    return None

def audit_file(filepath):
    """
    Audits a single file and returns structured issues.
    Separates 'TECHNICAL' (Tags/Attributes) from 'SUBJECTIVE' (Content Quality).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    results = {
        "technical": [],
        "subjective": []
    }

    # 1. Document - Viewport (Reflow)
    vp_issue = check_viewport(soup)
    if vp_issue:
        results["technical"].append(vp_issue)

    # 2. Remediation Markers (from remediate_master_v3.py)
    for element in soup.find_all(string=lambda t: "[ADA FIX" in str(t) or "[FIX_ME]" in str(t)):
        results["subjective"].append(f"Remediation Tag Found: {element.strip()}")
    
    # 3. Images
    for img in soup.find_all('img'):
        alt = img.get('alt', '').strip().lower()
        if 'alt' not in img.attrs:
            results["technical"].append(f"Image missing alt attribute: {img.get('src')}")
        elif alt in ['image', 'photo', 'picture']:
             results["subjective"].append(f"Generic Alt Text: '{alt}'")
        
        # Check for LaTeX in alt text (Canvas convention is good, but just FYI)
        if re.search(r'\\\(|\\\[', alt):
            pass # This is likely a Canvas Math equation, which is safe.

    # 4. Headings
    h_issues = check_headings(soup)
    results["technical"].extend(h_issues)

    # 5. Tables
    for table in soup.find_all('table'):
        if not table.find('caption'):
            results["technical"].append("Table missing caption")
        for th in table.find_all('th'):
            if not th.has_attr('scope'):
                results["technical"].append("Header cell missing scope")

    # 6. Contrast & Style Checks (Updated)
    for tag in soup.find_all(style=True):
        # Contrast
        c_issue = check_style_contrast(tag)
        if c_issue:
            results["technical"].append(c_issue)
        
        # Reflow / Typography
        r_issue = check_reflow_styles(tag)
        if r_issue:
            results["technical"].append(r_issue)
            
    # 7. Panorama Specials
    if soup.find_all('iframe', title=False):
        results["technical"].append("Iframe missing title")
    
    # 8. Media Checks (Video/Audio Captions)
    for media in soup.find_all(['video', 'audio']):
        if not media.find('track', kind="captions") and not media.find('track', kind="subtitles"):
            tag_name = media.name
            src = media.get('src', 'embedded')
            results["technical"].append(f"<{tag_name}> missing Captions/Subtitles (<track> tag): {src[:30]}...")

    deprecated = ['b', 'i', 'font', 'center', 'blink', 'marquee']
    for tag in deprecated:
        if soup.find(tag):
            results["technical"].append(f"Deprecated tag used: <{tag}>")

    return results


def run_audit_v3(directory):
    print(f"Auditing {directory}...")
    all_issues = {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
             if file.endswith('.html'):
                path = os.path.join(root, file)
                res = audit_file(path)
                if res:
                    rel_path = os.path.relpath(path, directory)
                    all_issues[rel_path] = res
    
    out_file = os.path.join(directory, 'audit_report.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_issues, f, indent=2)
    
    print(f"Audit Complete. Issues found in {len(all_issues)} files.")
    print(f"Report saved to {out_file}")

if __name__ == "__main__":
    import sys
    print("--- MASTER AUDITOR V3 (Toolkit Merge) ---")
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("Enter path to audit: ").strip('"')
    
    if os.path.isdir(target_path):
        run_audit_v3(target_path)
    elif os.path.isfile(target_path):
        # Single file mode
        print(f"Auditing single file: {target_path}")
        issues = audit_file(target_path)
        if issues:
            print(json.dumps({target_path: issues}, indent=2))
        else:
            print("No issues found.")
    else:
        print("Invalid path.")
