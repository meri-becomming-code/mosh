#!/usr/bin/env python3
"""
Math Converter Module for MOSH Toolkit
Integrates with Gemini AI to convert handwritten math to Canvas LaTeX
"""

import os
import re
import time
import random
import json
import html as html_lib
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

try:
    # Preferred import path for current SDK versions.
    import google.genai as genai
except Exception as _e:
    print(f"[DEBUG] primary import failed: {_e}", file=sys.stderr)
    try:
        # Fallback path for environments that expose namespace differently.
        from google import genai  # type: ignore
    except Exception as _e2:
        print(f"[DEBUG] namespace import failed: {_e2}", file=sys.stderr)
        try:
            # Last resort: direct submodule import (helps in PyInstaller EXE context
            # where the google namespace package __init__.py may not be present)
            import importlib, sys as _sys
            genai = importlib.import_module("google.genai")
        except Exception as _e3:
            print(f"[DEBUG] importlib import failed: {_e3}", file=sys.stderr)
            genai = None

# Additional fallback specific to PyInstaller single-file exe:
# When PyInstaller bundles packages, it often places them under the
# temporary _MEIPASS directory. The namespace package structure can get
# lost, so 'import google.genai' may still fail even though the files
# are present. The following hack ensures the bundled 'google' package
# directory is added to sys.path so the import can succeed.
if genai is None:
    try:
        import sys as _sys, os as _os
        print(f"[DEBUG] _MEIPASS={getattr(_sys,'_MEIPASS',None)}", file=sys.stderr)
        base = getattr(_sys, '_MEIPASS', None)
        if base:
            candidate = _os.path.join(base, 'google')
            print(f"[DEBUG] candidate google path: {candidate}", file=sys.stderr)
            if _os.path.isdir(candidate) and candidate not in _sys.path:
                _sys.path.insert(0, candidate)
                # retry import
                import importlib
                genai = importlib.import_module('google.genai')
                print(f"[DEBUG] retry import succeeded, genai={genai}", file=sys.stderr)
    except Exception as _e4:
        print(f"[DEBUG] fallback import failed: {_e4}", file=sys.stderr)
        genai = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None


def _text_looks_mathy(text):
    """Heuristic check for likely math content in extracted text."""
    if not text:
        return False

    t = text.lower()
    signals = [
        r"\\b(sin|cos|tan|log|ln|sqrt|integral|derivative|matrix|vector|limit)\\b",
        r"[∑∫√πθΔ≤≥±×÷]",
        r"\\$[^\\$]{1,80}\\$",
        r"\\\\\([^\)]{1,80}\\\\\)",
        r"\\\\\[[^\]]{1,120}\\\\\]",
        r"\\b[fghxy]\s*\([^\)]*\)\s*=",
        r"\\b\d+\s*[/^]\s*\d+\\b",
        r"\\b\d+\s*[+\-*/=]\s*\d+\\b",
    ]
    for pat in signals:
        if re.search(pat, t):
            return True
    return False


def _docx_has_math(docx_path):
    """Best-effort DOCX math detection using document.xml and equation tags."""
    try:
        import zipfile

        with zipfile.ZipFile(docx_path, "r") as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")

        # Native Word math tags are strongest signal.
        if "<m:oMath" in xml or "<m:oMathPara" in xml:
            return True

        # Fallback: strip tags and run text heuristic.
        plain = re.sub(r"<[^>]+>", " ", xml)
        plain = re.sub(r"\s+", " ", plain)
        return _text_looks_mathy(plain)
    except Exception:
        # If uncertain, do not block conversion.
        return True


def _pdf_has_math(pdf_path):
    """Best-effort PDF math detection using PyMuPDF text extraction."""
    try:
        import fitz

        doc = fitz.open(pdf_path)
        chunks = []
        for i, page in enumerate(doc):
            if i >= 5:  # sample first pages for speed
                break
            chunks.append(page.get_text("text") or "")
        doc.close()
        return _text_looks_mathy("\n".join(chunks))
    except Exception:
        # If uncertain (image-only/parse issue), do not block conversion.
        return True

def clean_gemini_response(text):
    """
    Cleans Gemini response by removing markdown code blocks and HTML boilerplate.
    Returns only the body content.
    """
    # 1. Strip markdown code blocks (e.g. ```html ... ```)
    # Target ``` optionally followed by alphanumeric characters, and leading/trailing whitespace
    text = re.sub(r'```\w*\s*', '', text)
    text = text.replace('```', '')
    
    # 2. Extract body content if present
    if '<body' in text.lower():
        match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1)
            
    # 3. Strip other boilerplate if body tag wasn't strict
    if '<!DOCTYPE html>' in text:
        text = re.sub(r'<!DOCTYPE html>.*', '', text, flags=re.DOTALL)
    
    # 4. Clean up garbage OCR fragments (isolated single letters from diagram labels)
    # Pattern: multiple single letters separated by spaces that aren't part of words
    # e.g., "a a C A C a b" -> remove
    text = re.sub(r'(?<![A-Za-z])([A-Za-z]\s+){3,}[A-Za-z](?![A-Za-z])', '', text)
    
    # 5. Remove orphaned single letters on their own line (common from diagrams)
    text = re.sub(r'^\s*[A-Za-z]\s*$', '', text, flags=re.MULTILINE)

    return text.strip()


