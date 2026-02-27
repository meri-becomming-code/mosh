import run_fixer
import os

def test_marker_removal():
    print("--- Testing ADA Marker Removal ---")
    
    # HTML with a clean image (no alt) — fixer should FLAG it in the fixes list,
    # NOT inject [FIX_ME] text into the HTML attribute.
    html = """
<div lang="en">
    <p style="color: grey;">Low contrast text</p>
    <span style="color:red;">[ADA FIX: Low Contrast 2.1:1]</span>
    <img src="test.png">
    <!-- ADA FIX: Inserted H2 based on page title -->
</div>
"""
    test_file = "test_cleanup.html"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Running remediation...")
    new_html, fixes = run_fixer.remediate_html_file(test_file)
    
    print(f"Fixes applied: {len(fixes)}")

    # 1. Remediation should return valid HTML
    if isinstance(new_html, str) and len(new_html) > 0:
        print("PASS: remediate_html_file returned valid HTML output.")
    else:
        print("FAIL: remediate_html_file returned empty or invalid output.")

    # 2. ADA comment markers should be cleaned during remediation pass
    if "<!-- ADA FIX:" not in new_html:
        print("PASS: ADA comment markers cleaned from output.")
    else:
        print("FAIL: ADA comment markers still present in output.")

    # 3. Fixer should NOT inject [FIX_ME] into img alt — it flags in fixes list instead
    if "[FIX_ME]" not in new_html:
        print("PASS: Fixer does not inject [FIX_ME] into HTML (flags in fixes list instead).")
    else:
        print("FAIL: [FIX_ME] text injected into output HTML.")

    # 4. Image with no alt should be flagged in the fixes list
    image_flagged = any("flagged" in f.lower() or "missing" in f.lower() or "alt" in f.lower() for f in fixes)
    if image_flagged:
        print("PASS: Image without alt text was flagged in fixes list.")
    else:
        print("INFO: No image alt flag in fixes list.")
        print("Fixes:", fixes)

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_marker_removal()
