# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License version 3. USE AT YOUR OWN RISK.

import os
import json
import re
from bs4 import BeautifulSoup

# --- Helper Functions (Math & Logic) ---
def hex_to_rgb(color_str):
    """Converts hex OR basic named colors to RGB."""
    color_str = color_str.lower().strip()
    named_colors = {
        'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 
        'blue': '#0000ff', 'green': '#008000', 'yellow': '#ffff00',
        'gray': '#808080', 'grey': '#808080', 'purple': '#800080',
        'orange': '#ffa500', 'transparent': 'inherit' # Special case
    }
    if color_str in named_colors:
        color_str = named_colors[color_str]
    
    if color_str == 'inherit' or not color_str: return None
    
    hex_color = color_str.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6: return None
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_luminance(rgb):
    rgb_linear = []
    for c in rgb:
        c = c / 255.0
        if c <= 0.03928: rgb_linear.append(c / 12.92)
        else: rgb_linear.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]

def get_contrast_ratio(hex1, hex2):
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    if not rgb1 or not rgb2: return None
    lum1 = get_luminance(rgb1)
    lum2 = get_luminance(rgb2)
    return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)

# --- Check Functions ---

def get_style_property(tag, prop):
    """Helper to find a style property in this tag or or its parents."""
    # 1. Check current tag
    style = tag.get('style', '').lower()
    # Match hex or word characters (for named colors)
    pattern = rf'(?:^|[\s;]){prop}:\s*(#[0-9a-fA-F]{{3,6}}|[a-zA-Z]+)'
    match = re.search(pattern, style)
    if match: return match.group(1)
    
    # 2. If background, also check 'background' shorthand
    if 'background' in prop:
        match = re.search(r'(?:^|[\s;])background:\s*(#[0-9a-fA-F]{3,6}|[a-zA-Z]+)', style)
        if match: return match.group(1)
    
    # 3. Recursive Parent Check
    parent = tag.parent
    if parent and parent.name not in ['[document]', 'html']:
        return get_style_property(parent, prop)
    
    # 4. Defaults
    if prop == 'color': return 'black'
    if 'background' in prop: return 'white'
    return None

def check_style_contrast(tag):
    """Calculates WCAG AA Contrast Ratio with hierarchical lookup."""
    # Optimization: Only check tags that have text or are specific block levels
    if not tag.get_text(strip=True): return None
    
    fg = get_style_property(tag, 'color')
    bg = get_style_property(tag, 'background-color')
    
    if fg and bg:
        # Avoid checking if both are same as default (optimization)
        if fg == 'black' and bg == 'white': return None
        
        ratio = get_contrast_ratio(fg, bg)
        if ratio:
            # Thresholds
            # WCAG Normal: 4.5:1
            # WCAG Large: 3:1 (18pt+ or 14pt+ bold)
            threshold = 4.5
            
            # Check for large text
            style = tag.get('style', '').lower()
            size_match = re.search(r'font-size:\s*(\d+)(px|pt|em|rem)', style)
            is_bold = 'bold' in style or tag.name in ['h1', 'h2', 'strong']
            
            if size_match:
                val, unit = int(size_match.group(1)), size_match.group(2)
                # Roughly 18pt = 24px, 14pt = 18.6px
                if unit == 'px' and (val >= 24 or (val >= 18 and is_bold)): threshold = 3.0
                elif unit == 'pt' and (val >= 18 or (val >= 14 and is_bold)): threshold = 3.0
            
            if ratio < threshold:
                return f"Contrast Fail ({ratio:.2f}:1 vs {threshold}:1) {fg} on {bg}"
    return None

def check_small_fonts(tag):
    """Checks for font sizes <= 9px."""
    style = tag.get('style', '').lower()
    # Match px, pt, em, rem
    size_match = re.search(r'font-size:\s*([0-9.]+)(px|pt|em|rem)', style)
    if size_match:
        val = float(size_match.group(1))
        unit = size_match.group(2)
        
        is_small = False
        if unit == 'px' and val <= 9: is_small = True
        elif unit == 'pt' and val <= 7: is_small = True
        elif unit in ['em', 'rem'] and val <= 0.6: is_small = True
        
        if is_small:
            return f"Small Font Size: {val}{unit} (May be unreadable)"
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

def check_viewport(soup):
    """Reflow Check: Ensures <meta name='viewport'> exists."""
    meta = soup.find('meta', attrs={'name': 'viewport'})
    if not meta:
        return "Missing <meta name='viewport'> (Fails WCAG Reflow/Mobile)"
    content = meta.get('content', '').lower()
    if 'width=device-width' not in content:
        return "Viewport meta tag missing 'width=device-width'"
    return None

    return None

