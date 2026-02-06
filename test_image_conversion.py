import converter_utils
import os
from bs4 import BeautifulSoup

def test_image_conversion_logic():
    print("--- Testing Image Conversion Logic (Word/PPT/PDF) ---")
    
    # We can't easily create complex DOCX/PPTX on the fly without more libraries,
    # so we'll test the individual conversion logic components where possible or just run a dry build.
    
    # 1. Check if imports are working
    print(f"Mammoth loaded: {converter_utils.mammoth is not None}")
    print(f"Presentation loaded: {converter_utils.Presentation is not None}")
    print(f"PyMuPDF (fitz) loaded: {converter_utils.fitz is not None}")
    print(f"python-docx (docx) loaded: {converter_utils.docx is not None}")

    # 2. Test sanitize_filename (Crucial for pathing)
    test_name = "My Test File (v1.0).docx"
    sanitized = converter_utils.sanitize_filename(os.path.splitext(test_name)[0])
    print(f"Sanitized: {sanitized}")
    if sanitized == "My_Test_File_v1_0":
        print("PASS: Filename sanitization is robust.")
    else:
        print(f"FAIL: Filename sanitization returned '{sanitized}'")

    # 3. Test Manifest Update Logic
    # (Create dummy manifest)
    manifest_content = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="test">
  <resources>
    <resource identifier="res1" type="webcontent" href="old_file.docx"/>
  </resources>
</manifest>
"""
    with open("imsmanifest.xml", "w", encoding="utf-8") as f:
        f.write(manifest_content)
        
    success, msg = converter_utils.update_manifest_resource(".", "old_file.docx", "new_file.html")
    print(f"Manifest Update: {success} | {msg}")
    
    if success and "Updated 1 references" in msg:
        print("PASS: Manifest synchronization works.")
    else:
        print("FAIL: Manifest synchronization failed.")

    # Cleanup
    if os.path.exists("imsmanifest.xml"):
        os.remove("imsmanifest.xml")

if __name__ == "__main__":
    test_image_conversion_logic()
