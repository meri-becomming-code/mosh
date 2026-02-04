# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License version 3. USE AT YOUR OWN RISK.

import os
import re
from bs4 import BeautifulSoup, Comment

# --- Configuration: "Deep Obsidian" Code Theme ---
COLOR_BG_DARK = "#121212"
COLOR_TEXT_WHITE = "#ffffff"
COLOR_COMMENT = "#8ecafc"  # Light Blue
COLOR_STRING = "#a6e22e"   # Green
COLOR_NUMBER = "#fd971f"   # Orange
COLOR_BOOLEAN = "#ae81ff"  # Purple

def remediate_html_file(filepath):
    """
    MASTER REMEDIATION LOGIC (V3):
    1. Clean Strategy (Toolkit 1): Strips bad tags/styles without forcing layout.
    2. Code Strategy (Toolkit 2): Applies "Deep Obsidian" theme to code blocks.
    3. Structural Fixes: Tables, Headings, Images, Iframes.
    
    Returns: (remediated_html_str, fix_list)
    """
    fixes = []
    print(f"Processing {os.path.basename(filepath)}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # --- Part 1: Cleanup (Toolkit 1 Logic) ---
    # Strip <font> tags but keep content
    html_content = re.sub(r'<font[^>]*>(.*?)</font>', r'\1', html_content, flags=re.IGNORECASE | re.DOTALL)
    
    # REGEX REMOVED: Do not strip inline colors globally.
    # html_content = re.sub(r'(?:background-)?color:\s*#(?:000|fff|333|666|000000|ffffff|333333|666666);?', '', html_content, flags=re.IGNORECASE)
    
    # Strip Justified Text (Panorama / Dyslexia Fix)
    html_content = re.sub(r'text-align:\s*justify;?', 'text-align: left;', html_content, flags=re.IGNORECASE)

    # Cleanup "max-max-width" regression from previous runs
    html_content = html_content.replace('max-max-width', 'max-width')

    # REGEX REMOVED: Do not globally force width: 100%. Handled cleanly in BeautifulSoup.
    
    # UX Update: Widen containers per user request
    html_content = html_content.replace('max-width: 1100px', 'max-width: 1200px')
    html_content = html_content.replace('max-width: 800px', 'max-width: 950px')

    # Check for legacy shorthands
    
    # Check for legacy shorthands (REMOVED: Dangerous collisions with #ffffff)
    # html_content = html_content.replace('background-fff', '').replace('background-f;', '').replace('fff;', '')

    # --- Part 1: Pre-Soup Regex Fixes (Reflow/Mobile) ---
    # Fix 1: Fixed Width Containers > 320px
    # [FIX] Use negative lookbehind (?<!-) to avoid matching max-width
    def width_replacer(match):
        val = int(match.group(1))
        if val > 320:
            return f"width: 100%; max-width: {val}px"
        return match.group(0)

    if re.search(r'(?<!-)width:\s*(\d+)px', html_content, re.IGNORECASE):
        html_content = re.sub(r'(?<!-)width:\s*(\d+)px', width_replacer, html_content, flags=re.IGNORECASE)
        fixes.append("Converted fixed widths >320px to responsive max-width")

    # Fix 2: Justified Text
    if "text-align: justify" in html_content.lower() or "text-align:justify" in html_content.lower():
         html_content = re.sub(r'text-align:\s*justify;?', 'text-align: left;', html_content, flags=re.IGNORECASE)
         fixes.append("Replaced 'justify' text alignment with 'left'")

    soup = BeautifulSoup(html_content, 'html.parser')

    # --- Part 2: Document Structure ---
    # Ensure Mobile Viewport (Reflow Fix)
    head = soup.find('head')
    if not head:
        if soup.html:
             head = soup.new_tag('head')
             soup.html.insert(0, head)
    
    if head:
        meta_viewport = head.find('meta', attrs={'name': 'viewport'})
        if not meta_viewport:
            new_meta = soup.new_tag('meta', attrs={'name': 'viewport', 'content': 'width=device-width, initial-scale=1'})
            head.append(new_meta)
            fixes.append("Added mobile viewport meta tag")

    # Ensure main div has lang='en' (or inherits from doc)
    main_div = soup.find('div')
    if not main_div:
        # Create a wrapper if none exists
        new_div = soup.new_tag('div')
        if soup.body:
            for element in list(soup.body.contents):
                new_div.append(element.extract())
            soup.body.append(new_div)
        else:
            for element in list(soup.contents):
                new_div.append(element.extract())
            soup.append(new_div)
        main_div = new_div

    if main_div and not main_div.has_attr('lang'):
        # Check if <html> has a lang we can copy
        html_lang = soup.html.get('lang') if soup.html else None
        if html_lang:
            main_div['lang'] = html_lang
            fixes.append(f"Applied language '{html_lang}' to main container")
        else:
            main_div['lang'] = 'en'
            fixes.append("Applied default language 'en' to main container")


    # --- Part 4: "Deep Obsidian" Code & Standardized Math ---
    
    # A. Code Blocks
    for pre in soup.find_all('pre'):
        parent = pre.parent
        if parent.name != 'div' or 'overflow' not in parent.get('style', '').lower():
            new_wrapper = soup.new_tag('div', style="overflow-x: auto; margin-bottom: 20px;")
            pre.wrap(new_wrapper)

        
        # C. Syntax Highlighting (Basic Heuristics)
        # Check if already styled (Idempotency)
        current_style = pre.get('style', '').lower()
        if "background-color" in current_style and "#2b2b2b" in current_style:
            # Already fixed, skip
            pass 
        else:
            pre['style'] = (
                f"background-color: {COLOR_BG_DARK}; "
                f"color: {COLOR_TEXT_WHITE}; "
                "padding: 15px; "
                "border-radius: 5px; "
                "font-family: 'Courier New', monospace; "
                "white-space: pre;"
            )
            fixes.append("Applied 'Deep Obsidian' theme to code block")
        
        for span in pre.find_all('span'):
            text = span.get_text().strip()
            
            is_docstring = text.startswith('"""') or text.startswith("'''")
            is_comment = text.startswith('#') or (span.get('style') and 'italic' in span['style'])
            is_string = (text.startswith('"') or text.startswith("'")) and not is_docstring
            is_number = text.replace('.', '', 1).isdigit()
            is_bool = text in ['True', 'False', 'None']
            
            new_color = None
            if is_docstring: new_color = COLOR_STRING
            elif is_comment: new_color = COLOR_COMMENT
            elif is_string: new_color = COLOR_STRING
            elif is_number: new_color = COLOR_NUMBER
            elif is_bool: new_color = COLOR_BOOLEAN
                
            if new_color:
                span['style'] = f"color: {new_color};"
            else:
                # Ensure no other colors interfere
                if 'color' in span.get('style', ''):
                    del span['style']
            
    # B. Math Standardization (Canvas Native)
    # Note: Regex replacements for LaTeX delimiters are safer done on strings BEFORE soup parsing, 
    # OR we just assume if they exist, Canvas catches them.
    # We will just ensure that standard LaTeX is not mangled.
    # The current script doesn't mangle brackets, so we are good.

    # --- Part 5: Tables (Toolkit 1 Logic) ---
    for table in soup.find_all('table'):
        if not table.find('caption'):
            caption = soup.new_tag('caption')
            caption['style'] = "text-align: left; font-weight: bold; margin-bottom: 10px;"
            caption.string = "Information Table" 
            table.insert(0, caption)
            fixes.append("Added 'Information Table' caption to table")
        
        # Scope and Header Logic
        first_row = table.find('tr')
        if first_row and not table.find('thead'):
            # If explicit THs, wrap in THEAD
            if all(cell.name == 'th' for cell in first_row.find_all(['td', 'th'])):
                thead = soup.new_tag('thead')
                first_row.wrap(thead)
        
        for th in table.select('thead th'):
            th['scope'] = "col"
        for th in table.select('tbody th'):
            th['scope'] = "row"

    # --- Part 6: Heading Hierarchy & Standardization (Toolkit 1 Logic + Style Standard) ---
    
    # Standardize Header Taglines (Style 13A: Tagline Underneath)
    # Target: div[bg=#4b3190] > h2 + p[color=#e1bee7]
    for h2 in soup.find_all('h2'):
        parent = h2.parent
        # Check if parent is the dark purple header container
        if parent.name == 'div' and 'background-color' in parent.get('style', '').lower() and '#4b3190' in parent['style'].lower():
            # Check if next sibling is a paragraph (the tagline)
            tagline = h2.find_next_sibling('p')
            if tagline:
                # Move tagline OUT of the header div, to immediately after it
                tagline.extract()
                parent.insert_after(tagline)
                
                # Apply 13A Style (Dark Purple, Italic, Margin)
                tagline['style'] = "margin-top: 10px; margin-left: 15px; font-style: italic; color: #4b3190;"
                tagline.insert_after(Comment("ADA FIX: Refactored tagline to 13A Standard (High Contrast)"))
                fixes.append("Refactored header tagline for better contrast and layout")

    # 1. Clear old warnings
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment) and "ADA FIX" in text):
        comment.extract()
    
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if not headings:
        # Insert H2 if missing
        title_tag = soup.find('title')
        title_text = title_tag.get_text() if title_tag else "Course Content"
        new_h2 = soup.new_tag('h2')
        new_h2.string = title_text
        if main_div:
            main_div.insert(0, new_h2)
            new_h2.insert_after(Comment("ADA FIX: Inserted H2 based on page title"))
            fixes.append(f"Inserted H2 header: '{title_text}'")
        headings = [new_h2]
    
    # 2. Leveling
    if headings:
        # Canvas uses H1 for page title, so content should start at H2
        first_level = int(headings[0].name[1])
        if first_level > 2:
            old_tag = headings[0].name
            headings[0].name = 'h2'
            headings[0].insert_before(Comment(f"ADA FIX: Forced {old_tag} to H2"))
            fixes.append(f"Forced header '{headings[0].get_text()[:30]}' from {old_tag} to H2")
            last_level = 2
        else:
            last_level = first_level

        for h in headings[1:]:
            current_level = int(h.name[1])
            if current_level > last_level + 1:
                # Skipped a level (e.g., H2 -> H4)
                new_level = last_level + 1
                old_tag = h.name
                h.name = f"h{new_level}"
                h.insert_before(Comment(f"ADA FIX: Demoted {old_tag} to H{new_level}"))
                fixes.append(f"Fixed heading gap: Demoted '{h.get_text()[:30]}' to H{new_level}")
            last_level = int(h.name[1])

    # --- Part 7: Images (Visual Markers & Responsiveness) ---
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    for img in soup.find_all('img'):
        needs_fix = False
        reason = ""
        alt_val = img.get('alt', '').strip()
        
        # 7a. Responsive Fix (Safe)
        # Ensure image never exceeds container width, but do NOT force it to expand (width: 100%).
        style = img.get('style', '')
        if 'max-width' not in style.lower():
            # Add safe responsiveness
            new_style_part = "max-width: 100%; height: auto;"
            if style:
                img['style'] = style.rstrip(';') + "; " + new_style_part
            else:
                img['style'] = new_style_part
            fixes.append(f"Made image responsive: {os.path.basename(img.get('src', 'unknown'))}")
        # 7b. Alt Text Logic
        if 'alt' not in img.attrs:
            needs_fix = True
            reason = "Missing Alt Text"
        elif alt_val == "":
            pass # Decorative
        elif alt_val.lower() in ['image', 'picture', 'photo']:
            needs_fix = True
            reason = f"Generic Alt Text '{alt_val}'"
        elif any(alt_val.lower().endswith(ext) for ext in image_extensions):
            needs_fix = True
            reason = "Filename used as Alt Text"

        if needs_fix:
            # Check if we already flagged this
            next_node = img.find_next_sibling()
            already_flagged = next_node and next_node.name == 'span' and "ADA FIX" in next_node.get_text()
            
            if not already_flagged:
                img['alt'] = f"[FIX_ME]: {reason}. Describe this image."
                # Visual Marker
                warning_span = soup.new_tag('span', style="color:red; font-weight:bold; border:1px solid red; padding:2px;")
                warning_span.string = f"[ADA FIX: {reason}]"
                img.insert_after(warning_span)
                fixes.append(f"Flagged image for review: {reason}")

    # --- Part 8: Links & Iframes ---
    # Remove empty links
    for a in soup.find_all('a'):
        if not a.get_text(strip=True) and not a.find_all(True):
            fixes.append(f"Removed empty link to '{a.get('href', 'unknown')}'")
            a.extract()
    
    for iframe in soup.find_all('iframe'):
        if not iframe.has_attr('title') or not iframe['title'].strip():
            iframe['title'] = "Embedded Content"
            iframe.insert_after(Comment("ADA FIX: Added generic title to iframe"))
            fixes.append("Added title to embedded content (iframe)")

    # Deduplicate fixes
    unique_fixes = list(set(fixes))
    return str(soup), unique_fixes

def batch_remediate_v3(root_dir):
    report = {}
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                try:
                    path = os.path.join(root, file)
                    remediated, fixes = remediate_html_file(path)
                    if fixes:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(remediated)
                        report[file] = fixes
                except Exception as e:
                    print(f"Error checking {file}: {e}")
    return report

if __name__ == "__main__":
    import sys
    print("--- MASTER REMEDIATOR V3 (Toolkit Merge) ---")
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("Enter path to scan: ").strip('"')
    
    if os.path.isdir(target_path):
        report = batch_remediate_v3(target_path)
        print(f"Done. Remediated {len(report)} files.")
        for file, fixes in report.items():
            print(f"  [{file}]")
            for fix in fixes:
                print(f"    - {fix}")
    elif os.path.isfile(target_path):
        remediated, fixes = remediate_html_file(target_path)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(remediated)
        print(f"Done. Fixes in {os.path.basename(target_path)}:")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("Invalid directory.")
