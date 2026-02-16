#!/usr/bin/env python3
"""
Gemini Math to Canvas LaTeX Converter
Created by Meri Kasprak with Gemini assistance
Released under GNU GPL v3

FAST TRACK for teachers with Gemini API access.
Batch converts handwritten math and equations to Canvas LaTeX format.

Setup:
    pip install google-generativeai pillow pdf2image

Usage:
    python gemini_math_converter.py --folder images/
    python gemini_math_converter.py --pdf solutions.pdf
    python gemini_math_converter.py --image single_equation.png
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import json

try:
    from google import genai
    from PIL import Image
except ImportError:
    print("❌ Missing dependencies. Please run:")
    print("   pip install google-genai pillow pdf2image")
    sys.exit(1)

# Gemini prompt for math conversion
CONVERSION_PROMPT = """You are a Canvas LMS math content expert. Convert ALL mathematical content in this image to Canvas-compatible LaTeX format.

CRITICAL RULES:
1. Use \\(...\\) for inline equations (within text)
2. Use $$...$$ for display equations (on their own line)
3. Convert ALL handwritten math you see
4. Preserve the structure (numbered problems, steps, etc.)
5. Add descriptive text between equations if needed
6. Be 100% accurate with mathematical notation
7. DO NOT return a full HTML document (no <html>, <head>, <body> tags). Return ONLY the content.

OUTPUT FORMAT:
- Return clean, ready-to-paste Canvas HTML/LaTeX
- Include problem numbers if present
- Use proper LaTeX syntax (\\frac, \\sqrt, ^, _, etc.)
- Add <details><summary>Solution</summary>...</details> tags for solutions

Example output:
**Problem 1**: Solve \\(x^2 - 5x + 6 = 0\\)

<details>
<summary>Show Solution</summary>

**Step 1**: Factor the quadratic
$$x^2 - 5x + 6 = (x-2)(x-3)$$

**Step 2**: Set each factor to zero
$$x - 2 = 0 \\quad \\text{or} \\quad x - 3 = 0$$

**Answer**: \\(x = 2\\) or \\(x = 3\\)
</details>

Now convert the image:"""

def setup_gemini_api():
    """Configure Gemini API with user's key."""
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("\n🔑 Gemini API Key Required")
        print("\nOption 1: Set environment variable")
        print("   Windows: set GEMINI_API_KEY=your_key_here")
        print("   Mac/Linux: export GEMINI_API_KEY=your_key_here")
        print("\nOption 2: Get key from https://aistudio.google.com/app/apikey")
        api_key = input("\nEnter your Gemini API key now (or press Enter to exit): ").strip()
        
        if not api_key:
            print("❌ No API key provided. Exiting.")
            sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    print("✅ Gemini API configured")
    return client

def convert_image_to_latex(client, image_path: str) -> Tuple[str, bool]:
    """
    Converts a single image of handwritten math to Canvas LaTeX.
    
    Returns:
        Tuple of (latex_content, success)
    """
    try:
        img = Image.open(image_path)
        
        print(f"   📸 Sending to Gemini... ", end='', flush=True)
        response = client.models.generate_content(
            model='gemini-1.5-pro',
            contents=[CONVERSION_PROMPT, img]
        )
        
        if not response.text:
            print("❌ No response")
            return "", False
        
        latex_content = response.text.strip()
        
        # Clean up markdown code blocks
        import re
        latex_content = re.sub(r'^```\w*\s*', '', latex_content, flags=re.MULTILINE)
        latex_content = re.sub(r'\s*```$', '', latex_content, flags=re.MULTILINE)
        
        # Clean up HTML boilerplate
        if '<body' in latex_content.lower():
            match = re.search(r'<body[^>]*>(.*?)</body>', latex_content, re.DOTALL | re.IGNORECASE)
            if match:
                latex_content = match.group(1).strip()
        
        if '<!DOCTYPE html>' in latex_content:
            latex_content = re.sub(r'<!DOCTYPE html>.*', '', latex_content, flags=re.DOTALL).strip()
            
        print("✅ Converted!")
        return latex_content, True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"<!-- Error converting {image_path}: {e} -->", False

