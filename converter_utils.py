
# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License version 3. USE AT YOUR OWN RISK.

import os
import shutil
import re
from datetime import datetime
import zipfile
import base64
import uuid

# --- Constants ---
ARCHIVE_FOLDER_NAME = "_ORIGINALS_DO_NOT_UPLOAD_"

# --- Third Party Imports ---
try:
    import mammoth
except ImportError:
    mammoth = None

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
except ImportError:
    Presentation = None

try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

try:
    from pdfminer.high_level import extract_text
except ImportError:
    extract_text = None


# --- HTML Templates ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; 
            font-size: 16px;
            line-height: 1.6; 
            color: #333;
            max-width: 900px; 
            margin: 0 auto; 
            padding: 40px; 
        }}
        h1 {{ 
            font-size: 2.25em; 
            font-weight: 700;
            color: #4b3190; 
            border-bottom: 2px solid #e0e0e0; 
            padding-bottom: 10px; 
            margin-bottom: 30px;
        }}
        h2 {{ color: #2c3e50; margin-top: 40px; font-weight: 600; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        h3 {{ color: #444; margin-top: 30px; font-weight: 600; }}
        a {{ color: #0056b3; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        /* Table Styles */
        table {{ border-collapse: collapse; width: 100%; margin: 25px 0; font-size: 0.95em; border: 1px solid #ddd; }}
        th, td {{ border: 1px solid #ddd; padding: 12px 15px; text-align: left; }}
        th {{ background-color: #f8f9fa; font-weight: 600; color: #495057; }}
        tr:nth-child(even) {{ background-color: #fcfcfc; }}
        .content-table {{ width: 100%; border-collapse: collapse; }}
        
        img {{ max-width: 100%; height: auto; border-radius: 4px; border: 1px solid #eee; }}
        .grading-note {{ background-color: #e8f5e9; padding: 10px; border-left: 4px solid #4caf50; font-style: italic; }}
        .note {{ font-size: 0.9em; color: #666; background: #fff3cd; padding: 15px; border-radius: 4px; border: 1px solid #ffeeba; }}
        
        /* Code Block Styles */
        code {{ background-color: #f1f3f5; padding: 2px 5px; border-radius: 4px; font-family: Consolas, 'Courier New', monospace; color: #d63384; }}
        pre {{ 
            background-color: #272822; 
            color: #f8f8f2; 
            padding: 15px; 
            border-radius: 8px; 
            overflow-x: auto; 
            font-family: Consolas, 'Courier New', monospace; 
            line-height: 1.4;
            margin: 20px 0;
        }}
        .code-block {{ margin: 15px 0; }}
        
        .slide-container {{ overflow: auto; clear: both; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
        .slide-container::after {{ content: ""; display: table; clear: both; }}
        .slide-image {{ border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="note">✅ Remediated content from {source_file}</p>
    {content}
</body>
</html>
"""

def _save_html(content, title, source_file, output_path):
    """Wraps content in template and saves file."""
    html = HTML_TEMPLATE.format(
        title=title,
        source_file=os.path.basename(source_file),
        date=datetime.now().strftime("%Y-%m-%d"),
        content=content
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path

# --- Converters ---

def convert_docx_to_html(docx_path):
    """Converts DOCX to HTML using Mammoth (with style mapping)."""
    if not mammoth:
        return None, "Mammoth library not installed."

    try:
        # Custom Style Map for Canvas alignment
        style_map = """
        p[style-name='Title'] => h1:fresh
        p[style-name='Heading 1'] => h2:fresh
        p[style-name='Heading 2'] => h3:fresh
        p[style-name='Heading 3'] => h4:fresh
        p[style-name='Heading 4'] => h5:fresh
        p[style-name='Complete/Incomplete'] => p.grading-note:fresh
        r[style-name='Strong'] => strong
        b => strong
        i => em
        """
        
        filename = os.path.splitext(os.path.basename(docx_path))[0]
        output_dir = os.path.dirname(docx_path)
        
        # Image Handler for Mammoth
        def convert_image(image):
            # 1. Create web_resources/[filename] folder if it doesn't exist
            safe_filename = filename.replace(" ", "_")
            res_dir = os.path.join(output_dir, "web_resources", safe_filename)
            if not os.path.exists(res_dir):
                os.makedirs(res_dir)
            
            # 2. Extract description
            alt_text = image.alt_text if image.alt_text else f"Image from {filename}"
            
            # 3. Save Image File
            with image.open() as image_source:
                image_bytes = image_source.read()
            
            # Generate unique name
            ext = image.content_type.split('/')[-1]
            if ext == 'jpeg': ext = 'jpg'
            short_id = uuid.uuid4().hex[:8]
            img_name = f"img_{short_id}.{ext}"
            img_path = os.path.join(res_dir, img_name)
            
            with open(img_path, 'wb') as f:
                f.write(image_bytes)
            
            # 4. Return Tag with Standard Relative Path
            # This ensures images work locally AND in Canvas (standard import)
            return {
                "src": f"web_resources/{safe_filename}/{img_name}",
                "alt": alt_text
            }

        with open(docx_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file, style_map=style_map, convert_image=mammoth.images.img_element(convert_image))
            html_content = result.value
            messages = result.messages # Warnings
            
        # Logging for user visibility
        img_count = html_content.count("<img")
        print(f"    [LOG] Extracted {img_count} images from Word document.")

        # Post-Processing: Basic Cleanup
        # Remove empty paragraphs often generated by extra Returns in Word
        html_content = html_content.replace("<p></p>", "").replace("<p>&nbsp;</p>", "")
        
        # Ensure tables have some basic class for our CSS
        html_content = html_content.replace("<table>", '<table class="content-table">')

        output_path = os.path.join(output_dir, f"{filename}.html")
        
        # Wrap in template
        _save_html(html_content, filename, docx_path, output_path)
        
        return output_path, None
    except Exception as e:
        return None, str(e)


def convert_excel_to_html(xlsx_path):
    """Converts Excel to HTML Tables using OpenPyXL."""
    if not openpyxl:
        return None, "OpenPyXL library not installed."

    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        html_parts = []
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            html_parts.append(f"<h2>Sheet: {sheet_name}</h2>")
            html_parts.append('<table class="content-table">')
            
            rows = list(ws.rows)
            if rows:
                # Header
                html_parts.append("<thead><tr>")
                for cell in rows[0]:
                    val = cell.value if cell.value is not None else ""
                    html_parts.append(f"<th>{val}</th>")
                html_parts.append("</tr></thead>")
                
                # Body
                html_parts.append("<tbody>")
                for row in rows[1:]:
                    html_parts.append("<tr>")
                    for cell in row:
                        val = cell.value if cell.value is not None else ""
                        html_parts.append(f"<td>{val}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</tbody>")
            
            html_parts.append("</table>")

        full_content = "\n".join(html_parts)
        
        filename = os.path.splitext(os.path.basename(xlsx_path))[0]
        output_path = os.path.join(os.path.dirname(xlsx_path), f"{filename}.html")
        
        _save_html(full_content, filename, xlsx_path, output_path)
        return output_path, None
        
    except Exception as e:
        return None, str(e)


def convert_ppt_to_html(ppt_path):
    """Converts PPTX to HTML Lecture Notes + Extracts Images."""
    if not Presentation:
        return None, "python-pptx library not installed."

    try:
        prs = Presentation(ppt_path)
        filename = os.path.splitext(os.path.basename(ppt_path))[0]
        output_dir = os.path.dirname(ppt_path)
        
        # Media Folder
        media_folder_name = f"{filename}_media"
        media_path = os.path.join(output_dir, media_folder_name)
        if not os.path.exists(media_path):
            os.makedirs(media_path)

        html_parts = []
        
        for i, slide in enumerate(prs.slides):
            slide_num = i + 1
            html_parts.append(f'<div class="slide-container" id="slide-{slide_num}">')
            html_parts.append(f'<p class="note">Slide {slide_num}</p>')
            
            # Title
            if slide.shapes.title:
                title_text = slide.shapes.title.text_frame.text
                html_parts.append(f'<h2 class="slide-title">{title_text}</h2>')
            
            # Content (Text & Images)
            for shape in slide.shapes:
                # Text
                if shape.has_text_frame:
                    if shape == slide.shapes.title: continue 

                    # [SMART FIX] 1. Code Block Detection (Monospace Fonts)
                    is_code = False
                    bg_color = None
                    text_color = None
                    
                    if shape.text_frame.paragraphs:
                        # Check first paragraph font
                        para = shape.text_frame.paragraphs[0]
                        font_name = para.font.name
                        if font_name and any(f in font_name.lower() for f in ['courier', 'consolas', 'mono', 'lucida console']):
                            is_code = True
                            
                            # Try to extract Background Color from Shape Fill
                            try:
                                if shape.fill.type == 1: # Solid fill
                                    rgb = shape.fill.fore_color.rgb
                                    bg_color = f"#{rgb}"
                            except: pass
                            
                            # Try to extract Text Color from first run
                            try:
                                if para.runs:
                                    rgb = para.runs[0].font.color.rgb
                                    if rgb:
                                        text_color = f"#{rgb}"
                            except: pass

                    if is_code:
                        safe_text = shape.text_frame.text.replace("<", "&lt;").replace(">", "&gt;")
                        style = ""
                        if bg_color: style += f"background-color: {bg_color}; "
                        if text_color: style += f"color: {text_color}; "
                        
                        html_parts.append(f'<pre class="code-block" style="{style}">{safe_text}</pre>')
                        continue

                    # [SMART FIX] 2. Improved Bullet Detection
                    # Instead of assuming bullets, we check the actual paragraph level/bullet property
                    text_content = []
                    for paragraph in shape.text_frame.paragraphs:
                        txt = paragraph.text.strip()
                        if not txt: continue
                        
                        # Check if this paragraph is actually a bullet
                        # In python-pptx, a bullet is often indicated by level > 0 OR explicit bullet property
                        # but often we can just check if the paragraph has a bullet character or is in a bulleted style
                        is_bullet = False
                        try:
                            # Level > 0 is a strong indicator of intent for bullets in PPT
                            if paragraph.level > 0:
                                is_bullet = True
                            # Check if the text actually starts with a bullet-like character if it's level 0
                            elif txt.startswith(('•', '-', '*', '◦', '▪')):
                                is_bullet = True
                        except: pass

                        if is_bullet:
                            text_content.append(f"<li>{txt}</li>")
                        else:
                            # Close <ul> if it was open (handled by joining logic later)
                            text_content.append(f"<p>{txt}</p>")
                    
                    if text_content:
                        final_shape_html = ""
                        in_list = False
                        for item in text_content:
                            if item.startswith("<li>"):
                                if not in_list:
                                    final_shape_html += "<ul>"
                                    in_list = True
                                final_shape_html += item
                            else:
                                if in_list:
                                    final_shape_html += "</ul>"
                                    in_list = False
                                final_shape_html += item
                        if in_list:
                            final_shape_html += "</ul>"
                        html_parts.append(final_shape_html)

                # Tables
                if shape.has_table:
                    html_parts.append('<table class="content-table" border="1">')
                    for row in shape.table.rows:
                        html_parts.append('<tr>')
                        for cell in row.cells:
                            # Extract text from cell
                            cell_text = ""
                            if cell.text_frame:
                                cell_text = cell.text_frame.text.strip()
                            html_parts.append(f'<td>{cell_text}</td>')
                        html_parts.append('</tr>')
                    html_parts.append('</table>')

                # Images
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    try:
                        image = shape.image
                        image_bytes = image.blob
                        ext = image.ext
                        # Use web_resources/[filename] folder
                        safe_filename = filename.replace(" ", "_")
                        res_dir = os.path.join(output_dir, "web_resources", safe_filename)
                        if not os.path.exists(res_dir): os.makedirs(res_dir)
                        
                        image_filename = f"slide{slide_num}_{uuid.uuid4().hex[:6]}.{ext}"
                        image_full_path = os.path.join(res_dir, image_filename)
                        
                        with open(image_full_path, 'wb') as img_f:
                            img_f.write(image_bytes)
                            
                        # Embed in HTML with Standard Relative Path
                        rel_path = f"web_resources/{safe_filename}/{image_filename}"
                        
                        # [ENHANCED] Calculate dimensions and position for floating
                        # PPTX uses EMUs (English Metric Units). 1 inch = 914400 EMUs. 
                        # Web usually treats 96 DPI. So 914400 / 96 = 9525 EMUs per pixel.
                        width_px = int(shape.width / 9525) if hasattr(shape, 'width') else 300
                        
                        # Limit max width for better text flow
                        max_img_width = 300
                        if width_px > max_img_width:
                            width_px = max_img_width
                        
                        # Detect horizontal position on slide (for floating)
                        # Slide width is typically 9144000 EMUs (10 inches)
                        slide_width = prs.slide_width if hasattr(prs, 'slide_width') else 9144000
                        shape_center_x = shape.left + (shape.width / 2) if hasattr(shape, 'left') else 0
                        
                        # Determine float direction based on position
                        if shape_center_x < slide_width / 2:
                            # Image is on the left side of slide
                            float_style = "float: left; margin: 0 15px 10px 0;"
                        else:
                            # Image is on the right side of slide
                            float_style = "float: right; margin: 0 0 10px 15px;"
                        
                        html_parts.append(f'<img src="{rel_path}" alt="[FIX_ME] Image from Slide {slide_num}" width="{width_px}" class="slide-image" style="{float_style}">')
                    except Exception as img_err:
                        print(f"Skipped image on slide {slide_num}: {img_err}")

            html_parts.append('</div>')

        full_content = "\n".join(html_parts)
        output_path = os.path.join(output_dir, f"{filename}.html")
        
        _save_html(full_content, filename, ppt_path, output_path)
        return output_path, None

    except Exception as e:
        return None, str(e)


def convert_pdf_to_html(pdf_path):
    """Converts PDF to HTML using PyMuPDF (Images + Text)."""
    if not fitz:
        if not extract_text:
             return None, "Neither PyMuPDF (fitz) nor pdfminer.six are installed."
        else:
             # Fallback to old method if fitz is missing (though we just installed it)
             return _convert_pdf_fallback(pdf_path)

    try:
        doc = fitz.open(pdf_path)
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.dirname(pdf_path)
        
        # Media Folder
        media_folder_name = f"{filename}_media"
        media_path = os.path.join(output_dir, media_folder_name)
        if not os.path.exists(media_path):
            os.makedirs(media_path)
            
        html_parts = []
        html_parts.append('<div class="pdf-content">')
        
        for i, page in enumerate(doc):
            page_num = i + 1
            html_parts.append(f'<div class="page-container" id="page-{page_num}" style="margin-bottom: 30px; border-bottom: 1px solid #ccc; padding-bottom: 20px;">')
            html_parts.append(f'<p class="note">Page {page_num}</p>')
            
            # 1. Extract Content via Dict (Structure + Images)
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])
            
            for block in blocks:
                # Type 1 = Image
                if block['type'] == 1:
                    try:
                        ext = block['ext']
                        image_bytes = block['image']
                        
                        # [SIZE FIX] Get dimensions from BBox (in points)
                        bbox = block['bbox'] # (x0, y0, x1, y1)
                        width_pt = bbox[2] - bbox[0]
                        # Convert to roughly pixels (1pt = 1.33px roughly, or just use pt)
                        # Let's use int points for cleaner HTML
                        width_attr = int(width_pt)
                        
                        # Save Image
                        safe_filename = filename.replace(" ", "_")
                        res_dir = os.path.join(output_dir, "web_resources", safe_filename)
                        if not os.path.exists(res_dir): os.makedirs(res_dir)

                        image_filename = f"page{page_num}_img_{uuid.uuid4().hex[:6]}.{ext}"
                        image_full_path = os.path.join(res_dir, image_filename)
                        
                        with open(image_full_path, "wb") as f:
                            f.write(image_bytes)
                            
                        rel_path = f"web_resources/{safe_filename}/{image_filename}"
                        html_parts.append(f'<img src="{rel_path}" alt="" width="{width_attr}" class="content-image" style="display: block; margin: 10px 0;">')
                    except Exception as e:
                        print(f"Skipped PDF image: {e}")

                # Type 0 = Text
                elif block['type'] == 0:
                     for line in block["lines"]:
                         for span in line["spans"]:
                             text = span["text"].strip()
                             font_size = span["size"]
                             if not text: continue
                             
                             # Simple Heuristic for Headers based on font size
                             # (Adjust thresholds as needed)
                             if font_size > 18:
                                  html_parts.append(f"<h2>{text}</h2>")
                             elif font_size > 14:
                                  html_parts.append(f"<h3>{text}</h3>")
                             else:
                                  # Basic text
                                  # Sanitize
                                  safe_text = text.replace("<", "&lt;").replace(">", "&gt;")
                                  html_parts.append(f"<p>{safe_text}</p>")

            html_parts.append('</div>')
            
            # [TABLE FIX] Extract Tables
            # We append them at the bottom of the page content for now to avoid breaking flow logic
            try:
                tables = page.find_tables()
                if tables.tables:
                    html_parts.append('<h4>Found Tables:</h4>')
                    for tab in tables:
                        html_parts.append(tab.to_pandas().to_html(index=False, header=False, classes="content-table").replace('class="dataframe content-table"', 'class="content-table"'))
            except Exception as e:
                print(f"Table detection failed: {e}")

        html_parts.append('</div>')
        
        full_content = "\n".join(html_parts)
        
        # Logging
        h_count = full_content.count("<h3") + full_content.count("<h2")
        img_count = full_content.count("<img")
        print(f"    [LOG] PDF Conversion: Detected {h_count} headers and {img_count} images.")
        output_path = os.path.join(output_dir, f"{filename}.html")
        
        _save_html(full_content, filename, pdf_path, output_path)
        return output_path, None

    except Exception as e:
        return None, f"PyMuPDF Error: {str(e)}"

def _convert_pdf_fallback(pdf_path):
    """Legacy text-only converter using pdfminer."""
    try:
        text = extract_text(pdf_path)
        paragraphs = text.split('\n\n')
        html_parts = []
        html_parts.append('<div class="pdf-content">')
        html_parts.append('<p class="note">⚠️ Text-Only Extraction (Images Missing).</p>')
        
        for p in paragraphs:
             clean_p = p.strip()
             if clean_p:
                  html_parts.append(f"<p>{clean_p}</p>")
        
        html_parts.append('</div>')
        full_content = "\n".join(html_parts)
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(os.path.dirname(pdf_path), f"{filename}.html")
        _save_html(full_content, filename, pdf_path, output_path)
        return output_path, None

    except Exception as e:
        return None, str(e)


def update_links_in_directory(directory, old_filename, new_filename):

    """
    Scans all HTML files in directory and replaces links.
    e.g. href="syllabus.docx" -> href="syllabus.html"
    """
    count = 0
    old_base = os.path.basename(old_filename)
    new_base = os.path.basename(new_filename)
    
    # [CANVAS FIX] Remove extension for the NEW link as requested
    # e.g. "syllabus.docx" -> "syllabus" (instead of "syllabus.html")
    new_base_no_ext = os.path.splitext(new_base)[0]
    
    # URL encode spaces
    old_base_enc = old_base.replace(' ', '%20')
    new_base_no_ext_enc = new_base_no_ext.replace(' ', '%20')

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if old_base in content or old_base_enc in content:
                        # Replace with the extensionless version
                        new_content = content.replace(old_base, new_base_no_ext)
                        new_content = new_content.replace(old_base_enc, new_base_no_ext_enc)
                        
                        if new_content != content:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            count += 1
                except:
                    pass
    return count

def unzip_course_package(zip_path, extract_to):
    """
    Extracts a Canvas Export (.imscc) or Zip file to the target directory.
    Renames .imscc to .zip internally if needed.
    """
    try:
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            
        return True, f"Successfully extracted to: {extract_to}"
    except Exception as e:
        return False, str(e)

def create_course_package(source_dir, output_path):
    """
    Zips the directory back into a .imscc file.
    Automatically excludes the originals archive folder.
    """
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Skip the archive folder entirely
                if ARCHIVE_FOLDER_NAME in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    # Archive name should be relative to source_dir
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
        return True, f"Created: {output_path}"
    except Exception as e:
        return False, str(e)

def archive_source_file(file_path):
    """
    Moves an original source file to the archive folder.
    Returns the new path.
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        dir_name = os.path.dirname(file_path)
        archive_dir = os.path.join(dir_name, ARCHIVE_FOLDER_NAME)
        
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            
        new_path = os.path.join(archive_dir, os.path.basename(file_path))
        
        # If file already exists in archive, add a timestamp or just overwrite
        if os.path.exists(new_path):
            # For simplicity, we just move it. Shutil.move handles destination objects.
            pass
            
        shutil.move(file_path, new_path)
        return new_path
    except Exception as e:
        print(f"Error archiving {file_path}: {e}")
        return None

