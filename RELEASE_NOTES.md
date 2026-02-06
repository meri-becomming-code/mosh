# MOSH ADA Toolkit - Release Notes (v1.1)

This release focuses on automation and improved visual fidelity for course remediation.

## 🚀 New Features
- **✨ Full Automation**: The toolkit now **automatically** removes all red `[ADA FIX]` labels and `[FIX_ME]` tags at the end of the Auto-Fix and Batch conversion processes. No manual cleanup button required!
- **📸 Smart Image Alignment**: 
    - **Word & PDF**: Images now retain their natural sizing and positioning using CSS floats.
    - **PowerPoint**: Enhanced alignment detection (left, right, or center) ensuring lecture notes follow the original slide layout.
- **🛠️ Table Structure Sanitizer**: Automatically fixes "Invalid Table Structure" errors in Canvas by cleaning up out-of-order tags and empty content.
- **🔄 Sync-on-Convert**: Individual conversion buttons (Word, PPT, PDF) now automatically synchronize with the `imsmanifest.xml` for seamless Canvas imports.

## 📦 Executable Updates
- A fresh **MOSH_ADA_Toolkit.exe** has been bundled in the `dist/` folder with all version 1.1 features and new dependencies (`PyMuPDF`, `python-docx`).