def convert_pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """Converts PDF pages to images for processing."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("❌ pdf2image not installed. Run: pip install pdf2image")
        print("   Also need poppler: https://github.com/oschwartz10612/poppler-windows/releases")
        sys.exit(1)
    
    print(f"📄 Converting PDF to images...")
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    images = convert_from_path(pdf_path, dpi=300, output_folder=output_dir, fmt='png')
    
    image_paths = []
    for i, img in enumerate(images, 1):
        img_path = output_path / f"page_{i:03d}.png"
        img.save(img_path, 'PNG')
        image_paths.append(str(img_path))
    
    print(f"✅ Created {len(image_paths)} images")
    return image_paths

def batch_convert_folder(client, folder_path: str, output_file: str):
    """Converts all images in a folder to LaTeX."""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(folder_path).glob(f'*{ext}'))
        image_files.extend(Path(folder_path).glob(f'*{ext.upper()}'))
    
    if not image_files:
        print(f"❌ No images found in {folder_path}")
        return
    
    print(f"\n📚 Found {len(image_files)} images to convert\n")
    
    all_latex = []
    stats = {'success': 0, 'failed': 0}
    
    for i, img_path in enumerate(sorted(image_files), 1):
        print(f"[{i}/{len(image_files)}] {img_path.name}")
        latex, success = convert_image_to_latex(client, str(img_path))
        
        if success:
            stats['success'] += 1
            all_latex.append(f"\n<!-- Converted from {img_path.name} -->\n{latex}\n")
        else:
            stats['failed'] += 1
            all_latex.append(f"\n<!-- FAILED: {img_path.name} -->\n")
    
    # Save combined output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Canvas Math Content - Converted by Gemini\n\n")
        f.write("<!-- Copy this entire file into Canvas HTML editor, or copy sections as needed -->\n\n")
        f.write("".join(all_latex))
    
    print(f"\n✅ Conversion complete!")
    print(f"   ✓ Success: {stats['success']}")
    if stats['failed'] > 0:
        print(f"   ✗ Failed: {stats['failed']}")
    print(f"\n📄 Output saved to: {output_file}")
    print(f"\n🎯 Next steps:")
    print(f"   1. Open {output_file}")
    print(f"   2. Review the LaTeX (check for accuracy)")
    print(f"   3. Copy into Canvas HTML editor")
    print(f"   4. Save and preview in Canvas")

def interactive_single_image(client, image_path: str):
    """Converts a single image with interactive review."""
    print(f"\n📸 Converting: {Path(image_path).name}")
    
    latex, success = convert_image_to_latex(client, image_path)
    
    if not success:
        print("❌ Conversion failed")
        return
    
    print("\n" + "="*60)
    print("CONVERTED LATEX:")
    print("="*60)
    print(latex)
    print("="*60)
    
    save = input("\n💾 Save to file? (y/n): ").lower().strip()
    if save == 'y':
        output_file = Path(image_path).stem + "_canvas.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex)
        print(f"✅ Saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Convert handwritten math to Canvas LaTeX using Gemini')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image', help='Single image file to convert')
    group.add_argument('--folder', help='Folder of images to batch convert')
    group.add_argument('--pdf', help='PDF file to convert (will extract pages as images)')
    parser.add_argument('--output', default='canvas_math_output.html', help='Output file name')
    
    args = parser.parse_args()
    
    print("🚀 Gemini Math to Canvas LaTeX Converter")
    print("="*60)
    
    client = setup_gemini_api()
    
    if args.image:
        interactive_single_image(client, args.image)
    
    elif args.folder:
        batch_convert_folder(client, args.folder, args.output)
    
    elif args.pdf:
        print(f"\n📄 Processing PDF: {args.pdf}")
        temp_dir = Path(args.pdf).stem + "_images"
        image_paths = convert_pdf_to_images(args.pdf, temp_dir)
        batch_convert_folder(client, temp_dir, args.output)
        
        cleanup = input(f"\n🗑️  Delete temporary images in {temp_dir}? (y/n): ").lower().strip()
        if cleanup == 'y':
            import shutil
            shutil.rmtree(temp_dir)
            print(f"✅ Cleaned up {temp_dir}")

if __name__ == '__main__':
    main()