def _extract_first_json_object(text):
    """Best-effort extraction of first JSON object from model output."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*", "", t).strip()
        t = re.sub(r"```$", "", t).strip()

    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = t[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def validate_math_conversion_page(client, model, img, converted_content, log_func=None):
    """Validate converted math for semantic risk and continuation-arrow issues."""
    prompt = (
        "You are a strict math QA validator for OCR-to-LaTeX conversion. "
        "Compare the ORIGINAL page image with the CONVERTED HTML/LaTeX content and return ONLY JSON.\n\n"
        "Primary checks:\n"
        "1) Math correctness preservation (operators, signs, exponents, fractions, radicals, limits, trig notation).\n"
        "2) Missing/extra terms.\n"
        "3) Continuation risk: arrows or visual cues indicating expression continues in another column/region and may be broken in conversion.\n"
        "4) Reading order risk for multi-column layouts.\n\n"
        "Output schema (JSON only):\n"
        "{\n"
        "  \"valid\": true|false,\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"continuation_risk\": true|false,\n"
        "  \"needs_teacher_review\": true|false,\n"
        "  \"issues\": [\"short issue 1\", \"short issue 2\"],\n"
        "  \"suggestion\": \"one concise fix instruction\"\n"
        "}\n\n"
        "Mark needs_teacher_review=true if confidence < 0.92 OR any continuation/multi-column risk OR any non-trivial issue.\n\n"
        "CONVERTED CONTENT:\n"
        f"{converted_content[:16000]}"
    )

    response = generate_content_with_retry(
        client=client,
        model=model,
        contents=[prompt, img],
        log_func=log_func,
    )

    parsed = _extract_first_json_object(getattr(response, "text", "") or "")
    if not isinstance(parsed, dict):
        return {
            "valid": False,
            "confidence": 0.0,
            "continuation_risk": True,
            "needs_teacher_review": True,
            "issues": ["Validation parser could not read model output"],
            "suggestion": "Open teacher review and confirm math/ordering manually.",
        }

    parsed.setdefault("valid", False)
    parsed.setdefault("confidence", 0.0)
    parsed.setdefault("continuation_risk", False)
    parsed.setdefault("needs_teacher_review", False)
    parsed.setdefault("issues", [])
    parsed.setdefault("suggestion", "")

    # Safety guardrails even if model under-flags.
    try:
        conf = float(parsed.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    if conf < 0.92:
        parsed["needs_teacher_review"] = True
    if parsed.get("continuation_risk"):
        parsed["needs_teacher_review"] = True
    if parsed.get("issues"):
        parsed["needs_teacher_review"] = True

    return parsed


def repair_docx_placeholder_image_sources(html_content, source_docx_path, log_func=None):
    """Replace AI placeholder/external DOCX image URLs with local extracted graph paths."""
    try:
        src_path = Path(source_docx_path)
        if src_path.suffix.lower() != ".docx":
            return html_content

        graph_dir = src_path.parent / f"{src_path.stem}_graphs"
        if not graph_dir.exists():
            return html_content

        local_images = sorted(
            [
                p.name
                for p in graph_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
            ]
        )
        if not local_images:
            return html_content

        img_tag_pattern = re.compile(
            r'(<img\b[^>]*\bsrc\s*=\s*)(["\'])(.*?)(\2)',
            flags=re.IGNORECASE | re.DOTALL,
        )

        replace_count = 0
        idx = 0

        def _replace(match):
            nonlocal replace_count, idx
            prefix, quote, src, _ = match.groups()
            src_clean = (src or "").strip()
            src_l = src_clean.lower()

            looks_placeholder = (
                "example.com" in src_l
                or src_l.startswith("http://")
                or src_l.startswith("https://")
            )

            if not looks_placeholder:
                return match.group(0)

            if idx >= len(local_images):
                return match.group(0)

            new_src = f"{src_path.stem}_graphs/{local_images[idx]}"
            idx += 1
            replace_count += 1
            return f"{prefix}{quote}{new_src}{quote}"

        repaired = img_tag_pattern.sub(_replace, html_content)
        if replace_count and log_func:
            log_func(f"   [IMG-REMAP] Replaced {replace_count} placeholder image URL(s) with local graph assets")
        return repaired
    except Exception as e:
        if log_func:
            log_func(f"   [IMG-REMAP] Skipped: {e}")
        return html_content


def remove_duplicate_headers(pages):
    """
    Remove duplicate page headers from subsequent pages.
    Common patterns like 'MAT 165 Notes Chapter X' should only appear once.
    """
    if not pages or len(pages) < 2:
        return pages
    
    # Find common header pattern from first page (first line or first significant text)
    first_page = pages[0]
    
    # Common patterns to detect and remove from subsequent pages
    header_patterns = [
        r'^MAT\s*\d+\s*Notes.*?(?=<h[23]|Section|\n\n)',  # "MAT 165 Notes Chapter X"
        r'^[A-Z]{2,4}\s*\d+\s*Notes.*?(?=<h[23]|Section|\n\n)',  # Other course codes
    ]
    
    cleaned_pages = [pages[0]]  # Keep first page as-is
    
    for page in pages[1:]:
        cleaned = page
        for pattern in header_patterns:
            # Remove the header if it appears at the start
            cleaned = re.sub(pattern, '', cleaned, count=1, flags=re.IGNORECASE | re.DOTALL)
        cleaned_pages.append(cleaned.strip())
    
    return cleaned_pages

# --- NEW: PROBING PROMPT ---
PROBING_PROMPT = """Analyze this image and list EVERY visual element that is NOT standard text.
For each element, provide:
1. Type: (Graph, Diagram, Illustration, Icon, or Table)
2. Bounding Box: [ymin, xmin, ymax, xmax] (0-1000 scale)
3. Brief Description: 1 sentence.

FORMAT:
Element: Type | Box: [box] | Desc: description
...

If there are no visual elements, reply: "NO_VISUALS"
"""

MATH_PROMPT = """Convert the content of this image to Canvas-compatible HTML/LaTeX.

RULES:
1. Identify all mathematical content and convert to LaTeX:
   - Use \\(...\\) for inline equations
   - Use $$...$$ for display equations
   - For systems of equations, use \\begin{cases}...\\end{cases} wrapped in $$ delimiters
   - For crossed-out terms, use \\cancel{} (Canvas supports this via MathJax)
   - Use \\qquad for large spacing between aligned steps
   - Use \\text{} for text within equations (e.g., \\text{or})
2. TRANSCRIBE any standard text exactly as it appears.
3. VISUAL ELEMENTS (GRAPHS, DIAGRAMS, ICONS):
   - You MUST output a token for every visual element detected.
   - Format: [GRAPH_BBOX: ymin, xmin, ymax, xmax, TYPE, STORY]
   - TYPE: Set to 'icon' (< 100px), 'graph' (math-heavy), or 'diagram' (complex illustration).
   - STORY: ALWAYS provide a meaningful description (1-2 sentences) for accessibility.
     Describe what the visual shows - shapes, labels, values, relationships.
     NEVER use 'none' as the story - every image needs a real description.
   - Use the 0-1000 coordinate scale.
   - Example: [GRAPH_BBOX: 100, 100, 400, 400, graph, A triangle ABC with sides labeled a, b, c opposite their respective angles]
   - Example: [GRAPH_BBOX: 500, 500, 800, 800, diagram, A unit circle showing angles in quadrants I and II with reference angle marked]
4. TABLES (AI Reconstruction):
   - If you see a table, RECONSTRUCT it perfectly using HTML <table>.
   - Include <thead> and <tbody>.
   - Use <th> for headers and ensure they are under 120 characters.
   - Do NOT just list table content as text.
5. HANDWRITING / TEACHER NOTES:
   - If you detect handwritten notes or solutions, style them in BLUE.
   - Use: <br><span style="color: #0066cc; font-family: 'Comic Sans MS', cursive, sans-serif;">[Note: ...]</span><br>
6. Preservation: Keep problem numbers (e.g., "1.", "a)") and layout structure.
7. Formatting:
   - Use <h3> for section headers
   - Use <b> for bold text
   - Use <i> for italics
8. Solutions/Answers:
   - Wrap solutions in <details><summary>View Solution</summary>...</details>
9. Output MUST be valid HTML snippet (no <html> cards, no markdown code blocks).
10. GARBAGE FILTER:
    - DO NOT output isolated single letters like "a a C A C a b" - these are diagram labels, not text.
    - If you see scattered single letters near a diagram, they belong TO the diagram, not the text.
    - Only transcribe coherent words and sentences.
11. REPEATED HEADERS:
    - If the page header (e.g., "MAT 165 Notes Chapter 10") appears at the top of every page,
      only include it ONCE at the very beginning. Skip it on subsequent pages.
12. ARROW-BASED CONTINUATION (TEACHER WORKFLOW):
        - If a teacher draws arrows to continue work in another column/region, preserve that flow order.
        - Read in logical solving order (top-to-bottom, then follow drawn arrows to the next region).
        - Keep the continuation explicit by including arrow connectors (→) or short transition text like
            "Continue in right column:" when needed.
        - Do NOT treat these continuation arrows as standalone decorative visuals.
            They are part of the math solution structure unless clearly a separate diagram.

