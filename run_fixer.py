import os
import re
import colorsys
from bs4 import BeautifulSoup, Comment

# --- Configuration: "Deep Obsidian" Code Theme ---
COLOR_BG_DARK = "#121212"
COLOR_TEXT_WHITE = "#ffffff"
COLOR_COMMENT = "#8ecafc"  # Light Blue
COLOR_STRING = "#a6e22e"   # Green
COLOR_NUMBER = "#fd971f"   # Orange
COLOR_BOOLEAN = "#ae81ff"  # Purple

# --- WCAG 2.1 Contrast Math ---
def hex_to_rgb(color_str):
    color_str = color_str.lower().strip()
    named_colors = {
        'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 
        'blue': '#0000ff', 'green': '#008000', 'yellow': '#ffff00',
        'gray': '#808080', 'grey': '#808080', 'purple': '#800080',
        'orange': '#ffa500', 'transparent': 'inherit'
    }
    if color_str in named_colors: color_str = named_colors[color_str]
    if color_str == 'inherit' or not color_str: return None
    
    hex_color = color_str.lstrip('#')
    if len(hex_color) == 3: hex_color = ''.join([c*2 for c in hex_color])
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

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def adjust_color_for_contrast(fg_hex, bg_hex, target_ratio=4.5):
    """Automatically darkens or lightens FG to meet target contrast against BG."""
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    if not fg_rgb or not bg_rgb: return fg_hex
    
    bg_lum = get_luminance(bg_rgb)
    curr_fg_rgb = list(fg_rgb)
    
    # Decide direction: if BG is dark, lighten FG; if BG is light, darken FG
    direction = -5 if bg_lum > 0.5 else 5 # Step size
    
    for _ in range(51): # Max 50 steps
        ratio = get_contrast_ratio(rgb_to_hex(curr_fg_rgb), bg_hex)
        if ratio and ratio >= target_ratio:
            return rgb_to_hex(curr_fg_rgb)
        
        # Move RGB values
        for i in range(3):
            curr_fg_rgb[i] = max(0, min(255, curr_fg_rgb[i] + direction))
            
    return "#000000" if bg_lum > 0.5 else "#ffffff"

