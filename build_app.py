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
        f"GUIDE_MANUAL_FIXES.md{sep}."
    ]

    args = [
        'toolkit_gui.py',
        '--name=MCC_ADA_Toolkit',
        '--noconfirm',
        '--onefile',
        '--windowed',  # No console window
        '--clean',
    ]

    # Add data files
    for d in datas:
        args.append(f'--add-data={d}')

    # Hidden imports if needed (bs4 is usually found, but just in case)
    args.append('--hidden-import=bs4')
    args.append('--hidden-import=interactive_fixer')
    args.append('--hidden-import=run_fixer')
    args.append('--hidden-import=run_audit')

    print("Building with PyInstaller...")
    PyInstaller.__main__.run(args)
    
    print("\nBuild Complete!")
    print(f"Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    build()
