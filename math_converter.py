#!/usr/bin/env python3
"""
Math Converter Module for MOSH Toolkit
Integrates with Gemini AI to convert handwritten math to Canvas LaTeX
"""

import os
from pathlib import Path
from PIL import Image

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_gemini_response(text):
    """
    Cleans Gemini response by removing markdown code blocks and HTML boilerplate.
    Returns only the body content.
    """
    # 1. Strip markdown code blocks (e.g. ```html ... ```)
    text = re.sub(r'^```\w*\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    
    # 2. Extract body content if present
    if '<body' in text.lower():
        match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1)
            
    # 3. Strip other boilerplate if body tag wasn't strict
    if '<!DOCTYPE html>' in text:
        text = re.sub(r'<!DOCTYPE html>.*', '', text, flags=re.DOTALL)
        
    return text.strip()

MATH_PROMPT = """Convert the content of this image to Canvas-compatible HTML/LaTeX.

RULES:
1. Identify all mathematical content and convert to LaTeX:
   - Use \\(...\\) for inline equations
   - Use $$...$$ for display equations
2. TRANSCRIBE any standard text exactly as it appears.
3. If the image contains NO MATH, just transcribe the text or describe the image. DO NOT REFUSE.
4. GRAPHS & DIAGRAMS:
   - Provide a DETAILED text description of the graph/diagram.
   - CRITICAL: Calculate the bounding box of the graph (0-1000 scale).
   - Output the code: [GRAPH_BBOX: ymin, xmin, ymax, xmax]
   - Example: [GRAPH_BBOX: 150, 100, 450, 900]
   - I will use this to auto-crop the image.
   - Example: <p><em>[Graph Description: A parabola...]</em></p> [GRAPH_BBOX: 200, 200, 500, 500]
   - Do NOT ignore visual elements.
5. HANDWRITING / TEACHER NOTES:
   - If you detect handwritten notes or solutions, style them in BLUE.
   - Use: <br><span style="color: #0066cc; font-family: 'Comic Sans MS', cursive, sans-serif;">[Note: ...]</span><br>
6. Preserve problem numbers (e.g., "1.", "a)") and layout structure.
7. Formatting:
   - Use <h3> for section headers
   - Use <b> for bold text
   - Use <i> for italics
   - Use <table> for tabular data
7. Solutions/Answers:
   - Wrap solutions in <details><summary>View Solution</summary>...</details>
8. Output MUST be valid HTML snippet (no <html> cards). 
9. DO NOT include markdown code blocks (```html).

Goal: A perfect accessible digital version of this document."""

