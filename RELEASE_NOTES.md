# MOSH ADA Toolkit - Release Notes (v1.1)

This release focuses on improving the robustness of the IMSCC export process and streamlining the transition from remediation to Canvas upload.

## 🚀 New Features
- **🧹 Visual Marker Cleanup**: Added a new "Remove Visual Markers" button to the main dashboard. This tool strips all red `[ADA FIX]` labels and `[FIX_ME]` tags from your HTML files in one click, ensuring a clean, professional look for your students.
- **🛠️ Automated Table Remediation**: The toolkit now automatically fixes invalid table structures by removing empty `<tbody>` tags and ensuring correct `<thead>` placement. This resolves the common "Table structure is invalid" error in Canvas.

## 🔧 Critical Fixes
- **IMSCC Manifest Sync**: Fixed a major export error where `imsmanifest.xml` was not updated after file conversions. The toolkit now automatically synchronizes manifest references when you convert Word, PPT, or PDF files to HTML.
- **Robust Image Resolution**: Enhanced the logic for finding course images, particularly for home pages (`home.html`) and resources using Canvas-specific tokens (`$IMS-CC-FILEBASE$`).
- **Path Handling**: Improved support for nested folder structures within course packages, ensuring links remain stable after export and re-import.

## 📦 Executable Update
- The standalone Windows executable (**dist/MOSH_ADA_Toolkit.exe**) has been updated to include all version 1.1 features and fixes. No manual Python installation is required.

## 🎯 Next Steps for Users
1. Use the **🧹 Remove Visual Markers** tool before your final export.
2. Click **📤 Repackage Course (.imscc)** to generate your updated course file.
3. Import into a test course in Canvas to verify your accessible content!