def check_tables_mobile(table):
    """Reflow Check: Monitors wide tables that break mobile."""
    # Heuristic: more than 4 columns or fixed width style
    first_row = table.find('tr')
    if not first_row: return None
    
    col_count = len(first_row.find_all(['td', 'th']))
    if col_count > 4:
        # Check if already wrapped in overflow container
        if not (table.parent.name == 'div' and 'overflow-x' in table.parent.get('style', '')):
            return f"Wide table ({col_count} columns) lacks mobile scroll wrapper"
            
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

    # [REMOVED] Remediation Markers check per user request. 
    # Logic for checking [ADA FIX] or [FIX_ME] is gone.
    
    # 3. Images
    for img in soup.find_all('img'):
        alt = img.get('alt', '').strip().lower()
        role = img.get('role', '').strip().lower()
        
        if 'alt' not in img.attrs:
            results["technical"].append(f"Missing alt attribute: {img.get('src')}")
        elif not alt:
            # [PANORAMA MATCH] Empty alt is OK if role="presentation"
            if role != "presentation":
                 results["technical"].append(f"Empty alt text (needs role='presentation'): {img.get('src')}")
        elif alt in ['image', 'photo', 'picture']:
             results["subjective"].append(f"Generic Alt Text: '{alt}'")
        
        # Check for LaTeX in alt text (Canvas convention is good, but just FYI)
        if re.search(r'\\\(|\\\[', alt):
            pass # This is likely a Canvas Math equation, which is safe.
            
        # [NEW] Math verification check
        if img.has_attr('data-math-check'):
             results["technical"].append(f"Potential Math Equation needs LaTeX verification: {img.get('src')}")

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
        
        # [NEW] Table Mobile/Reflow
        t_issue = check_tables_mobile(table)
        if t_issue:
            results["technical"].append(t_issue)

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
            
        # [NEW] Small Fonts
        f_issue = check_small_fonts(tag)
        if f_issue:
            results["technical"].append(f_issue)
            
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

def get_issue_summary(results):
    """Returns a detailed string summary of issues for logging."""
    if not results: return "None"
    
    parts = []
    
    # 1. Tech Issues - Detailed Breakdown
    tech_issues = results.get("technical", [])
    if tech_issues:
        counts = {}
        for issue in tech_issues:
            # Simplistic grouping by keyword
            key = "Other"
            lower = issue.lower()
            if "missing alt" in lower: key = "Missing Alt Attr"
            elif "empty alt" in lower: key = "Empty Alt Text"
            elif "heading" in lower: key = "Heading Structure"
            elif "table" in lower: key = "Table Issues"
            elif "iframe" in lower: key = "Missing Iframe Title"
            elif "caption" in lower or "track" in lower: key = "Missing Captions"
            elif "deprecated" in lower: key = "Deprecated Tags"
            elif "contrast" in lower: key = "Contrast"
            elif "small font" in lower: key = "Small Font"          # [NEW]
            elif "scope" in lower: key = "Missing Header Scope"    # [NEW]
            elif "viewport" in lower: key = "Missing Viewport"      # [NEW]
            elif "fixed width" in lower or "justify" in lower: key = "Reflow/Mobile Issue" # [NEW] Reflow checks
            elif "wide table" in lower: key = "Table Reflow Issue" # [NEW]
            elif "math" in lower: key = "Potential Math"           # [NEW]
            else: 
                 # Fallback: Capture the actual issue text to help debug "Other"
                 # Truncate to keep log readable
                 short_issue = issue.split(':')[0] if ':' in issue else issue[:20]
                 key = f"Other ({short_issue})"
            
            counts[key] = counts.get(key, 0) + 1
            
        # Format: "Missing Alt (3), Headings (1)"
        details = [f"{k} {v}" for k, v in counts.items()]
        parts.append(", ".join(details))

    # 2. Subjective
    subj_count = len(results.get("subjective", []))
    if subj_count > 0:
        parts.append(f"{subj_count} Suggestions")
        
    return ", ".join(parts)


def run_audit_v3(directory):
    print(f"Auditing {directory}...")
    all_issues = {}
    archive_name = "_ORIGINALS_DO_NOT_UPLOAD_"
    
    for root, dirs, files in os.walk(directory):
        if archive_name in root: continue
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