def fix_emoji_accessibility(soup):
    """Wraps emojis in spans with role='img' and aria-label."""
    import unicodedata
    # Emoji regex (broad range)
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    
    fixes = []
    # Find text nodes containing emojis
    for text_node in soup.find_all(string=True):
        if text_node.parent.name in ['script', 'style']: continue
        
        matches = list(emoji_pattern.finditer(text_node))
        if matches:
            # We found emojis. We need to replace them with spans.
            # This is tricky with BeautifulSoup strings. 
            # We'll build a new content list.
            new_contents = []
            last_idx = 0
            for match in matches:
                # Add preceding text
                new_contents.append(text_node[last_idx:match.start()])
                # Create emoji span
                emoji = match.group()
                try:
                    desc = unicodedata.name(emoji).title()
                except:
                    desc = "Emoji"
                
                span = soup.new_tag("span", attrs={"role": "img", "aria-label": desc})
                span.string = emoji
                new_contents.append(span)
                last_idx = match.end()
            
            # Add remaining text
            new_contents.append(text_node[last_idx:])
            
            # Replace text node with new contents
            for content in reversed(new_contents):
                if content: # Avoid empty strings
                    text_node.insert_after(content)
            text_node.extract()
            fixes.append(f"Accessible-wrapped {len(matches)} emojis")
            
    return fixes

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

    # Note: The regex now uses (?<!-) lookbehind to avoid matching max-width/min-width

    # REGEX REMOVED: Do not globally force width: 100%. Handled cleanly in BeautifulSoup.
    
    # UX Update: Widen containers per user request
    html_content = html_content.replace('max-width: 1100px', 'max-width: 1200px')
    html_content = html_content.replace('max-width: 800px', 'max-width: 950px')

    # Check for legacy shorthands
    
    # Check for legacy shorthands (REMOVED: Dangerous collisions with #ffffff)
    # html_content = html_content.replace('background-fff', '').replace('background-f;', '').replace('fff;', '')

    # --- Part 1: Pre-Soup Regex Fixes (Reflow/Mobile) ---
    # [FIX] Track if we actually changed anything
    reflow_fixed = False
    def width_replacer(match):
        nonlocal reflow_fixed
        val = int(match.group(1))
        if val > 320:
            reflow_fixed = True
            return f"width: 100%; max-width: {val}px"
        return match.group(0)

    # Transform
    html_content = re.sub(r'(?<!-)width:\s*(\d+)px', width_replacer, html_content, flags=re.IGNORECASE)
    
    if reflow_fixed:
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
    # First, check if any top-level div already has lang attribute (idempotency)
    main_div = soup.find('div', attrs={'lang': True})
    if not main_div:
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

        # Apply Deep Obsidian theme - but check if already styled (idempotency)
        current_style = pre.get('style', '').lower()
        already_styled = COLOR_BG_DARK.lower() in current_style
        
        if not already_styled:
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

    # --- Part 5: Tables (AGGRESSIVE REMEDIATION) ---
    for table in soup.find_all('table'):
        # 1. Cleanup empty TBODYs
        for tb in table.find_all('tbody'):
            if not tb.find('tr'):
                fixes.append("Removed empty <tbody> tag")
                tb.extract()

        # 2. Caption (Mandatory for screen readers)
        if not table.find('caption'):
            caption = soup.new_tag('caption')
            caption['style'] = "text-align: left; font-weight: bold; margin-bottom: 10px;"
            caption.string = "Data Table" 
            table.insert(0, caption)
            fixes.append("Added 'Data Table' caption to table")
        
        # 3. FORCE HEADERS (The most common error)
        thead = table.find('thead')
        if not thead:
            first_row = table.find('tr')
            if first_row:
                # Convert first row to a header row
                thead = soup.new_tag('thead')
                first_row.wrap(thead)
                for cell in first_row.find_all('td'):
                    cell.name = 'th'
                    cell['scope'] = "col"
                for th in first_row.find_all('th'):
                    th['scope'] = "col"
                fixes.append("Converted first row to proper <thead> header")

        # 4. Standardize Scopes (Canvas requirement)
        for th in table.find_all('th'):
            if not th.has_attr('scope'):
                # Heuristic: if it's in a thead, it's a col. If it's the first cell of a tr, it's a row.
                if th.find_parent('thead'):
                    th['scope'] = "col"
                else:
                    th['scope'] = "row"
                fixes.append("Assigned WCAG scope to table header")
        
        if not table.has_attr('border'):
            table['border'] = "1"
        if 'border-collapse' not in table.get('style', ''):
            table['style'] = table.get('style', '') + " border-collapse: collapse; min-width: 50%;"
        
        # 6. Mobile Reflow Check (UX)
        # If table has more than 5 columns or fixed width, warn or wrap
        col_count = 0
        first_row = table.find('tr')
        if first_row: col_count = len(first_row.find_all(['td', 'th']))
        
        if col_count > 4:
            # Wrap in a scrollable div for mobile
            if not (table.parent.name == 'div' and 'overflow-x' in table.parent.get('style', '')):
                wrapper = soup.new_tag('div', style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; border: 1px solid #eee; padding: 5px;")
                table.wrap(wrapper)
                fixes.append(f"Added horizontal scroll wrapper for wide table ({col_count} columns)")

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
            # Note: Placeholders and markers removed per user request. Fixes are tracked in 'fixes' list only.
            fixes.append(f"Flagged image for review: {reason}")
            
        # 7c. POTENTIAL EQUATION DETECTION (Math Check)
        # Heuristic: Small images with high contrast, or alt text containing math terms but no LaTeX
        src = img.get('src', '').lower()
        if not img.has_attr('data-math') and (any(term in alt_val.lower() or term in src for term in ['eq', 'formula', 'math', 'sigma', 'sqrt', 'frac'])):
             # Mark for interactive review to suggest LaTeX
             img['data-math-check'] = "true"
             fixes.append(f"Flagged potential math equation for accessibility verification: {os.path.basename(src)}")

    # --- Part 8: Typography & Accessibility (Small Fonts / AUTO-CONTRAST) ---
    import run_audit # Use get_style_property for robust lookup
    
    for tag in soup.find_all(style=True):
        style = tag.get('style', '').lower()
        
        # A. Font Size Fix
        size_match = re.search(r'font-size:\s*([0-9.]+)(px|pt|em|rem)', style)
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2)
            needs_elevation = False
            new_val = 12
            if unit == 'px' and val <= 9: needs_elevation = True
            elif unit == 'pt' and val <= 7: needs_elevation = True; new_val = 9
            elif unit in ['em', 'rem'] and val <= 0.6: needs_elevation = True; new_val = 0.8
            if needs_elevation:
                tag['style'] = re.sub(rf'font-size:\s*[0-9.]+{unit}', f'font-size: {new_val}{unit}', tag['style'], flags=re.IGNORECASE)
                fixes.append(f"Elevated small font size ({val}{unit} -> {new_val}{unit})")

        # B. AUTO-CONTRAST CORRECTION
        if tag.get_text(strip=True):
            fg = run_audit.get_style_property(tag, 'color')
            bg = run_audit.get_style_property(tag, 'background-color')
            
            if fg and bg:
                 ratio = get_contrast_ratio(fg, bg)
                 if ratio and ratio < 4.5:
                     # Calculate target
                     # If it's large text, we only need 3.0, but 4.5 is safer
                     new_fg = adjust_color_for_contrast(fg, bg)
                     
                     # Update the style string
                     if 'color:' in tag['style'].lower():
                         tag['style'] = re.sub(r'color:\s*#[0-9a-fA-F]{3,6}', f'color: {new_fg}', tag['style'], flags=re.IGNORECASE)
                         tag['style'] = re.sub(r'color:\s*[a-zA-Z]+', f'color: {new_fg}', tag['style'], flags=re.IGNORECASE)
                     else:
                         tag['style'] = tag['style'].rstrip('; ') + f"; color: {new_fg};"
                     
                     fixes.append(f"Auto-corrected low contrast ({ratio:.1f}:1 -> 4.5:1)")

    # --- Part 9: Links & Iframes (Vague Text Correction) ---
    vague_terms = ['click here', 'read more', 'learn more', 'more', 'link', 'here', 'view']
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True).lower()
        
        # 1. Remove empty links
        if not text and not a.find_all(True):
            fixes.append(f"Removed empty link to '{href}'")
            a.extract()
            continue
            
        # Link Text Cleanup (Strip extensions and underscores)
        # Heuristic: If text looks like a filename (ends in extension or has underscores)
        doc_exts = ['.pdf', '.docx', '.pptx', '.xlsx', '.zip', '.txt']
        if any(text.endswith(ext) for ext in doc_exts) or '_' in text:
            new_text = text
            for ext in doc_exts:
                if new_text.endswith(ext):
                    new_text = new_text[:-len(ext)]
                    break
            new_text = new_text.replace('_', ' ').strip()
            if new_text and new_text != text:
                a.string = new_text
                fixes.append(f"Cleaned link text: '{text}' -> '{new_text}'")
                text = new_text.lower() # Update for next check

        # 2. Fix Vague Text (e.g. "Click Here")
        if text in vague_terms:
            # Try to find context (previous text or heading)
            context = "Information"
            prev_tag = a.find_previous(['h2', 'h3', 'strong', 'b', 'p'])
            if prev_tag:
                context = prev_tag.get_text(strip=True)[:30]
            
            # If it's a file link, use the sanitized filename
            if any(ext in href.lower() for ext in doc_exts):
                filename = os.path.basename(href).split('?')[0]
                name_only = os.path.splitext(filename)[0].replace('%20', ' ').replace('_', ' ').strip()
                a.string = f"Download {name_only}"
                fixes.append(f"Fixed vague link text '{text}' -> 'Download {name_only}'")
            else:
                a.string = f"View {context}"
                fixes.append(f"Fixed vague link text '{text}' -> 'View {context}'")
    
    for iframe in soup.find_all('iframe'):
        if not iframe.has_attr('title') or not iframe['title'].strip():
            # Try to guess title from src
            src = iframe.get('src', '').lower()
            if 'youtube' in src: title = "Embedded YouTube Video"
            elif 'panopto' in src: title = "Embedded Panopto Video"
            elif 'vimeo' in src: title = "Embedded Vimeo Video"
            else: title = "Embedded Content"
            
            iframe['title'] = title
            fixes.append(f"Added title '{title}' to iframe")

    # --- Part 10: SMART IMAGE ALIGNMENT (For Word/PDF) ---
    for img in soup.find_all('img'):
        parent = img.parent
        # If image is alone in a paragraph, it might benefit from being floated
        if parent.name == 'p' and len(parent.contents) == 1:
            # Check image size (heuristic)
            width = img.get('width', '800')
            try:
                w_val = int(width)
                if w_val < 400:
                    # Small image alone in a P? Let's make it look nice.
                    # We'll float it right by default if it's small, to let text wrap
                    img['style'] = img.get('style', '') + " float: right; margin: 10px 0 15px 20px; max-width: 40%;"
                    fixes.append(f"Applied smart float-right to small image: {os.path.basename(img.get('src',''))}")
            except: pass

    # --- Part 8: Deprecated Tags ---
    # Convert <b> to <strong>
    for tag in soup.find_all('b'):
        tag.name = 'strong'
        fixes.append("Converted deprecated <b> to <strong>")
    
    # Convert <i> to <em>
    for tag in soup.find_all('i'):
        # Skip Font Awesome icons (they use <i class="fa-...">)
        if tag.get('class') and any('fa' in c for c in tag.get('class', [])):
            continue
        tag.name = 'em'
        fixes.append("Converted deprecated <i> to <em>")
    
    # Convert <center> to <div style="text-align: center">
    for tag in soup.find_all('center'):
        tag.name = 'div'
        existing_style = tag.get('style', '')
        tag['style'] = f"text-align: center; {existing_style}".strip()
        fixes.append("Converted deprecated <center> to styled <div>")
    
    # Unwrap <font> (preserve content, remove tag)
    for tag in soup.find_all('font'):
        # Try to preserve color as a span with inline style
        color = tag.get('color')
        if color:
            new_span = soup.new_tag('span', style=f"color: {color};")
            new_span.extend(tag.contents[:])
            tag.replace_with(new_span)
        else:
            tag.unwrap()
        fixes.append("Removed deprecated <font> tag")
    
    # Unwrap <blink> and <marquee> (just remove the tag, keep content)
    for tag_name in ['blink', 'marquee']:
        for tag in soup.find_all(tag_name):
            tag.unwrap()
            fixes.append(f"Removed deprecated <{tag_name}> tag")

    # --- Part 11: Final Polish & Special Checks ---
    emoji_fixes = fix_emoji_accessibility(soup)
    fixes.extend(emoji_fixes)

    # Deduplicate fixes
    unique_fixes = list(set(fixes))
    return str(soup), unique_fixes

    return report

# [REMOVED] strip_ada_markers and batch_strip_markers per user request. 
# Markers are no longer added, so cleanup is unnecessary.

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
