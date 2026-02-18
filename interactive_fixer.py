# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License version 3. USE AT YOUR OWN RISK.

import os
import sys
import json
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import re
import base64
import tempfile
import hashlib
import jeanie_ai

# --- Configuration ---
BAD_ALT_TEXT = ['image', 'photo', 'picture', 'spacer', 'undefined', 'null']
BAD_LINK_TEXT = ['click here', 'here', 'read more', 'link', 'more info', 'info']

def sanitize_filename(base_name):
    """
    Replaces spaces, dots, and special characters with underscores to ensure web safety.
    Input should be the filename WITHOUT extension.
    """
    # [STRICT FIX] Only allow letters, numbers, underscores, and hyphens. 
    # Everything else (including dots and commas) becomes an underscore.
    s_name = re.sub(r'[^\w\-]', '_', base_name)
    # Collapse multiple underscores
    s_name = re.sub(r'_+', '_', s_name)
    # Clean up trailing/leading underscores
    s_name = s_name.strip('_')
    return s_name

class FixerIO:
    """Handles Input/Output. Subclass this for GUI integration."""
    def __init__(self):
        self.is_running = True
        self.stop_requested = False
        self.api_key = ""
        self.memory = {} # basename|sz -> alt_text
        self.global_decorative_keys = set() # Keys to automatically mark as decorative session-wide
        self.mem_path = os.path.join(os.path.expanduser("~"), ".mosh_alt_memory.json")
        self.memory = self._load_memory()
        
        # [NEW] Mitigation for Duplicate Fatigue
        # If an image filename matches these, we auto-mark as decorative without asking.
        self.ignore_patterns = [
            r'divider.*', 
            r'spacer.*', 
            r'line.*', 
            r'shim.*', 
            r'transparent.*',
            r'white_pixel.*'
        ]

    def _load_memory(self):
        if os.path.exists(self.mem_path):
            try:
                with open(self.mem_path, 'r', encoding='utf-8') as f:
                    raw_memory = json.load(f)
                    # Normalize keys for consistent matching (URL decode + lowercase)
                    normalized = {}
                    for key, value in raw_memory.items():
                        norm_key = urllib.parse.unquote(key).lower()
                        normalized[norm_key] = value
                    return normalized
            except Exception as e:
                print(f"[Warning] Could not load memory file: {e}")
                return {}
        return {}

    def save_memory(self):
        try:
            with open(self.mem_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            print(f"[Warning] Could not save memory file: {e}")

    def log(self, message):
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback for Windows consoles that hate emojis
            print(message.encode('utf-8', errors='ignore').decode('utf-8'))

    def is_stopped(self):
        """Check if skip or stop was requested."""
        return self.stop_requested
        
    def prompt_image(self, message, image_path, context=None, suggestion=None):
        """Ask user for input while showing an image and context."""
        if suggestion:
            print(f"Suggestion: {suggestion}")
        print(f"Context: {context}")
        return input(message)

    def prompt_link(self, message, help_url, context=None):
        """Ask user for input while showing a link and context."""
        print(f"Context: {context}")
        return input(message)

    def prompt(self, message, help_url=None):
        """Ask user for input. help_url is optional for clickable links."""
        try:
            return input(message)
        except NameError:
            return raw_input(message)

    def confirm(self, message):
        return self.prompt(f"{message} (y/n): ").lower().strip() == 'y'

def normalize_image_key(src, full_path=None):
    """
    Normalizes an image src to a consistent memory key.
    If full_path is provided and exists, we include file size for uniqueness 
    (to handle generic names like 'image1.png' from different PPTs).
    """
    basename = os.path.basename(src)
    decoded = urllib.parse.unquote(basename)
    key = decoded.lower()
    
    if full_path and os.path.exists(full_path):
        try:
            size = os.path.getsize(full_path)
            # We use filename + size as a lightweight 'unique enough' key
            # This prevents 'image1.png' from one PPT being confused with 'image1.png' from another.
            return f"{key}|sz:{size}"
        except:
            pass
            
    return key

def get_suggested_title(tag):
    """Attempts to guess a title based on surrounding text."""
    # 1. Check previous siblings (Headers or bold text)
    prev = tag.find_previous_sibling()
    # Skip empty/whitespace nodes
    while prev and (prev.name == 'br' or not prev.get_text(strip=True)):
        prev = prev.find_previous_sibling()
    
    if prev:
        text = prev.get_text(strip=True)
        # If it's a header, it's a very strong candidate
        if prev.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return text
        # If it's short text (likely a label), use it
        if len(text) < 60:
             return text

    # 2. Check next siblings (Captions)
    next_node = tag.find_next_sibling()
    while next_node and (next_node.name == 'br' or not next_node.get_text(strip=True)):
        next_node = next_node.find_next_sibling()

    if next_node:
        text = next_node.get_text(strip=True)
        if len(text) < 80: # Rule of thumb for a caption
            return text

    return None


def get_link_suggestion(href, context=None):
    """Generates a smart suggestion for link text based on the href and context."""
    if not href: return None
    
    clean_href = href.strip()
    
    # 1. Handle File Links (extensions)
    doc_exts = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.zip', '.rtf']
    base, ext = os.path.splitext(clean_href)
    
    if ext.lower() in doc_exts:
        # Strategy: Filename -> Title Case + (EXT)
        filename = os.path.basename(clean_href)
        name_only = os.path.splitext(filename)[0]
        # Replace common separators with spaces
        suggestion = name_only.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        # Capitalize words
        suggestion = suggestion.title()
        return f"{suggestion} ({ext.upper().replace('.', '')})"

    # 2. Handle "View Solution" or generic links using context
    if context and ("solution" in context.lower() or "answer" in context.lower()):
        # Try to extract a problem number or section from context
        match = re.search(r'(\d+[\.]?|[a-z]\))', context[:20]) # Look near start
        if match:
             return f"View Solution for Problem {match.group(1).strip('.')}"
        return "View Solution"

    # 3. Handle Web Links
    if clean_href.lower().startswith('http'):
        try:
            parsed = urllib.parse.urlparse(clean_href)
            domain = parsed.netloc
            path = parsed.path
            
            # Domain Mapping
            site_name = ""
            if 'mchenry.edu' in domain:
                site_name = "McHenry County College"
            elif 'instructure.com' in domain:
                site_name = "Canvas"
            elif 'google.com' in domain:
                 site_name = "Google"
            elif 'youtube.com' in domain:
                 site_name = "YouTube"
            else:
                 # Fallback: Use domain name
                 if domain.startswith('www.'): domain = domain[4:]
                 site_name = domain.split('.')[0].capitalize()

            # Page Name Extraction
            # e.g. /itsupport.html -> IT Support
            page_part = ""
            if path and path != "/" and not path.endswith('index.html'):
                basename = os.path.basename(path)
                name_only = os.path.splitext(basename)[0]
                # cleanup
                name_only = name_only.replace('-', ' ').replace('_', ' ').replace('+', ' ')
                page_part = name_only.title()
                
            if site_name and page_part:
                return f"{site_name}: {page_part}"
            elif site_name:
                return f"{site_name} (External Site)"
            elif page_part:
                return page_part
                
            return domain
        except:
            return None
            
    return None

def get_image_suggestion(src, context=None):
    """Generates a smart suggestion for alt text based on filename and context."""
    if not src: return None
    
    # 1. Filename Strategy
    filename = os.path.basename(src).split('?')[0]
    name_only = os.path.splitext(filename)[0]
    
    # Clean up common junk (UUIDs, 'slide1', etc)
    clean_name = re.sub(r'[0-9]{5,}', '', name_only) # Remove long numbers
    clean_name = clean_name.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    
    # 2. Context Strategy
    # If the context is just a few words, it might be the label
    if context and len(context) < 100:
        return f"{clean_name.strip().title()} - {context.strip()}"
    
    # 3. Handle specific labels
    if 'logo' in clean_name.lower(): return "Company Logo"
    if 'icon' in clean_name.lower(): return "" # Suggest decorative for icons
    
    suggestion = clean_name.strip().title()
    if len(suggestion) < 3: return None
    return suggestion

def fetch_youtube_title(url):
    """Fetches the title of a YouTube video from its URL."""
    # 1. Extract Video ID from Embed URL
    # Format: https://www.youtube.com/embed/VIDEO_ID
    video_id = None
    if "youtube.com/embed/" in url:
        match = re.search(r'embed/([^?&"]+)', url)
        if match:
            video_id = match.group(1)
    
    if not video_id:
        return None

    # 2. Fetch the Watch Page (which has the <title>)
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        req = urllib.request.Request(
            watch_url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            html = response.read().decode('utf-8', errors='ignore')
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                title = match.group(1).replace(" - YouTube", "").strip()
                if title == "YouTube": return None # Failed to get specific title
                return title
    except Exception as e:
        pass
    
    return None

def ensure_short_path(filepath):
    """Truncates filename if path is too long for Windows (MAX_PATH=260)."""
    if len(filepath) < 240: return filepath
    
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    name, ext = os.path.splitext(basename)
    
    # Calculate overflow
    overflow = len(filepath) - 240
    if overflow > 0:
        import hashlib
        short_hash = hashlib.md5(basename.encode()).hexdigest()[:6]
        # Try to keep start of name
        keep_len = len(name) - overflow - 10
        if keep_len < 2: keep_len = 2 # minimum
        
        new_name = name[:keep_len] + f"_{short_hash}" + ext
        return os.path.join(dirname, new_name)
    return filepath

def save_html(filepath, soup, io_handler):
    """Saves the modified soup to the file."""
    try:
        # [FIX] Ensure path is safe for Windows
        filepath = ensure_short_path(filepath)

        io_handler.log(f"  [DEBUG] Attempting to save file: {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        io_handler.log(f"  [SUCCESS] Saved file: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        io_handler.log(f"  [ERROR] Could not save {filepath}: {e}")
        return False

def resolve_image_path(src, filepath, root_dir, io_handler):
    """
    Robustly resolves an image src to an absolute filesystem path.
    Handles:
    - Absolute paths
    - Relative paths
    - $IMS-CC-FILEBASE$ tokens (Canvas exports)
    - URL encoding
    - Fuzzy matching (case-insensitive)
    """
    try:
        # 1. Basic Cleanup
        clean_src = urllib.parse.unquote(src)
        
        # 2. Handle Canvas Token (IMS-CC-FILEBASE)
        if "$IMS-CC-FILEBASE$" in clean_src:
            # Replace token with empty string
            expanded = clean_src.replace("$IMS-CC-FILEBASE$/", "").replace("$IMS-CC-FILEBASE$", "")
            # Remove any query params (like ?canvas_download=1) for local resolution
            expanded = expanded.split('?')[0]
            expanded = expanded.replace('/', os.sep).replace('\\', os.sep)
            if expanded.startswith(os.sep): expanded = expanded[1:]
            
            # Strategy A: Check relative to Root Dir (Primary)
            if root_dir:
                candidate = os.path.join(root_dir, expanded)
                if os.path.exists(candidate):
                    return candidate
            
            # Strategy B: Check relative to HTML file (e.g. current folder or ../web_resources)
            parent = os.path.dirname(filepath)
            
            # Try 1: Expanded path directly from parent (for grouped images)
            candidate_grp = os.path.abspath(os.path.join(parent, expanded))
            if os.path.exists(candidate_grp): return candidate_grp
            
            # Try 2: Up one level (standard structure for wiki_content vs web_resources)
            candidate_rel = os.path.abspath(os.path.join(parent, "..", expanded))
            if os.path.exists(candidate_rel): return candidate_rel
            
            # Try 3: Specifically check web_resources in root if expanded is just a filename
            if root_dir:
                candidate_wr = os.path.join(root_dir, 'web_resources', os.path.basename(expanded))
                if os.path.exists(candidate_wr): return candidate_wr

            # Strategy C: Token expansion failed to find file.
            io_handler.log(f"    [Info] Token path '{expanded}' not found. Checking elsewhere...")
            clean_src = os.path.basename(clean_src)

    except Exception as e:
        io_handler.log(f"    [Error] preparing path: {e}")
        # Ensure fallback
        clean_src = os.path.basename(urllib.parse.unquote(src))

    # 3. Standard Path Resolution
    candidates = []
    
    if os.path.isabs(clean_src):
        candidates.append(clean_src)
    elif clean_src.startswith('/'): # Root relative
        if root_dir:
            candidates.append(os.path.join(root_dir, clean_src.lstrip('/')))
        else:
            candidates.append(os.path.abspath(clean_src))
    else: # Current dir relative
        candidates.append(os.path.join(os.path.dirname(filepath), clean_src))
        candidates.append(os.path.abspath(clean_src)) # Fallback to CWD

    for c in candidates:
        if os.path.exists(c):
            return c
            
    # 3. Nuclear Option 0: Base64 fallback (Word often does this)
    if clean_src.startswith('data:image'):
        # Save to a temp file so GUI can show it
        try:
            header, data = clean_src.split(',', 1)
            ext = header.split('/')[1].split(';')[0]
            content = base64.b64decode(data)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tmp.write(content)
            tmp.close()
            return tmp.name
        except Exception as e:
            print(f"[Warning] Could not decode base64 image: {e}")

    # 4. Nuclear Option: Fuzzy / Recursive Search
    target_name = os.path.basename(clean_src)
    
    # Search in web_resources first (optimization)
    search_roots = []
    if root_dir:
        search_roots.append(os.path.join(root_dir, 'web_resources'))
        search_roots.append(root_dir)
        
    for search_root in search_roots:
        if not os.path.exists(search_root): continue
        
        for root, dirs, files in os.walk(search_root):
            # Case-insensitive finding
            for file in files:
                if file.lower() == target_name.lower():
                    found = os.path.join(root, file)
                    io_handler.log(f"    [Trace] Found via fuzzy search: {found}")
                    return found
                    
    return None

def get_context(tag):
    """Get surrounding text context for a tag (parent paragraph or surrounding text)."""
    parent = tag.find_parent(['p', 'div', 'li', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if parent:
        text = parent.get_text(strip=True)
        if len(text) > 300:
            return text[:297] + "..."
        return text
    return "No surrounding text context found."

def scan_and_fix_file(filepath, io_handler=None, root_dir=None):
    """Scans a single file and prompts for fixes."""
    if io_handler is None:
        io_handler = FixerIO()

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    modified = False
    
    
    filename = os.path.basename(filepath)
    io_handler.log(f"\nScanning: {filename}...")
    io_handler.log(f"[INFO] Using Image Resolution Logic v2.1")
    if root_dir:
        io_handler.log(f"[INFO] Root Dir: {root_dir}")

    # --- 0. Filename Audit ---
    filepath = audit_filename(filepath, io_handler, root_dir)
    filename = os.path.basename(filepath)
    if io_handler.is_stopped():
        return

    # --- 1. Image Remediation ---
    images = soup.find_all('img')
    for i, img in enumerate(images):
        src = img.get('src', 'MISSING_SRC')
        img_filename = os.path.basename(src)
        alt = urllib.parse.unquote(img.get('alt', '')).strip()
        
        # [NEW] Auto-Ignore Pattern Check
        for pattern in io_handler.ignore_patterns:
            if re.match(pattern, img_filename, re.IGNORECASE):
                # It's a known decorative file pattern.
                if not alt:
                    img['alt'] = ""
                    img['role'] = "presentation"
                    modified = True
                    continue
        
        issue = None

        # [SILENT MEMORY CHECK] 
        img_full_path = resolve_image_path(src, filepath, root_dir, io_handler)
        mem_key = normalize_image_key(src, img_full_path)

        # 0. Check Session-Global Memory (Smart Ignore)
        if mem_key in io_handler.global_decorative_keys:
             img['alt'] = ""
             img['role'] = "presentation"
             io_handler.log(f"    [SMART IGNORE] Auto-marked decorative: {os.path.basename(src)}")
             modified = True
             continue

        # 1. Check Long-Term Memory (Persistent)
        if img_full_path:
            if mem_key in io_handler.memory:
                saved_alt = io_handler.memory[mem_key]
                
                # Check if it was saved as decorative
                if saved_alt == "__DECORATIVE__":
                    img['alt'] = ""
                    img['role'] = "presentation"
                    io_handler.log(f"    [MEMORY] Auto-marked decorative: {os.path.basename(src)}")
                    modified = True
                    continue

                if saved_alt and saved_alt != "__SKIP__":
                    img['alt'] = saved_alt
                    io_handler.log(f"    [MEMORY] Auto-filled: \"{saved_alt}\"")
                    modified = True
                    continue

        # Detection Logic (only if not already resolved by memory)
        if 'alt' not in img.attrs:
            issue = "Missing 'alt' attribute"
        elif not alt:
            issue = "Empty alt text"
        elif alt.lower() in BAD_ALT_TEXT:
            issue = f"Generic alt text ('{alt}')"
        elif alt.lower() == img_filename.lower():
            issue = "Filename used as alt text"
        
        # [NEW] Math Equation Check (Flagged by run_fixer)
        if img.has_attr('data-math-check'):
             issue = "Potential Math Equation (Needs Verification/LaTeX)"
        
        # [SMART SILENCE] Only flag "Review suggested" if we DON'T have a memory for this image.
        # If we have a memory, even if it contains the word "image", we trust the user's previous choice.
        elif "image" in alt.lower() and len(alt) > 10:
             has_memory = False
             # mem_key is guaranteed to be defined here from above
             if mem_key in io_handler.memory:
                 has_memory = True
             
             if not has_memory:
                issue = "Review suggested alt text"
        
        if issue:
            io_handler.log(f"\n  [ISSUE #{i+1}] Image: {src}")
            io_handler.log(f"    Reason: {issue}")
            io_handler.log(f"    Current Alt: '{alt}'")
            
            # context and prompt (resolve_image_path already called above)
            context = get_context(img)
            initial_val = get_image_suggestion(src, context) # [FIX] Use consistent naming
            
            # Final check of memory before prompting (in case it was just added in this session)
            if mem_key in io_handler.memory:
                saved_alt = io_handler.memory[mem_key]
                if saved_alt == "__DECORATIVE__":
                    img['alt'] = ""
                    img['role'] = "presentation"
                    modified = True
                    continue
                elif saved_alt and saved_alt != "__SKIP__":
                    img['alt'] = saved_alt
                    modified = True
                    continue

            if not img_full_path:
                 io_handler.log(f"    [Warning] Could not find local image file.")

            # [JEANIE MAGIC] Auto-Generate Suggestion if API Key exists
            ai_suggestion = None
            choice = None # [FIX] Initialize choice to avoid UnboundLocalError
            
            if io_handler.api_key and img_full_path:
                if img.has_attr('data-math-check'):
                    io_handler.log("    [JEANIE] Consulting the oracle for LaTeX (Auto)...")
                    ai_suggestion, msg = jeanie_ai.generate_latex_from_image(img_full_path, io_handler.api_key)
                else:
                    io_handler.log("    [JEANIE] Consulting the oracle for Alt-Text (Auto)...")
                    ai_suggestion, msg = jeanie_ai.generate_alt_text_from_image(img_full_path, io_handler.api_key, context=context)
                
                if ai_suggestion:
                    io_handler.log(f"    [JEANIE] Suggestion: {ai_suggestion}")
                else:
                    io_handler.log(f"    [JEANIE] Error: {msg}")

            # Define prompt_suffix to avoid UnboundLocalError
            prompt_suffix = ""
            if ai_suggestion:
                prompt_suffix = f" (Default: {ai_suggestion[:20]}...)"

            if img.has_attr('data-math-check'):
                 prompt_text = "    > Verify: Is this a Math Equation? If yes, enter LaTeX. If no, enter Alt Text: "
            else:
                 prompt_text = "    > Enter Alt Text (Press Enter to accept suggestion): " + prompt_suffix
            
            if img_full_path and os.path.exists(img_full_path):
                 # Pass the AI suggestion (or filename based on if no AI) to the UI
                 display_suggestion = ai_suggestion if ai_suggestion else initial_val
                 choice = io_handler.prompt_image(prompt_text, img_full_path, context=context, suggestion=display_suggestion).strip()
            else:
                 choice = io_handler.prompt(prompt_text).strip()
            
            # Use suggestion if Enter pressed
            if not choice and (ai_suggestion or initial_val):
                choice = ai_suggestion if ai_suggestion else initial_val
            
            # [OVERRIDE] Allow skipping all remaining items
            if choice == "!!":
                io_handler.log("    [OVERRIDE] Skipping all remaining items for this file.")
                return modified
            
            # If they enter text (or special token), save to memory

            if choice:
                # [NEW] Table OCR Handling
                if choice == "__TABLE_OCR__":
                    io_handler.log("    [JEANIE] Converting image into an HTML table...")
                    table_html, msg = jeanie_ai.generate_table_from_image(img_full_path, io_handler.api_key)
                    if table_html:
                         # Replace img tag with table html (wrapped in a div for style)
                         table_soup = BeautifulSoup(table_html, 'html.parser')
                         wrapper = soup.new_tag("div", attrs={"class": "table-ocr-result", "style": "margin: 20px 0;"})
                         wrapper.append(table_soup)
                         img.replace_with(wrapper)
                         io_handler.log("    -> Success! Image replaced with accessible HTML table.")
                         modified = True
                    else:
                         io_handler.log(f"    [Error] Table OCR failed: {msg}")
                    continue

                # [NEW] Regular OCR Handling
                elif choice == "__OCR__":
                    io_handler.log("    [JEANIE] Extracting text from image...")
                    text, msg = jeanie_ai.generate_text_from_scanned_image(img_full_path, io_handler.api_key)
                    if text:
                         # Replace img tag with text
                         ocr_tag = soup.new_tag("div", attrs={"class": "ocr-text-result", "style": "background: #f9f9f9; padding: 15px; border: 1px solid #ddd;"})
                         ocr_tag.string = text
                         img.replace_with(ocr_tag)
                         io_handler.log("    -> Success! Image replaced with extracted text.")
                         modified = True
                    else:
                         io_handler.log(f"    [Error] OCR failed: {msg}")
                    continue

                # [NEW] Math OCR Handling
                elif choice == "__MATH_OCR__":
                    io_handler.log("    [JEANIE] Converting image into LaTeX Math...")
                    latex, msg = jeanie_ai.generate_latex_from_image(img_full_path, io_handler.api_key)
                    if latex:
                         # Replace img tag with LaTeX wrapped in delimiters
                         # Canvas uses \( ... \) for standard rendering
                         math_tag = soup.new_tag("span", attrs={"class": "math-ocr-result", "style": "font-size: 1.1em;"})
                         math_tag.string = f"\\({latex}\\)"
                         img.replace_with(math_tag)
                         io_handler.log(f"    -> Success! Image replaced with LaTeX: \\({latex[:30]}...\\)")
                         modified = True
                    else:
                         io_handler.log(f"    [Error] Math OCR failed: {msg}")
                    continue

                # [DECORATIVE LOGIC]
                if choice == "__DECORATIVE__":
                    img['alt'] = ""
                    # [PANORAMA MATCH] Add role="presentation" to explicitly hide from screen readers
                    img['role'] = "presentation"
                    io_handler.log("    -> Marked as decorative.")
                    
                    # [NEW] SMART IGNORE PROMPT
                    if mem_key not in io_handler.global_decorative_keys:
                        msg = f"Would you like to automatically mark all identical images ('{os.path.basename(src)}') as decorative in the rest of this course?"
                        if io_handler.confirm(msg):
                            io_handler.global_decorative_keys.add(mem_key)
                            io_handler.memory[mem_key] = "__DECORATIVE__" # Also save to persistent memory
                            io_handler.save_memory()
                    
                    modified = True
                    io_handler.memory[mem_key] = "__DECORATIVE__"
                    io_handler.save_memory()
                else:
                    img['alt'] = choice
                    io_handler.memory[mem_key] = choice
                    io_handler.log(f"    -> Updated and saved to memory: '{choice}'")

                io_handler.save_memory()
                
                # Remove any warning spans/markers if they exist
                if img.has_attr('data-math-check'):
                    # If it was a math check, and they entered something, we can mark it as handled
                    if choice:
                        img['data-math'] = choice
                        # Also put it in Alt so non-MathJax users can see it
                        img['alt'] = f"Equation: {choice}"
                        io_handler.memory[mem_key] = f"Equation: {choice}"
                    del img['data-math-check']
                pass
                
                modified = True
                
            # If "Review suggest alt" and they press enter, it's NOT a skip, it's a keep.
            elif not choice and issue == "Review suggested alt text":
                choice = alt
                io_handler.memory[mem_key] = choice
                io_handler.save_memory()
                img['alt'] = choice
                modified = True
                io_handler.log(f"    -> Kept suggested and saved to memory: '{choice}'")
            else:
                io_handler.log("    -> Skipped.")
            
            if io_handler.is_stopped(): return

    # --- 2. Link Remediation ---
    links = soup.find_all('a')
    for i, a in enumerate(links):
        text = a.get_text(strip=True)
        href = a.get('href', 'MISSING_HREF')
        
        issue = None
        
        # Check for Empty Text
        if not text:
             issue = "Link text is empty"
             
        # Check for Vague Text
        elif text.lower() in BAD_LINK_TEXT:
            issue = f"Vague link text ('{text}')"
        # Check for Raw URL as Text or Filenames
        elif text.lower() == href.lower() or (text.lower().startswith('http') and len(text) > 20):
             issue = "Raw URL used as link text"
        elif any(text.strip().lower().endswith(ext) for ext in ['.html', '.pdf', '.docx', '.pptx', '.zip']):
             issue = "Filename used as link text"

        if issue:
            io_handler.log(f"\n  [ISSUE #{i+1}] Link: {href}")
            io_handler.log(f"    Reason: {issue}")
            io_handler.log(f"    Current Text: '{text}'")
            
            # Generate Suggestion
            context = get_context(a)
            suggestion = get_link_suggestion(href, context)
            
            # Resolve Link Path for "Clickable" help
            # (Reusing image resolution logic since it does good absolute path finding)
            help_url = resolve_image_path(href, filepath, root_dir, io_handler)
            if not help_url and href.startswith('http'):
                help_url = href # Web links are fine as-is
            
            prompt_suffix = " (Type '!!' to skip all remaining): "
            msg = (f"    > Enter new text for this link (Press Enter to use '{suggestion}')" if suggestion else "    > Enter new text for this link (or Press Enter to skip)") + prompt_suffix
            choice = io_handler.prompt_link(msg, help_url, context=context)
            
            if choice == "!!":
                io_handler.log("    [OVERRIDE] Skipping all remaining items for this file.")
                return modified
            
            if choice and choice.strip():
                a.string = choice.strip()
                modified = True
                io_handler.log(f"    [FIXED] Updated Link Text: {href[:30]}... -> \"{choice.strip()}\"")
            else:
                io_handler.log(f"    [SKIP] No change for link: {href[:30]}...")
            
            if io_handler.is_stopped(): return

    # --- 3. Iframe Remediation ---
    iframes = soup.find_all('iframe')
    for i, iframe in enumerate(iframes):
        title = iframe.get('title', '').strip()
        
        issue = None
        if not title:
            issue = "Missing 'title' attribute"
        elif title.lower() in ['embedded content', 'video', 'youtube']:
            issue = f"Generic title ('{title}')"
            
        if issue:
            io_handler.log(f"\n  [ISSUE #{i+1}] Iframe Src: {iframe.get('src', 'Unknown')}")
            io_handler.log(f"    Reason: {issue}")
            
            # Smart Suggestion
            suggestion = get_suggested_title(iframe)
            
            # [NEW] Try to get YouTube title if available
            src = iframe.get('src', '')
            if 'youtube.com' in src or 'youtu.be' in src:
                io_handler.log("    [network] Fetching YouTube title...")
                yt_title = fetch_youtube_title(src)
                if yt_title:
                    suggestion = yt_title
                    io_handler.log(f"    [network] Found: \"{yt_title}\"")

            prompt_suffix = " (Type '!!' to skip all remaining): "
            if suggestion:
                io_handler.log(f"    [TIP] Suggested Title: \"{suggestion}\"")
                prompt_text = f"    > Enter Title (Press Enter to use '{suggestion}')" + prompt_suffix
            else:
                prompt_text = "    > Enter Container Title for this video" + prompt_suffix
            
            choice = io_handler.prompt(prompt_text).strip()

            # [OVERRIDE]
            if choice == "!!":
                io_handler.log("    [OVERRIDE] Skipping all remaining items for this file.")
                return modified
            
            if choice:
                iframe['title'] = choice
                modified = True
                io_handler.log(f"    -> Updated to: '{choice}'")
            elif suggestion:
                iframe['title'] = suggestion
                modified = True
                io_handler.log(f"    -> Updated to: '{suggestion}' (Used Suggestion)")
            else:
                io_handler.log("    -> Skipped.")
            
            if io_handler.is_stopped(): return

    if modified:
        save_html(filepath, soup, io_handler)
    elif not images and not links and not iframes:
         # No interactive elements found, but file might still be bad
         io_handler.log("  [NOTE] No images, links, or iframes to check.")
         io_handler.log("  (This file may still have Heading or Contrast issues. Run Option 2: Auto-Fixer to fix those.)")
    else:
        io_handler.log("  No interactive issues found (Alt Text, Link Text, Iframe Titles are OK).")

def fix_link_filenames(root_dir, old_name, new_name, io_handler):
    """
    Project-wide Find & Replace for file references.
    Updates all .html files when a linked file is renamed.
    """
    io_handler.log(f"    [Global Fix] Updating links: '{old_name}' -> '{new_name}'...")
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # We do a careful replace of the filename in src/href
                # Target common patterns: href="name" src="name"
                new_content = content.replace(f'href="{old_name}"', f'href="{new_name}"')
                new_content = new_content.replace(f'src="{old_name}"', f'src="{new_name}"')
                # Also handle URL encoded spaces if the old name had them
                old_encoded = old_name.replace(" ", "%20")
                new_content = new_content.replace(f'href="{old_encoded}"', f'href="{new_name}"')
                new_content = new_content.replace(f'src="{old_encoded}"', f'src="{new_name}"')

                if content != new_content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    count += 1
    io_handler.log(f"    [Global Fix] Updated {count} files.")

def audit_filename(filepath, io_handler, root_dir):
    """
    Checks if a filename has spaces or bad characters.
    Prompts user to sanitize and updates project links.
    """
    old_full_path = filepath
    dir_name = os.path.dirname(filepath)
    old_name = os.path.basename(filepath)
    
    # Check for spaces or special chars using strict logic
    name_only, ext = os.path.splitext(old_name)
    suggested_base = sanitize_filename(name_only)
    suggested = suggested_base + ext.lower()
    
    if old_name != suggested:
        io_handler.log(f"\n  [AUTO-FIX] Sanitizing filename: \"{old_name}\" -> \"{suggested}\"")
        new_full_path = os.path.join(dir_name, suggested)
        
        # 1. Rename File
        try:
            if os.path.exists(new_full_path):
                io_handler.log(f"    [ERROR] Cannot rename: \"{suggested}\" already exists.")
                return filepath
            
            os.rename(old_full_path, new_full_path)
            
            # 2. Global Link Update
            if root_dir:
                fix_link_filenames(root_dir, old_name, suggested, io_handler)
            
            return new_full_path
        except Exception as e:
            io_handler.log(f"    [ERROR] Rename failed: {e}")
    
    return filepath

# --- Auto-Fix Logic (Imported from run_fixer.py) ---
def run_auto_fixer(filepath, io_handler=None):
    """Applies structural fixes (Headings, Tables, Contrast)."""
    if io_handler is None: io_handler = FixerIO()
    
    import run_fixer
    try:
        remediated, fixes = run_fixer.remediate_html_file(filepath)
        
        # Only write if there were actual fixes
        if fixes:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(remediated)
            # Verify write succeeded
            import os as os_check
            if os_check.path.getsize(filepath) > 0:
                io_handler.log(f"      [SAVED] {os.path.basename(filepath)}")
            else:
                io_handler.log(f"      [WARNING] File may not have saved: {os.path.basename(filepath)}")
        
        return True, fixes
    except PermissionError as e:
        io_handler.log(f"  [ERROR] Permission denied writing to {os.path.basename(filepath)}: {e}")
        return False, []
    except Exception as e:
        io_handler.log(f"  [ERROR] Auto-fix failed for {os.path.basename(filepath)}: {e}")
        return False, []

def main_interactive_mode(io_handler=None):
    if io_handler is None: io_handler = FixerIO()

    io_handler.log("==========================================")
    io_handler.log("   MOSH's TOOLKIT (Making Online Spaces Helpful)  ")
    io_handler.log("==========================================")
    
    # 1. Path Selection
    if len(sys.argv) > 1 and sys.argv[1].strip():
        root_dir = sys.argv[1]
    else:
        io_handler.log("\nNo folder selected.")
        user_input = io_handler.prompt("Enter path to folder to scan (or Press Enter for this folder): ").strip()
        
        if user_input:
            root_dir = user_input.strip('"').strip("'")
        elif os.path.exists("HTML_Files"):
             root_dir = "HTML_Files"
        else:
             root_dir = os.getcwd()

    if not os.path.isdir(root_dir):
        io_handler.log(f"\n[ERROR] The path \"{root_dir}\" is not a valid directory.")
        io_handler.prompt("Press Enter to exit...")
        return

    # 2. Files Discovery
    html_files = []
    archive_name = "_ORIGINALS_DO_NOT_UPLOAD_"
    for root, dirs, files in os.walk(root_dir):
        if archive_name in root: continue
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    
    if not html_files:
         io_handler.log("No .html files found in this directory.")
         io_handler.prompt("Press Enter to exit...")
         return
         
    io_handler.log(f"\nFound {len(html_files)} HTML files.")

    # 3. OPTIONAL: Run Auto-Fixer First
    io_handler.log("\n[STEP 1] AUTO-FIXER")
    io_handler.log("Do you want to automatically fix Headings, Tables, and Contrast first?")
    io_handler.log("(This is HIGHLY recommended for old content)")
    
    if io_handler.confirm("Run Auto-Fixer?"):
        io_handler.log("\nRunning Auto-Fixer on all files...")
        count = 0
        for filepath in html_files:
            if io_handler.is_stopped(): break
            if run_auto_fixer(filepath, io_handler):
                count += 1
        io_handler.log(f"Done. Auto-fixed {count} files.")
    else:
        io_handler.log("Skipping Auto-Fixer.")

    # 4. Interactive Loop
    io_handler.log("\n[STEP 2] INTERACTIVE SCAN")
    io_handler.log("Scanning for missing descriptions and titles...")
    
    for filepath in html_files:
        if io_handler.is_stopped(): break
        scan_and_fix_file(filepath, io_handler, root_dir)
        
    io_handler.log("\n==========================================")
    io_handler.log("   All files processed!")
    io_handler.log("==========================================")
    io_handler.prompt("Press Enter to exit...")

if __name__ == "__main__":
    main_interactive_mode()
