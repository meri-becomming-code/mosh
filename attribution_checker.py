#!/usr/bin/env python3
"""
Attribution & License Checker for MOSH Toolkit
Helps teachers honor copyright and Creative Commons attribution requirements
"""

import os
import re
from pathlib import Path
from datetime import datetime

# Creative Commons license patterns
CC_PATTERNS = {
    'CC BY': r'CC\s*BY',
    'CC BY-SA': r'CC\s*BY-SA',
    'CC BY-NC': r'CC\s*BY-NC',
    'CC BY-ND': r'CC\s*BY-ND',
    'CC BY-NC-SA': r'CC\s*BY-NC-SA',
    'CC BY-NC-ND': r'CC\s*BY-NC-ND',
    'CC0': r'CC0|Public\s*Domain',
}

# Publisher warnings (DO NOT CONVERT without permission)
PUBLISHER_WARNINGS = [
    'Pearson',
    'McGraw-Hill',
    'McGraw Hill',
    'Cengage',
    'Wiley',
    'Elsevier',
    'Macmillan',
    'Houghton Mifflin',
    'Oxford University Press',
    'Cambridge University Press',
    'All Rights Reserved',
    '© Copyright',
    'Copyrighted Material',
]

def check_file_for_licensing(file_path, log_func=None):
    """
    Check a file (PDF, Word doc, HTML) for licensing information.
    
    Returns:
        (license_type, attribution_required, warnings)
    """
    try:
        # Try to extract text from file
        text_content = extract_text(file_path)
        
        if not text_content:
            return "UNKNOWN", True, ["Could not extract text - please check manually"]
        
        # Check for Creative Commons licenses
        cc_license = None
        for license_name, pattern in CC_PATTERNS.items():
            if re.search(pattern, text_content, re.IGNORECASE):
                cc_license = license_name
                break
        
        # Check for publisher warnings
        warnings = []
        for publisher in PUBLISHER_WARNINGS:
            if publisher.lower() in text_content.lower():
                warnings.append(f"⚠️ Contains '{publisher}' - likely proprietary content!")
        
        # Determine attribution requirements
        attribution_required = True
        if cc_license:
            if cc_license == 'CC0':
                attribution_required = False
            license_type = cc_license
        elif warnings:
            license_type = "PROPRIETARY"
            warnings.insert(0, "❌ DO NOT CONVERT - This appears to be copyrighted publisher material")
        else:
            license_type = "UNKNOWN"
            warnings.append("⚠️ No license found - assume attribution required")
        
        if log_func:
            log_func(f"   License: {license_type}")
            if attribution_required:
                log_func(f"   Attribution: REQUIRED")
            for warning in warnings:
                log_func(f"   {warning}")
        
        return license_type, attribution_required, warnings
        
    except Exception as e:
        if log_func:
            log_func(f"   Error checking license: {e}")
        return "ERROR", True, [str(e)]

def extract_text(file_path):
    """Extract text from PDF, Word, or HTML files."""
    path = Path(file_path)
    ext = path.suffix.lower()
    
    try:
        if ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return extract_text_from_word(file_path)
        elif ext in ['.html', '.htm']:
            return extract_text_from_html(file_path)
        else:
            return ""
    except:
        return ""

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF (first page only for speed)."""
    try:
        from pdf2image import convert_from_path
        # Only check first page for licensing info
        # images = convert_from_path(str(pdf_path), dpi=150, last_page=1)
        # Placeholder: Real OCR would go here. For now, return empty.
        return ""
    except:
        return ""

def extract_text_from_word(doc_path):
    """Extract text from Word document."""
    try:
        from docx import Document
        doc = Document(doc_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        return text
    except:
        return ""

def extract_text_from_html(html_path):
    """Extract text from HTML file."""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Simple text extraction
        from html.parser import HTMLParser
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data):
                self.text.append(data)
        extractor = TextExtractor()
        extractor.feed(content)
        return ' '.join(extractor.text)
    except:
        return ""

def generate_attribution_footer(file_name, license_type, author="Unknown", source_url=""):
    """
    Generate proper attribution footer for converted content.
    
    Returns HTML snippet to append to converted pages.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    footer = f"""
<hr style="margin-top: 30px;">
<div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #4b3190; font-size: 0.9em;">
    <strong>📜 Source Attribution</strong><br>
    Original material: <em>{file_name}</em><br>
"""
    
    if author != "Unknown":
        footer += f"    Author/Creator: {author}<br>\n"
    
    if license_type and license_type != "UNKNOWN":
        footer += f"    License: {license_type}<br>\n"
    
    if source_url:
        footer += f"    Source: <a href='{source_url}'>{source_url}</a><br>\n"
    
    footer += f"""    Converted to accessible LaTeX: {today} using MOSH Toolkit<br>
    <br>
    <em>This derivative work is shared under the same license as the original.</em>
</div>
"""
    
    return footer