Goal: A perfect accessible digital version of this document."""

# Simple rate limiter to track API calls and enforce delays
_api_call_times = []
_current_tier = "free"  # "free" or "paid"

DEFAULT_STYLE_PREFERENCES = {
    "image_margin_px": 15,
    "h1_color": "#4b3190",
    "h2_color": "#2c3e50",
    "h3_color": "#2c3e50",
    "h4_color": "#374151",
    "h5_color": "#4b5563",
    "h6_color": "#6b7280",
}

_style_preferences = DEFAULT_STYLE_PREFERENCES.copy()


def _normalize_hex_color(value, fallback):
    s = str(value or "").strip()
    if re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", s):
        return s
    return fallback


def set_style_preferences(preferences=None):
    """Set module-wide style preferences for generated Canvas math HTML."""
    global _style_preferences
    prefs = dict(DEFAULT_STYLE_PREFERENCES)
    incoming = preferences or {}

    try:
        margin = int(incoming.get("image_margin_px", prefs["image_margin_px"]))
    except Exception:
        margin = prefs["image_margin_px"]
    prefs["image_margin_px"] = max(0, min(80, margin))

    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        key = f"{tag}_color"
        prefs[key] = _normalize_hex_color(incoming.get(key), prefs[key])

    _style_preferences = prefs

def set_api_tier(tier):
    """Set the API tier to adjust rate limiting. Call this before processing."""
    global _current_tier
    _current_tier = tier.lower() if tier else "free"

def _get_min_call_interval():
    """Get minimum seconds between API calls based on tier."""
    if _current_tier == "paid":
        return 1.5  # ~60 RPM for paid tier
    return 4.0  # ~15 RPM for free tier

def _rate_limit_delay():
    """Enforce minimum delay between API calls to respect rate limits."""
    import time
    global _api_call_times
    min_interval = _get_min_call_interval()
    now = time.time()
    # Clean old entries (older than 60 seconds)
    _api_call_times = [t for t in _api_call_times if now - t < 60]
    
    if _api_call_times:
        elapsed = now - _api_call_times[-1]
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
    
    _api_call_times.append(time.time())

def generate_content_with_retry(client, model, contents, log_func=None):
    """
    Wraps Gemini generation with exponential backoff for rate limits and connection issues.
    """
    max_retries = 6
    base_delay = 5  # Start with 5 seconds

    for attempt in range(max_retries):
        # Enforce rate limiting BEFORE making the call
        _rate_limit_delay()
        
        # Use a context manager so the executor is always cleaned up, even on unexpected exceptions.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model=model,
                contents=contents
            )
            try:
                result = future.result(timeout=120)  # 2 minute absolute maximum
                return result
            except concurrent.futures.TimeoutError:
                error_str = "timeout"
                is_retryable = True
            except Exception as e:
                error_str = str(e).lower()

                # Check for Rate Limits (429) OR Connection Resets (10054) OR Timeout
                is_retryable = (
                    "429" in error_str or
                    "resource_exhausted" in error_str or
                    "connection" in error_str or
                    "10054" in error_str or
                    "remote host" in error_str or
                    "deadline" in error_str or
                    "timeout" in error_str
                )

                if not is_retryable:
                    # Real auth error or other unrecoverable — re-raise immediately.
                    raise

        if is_retryable:
            jitter = random.uniform(1.0, 3.0)
            wait_time = base_delay * (2 ** attempt) + jitter  # 5, 10, 20, 40, 80… + jitter
            if log_func:
                reason = "Quota" if ("429" in error_str or "exhausted" in error_str) else "Network"
                log_func(f"   ⏳ {reason} Hiccup. Pausing for {wait_time:.1f}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)

    raise Exception("MOSH Magic failed after multiple retries. The AI server might be too busy or your connection is unstable. Please try again in a few minutes.")

def detect_visual_elements(client, model, img, log_func=None):
    """
    Probes the image for visual elements to ensure none are missed in the second pass.
    """
    if log_func:
        log_func("   🔍 Probing image for visual elements (Pass 1)...")
    
    response = generate_content_with_retry(
        client=client,
        model=model,
        contents=[PROBING_PROMPT, img],
        log_func=log_func
    )
    
    if not response.text or "NO_VISUALS" in response.text:
        return []
        
    return response.text.strip()


def parse_bounding_boxes(html_content, page_width, page_height):
    """
    Extract all GRAPH_BBOX tokens from AI response.
    
    Args:
        html_content: AI response text containing [GRAPH_BBOX: ...] tokens
        page_width: Width of source image in pixels
        page_height: Height of source image in pixels
    
    Returns:
        List of dicts: [{
            'token': full token string,
            'rel_coords': (ymin_rel, xmin_rel, ymax_rel, xmax_rel) in 0-1000 range,
            'abs_coords': (xmin, ymin, xmax, ymax) in pixels (with padding),
            'type': 'graph'|'icon'|etc,
            'story': description text,
            'index': index in page
        }, ...]
    """
    boxes = []
    pattern = r'\[GRAPH_BBOX:\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*([^\]]+)\]'
    matches = list(re.finditer(pattern, html_content))
    
    for i, match in enumerate(matches):
        ymin_rel, xmin_rel, ymax_rel, xmax_rel = map(int, [match.group(j) for j in range(1, 5)])
        img_type = match.group(5).lower()
        story = match.group(6).strip()
        
        # Convert to pixels with padding
        ymin = int((ymin_rel / 1000) * page_height)
        xmin = int((xmin_rel / 1000) * page_width)
        ymax = int((ymax_rel / 1000) * page_height)
        xmax = int((xmax_rel / 1000) * page_width)
        
        # Add 100px padding
        ymin_pad = max(0, ymin - 100)
        xmin_pad = max(0, xmin - 100)
        ymax_pad = min(page_height, ymax + 100)
        xmax_pad = min(page_width, xmax + 100)
        
        boxes.append({
            'token': match.group(0),
            'rel_coords': (ymin_rel, xmin_rel, ymax_rel, xmax_rel),
            'abs_coords': (xmin_pad, ymin_pad, xmax_pad, ymax_pad),
            'type': img_type,
            'story': story,
            'index': i
        })
    
    return boxes


def extract_and_crop_graphs(html_content, image_path, output_dir, base_name, page_num, log_func=None):
    """
    Parses [GRAPH_BBOX] tokens, crops images from the source page, 
    saves them alongside the HTML output, and replaces tokens with <img> tags.
    """
    try:
        # Save cropped images into a subfolder next to the HTML file.
        # e.g. output_dir/MyPDF_graphs/MyPDF_p1_graph1.png
        # The HTML <img src> uses a relative path: MyPDF_graphs/filename.png
        # This keeps paths correct whether the HTML is in web_resources or anywhere else.
        graphs_dir = Path(output_dir) / f"{base_name}_graphs"
        graphs_dir.mkdir(exist_ok=True)
        
        # [NEW] Save full original page for later interactive re-cropping
        import shutil
        import json
        full_page_name = f"full_p{page_num + 1}.png"
        full_page_path = graphs_dir / full_page_name
        if not full_page_path.exists():
            shutil.copy(image_path, full_page_path)
        
        crop_meta_path = graphs_dir / "crop_meta.json"
        
        # Load existing meta to append (since it processes page by page)
        meta_data = {}
        if crop_meta_path.exists():
            try:
                with open(crop_meta_path, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
            except Exception:
                pass
        
        # 2. Open Source Image
        with Image.open(image_path) as img:
            width, height = img.size
            
            # 3. Find all BBOX tokens
            # Format: [GRAPH_BBOX: ymin, xmin, ymax, xmax, TYPE, STORY]
            matches = list(re.finditer(r'\[GRAPH_BBOX:\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*([^\]]+)\]', html_content))
            
            for i, match in enumerate(matches):
                try:
                    full_token = match.group(0)
                    ymin_rel, xmin_rel, ymax_rel, xmax_rel = map(int, [match.group(j) for j in range(1, 5)])
                    img_type = match.group(5).lower()
                    story = match.group(6).strip()
                    
                    # 4. Convert to Pixels with Padding
                    ymin = int((ymin_rel / 1000) * height)
                    xmin = int((xmin_rel / 1000) * width)
                    ymax = int((ymax_rel / 1000) * height)
                    xmax = int((xmax_rel / 1000) * width)
                    
                    # Add 100px padding (user requested an "extra 50px")
                    ymin = max(0, ymin - 100)
                    xmin = max(0, xmin - 100)
                    ymax = min(height, ymax + 100)
                    xmax = min(width, xmax + 100)
                    
                    if (xmax - xmin) < 50 or (ymax - ymin) < 50:
                        continue # Skip tiny crops
                        
                    # 5. Crop and Save
                    crop = img.crop((xmin, ymin, xmax, ymax))
                    
                    # Unique filename
                    graph_filename = f"{base_name}_p{page_num + 1}_graph{i + 1}.png"
                    save_path = graphs_dir / graph_filename
                    crop.save(save_path)
                    
                    # Store crop metadata for Interactive Review UI
                    meta_data[graph_filename] = {
                        "full_image": full_page_name,
                        "box_abs": [xmin, ymin, xmax, ymax],
                        "page_width": width,
                        "page_height": height,
                        "story": story,
                        "type": img_type
                    }
                    
                    # 6. Build relative src path (relative to the HTML file's location)
                    # graphs_dir is a sibling of the HTML, so just use folder/filename
                    rel_src = f"{base_name}_graphs/{graph_filename}"
                    
                    # 7. Replace Token with Adaptive Image Tag
                    margin_px = _style_preferences.get("image_margin_px", 15)
                    style = f"max-width: 500px; width: 100%; height: auto; border: 1px solid #ccc; display: block; margin: {margin_px}px auto;"
                    if img_type == 'icon':
                        style = "max-width: 120px; height: auto; vertical-align: middle; margin: 0 5px;"
                    elif img_type == 'graph':
                        style = f"max-width: 500px; width: 100%; height: auto; border: 1px solid #ccc; margin: {margin_px}px auto;"
                    
                    # Use story as alt text if available, otherwise generic
                    alt_text = story if story.lower() != 'none' and len(story) > 5 else "Visual Element"
                    # Escape HTML in alt text
                    alt_text = html_lib.escape(alt_text)
                    img_tag = f'<div class="mosh-visual" style="text-align: center;"><img src="{rel_src}" alt="{alt_text}" style="{style}">'

                    # Feature 5: Storytelling (Long Description)
                    if story.lower() != 'none':
                        if log_func:
                            preview = story if len(story) <= 80 else story[:77] + "..."
                            log_func(f"   ✅ [Math-Alt] {graph_filename}: \"{preview}\"")

                        safe_story = html_lib.escape(story)
                        img_tag += f'<details style="margin-top: 5px;"><summary style="color: #4b3190; cursor: pointer; font-style: italic; font-size: 0.9em;">View Description</summary><div style="padding: 10px; background: #f9f9f9; border-left: 3px solid #4b3190; text-align: left; font-size: 0.95em;">{safe_story}</div></details>'
                    
                    img_tag += '</div>'
                    
                    html_content = html_content.replace(full_token, img_tag)
                    
                except Exception as e:
                    # Remove token on error to clean up
                    html_content = html_content.replace(match.group(0), "")
                    
            # Save updated meta
            with open(crop_meta_path, 'w', encoding='utf-8') as mf:
                json.dump(meta_data, mf, indent=2)
                
    except Exception as e:
        pass
        
    return html_content

def convert_pdf_to_latex(api_key, pdf_path, log_func=None, poppler_path=None, progress_callback=None, visual_review_callback=None, step_mode=False, page_gate_callback=None, detect_visuals=True, manual_visual_selection=False, strict_math_validation=False, latex_review_callback=None):
    """
    Convert a PDF with handwritten math to Canvas LaTeX.
    
    Args:
        api_key: Gemini API key
        pdf_path: Path to PDF file
        log_func: Logging function
        poppler_path: Path to Poppler binaries
        progress_callback: Progress callback (current, total)
        visual_review_callback: Optional callback for human review of AI-detected bounding boxes.
                                Called BEFORE cropping with: (page_images, ai_responses, parsed_boxes)
                                Should return corrected_boxes dict: {page_idx: [(x1,y1,x2,y2,type,story), ...]}
                                Return None to skip review and use AI boxes as-is.
    
    Returns:
        (success, html_content_or_error_message)
    """
    # ensure genai is available, with more detailed error if not
    if not genai:
        try:
            import google.genai as genai_test
            genai = genai_test
        except Exception as ie:
            return False, f"Gemini library not installed ({ie})"
    
    if log_func:
        log_func(f"📄 Processing PDF: {Path(pdf_path).name}")
    
    if not convert_from_path:
        return False, "pdf2image library not installed or import failed."
    
    try:
        # Configure Gemini
        client = genai.Client(api_key=api_key)
        
        # Convert PDF to images
        if log_func:
            log_func("   Converting PDF pages to images...")
        
        # [FIX] Use unique temp dir to avoid WinError 32 (file lock) from previous runs
        import uuid
        temp_dir = Path(pdf_path).parent / f"{Path(pdf_path).stem}_temp_{uuid.uuid4().hex[:8]}"
        
        # Clean up previous temp dir if it exists (highly unlikely with UUID but good practice)
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(exist_ok=True)
        
        images = convert_from_path(
            str(pdf_path), 
            dpi=300, 
            output_folder=str(temp_dir),
            poppler_path=poppler_path,
            fmt='png'
        )
        
        if log_func:
            log_func(f"   ✅ Created {len(images)} page images")

        total_image_count = len(images)
        
        # Process each page sequentially (teacher-paced option supported)
        all_content = [None] * len(images)
        progress_count = 0
        
        def process_page(index, img_path):
            import time
            import random
            # Add delay between pages to respect API rate limits
            # Free tier: ~15 RPM, Paid: ~60 RPM. We do 2 calls/page.
            time.sleep(random.uniform(2.0, 4.0))  # 2-4 second delay per page
            try:
                # [FIX] Use context manager to ensure file handle is closed
                with Image.open(img_path) as img:
                    model = 'gemini-2.0-flash'
                    visual_context = []

                    # Pass 1: Probing (optional)
                    if detect_visuals and not manual_visual_selection:
                        visual_context = detect_visual_elements(client, model, img, log_func)
                    
                    # Pass 2: Final Conversion with Context
                    conversion_prompt = MATH_PROMPT
                    if visual_context:
                        conversion_prompt += f"\n\nCONTEXT FROM PROBING PASS:\n{visual_context}\n\nEnsure every element listed above has a [GRAPH_BBOX] token."
                    elif (not detect_visuals) or manual_visual_selection:
                        conversion_prompt += (
                            "\n\nNO_VISUALS_MODE:\n"
                            "Assume there are no diagrams/graphs/icons to extract. "
                            "Do not emit any [GRAPH_BBOX: ...] tokens."
                        )

                    response = generate_content_with_retry(
                        client=client,
                        model=model,
                        contents=[conversion_prompt, img],
                        log_func=log_func
                    )
                    return index, clean_gemini_response(response.text)
            except Exception as e:
                if log_func:
                    log_func(f"   [Error] Page {index+1} failed: {e}")
                return index, f"<p>[Error converting page {index+1}: {e}]</p>"

        def apply_corrected_boxes_to_content(content, new_boxes, page_w, page_h):
            """Replace GRAPH_BBOX tokens in page content with corrected boxes."""
            old_boxes = parse_bounding_boxes(content, page_w, page_h)
            updated_content = content

            # Remove old tokens first
            for old_box in old_boxes:
                updated_content = updated_content.replace(old_box.get('token', ''), '', 1)

            # Append corrected tokens
            for new_box in new_boxes:
                if not new_box.get('include', True):
                    continue
                x1, y1, x2, y2 = new_box['abs_coords']
                ymin_rel = int((y1 / page_h) * 1000)
                xmin_rel = int((x1 / page_w) * 1000)
                ymax_rel = int((y2 / page_h) * 1000)
                xmax_rel = int((x2 / page_w) * 1000)
                box_type = new_box.get('type', 'graph')
                story = new_box.get('story', 'Visual element')
                new_token = f"[GRAPH_BBOX: {ymin_rel}, {xmin_rel}, {ymax_rel}, {xmax_rel}, {box_type}, {story}]"
                updated_content += f"\n{new_token}"

            return updated_content

        # Process pages sequentially to avoid API quota issues.
        # Optional step_mode inserts teacher confirmation pauses between pages.
        sorted_image_paths = sorted(temp_dir.glob('*.png'))

        stop_early = False
        total_pages = len(sorted_image_paths)
        per_page_step_review = bool(visual_review_callback and step_mode and (detect_visuals or manual_visual_selection))
        for i, img_path in enumerate(sorted_image_paths):
            page_num = i + 1

            if step_mode and page_gate_callback:
                try:
                    if not page_gate_callback(page_num, total_pages):
                        stop_early = True
                        if log_func:
                            log_func(f"   ⏸️ Stopped by user before page {page_num}. Saving completed pages...")
                        break
                except Exception:
                    # If gate callback fails, continue without blocking conversion.
                    pass

            idx, content = process_page(i, img_path)
            all_content[idx] = content

            # Strict validation pass: catches continuation arrows / column-order risks.
            if strict_math_validation and content:
                try:
                    with Image.open(sorted_image_paths[idx]) as img_page:
                        validation = validate_math_conversion_page(
                            client=client,
                            model='gemini-2.0-flash',
                            img=img_page,
                            converted_content=content,
                            log_func=log_func,
                        )

                    needs_review = bool(validation.get("needs_teacher_review"))
                    if needs_review:
                        issues = validation.get("issues") or []
                        if log_func:
                            log_func(
                                f"   ⚠️ Strict math validation flagged page {idx+1}: "
                                + ("; ".join(issues[:3]) if issues else "manual confirmation required")
                            )

                        if latex_review_callback:
                            review_payload = {
                                "file_name": Path(pdf_path).name,
                                "page_num": idx + 1,
                                "total_pages": total_pages,
                                "image_path": str(sorted_image_paths[idx]),
                                "content": content,
                                "validation": validation,
                            }
                            reviewed = latex_review_callback(review_payload)
                            if isinstance(reviewed, dict):
                                action = reviewed.get("action", "continue")
                                reviewed_content = reviewed.get("content", content)
                                all_content[idx] = reviewed_content
                                content = reviewed_content
                                if action == "skip_file":
                                    stop_early = True
                                    if log_func:
                                        log_func(f"   ⏭️ Teacher skipped remaining pages for {Path(pdf_path).name} during strict validation.")
                                    break
                except Exception as e_validate:
                    if log_func:
                        log_func(f"   ⚠️ Strict validation warning on page {idx+1}: {e_validate}")

            # Teacher-paced mode: review each page immediately after conversion.
            # This keeps flow predictable: review -> process next page.
            if per_page_step_review and content:
                try:
                    with Image.open(sorted_image_paths[idx]) as img_page:
                        w_page, h_page = img_page.size
                    page_boxes = parse_bounding_boxes(content, w_page, h_page)
                    page_review_data = [{
                        'page_index': idx,
                        'image_path': str(sorted_image_paths[idx]),
                        'content': content,
                        'boxes': page_boxes,
                        'width': w_page,
                        'height': h_page,
                    }]
                    if log_func:
                        log_func(f"   👁️ Opening image selection review now (page {idx+1} ready)...")
                    corrected_page = visual_review_callback(page_review_data)
                    if corrected_page and idx in corrected_page:
                        all_content[idx] = apply_corrected_boxes_to_content(
                            content,
                            corrected_page[idx],
                            w_page,
                            h_page,
                        )
                        if log_func:
                            log_func(f"   ✅ Applied page {idx+1} review edits")
                except Exception as e_early:
                    if log_func:
                        log_func(f"   ⚠️ Page {idx+1} review failed: {e_early}")

            progress_count += 1
            if progress_callback:
                progress_callback(progress_count, total_image_count)
            if log_func:
                log_func(f"   ✅ Finished processing page {idx+1}/{total_image_count}")
        
        # [NEW] Post-Processing: Extract and Crop Graphs
        if (detect_visuals or manual_visual_selection) and log_func:
            log_func("   ✂️  Auto-cropping graphs from pages...")
        output_dir = Path(pdf_path).parent
        pdf_stem = Path(pdf_path).stem
        
        # [VISUAL REVIEW] Parse all AI-detected boxes BEFORE cropping
        if detect_visuals and (not manual_visual_selection) and visual_review_callback and not per_page_step_review:
            if log_func: log_func("   🔍 Parsing AI-detected bounding boxes for review...")
            
            # Collect page images and parsed boxes for review
            page_data = []
            for i, content in enumerate(all_content):
                if content:
                    with Image.open(sorted_image_paths[i]) as img:
                        w, h = img.size
                    boxes = parse_bounding_boxes(content, w, h)
                    page_data.append({
                        'page_index': i,
                        'image_path': str(sorted_image_paths[i]),
                        'content': content,
                        'boxes': boxes,
                        'width': w,
                        'height': h
                    })
            
            # Call the visual review callback - user can adjust/delete/add boxes
            # Returns None if user wants to use AI boxes as-is
            if page_data:
                if log_func: log_func(f"   👁️ Requesting human review of {len(page_data)} pages with visual elements...")
                corrected_boxes = visual_review_callback(page_data)
                
                # If user provided corrections, update the boxes
                if corrected_boxes:
                    if log_func: log_func(f"   ✅ Applied human corrections to {len(corrected_boxes)} pages")
                    # corrected_boxes format: {page_idx: [{'abs_coords': (x1,y1,x2,y2), 'type': str, 'story': str}, ...]}
                    for i, data in enumerate(page_data):
                        if data['page_index'] in corrected_boxes:
                            # Rebuild AI content with corrected boxes
                            new_boxes = corrected_boxes[data['page_index']]
                            all_content[data['page_index']] = apply_corrected_boxes_to_content(
                                data['content'],
                                new_boxes,
                                data['width'],
                                data['height'],
                            )
        
        final_pages = []
        for i, content in enumerate(all_content):
            if content:
                if detect_visuals or manual_visual_selection:
                    # Use the original temp image for cropping
                    try:
                        content = extract_and_crop_graphs(content, sorted_image_paths[i], output_dir, pdf_stem, i, log_func)
                    except Exception as e:
                        if log_func: log_func(f"   ⚠️ Graph crop warning p{i+1}: {e}")
                else:
                    # Safety cleanup if model still emitted bbox tokens while visuals are disabled.
                    content = re.sub(r'\[GRAPH_BBOX:[^\]]+\]', '', content)
                final_pages.append(content)
            else:
                if log_func:
                    log_func(f"   ⚠️ Page {i+1} produced no content and was skipped.")
        
        # [NEW] Remove duplicate page headers (e.g., "MAT 165 Notes" on every page)
        final_pages = remove_duplicate_headers(final_pages)
                
        # Combine everything
        final_html_content = "\n<hr style=\"margin: 2% 0; border: 0; border-top: 1px solid #ccc;\">\n".join(final_pages)
        
        # Robust cleanup
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            if log_func: log_func(f"   ⚠️ Cleanup warning: {e}")
        
        # Create HTML
        title = Path(pdf_path).stem.replace('_', ' ').title()
        html = create_canvas_html(final_html_content, title=title)
        
        if log_func:
            completed_pages = len([p for p in all_content if p])
            if stop_early:
                log_func(f"✅ Partial conversion complete: {completed_pages}/{total_image_count} pages")
            else:
                log_func(f"✅ Conversion complete: {completed_pages}/{total_image_count} pages")
        
        return True, html
        
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def convert_image_to_latex(api_key, image_path, log_func=None):
    """Convert a single image to LaTeX using Multi-Pass Probing."""
    if not genai:
        return False, "Gemini library not installed"
    
    try:
        client = genai.Client(api_key=api_key)
        model = 'gemini-2.0-flash'
        
        if log_func:
            log_func(f"📸 Converting image: {Path(image_path).name}")

        with Image.open(image_path) as img:
            # Pass 1: Probing
            visual_context = detect_visual_elements(client, model, img, log_func)

            # Pass 2: Final Conversion with Context
            if log_func:
                log_func("   ✨  Converting content (Pass 2)...")

            conversion_prompt = MATH_PROMPT
            if visual_context:
                conversion_prompt += f"\n\nCONTEXT FROM PROBING PASS:\n{visual_context}\n\nEnsure every element listed above has a [GRAPH_BBOX] token."

            response = generate_content_with_retry(
                client=client,
                model=model,
                contents=[conversion_prompt, img],
                log_func=log_func
            )

        if response.text:
            cleaned_text = clean_gemini_response(response.text)
            
            # Use extract_and_crop_graphs to handle all detected elements
            output_dir = Path(image_path).parent
            image_stem = Path(image_path).stem
            try:
                cleaned_text = extract_and_crop_graphs(cleaned_text, image_path, output_dir, image_stem, 0, log_func)
            except Exception as e:
                if log_func: log_func(f"   ⚠️ Graph crop warning: {e}")
                
            title = Path(image_path).stem.replace('_', ' ').title()
            html = create_canvas_html(cleaned_text, title=title)
            
            if log_func:
                log_func(f"✅ Conversion complete")
            
            return True, html
        else:
            return False, "No response from Gemini"
            
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def convert_word_to_latex(api_key, doc_path, log_func=None):
    """
    Convert Word doc to LaTeX.
    Uses Gemini File API to preserve BOTH text and math globally.
    """
    if not genai:
        return False, "Gemini library not installed"
    
    try:
        if log_func:
            log_func(f"📝 Processing Word doc via AI File Reader: {Path(doc_path).name}")
        
        client = genai.Client(api_key=api_key)
        import time, zipfile, io, tempfile, os
        from PIL import Image
        
        try:
            # 1. Open DOCX and Extract document.xml + images
            with zipfile.ZipFile(doc_path, 'r') as z:
                xml_content = z.read('word/document.xml').decode('utf-8')
                
                # Gather Images
                pil_images = []
                image_filenames = []
                
                output_dir = Path(doc_path).parent
                doc_stem = Path(doc_path).stem
                graphs_dir = output_dir / f"{doc_stem}_graphs"
                graphs_dir.mkdir(exist_ok=True)
                
                try:
                    import xml.etree.ElementTree as ET
                    rels_content = z.read('word/_rels/document.xml.rels')
                    rels_root = ET.fromstring(rels_content)
                    namespaces = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                    
                    # Store mapping so we can extract in relatively chronological order
                    img_idx = 1
                    for rel in rels_root.findall('.//rel:Relationship', namespaces):
                        target = rel.get('Target')
                        if target and target.startswith('media/'):
                            try:
                                img_data = z.read('word/' + target)
                                img = Image.open(io.BytesIO(img_data))
                                img.load() # Ensure memory is mapped
                                
                                # Convert EMF/WMF to PNG if needed, or save natively
                                # Use standard RGBA to PNG saving
                                if img.mode in ("RGBA", "P"):
                                    img = img.convert("RGB")
                                    
                                img_filename = f"graph_{doc_stem}_{img_idx}.png"
                                img_path = graphs_dir / img_filename
                                img.save(img_path, format="PNG")
                                
                                pil_images.append(img)
                                image_filenames.append(f"{graphs_dir.name}/{img_filename}")
                                img_idx += 1
                            except Exception as e:
                                pass
                except Exception as e:
                    pass

            if log_func: log_func(f"   ⬆️ Found {len(pil_images)} images/graphs and XML text layout...")
            
            # 2. Save XML locally to a safe temporary file
            fd, temp_xml_path = tempfile.mkstemp(suffix=".xml")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(xml_content)
                
            try:
                # 3. Upload exactly as XML to bypass Microsoft specific strict mime_type limits
                doc_file = client.files.upload(file=temp_xml_path, config={'mime_type': 'text/xml'})
                if log_func: log_func(f"   ⬆️ Uploaded layout structure: {doc_file.name} (Waiting for processing...)")
                
                # Wait for ACTIVE state
                max_wait = 60
                start_time = time.time()
                while True:
                    doc_file = client.files.get(name=doc_file.name)
                    if doc_file.state.name == 'ACTIVE':
                        break
                    if doc_file.state.name == 'FAILED':
                        return False, "Gemini failed to process the DOCX XML layout."
                    if time.time() - start_time > max_wait:
                        return False, "Timeout waiting for DOCX XML processing."
                    time.sleep(2)
                
                # 4. Process Full Document
                model = 'gemini-2.0-flash'
                conversion_prompt = MATH_PROMPT + f"\n\nConvert this underlying Word document XML into clean, accessible Canvas HTML. \nTranscribe ALL text, maintain headers (h1, h2, h3), lists, and styling. \nTranslate all OMML math equations (`<m:oMath>`) to LaTeX wrapped in standard MathJax syntax \\( \\) or \\[ \\] or $$. Return pure HTML. \nNote: We have attached {len(pil_images)} images inline extracted from the DOCX in chronological order. Their physical filenames are: {', '.join(image_filenames)}. Whenever you see a physical image referenced in the narrative or text, you MUST place an `<img>` tag into the HTML using the corresponding exact filename as the `src` attribute (e.g. `<img src=\"{doc_stem}_graphs/graph_{doc_stem}_1.png\" alt=\"...\">`), and provide an extensive, highly detailed descriptive `alt` attribute for accessibility."
                
                if log_func: log_func(f"   🧠 Asking Gemini to reconstruct Full Document Text, Layout, and Math...")
                
                contents_payload = [conversion_prompt, doc_file] + pil_images
                
                response = generate_content_with_retry(
                    client=client,
                    model=model,
                    contents=contents_payload,
                    log_func=log_func
                )
                
                if response and response.text:
                    cleaned_text = clean_gemini_response(response.text)
                    title = Path(doc_path).stem.replace('_', ' ').title()
                    html = create_canvas_html(cleaned_text, title=title)
                    
                    if log_func:
                        log_func(f"✅ Converted Word doc preserving full text, layout, and math")
                    
                    # Cleanup Gemini servers
                    try:
                        client.files.delete(name=doc_file.name)
                    except Exception:
                        pass

                    return True, html
                else:
                    return False, "No response from Gemini API for Word Document."
            
            finally:
                # Cleanup local temp file
                try:
                    os.remove(temp_xml_path)
                except Exception:
                    pass
                
        except Exception as e:
            if log_func: log_func(f"   ⚠️ Gemini DOCX extraction failed for {Path(doc_path).name}: {e}")
            raise e
            
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def process_canvas_export(api_key, export_dir, log_func=None, poppler_path=None, progress_callback=None, on_file_converted=None, visual_review_callback=None, step_mode=False, page_gate_callback=None, detect_visuals=True, detect_visuals_callback=None, fast_license_mode=False, manual_visual_selection=False, strict_math_validation=False, latex_review_callback=None):
    """
    Process all PDFs in a Canvas export (IMSCC) structure.
    Includes licensing/attribution checking to protect teachers.
    
    Args:
        visual_review_callback: Optional callback for human review of AI-detected bounding boxes.
                                Passed through to convert_pdf_to_latex.
    
    Returns:
        (success, dict_or_error) where dict has:
        {
            "converted": [(source_path, html_path), ...],
            "skipped_no_math": [source_path, ...]
        }
    """
    # ensure genai is importable and provide detailed error if not
    if not genai:
        try:
            import google.genai as genai_test
            genai = genai_test
        except Exception as ie:
            return False, f"Gemini library not installed ({ie})"
    
    if not genai:
        return False, "Gemini library not installed"
    
    export_path = Path(export_dir)
    web_resources = export_path / 'web_resources'
    
    if not web_resources.exists():
        return False, f"No web_resources folder found in {export_dir}"
    
    # STEP 1: Check licensing FIRST (or fast-start skip)
    if log_func:
        if fast_license_mode:
            log_func("\n⚡ FAST START: Skipping detailed licensing scan for this run.")
            log_func("   You are responsible for attribution and rights checks.")
        else:
            log_func("\n🔍 STEP 1: Checking file licenses to protect you from copyright issues...")

    # Pre-initialise so the fallback branch and the attribution lookup below always see defined names.
    safe_files = []
    risky_files = []

    def _is_archived_path(p):
        return "_ORIGINALS_DO_NOT_UPLOAD_" in str(p)

    def _dedupe_keep_order(paths):
        out = []
        seen = set()
        for p in paths:
            key = os.path.abspath(str(p))
            if key in seen:
                continue
            seen.add(key)
            out.append(str(p))
        return out

    try:
        if fast_license_mode:
            # Fast path: skip attribution scanner and start conversion immediately.
            safe_file_paths = [str(p) for p in web_resources.glob('**/*.pdf') if not _is_archived_path(p)] + [str(p) for p in web_resources.glob('**/*.docx') if not _is_archived_path(p)]
            safe_file_paths = _dedupe_keep_order(safe_file_paths)
            if log_func:
                log_func(f"   Found {len(safe_file_paths)} candidate file(s) for conversion.")
        else:
            import attribution_checker
            # Keep scan silent to avoid long, noisy per-file UI logging.
            safe_files, risky_files, blocked_files = attribution_checker.scan_export_for_licensing(
                export_dir,
                None,
            )

            # Create licensing report
            report_path = export_path / "LICENSING_REPORT.md"
            attribution_checker.create_licensing_report(export_dir, str(report_path))

            if log_func:
                log_func("\n📊 LICENSING SCAN RESULTS:")
                log_func(f"   ✅ Safe to convert: {len(safe_files)}")
                log_func(f"   ⚠️  Needs review: {len(risky_files)}")
                log_func(f"   ❌ DO NOT convert: {len(blocked_files)}")
                log_func(f"\n📄 Full licensing report saved: {report_path}")

            # Block conversion if proprietary content found
            if blocked_files:
                if log_func:
                    log_func("\n❌ STOPPING: Found publisher copyrighted materials!")
                    log_func("   Review LICENSING_REPORT.md for details.")
                    log_func("   DO NOT convert blocked files without written permission!")
                return False, f"Found {len(blocked_files)} proprietary files. See LICENSING_REPORT.md"

            if risky_files and log_func:
                log_func(f"\n⚠️  WARNING: {len(risky_files)} files need review")
                log_func("   Proceeding with conversion, but CHECK LICENSING_REPORT.md")
                log_func("   You are responsible for proper attribution!")

            # Get list of safe files (include risky/UNKNOWN files - teacher's own content)
            # Only block PROPRIETARY publisher content
            convertible_files = safe_files + risky_files
            safe_file_paths = [f['path'] for f in convertible_files if f['path'].lower().endswith(('.pdf', '.docx')) and not _is_archived_path(f['path'])]
            safe_file_paths = _dedupe_keep_order(safe_file_paths)

            if not safe_file_paths:
                return False, "No safe PDF or Word files found to convert"

    except Exception as e_license:
        # Fallback: If the licensing checker crashes, just continue with safe paths
        if log_func:
            log_func(f"[Licensing scan error] {e_license}")
        safe_file_paths = []
    
    # STEP 2: Convert safe files
    if log_func:
        log_func(f"\n🤖 STEP 2: Converting files with Gemini AI...")
    
    # [NEW] Pre-check: How many are actually left?
    already_done = 0
    remaining_paths = []
    for fp in safe_file_paths:
        p = Path(fp)
        html_out = p.parent / f"{p.stem}.html"
        if html_out.exists():
            already_done += 1
        else:
            remaining_paths.append(fp)
    
    if log_func:
        log_func(
            f"   📊 Status: {already_done} already converted, {len(remaining_paths)} remaining "
            f"(based on existing .html files next to source files in this extracted folder)."
        )
        if not remaining_paths:
            log_func("   ✨ Everything is already up to date!")
            return True, []

    client = genai.Client(api_key=api_key)
    
    conversion_results = [] # List of (source_path, output_path)
    skipped_no_math = []
    total_files = len(safe_file_paths)
    
    stop_requested = False
    for i, file_path in enumerate(safe_file_paths, 1):
        if progress_callback:
            progress_callback(i, total_files)
        try:
            p = Path(file_path)
            ext = p.suffix.lower()
            
            html_output_path = p.parent / f"{p.stem}.html"
            if html_output_path.exists():
                if log_func: log_func(f"   ⏩ Skipping: {p.name} (Already converted: found {html_output_path.name})")
                # Still trigger callback to ensure upload happens if needed
                if on_file_converted:
                    try:
                        on_file_converted(str(file_path), str(html_output_path))
                    except Exception:
                        pass
                continue

            if log_func:
                log_func(f"   🔄 Converting: {p.name} ...")

            if ext == '.pdf':
                if not _pdf_has_math(str(p)):
                    skipped_no_math.append(str(file_path))
                    if log_func:
                        log_func(f"   ⏭️ Ignored (no math detected): {p.name}")
                    continue

                detect_visuals_for_file = detect_visuals
                if detect_visuals_callback:
                    try:
                        detect_choice = detect_visuals_callback(str(p))
                        if detect_choice is None:
                            if log_func:
                                log_func(f"   ⏹️ Stopped by user before converting: {p.name}")
                            stop_requested = True
                            break
                        detect_visuals_for_file = bool(detect_choice)
                    except Exception as e_cb:
                        if log_func:
                            log_func(f"   ⚠️ Visual option callback error for {p.name}: {e_cb}. Using default.")

                gate_cb = None
                if step_mode and page_gate_callback:
                    gate_cb = lambda page_num, total_pages, fname=p.name: page_gate_callback(fname, page_num, total_pages)
                success, html_or_error = convert_pdf_to_latex(
                    api_key, str(p), log_func, poppler_path=poppler_path,
                    visual_review_callback=visual_review_callback,
                    step_mode=step_mode,
                    page_gate_callback=gate_cb,
                    detect_visuals=detect_visuals_for_file,
                    manual_visual_selection=manual_visual_selection,
                    strict_math_validation=strict_math_validation,
                    latex_review_callback=latex_review_callback,
                )
            elif ext == '.docx':
                if not _docx_has_math(str(p)):
                    skipped_no_math.append(str(file_path))
                    if log_func:
                        log_func(f"   ⏭️ Ignored (no math detected): {p.name}")
                    continue

                success, html_or_error = convert_word_to_latex(api_key, str(p), log_func)
            else:
                continue
           

            if success:
                # Safety cleanup for leaked internal graph tokens.
                html_or_error = re.sub(r'\[GRAPH_BBOX:[^\]]+\]', '', html_or_error)

                # DOCX fallback: replace AI placeholder/external image URLs with local extracted assets.
                if ext == '.docx':
                    html_or_error = repair_docx_placeholder_image_sources(
                        html_or_error,
                        str(p),
                        log_func,
                    )

                # Add attribution footer if needed
                license_info = next((f for f in safe_files + risky_files if f['path'] == file_path), None)
                
                if license_info and license_info['requires_attribution']:
                    import attribution_checker
                    footer = attribution_checker.generate_attribution_footer(
                        p.name,
                        license_info['license']
                    )
                    # Insert footer before </body>
                    html_or_error = html_or_error.replace('</body>', f'{footer}</body>')
                
                # Save HTML file IN THE SAME FOLDER as the source (for link syncing)
                html_filename = f"{p.stem}.html"
                html_path = p.parent / html_filename
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_or_error)
                
                conversion_results.append((str(file_path), str(html_path)))
                
                if log_func:
                    log_func(f"   ✅ Saved: {html_filename}")
                
                # [NEW] Call immediate callback for upload/sync
                if on_file_converted:
                    try:
                        on_file_converted(str(file_path), str(html_path))
                    except Exception as e_cb:
                        if log_func: log_func(f"   ⚠️ Post-processing error: {e_cb}")
            else:
                 if log_func:
                    log_func(f"   ⚠️ Skipping file due to error: {html_or_error}")
        
        except Exception as e_file {
            if log_func:
                log_func(f"   ❌ Oops! Problem with {Path(file_path).name}: {e_file}")
            continue
    }
    
    if stop_requested and conversion_results:
        if log_func:
            log_func(f"\n✅ Partial conversion complete: {len(conversion_results)} file(s) converted before stop.")
            if skipped_no_math:
                log_func(f"ℹ️ Left unconverted (no math detected): {len(skipped_no_math)} file(s).")
        return True, {
            "converted": conversion_results,
            "skipped_no_math": skipped_no_math,
        }

    if conversion_results:
        if log_func:
            log_func(f"\n✅ Converted {len(conversion_results)} file(s) successfully!")
            log_func(f"📁 Files saved in their original folders (ready for sync)")
            if skipped_no_math:
                log_func(f"ℹ️ Left unconverted (no math detected): {len(skipped_no_math)} file(s).")
            log_func(f"\n⚖️  REMEMBER: Review LICENSING_REPORT.md before publishing!")
        return True, {
            "converted": conversion_results,
            "skipped_no_math": skipped_no_math,
        }
    elif skipped_no_math:
        if log_func:
            log_func(f"\nℹ️ No files converted. {len(skipped_no_math)} file(s) were left in place because no math was detected.")
        return True, {
            "converted": [],
            "skipped_no_math": skipped_no_math,
        }
    else:
        if log_func:
             log_func(f"\n❌ Note: No PDF files were converted. (See detailed log above)")
        return False, "No files processed successfully."

def create_canvas_html(content, title="Canvas Math Content"):
    """
    Creates a standalone HTML file with the converted content.
    Uses INLINE STYLES for maximum compatibility with Canvas LMS.
    """
    # Escape the title so a filename like <script>... can't inject into the <title> tag.
    safe_title = html_lib.escape(title)

    # Inject inline styles into standard elements returned by Gemini
    content = re.sub(
        r'<details\s*>', 
        r'<details style="background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #4b3190; border-radius: 4px;">', 
        content,
        flags=re.IGNORECASE
    )
    
    content = re.sub(
        r'<summary\s*>', 
        r'<summary style="cursor: pointer; font-weight: bold; color: #4b3190;">', 
        content,
        flags=re.IGNORECASE
    )

    margin_px = _style_preferences.get("image_margin_px", 15)
    h1_color = _style_preferences.get("h1_color", "#4b3190")
    h2_color = _style_preferences.get("h2_color", "#2c3e50")
    h3_color = _style_preferences.get("h3_color", "#2c3e50")
    h4_color = _style_preferences.get("h4_color", "#374151")
    h5_color = _style_preferences.get("h5_color", "#4b5563")
    h6_color = _style_preferences.get("h6_color", "#6b7280")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <!-- MathJax for local preview with cancel extension for crossed-out terms -->
    <script>
    window.MathJax = {{
        tex: {{
            packages: {{'[+]': ['cancel', 'cases']}}
        }},
        loader: {{
            load: ['[tex]/cancel', '[tex]/cases']
        }}
    }};
    </script>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', 'Roboto', Helvetica, Arial, sans-serif;
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px;
            line-height: 1.6;
            color: #2D2D2D;
            background-color: #ffffff;
        }}
        h1 {{
            color: {h1_color};
            border-bottom: 2px solid {h1_color};
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 28px; /* Reduced from browser default */
            font-weight: 700;
        }}
        h2 {{ color: {h2_color}; margin-top: 30px; }}
        h3 {{ color: {h3_color}; margin-top: 30px; }}
        h4 {{ color: {h4_color}; margin-top: 24px; }}
        h5 {{ color: {h5_color}; margin-top: 20px; }}
        h6 {{ color: {h6_color}; margin-top: 16px; }}

        /* Table Handling - Prevent Cutoff */
        table {{
            display: table;
            width: 100%;
            overflow-x: auto;
            border-collapse: collapse;
            margin: 20px 0;
            -webkit-overflow-scrolling: touch;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{ background-color: #f8f9fa; color: #4b3190; }}

        /* Interactive Solutions */
        details {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-left: 5px solid #4b3190;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
            transition: all 0.2s ease;
        }}
        summary {{
            font-weight: 600;
            color: #4b3190;
            cursor: pointer;
            padding-bottom: 5px;
        }}
        summary:hover {{ color: #2c3e50; }}

        /* Images */
        img {{
            max-width: 500px;
            width: 100%;
            height: auto;
            border-radius: 4px;
            display: block;
            margin: {margin_px}px 0;
        }}

        @media (max-width: 768px) {{
            img {{ max-width: 100% !important; }}
        }}

        /* Print Friendly */
        @media print {{
            body {{ max-width: 100%; padding: 0; }}
            details {{ display: block !important; border: none; }}
            summary {{ display: none; }}
        }}
    </style>
</head>
<body>
    <h1>{safe_title}</h1>

    <div class="content-wrapper">
        {content}
    </div>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 50px 0;">
    <p style="font-size: 10px; color: #7f8c8d; text-align: center; font-family: monospace;">
        Accessible format created by MOSH Toolkit using Gemini AI
    </p>
</body>
</html>
"""
    return html