def generate_content_with_retry(client, model, contents, log_func=None):
    """
    Wraps Gemini generation with exponential backoff for rate limits and connection issues.
    """
    max_retries = 6
    base_delay = 5  # Start with 5 seconds
    
    for attempt in range(max_retries):
        try:
            # Proactive pacing: 4.0s delay guarantees <15 RPM (Free Tier Limit)
            # This is actually FASTER than hitting a rate limit and waiting 60s.
            if attempt == 0:
                time.sleep(4.0)
            
            return client.models.generate_content(
                model=model,
                contents=contents
            )
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

            if is_retryable:
                wait_time = base_delay * (2 ** attempt) # 5, 10, 20, 40, 80...
                if log_func:
                    reason = "Quota" if ("429" in error_str or "exhausted" in error_str) else "Network"
                    log_func(f"   ⏳ {reason} Hiccup. Pausing for {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                # If it's a real Auth error or something else, don't wait 2 minutes
                raise e
    
    raise Exception("MOSH Magic failed after multiple retries. The AI server might be too busy or your connection is unstable. Please try again in a few minutes.")

def extract_and_crop_graphs(html_content, image_path, output_dir, base_name, page_num):
    """
    Parses [GRAPH_BBOX] tokens, crops images from the source page, 
    saves them to web_resources, and replaces tokens with <img> tags.
    """
    if '[GRAPH_BBOX:' not in html_content:
        return html_content
        
    try:
        # 1. Ensure web_resources exists
        res_dir = Path(output_dir) / 'web_resources'
        res_dir.mkdir(exist_ok=True)
        
        # 2. Open Source Image
        with Image.open(image_path) as img:
            width, height = img.size
            
            # 3. Find all BBOX tokens
            # Format: [GRAPH_BBOX: ymin, xmin, ymax, xmax] (0-1000 scale)
            matches = re.finditer(r'\[GRAPH_BBOX:\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]', html_content)
            
            for i, match in enumerate(matches):
                try:
                    full_token = match.group(0)
                    ymin_rel, xmin_rel, ymax_rel, xmax_rel = map(int, match.groups())
                    
                    # 4. Convert to Pixels with Padding
                    ymin = int((ymin_rel / 1000) * height)
                    xmin = int((xmin_rel / 1000) * width)
                    ymax = int((ymax_rel / 1000) * height)
                    xmax = int((xmax_rel / 1000) * width)
                    
                    # Add 20px padding
                    ymin = max(0, ymin - 20)
                    xmin = max(0, xmin - 20)
                    ymax = min(height, ymax + 20)
                    xmax = min(width, xmax + 20)
                    
                    if (xmax - xmin) < 50 or (ymax - ymin) < 50:
                        continue # Skip tiny crops
                        
                    # 5. Crop and Save
                    crop = img.crop((xmin, ymin, xmax, ymax))
                    
                    # Unique filename
                    graph_filename = f"{base_name}_p{page_num + 1}_graph{i + 1}.png"
                    save_path = res_dir / graph_filename
                    crop.save(save_path)
                    
                    # 6. Replace Token with Image Tag
                    img_tag = f'<br><img src="web_resources/{graph_filename}" alt="Graph from Page {page_num + 1}" style="max-width: 600px; border: 1px solid #ccc;"><br>'
                    html_content = html_content.replace(full_token, img_tag)
                    
                except Exception as e:
                    print(f"Crop Error: {e}")
                    # Remove token on error to clean up
                    html_content = html_content.replace(full_token, "")
                    
    except Exception as e:
        print(f"Graph extraction failed: {e}")
        
    return html_content

def convert_pdf_to_latex(api_key, pdf_path, log_func=None, poppler_path=None, progress_callback=None):
    """
    Convert a PDF with handwritten math to Canvas LaTeX.
    
    Returns:
        (success, html_content_or_error_message)
    """
    if not genai:
        return False, "Gemini library not installed. Run: pip install google-genai pillow pdf2image"
    
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
        
        temp_dir = Path(pdf_path).parent / f"{Path(pdf_path).stem}_temp"
        
        # Clean up previous temp dir if it exists to avoid stale images
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
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
        
        # Process each page using Multi-threading (3x Faster!)
        all_content = [None] * len(images) # Preschool for ordered results
        progress_count = 0
        
        def process_page(index, img_path):
            try:
                img = Image.open(img_path)
                response = generate_content_with_retry(
                    client=client,
                    model='gemini-2.0-flash',
                    contents=[MATH_PROMPT, img],
                    log_func=log_func
                )
                return index, clean_gemini_response(response.text)
            except Exception as e:
                if log_func:
                    log_func(f"   [Error] Page {index+1} failed: {e}")
                return index, f"<p>[Error converting page {index+1}: {e}]</p>"

        # Use 1 worker for stability (prevents Poppler/Tkinter crashes)
        # Sort images to ensure index matches sorted(glob)
        sorted_image_paths = sorted(temp_dir.glob('*.png'))
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = []
            for i, img_path in enumerate(sorted_image_paths):
                futures.append(executor.submit(process_page, i, img_path))
            
            for future in as_completed(futures):
                idx, content = future.result()
                all_content[idx] = content
                progress_count += 1
                if progress_callback:
                    progress_callback(progress_count, len(images))
                if log_func:
                    log_func(f"   ✅ Finished processing page {idx+1}/{len(images)}")
        
        # [NEW] Post-Processing: Extract and Crop Graphs
        if log_func: log_func("   ✂️  Auto-cropping graphs from pages...")
        output_dir = Path(pdf_path).parent
        pdf_stem = Path(pdf_path).stem
        
        final_pages = []
        for i, content in enumerate(all_content):
            if content:
                # Use the original temp image for cropping
                try:
                    content = extract_and_crop_graphs(content, sorted_image_paths[i], output_dir, pdf_stem, i)
                except Exception as e:
                     if log_func: log_func(f"   ⚠️ Graph crop warning p{i+1}: {e}")
                final_pages.append(content)
                
        # Combine everything
        final_html_content = "\n<hr>\n".join(final_pages)
        
        # Clean up temp images
        try:
             del images
        except: pass
        
        # Robust cleanup
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            if log_func: log_func(f"   ⚠️ Cleanup warning: {e}")
        
        # Create HTML
        title = Path(pdf_path).stem.replace('_', ' ').title()
        html = create_canvas_html(final_html_content, title=title)
        
        if log_func:
            log_func(f"✅ Conversion complete: {len(all_content)} pages")
        
        return True, html
        
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def convert_image_to_latex(api_key, image_path, log_func=None):
    """Convert a single image to LaTeX."""
    if not genai:
        return False, "Gemini library not installed"
    
    try:
        client = genai.Client(api_key=api_key)
        
        if log_func:
            log_func(f"📸 Converting image: {Path(image_path).name}")
        
        img = Image.open(image_path)
        response = generate_content_with_retry(
            client=client,
            model='gemini-2.0-flash',
            contents=[MATH_PROMPT, img],
            log_func=log_func
        )
        
        if response.text:
            cleaned_text = clean_gemini_response(response.text)
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
    Convert equations in Word doc to LaTeX.
    Uses python-docx to extract images, then processes with Gemini.
    """
    if not genai:
        return False, "Gemini library not installed"
    
    try:
        from docx import Document
    except ImportError:
        return False, "python-docx not installed. Run: pip install python-docx"
    
    try:
        if log_func:
            log_func(f"📝 Processing Word doc: {Path(doc_path).name}")
        
        doc = Document(doc_path)
        client = genai.Client(api_key=api_key)
        
        # Extract text and images
        all_content = []
        
        for i, rel in enumerate(doc.part.rels.values(), 1):
            if "image" in rel.target_ref:
                # Extract image
                image_blob = rel.target_part.blob
                
                # Save temporarily
                temp_img = Path(doc_path).parent / f"temp_img_{i}.png"
                with open(temp_img, 'wb') as f:
                    f.write(image_blob)
                
                # Convert with Gemini
                img = Image.open(temp_img)
                response = generate_content_with_retry(
                    client=client,
                    model='gemini-2.0-flash',
                    contents=[MATH_PROMPT, img],
                    log_func=log_func
                )
                
                if response.text:
                    cleaned_text = clean_gemini_response(response.text)
                    all_content.append(f"\n<!-- Image {i} -->\n{cleaned_text}\n")
                
                temp_img.unlink()  # Clean up
        
        if all_content:
            title = Path(doc_path).stem.replace('_', ' ').title()
            html = create_canvas_html("\n".join(all_content), title=title)
            
            if log_func:
                log_func(f"✅ Converted {len(all_content)} equations from Word doc")
            
            return True, html
        else:
            return False, "No math images found in Word document"
            
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def process_canvas_export(api_key, export_dir, log_func=None, poppler_path=None, progress_callback=None, on_file_converted=None):
    """
    Process all PDFs in a Canvas export (IMSCC) structure.
    Includes licensing/attribution checking to protect teachers.
    
    Returns:
        (success, list_of_html_files_or_error)
    """
    if not genai:
        return False, "Gemini library not installed"
    
    export_path = Path(export_dir)
    web_resources = export_path / 'web_resources'
    
    if not web_resources.exists():
        return False, f"No web_resources folder found in {export_dir}"
    
    # STEP 1: Check licensing FIRST
    if log_func:
        log_func("\n🔍 STEP 1: Checking file licenses to protect you from copyright issues...")
    
    try:
        import attribution_checker
        safe_files, risky_files, blocked_files = attribution_checker.scan_export_for_licensing(
            export_dir, 
            log_func
        )
        
        # Create licensing report
        report_path = export_path / "LICENSING_REPORT.md"
        attribution_checker.create_licensing_report(export_dir, str(report_path))
        
        if log_func:
            log_func(f"\n📄 Full licensing report saved: {report_path}")
        
        # Block conversion if proprietary content found
        if blocked_files and log_func:
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
        safe_file_paths = [f['path'] for f in convertible_files if f['path'].lower().endswith(('.pdf', '.docx'))]
        
        if not safe_file_paths:
            return False, "No safe PDF or Word files found to convert"
            
    except Exception as e:
        if log_func:
            log_func(f"\n⚠️  Could not check licensing: {e}")
            log_func("   Proceeding cautiously - YOU must verify licensing manually!")
        # Fall back to processing all PDFs and Docx
        safe_file_paths = [str(p) for p in web_resources.glob('**/*.pdf')] + [str(p) for p in web_resources.glob('**/*.docx')]
    
    # STEP 2: Convert safe files
    if log_func:
        log_func(f"\n🤖 STEP 2: Converting {len(safe_file_paths)} files with Gemini AI...")
    
    client = genai.Client(api_key=api_key)
    
    conversion_results = [] # List of (source_path, output_path)
    total_files = len(safe_file_paths)
    
    for i, file_path in enumerate(safe_file_paths, 1):
        if progress_callback:
            progress_callback(i, total_files)
        try:
            p = Path(file_path)
            ext = p.suffix.lower()
            
            html_output_path = p.parent / f"{p.stem}.html"
            if html_output_path.exists():
                if log_func: log_func(f"   ⏩ Skipping: {p.name} (Already converted)")
                # Still trigger callback to ensure upload happens if needed
                if on_file_converted:
                    try:
                        on_file_converted(str(file_path), str(html_output_path))
                    except: pass
                continue

            if log_func:
                log_func(f"   🔄 Converting: {p.name} ...")

            if ext == '.pdf':
                success, html_or_error = convert_pdf_to_latex(api_key, str(p), log_func, poppler_path=poppler_path)
            elif ext == '.docx':
                success, html_or_error = convert_word_to_latex(api_key, str(p), log_func)
            else:
                continue

            if success:
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
        
        except Exception as e_file:
            if log_func:
                log_func(f"   ❌ Oops! Problem with {Path(file_path).name}: {e_file}")
            continue
    
    if conversion_results:
        if log_func:
            log_func(f"\n✅ Converted {len(conversion_results)} PDFs successfully!")
            log_func(f"📁 Files saved in their original folders (ready for sync)")
            log_func(f"\n⚖️  REMEMBER: Review LICENSING_REPORT.md before publishing!")
        return True, conversion_results
    else:
        if log_func:
             log_func(f"\n❌ Note: No PDF files were converted. (See detailed log above)")
        return False, "No files processed successfully."

def create_canvas_html(content, title="Canvas Math Content"):
    """
    Creates a standalone HTML file with the converted content.
    Uses INLINE STYLES for maximum compatibility with Canvas LMS.
    """
    import re
    
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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- MathJax for local preview -->
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
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
            color: #4b3190;
            border-bottom: 2px solid #4b3190;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 28px; /* Reduced from browser default */
            font-weight: 700;
        }}
        h2, h3 {{ color: #2c3e50; margin-top: 30px; }}
        
        /* Table Handling - Prevent Cutoff */
        table {{
            display: block;
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
        img {{ max-width: 100%; height: auto; border-radius: 4px; }}
        
        /* Print Friendly */
        @media print {{
            body {{ max-width: 100%; padding: 0; }}
            details {{ display: block !important; border: none; }}
            summary {{ display: none; }}
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <div class="content-wrapper">
        {content}
    </div>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 50px 0;">
    <p style="font-size: 0.85em; color: #7f8c8d; text-align: center; font-family: monospace;">
        Accessible format created by MOSH Toolkit using Gemini AI
    </p>
</body>
</html>
"""
    return html