def scan_export_for_licensing(export_dir, log_func=None):
    """
    Scan entire Canvas export for licensing issues.
    
    Returns:
        (safe_files, risky_files, blocked_files)
    """
    export_path = Path(export_dir)
    web_resources = export_path / 'web_resources'
    
    if not web_resources.exists():
        if log_func:
            log_func("❌ No web_resources folder found")
        return [], [], []
    
    safe_files = []
    risky_files = []
    blocked_files = []
    
    # Check all PDFs and Word docs
    files = list(web_resources.glob('**/*.pdf')) + list(web_resources.glob('**/*.docx'))
    
    if log_func:
        log_func(f"\n📋 Scanning {len(files)} files for licensing...")
    
    for file_path in files:
        if log_func:
            log_func(f"\n   Checking: {file_path.name}")
        
        license_type, attribution_req, warnings = check_file_for_licensing(str(file_path), log_func)
        
        file_info = {
            'path': str(file_path),
            'name': file_path.name,
            'license': license_type,
            'requires_attribution': attribution_req,
            'warnings': warnings
        }
        
        if license_type == "PROPRIETARY":
            blocked_files.append(file_info)
        elif warnings:
            risky_files.append(file_info)
        else:
            safe_files.append(file_info)
    
    if log_func:
        log_func(f"\n\n📊 LICENSING SCAN RESULTS:")
        log_func(f"   ✅ Safe to convert: {len(safe_files)}")
        log_func(f"   ⚠️  Needs review: {len(risky_files)}")
        log_func(f"   ❌ DO NOT convert: {len(blocked_files)}")
    
    return safe_files, risky_files, blocked_files

def create_licensing_report(export_dir, output_path):
    """Create a detailed licensing report for the export."""
    safe, risky, blocked = scan_export_for_licensing(export_dir)
    
    report = f"""# Licensing Report for Canvas Export

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- ✅ **Safe to Convert**: {len(safe)} files
- ⚠️  **Needs Review**: {len(risky)} files  
- ❌ **DO NOT Convert**: {len(blocked)} files

---

## ✅ Safe Files (OER or Your Content)

These files show no proprietary warnings and can be converted:

"""
    
    for file in safe:
        report += f"- `{file['name']}` - License: {file['license']}\n"
    
    report += f"\n---\n\n## ⚠️  Files Needing Review\n\nThese files have warnings. Review before converting:\n\n"
    
    for file in risky:
        report += f"### `{file['name']}`\n"
        report += f"- License: {file['license']}\n"
        for warning in file['warnings']:
            report += f"- {warning}\n"
        report += "\n"
    
    report += f"\n---\n\n## ❌ Blocked Files (Proprietary Publisher Content)\n\n**DO NOT CONVERT THESE WITHOUT WRITTEN PERMISSION:**\n\n"
    
    for file in blocked:
        report += f"### `{file['name']}`\n"
        report += f"- License: {file['license']}\n"
        for warning in file['warnings']:
            report += f"- {warning}\n"
        report += "\n"
    
    report += f"""
---

## Legal Guidance

### ✅ Safe to Convert:
- Your own original content
- OER materials (Creative Commons, open textbooks)
- Public domain materials
- Content with explicit conversion permission

### ⚠️  Requires Attribution:
- Creative Commons licensed materials (except CC0)
- **You MUST include**: Author name, title, source, license type
- Use MOSH's auto-generated attribution footers

### ❌ DO NOT Convert:
- Pearson, McGraw-Hill, Cengage, or other publisher materials
- Copyrighted textbooks and workbooks
- "All Rights Reserved" content
- Anything without explicit permission

### When in Doubt:
1. Check with your institution's copyright office
2. Contact the publisher for permission
3. Only convert content you created OR OER materials

**Remember**: Just because you have access doesn't mean you have permission to create derivatives!

---

Generated by MOSH Toolkit - Protecting educators through responsible AI use.
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return safe, risky, blocked

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        export_dir = sys.argv[1]
        output = Path(export_dir) / "LICENSING_REPORT.md"
        safe, risky, blocked = create_licensing_report(export_dir, str(output))
        print(f"\n✅ Report saved to: {output}")
        print(f"\n📊 Results: {len(safe)} safe, {len(risky)} risky, {len(blocked)} blocked")
    else:
        print("Usage: python attribution_checker.py <canvas_export_directory>")
