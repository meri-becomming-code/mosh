import PyInstaller.__main__
import os
import sys

def build():
    # Detect OS
    is_windows = sys.platform.startswith('win')
    sep = ';' if is_windows else ':'
    
    # Define Data Files (Guides, etc.)
    # Format: "source_path:dest_path" (Unix) or "source_path;dest_path" (Windows)
    datas = [
        f"GUIDE_STYLES.md{sep}.",
        f"GUIDE_COMMON_MISTAKES.md{sep}.",
        f"GUIDE_MANUAL_FIXES.md{sep}.",
        f"POPPLER_GUIDE.md{sep}.",
        f"mosh_pilot.png{sep}."
    ]

    args = [
        'toolkit_gui.py',
        '--name=MOSH_ADA_Toolkit',
        '--noconfirm',
        '--onefile',
        '--windowed',  # No console window
        '--clean',
    ]

    # Add data files
    for d in datas:
        args.append(f'--add-data={d}')

    # Hidden imports if needed
    args.append('--hidden-import=bs4')
    args.append('--hidden-import=interactive_fixer')
    args.append('--hidden-import=run_fixer')
    args.append('--hidden-import=run_audit')
    args.append('--hidden-import=canvas_utils')
    args.append('--hidden-import=requests')
    args.append('--hidden-import=jeanie_ai')
    args.append('--hidden-import=google')
    args.append('--hidden-import=google.genai')
    
    # PDF Processing Libraries
    args.append('--hidden-import=fitz')  # PyMuPDF
    args.append('--hidden-import=pymupdf')
    args.append('--hidden-import=pdfminer')
    args.append('--hidden-import=pdfminer.high_level')
    
    # Document Conversion Libraries
    args.append('--hidden-import=mammoth')
    args.append('--hidden-import=openpyxl')
    args.append('--hidden-import=pptx')
    args.append('--hidden-import=docx')

    print("Building with PyInstaller...")
    PyInstaller.__main__.run(args)
    
    print("\nBuild Complete!")
    print(f"Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    build()
