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
    from pdf2image import convert_from_path
except ImportError:
    genai = None

import re
import time

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

MATH_PROMPT = """Convert ALL mathematical content in this image to Canvas-compatible LaTeX format.

RULES:
1. Use \\(...\\) for inline equations
2. Use $$...$$ for display equations  
3. Preserve problem numbers and steps
4. Add <details><summary>Solution</summary>...</details> for solutions
5. Be 100% accurate
6. DO NOT return a full HTML document (no <html>, <head>, <body> tags). Return ONLY the content.

Return ready-to-paste HTML/LaTeX for Canvas."""

def generate_content_with_retry(client, model, contents, log_func=None):
    """
    Wraps Gemini generation with exponential backoff for 429 errors.
    """
    max_retries = 5
    base_delay = 4  # Start with 4 seconds
    
    for attempt in range(max_retries):
        try:
            # Proactive delay to avoid hitting rate limits
            if attempt == 0:
                time.sleep(1.5)
            
            return client.models.generate_content(
                model=model,
                contents=contents
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = base_delay * (2 ** attempt) # 4, 8, 16, 32, 64
                if log_func:
                    log_func(f"   ⏳ Rate Limit Hit. Pausing for {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise e
    
    raise Exception("API Quota Exceeded. Please try again later.")

def convert_pdf_to_latex(api_key, pdf_path, log_func=None, poppler_path=None):
    """
    Convert a PDF with handwritten math to Canvas LaTeX.
    
    Returns:
        (success, html_content_or_error_message)
    """
    if not genai:
        return False, "Gemini library not installed. Run: pip install google-genai pillow pdf2image"
    
    if log_func:
        log_func(f"📄 Processing PDF: {Path(pdf_path).name}")
    
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
        
        # Process each page
        all_content = []
        for i, img_path in enumerate(sorted(temp_dir.glob('*.png')), 1):
            if log_func:
                log_func(f"   [{i}/{len(images)}] Converting page {i}...")
            
            img = Image.open(img_path)
            response = generate_content_with_retry(
                client=client,
                model='gemini-2.0-flash',
                contents=[MATH_PROMPT, img],
                log_func=log_func
            )
            
            if response.text:
                cleaned_text = clean_gemini_response(response.text)
                all_content.append(f"\n<!-- Page {i} -->\n{cleaned_text}\n")
            else:
                all_content.append(f"\n<!-- Page {i}: No response from Gemini -->\n")
        
        # Clean up temp images
        import time
        
        # Close any open file handles
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
        html = create_canvas_html(title, "\n".join(all_content))
        
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
            html = create_canvas_html(title, cleaned_text)
            
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
            html = create_canvas_html(title, "\n".join(all_content))
            
            if log_func:
                log_func(f"✅ Converted {len(all_content)} equations from Word doc")
            
            return True, html
        else:
            return False, "No math images found in Word document"
            
    except Exception as e:
        if log_func:
            log_func(f"❌ Error: {e}")
        return False, str(e)

def process_canvas_export(api_key, export_dir, log_func=None, poppler_path=None):
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
        
        # Get list of safe PDF files (include risky/UNKNOWN files - teacher's own content)
        # Only block PROPRIETARY publisher content
        convertible_files = safe_files + risky_files
        safe_pdf_paths = [f['path'] for f in convertible_files if f['path'].endswith('.pdf')]
        
        if not safe_pdf_paths:
            return False, "No safe PDF files found to convert"
            
    except Exception as e:
        if log_func:
            log_func(f"\n⚠️  Could not check licensing: {e}")
            log_func("   Proceeding cautiously - YOU must verify licensing manually!")
        # Fall back to processing all PDFs
        safe_pdf_paths = [str(p) for p in web_resources.glob('**/*.pdf')]
    
    # STEP 2: Convert safe files
    if log_func:
        log_func(f"\n🤖 STEP 2: Converting {len(safe_pdf_paths)} PDFs with Gemini AI...")
    
    client = genai.Client(api_key=api_key)
    
    # Create output directory - REMOVED to keep files in-place for syncing
    # output_dir = export_path / "converted_math_pages"
    # output_dir.mkdir(exist_ok=True)
    
    conversion_results = [] # List of (source_path, output_path)
    
    for pdf_path in safe_pdf_paths:
        try:
            pdf = Path(pdf_path)
            if log_func:
                log_func(f"   ► Converting: {pdf.name}...")

            success, html_or_error = convert_pdf_to_latex(api_key, str(pdf), log_func, poppler_path=poppler_path)
            
            if success:
                # Add attribution footer if needed
                license_info = next((f for f in safe_files + risky_files if f['path'] == pdf_path), None)
                
                if license_info and license_info['requires_attribution']:
                    import attribution_checker
                    footer = attribution_checker.generate_attribution_footer(
                        pdf.name,
                        license_info['license']
                    )
                    # Insert footer before </body>
                    html_or_error = html_or_error.replace('</body>', f'{footer}</body>')
                
                # Save HTML file IN THE SAME FOLDER as the PDF (for link syncing)
                html_filename = f"{pdf.stem}.html"
                html_path = pdf.parent / html_filename
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_or_error)
                
                conversion_results.append((str(pdf_path), str(html_path)))
                
                if log_func:
                    log_func(f"   ✅ Saved: {html_filename}")
            else:
                 if log_func:
                    log_func(f"   ⚠️ Skiping file due to error: {html_or_error}")
        
        except Exception as e_file:
            if log_func:
                log_func(f"   ❌ Oops! Problem with {Path(pdf_path).name}: {e_file}")
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
<body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6;">
    <h1 style="color: #4b3190; border-bottom: 2px solid #4b3190; padding-bottom: 10px;">{title}</h1>
    
    <div style="margin: 20px 0;">
        {content}
    </div>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
    <p style="font-size: 0.9em; color: #666; font-style: italic; text-align: center;">
        ✨ Converted to accessible LaTeX by MOSH Toolkit with Gemini AI
    </p>
</body>
</html>
"""
    return html
