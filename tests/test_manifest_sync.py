import os
import shutil
import converter_utils

def test_manifest_update():
    print("--- Testing Manifest Update Logic ---")
    test_dir = "test_manifest_env"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    manifest_content = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="gec15594036aa10e0bb83663219bb4b3a">
  <resources>
    <resource identifier="r1" type="webcontent" href="Old_Folder/Pres.pptx">
      <file href="Old_Folder/Pres.pptx"/>
    </resource>
    <resource identifier="r2" type="webcontent" href="Static.html">
      <file href="Static.html"/>
    </resource>
  </resources>
</manifest>
"""
    manifest_path = os.path.join(test_dir, "imsmanifest.xml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    # Test conversion: Old_Folder/Pres.pptx -> Pres.html
    print("Updating manifest for conversion: Old_Folder/Pres.pptx -> Pres.html")
    success, msg = converter_utils.update_manifest_resource(test_dir, "Old_Folder/Pres.pptx", "Pres.html")
    
    if not success:
        print(f"FAILED: {msg}")
        return

    print(f"Success: {msg}")

    # Verify content
    with open(manifest_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    
    if "Pres.html" in new_content and "Old_Folder/Pres.pptx" not in new_content:
        print("Verification PASSED: Manifest updated correctly.")
    else:
        print("Verification FAILED: Manifest content incorrect.")
        print(new_content)

    # Cleanup
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("Cleanup complete.")

if __name__ == "__main__":
    test_manifest_update()
