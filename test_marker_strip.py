import run_fixer
import os

def test_marker_removal():
    print("--- Testing ADA Marker Removal ---")
    
    html = """
<div lang="en">
    <p style="color: grey;">Low contrast text</p>
    <span style="color:red;">[ADA FIX: Low Contrast 2.1:1]</span>
    <img src="test.png" alt="[FIX_ME]: Missing Alt Text. Describe this image.">
    <!-- ADA FIX: Inserted H2 based on page title -->
</div>
"""
    test_file = "test_cleanup.html"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Running cleanup...")
    new_html, count = run_fixer.strip_ada_markers(html)
    
    print(f"Stripped {count} markers.")
    
    if "[ADA FIX" not in new_html and "[FIX_ME]" not in new_html:
        print("PASS: All markers and [FIX_ME] tags removed.")
    else:
        print("FAIL: Markers still present in HTML.")
        print(new_html)

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_marker_removal()
