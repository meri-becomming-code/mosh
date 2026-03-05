import PyInstaller.__main__
import os
import sys


def build():
    # Detect OS
    is_windows = sys.platform.startswith("win")
    sep = ";" if is_windows else ":"

    # Define Data Files (Guides, etc.)
    # Format: "source_path:dest_path" (Unix) or "source_path;dest_path" (Windows)
    datas = [
        f"GUIDE_STYLES.md{sep}.",
        f"GUIDE_COMMON_MISTAKES.md{sep}.",
        f"GUIDE_MANUAL_FIXES.md{sep}.",
        f"POPPLER_GUIDE.md{sep}.",
        f"mosh_pilot.png{sep}.",
    ]

    args = [
        "toolkit_gui.py",
        "--name=MOSH_ADA_Toolkit_v1.0.0_RC73",
        "--noconfirm",
        "--onefile",
        "--windowed",  # No console window
        "--clean",
    ]

    # Add data files
    for d in datas:
        args.append(f"--add-data={d}")

    # Hidden imports if needed
    args.append("--hidden-import=bs4")
    args.append("--hidden-import=interactive_fixer")
    args.append("--hidden-import=run_fixer")
    args.append("--hidden-import=run_audit")
    args.append("--hidden-import=audit_reporter")  # [NEW]
    args.append("--hidden-import=attribution_checker")  # [NEW]
    args.append("--hidden-import=canvas_utils")
    args.append("--hidden-import=converter_utils")  # [NEW]
    args.append("--hidden-import=math_converter")  # [NEW]
    args.append("--hidden-import=requests")
    args.append("--hidden-import=jeanie_ai")
    args.append("--hidden-import=google")
    args.append("--hidden-import=google.genai")
    args.append("--collect-all=google.genai")
    args.append("--copy-metadata=google-genai")
    args.append("--hidden-import=darkdetect")  # [NEW]
    args.append("--hidden-import=pdf2image")  # [NEW]

    # GUI refactoring - new packages
    args.append("--hidden-import=gui")
    args.append("--hidden-import=gui.base_view")
    args.append("--hidden-import=gui.views")
    args.append("--hidden-import=gui.views.dashboard_view")
    args.append("--hidden-import=gui.dialogs")
    args.append("--hidden-import=gui.components")
    args.append("--hidden-import=gui.handler")  # [NEW]
    args.append("--hidden-import=gui.components.tooltips")  # [NEW]

    # PDF Processing Libraries
    args.append("--hidden-import=fitz")  # PyMuPDF
    args.append("--hidden-import=pymupdf")
    args.append("--hidden-import=pdfminer")
    args.append("--hidden-import=pdfminer.high_level")

    # Document Conversion Libraries
    args.append("--hidden-import=mammoth")
    args.append("--hidden-import=openpyxl")
    args.append("--hidden-import=pptx")
    args.append("--hidden-import=docx")

    # Exclude optional/dev-only modules to reduce false-positive missing-module warnings
    # in PyInstaller analysis output. These are not required for toolkit runtime features.
    excluded_modules = [
        # google-genai optional integrations
        "google.genai.live",
        "google.genai.tunings",
        "google.genai.replay_api_client",
        "mcp",
        "mcp.types",
        "IPython",
        "IPython.display",
        "aiohttp",
        "multidict",
        # optional async/network extras
        "trio",
        "trio.lowlevel",
        "trio.from_thread",
        "trio.to_thread",
        "trio.socket",
        "trio.testing",
        "outcome",
        "uvloop",
        "winloop",
        "h2",
        "h2.connection",
        "h2.events",
        "h2.config",
        "h2.exceptions",
        "h2.settings",
        "socks",
        "socksio",
        "python_socks",
        "python_socks.async_",
        "python_socks.sync",
        # CLI/dev tooling extras
        "rich",
        "rich.console",
        "rich.pretty",
        "rich.table",
        "rich.syntax",
        "rich.progress",
        "rich.markup",
        "click",
        "pygments",
        "pygments.util",
        "mypy",
        "mypy.version",
        "mypy.util",
        "mypy.typevars",
        "mypy.types",
        "mypy.server",
        "mypy.semanal",
        "mypy.plugins",
        "mypy.plugin",
        "mypy.options",
        "mypy.nodes",
        "mypy.typeops",
        "mypy.type_visitor",
        "mypy.state",
        "mypy.expandtype",
        "hypothesis",
        "toml",
        "yaml",
        "tornado",
        "tornado.concurrent",
        # optional parsing/compression extras
        "html5lib",
        "html5lib.treebuilders",
        "html5lib.constants",
        "lxml_html_clean",
        "cssselect",
        "brotli",
        "brotlicffi",
        "zstandard",
        # optional crypto/auth extras
        "OpenSSL",
        "OpenSSL.crypto",
        "rsa",
        "bcrypt",
        "pyu2f",
        "pyu2f.model",
        "pyu2f.errors",
        # optional data science helpers not used by the GUI
        "numpy",
        "pandas",
        "pygame",
    ]
    for mod in excluded_modules:
        args.append(f"--exclude-module={mod}")

    print("Building with PyInstaller...")
    PyInstaller.__main__.run(args)

    print("\nBuild Complete!")
    print(f"Check the 'dist' folder for the executable.")


if __name__ == "__main__":
    build()
