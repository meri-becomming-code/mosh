import PyInstaller.__main__
import os
import sys
import shutil
import tempfile
import subprocess
import time


def build():
    # Detect OS
    is_windows = sys.platform.startswith("win")
    sep = ";" if is_windows else ":"
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Define Data Files (Guides, etc.)
    # Format: "source_path:dest_path" (Unix) or "source_path;dest_path" (Windows)
    datas = [
        f"{os.path.join(project_root, 'GUIDE_STYLES.md')}{sep}.",
        f"{os.path.join(project_root, 'GUIDE_COMMON_MISTAKES.md')}{sep}.",
        f"{os.path.join(project_root, 'GUIDE_MANUAL_FIXES.md')}{sep}.",
        f"{os.path.join(project_root, 'POPPLER_GUIDE.md')}{sep}.",
        f"{os.path.join(project_root, 'mosh_pilot.png')}{sep}.",
    ]

    # Build in a local, non-synced temp area to avoid OneDrive/AV file locks
    # during EXE resource updates (icon/manifest stamping).
    local_root = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
        "MOSH_build",
    )
    local_work = os.path.join(local_root, "build")
    local_dist = os.path.join(local_root, "dist")
    local_spec = os.path.join(local_root, "spec")
    os.makedirs(local_work, exist_ok=True)
    os.makedirs(local_dist, exist_ok=True)
    os.makedirs(local_spec, exist_ok=True)

    output_name = "MOSH_ADA_Toolkit_v1.0.0_RC73"

    # Pre-clean potentially locked prior outputs.
    local_exe = os.path.join(local_dist, f"{output_name}.exe")
    project_dist = os.path.join(project_root, "dist")
    project_exe = os.path.join(project_dist, f"{output_name}.exe")

    # If a previous EXE is running, stop it before resource-stamping phase.
    if is_windows:
        try:
            subprocess.run(
                ["taskkill", "/IM", f"{output_name}.exe", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            time.sleep(0.2)
        except Exception:
            pass

    for p in [local_exe, project_exe]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    args = [
        "toolkit_gui.py",
        f"--name={output_name}",
        "--noconfirm",
        "--onefile",
        "--windowed",  # No console window
        "--clean",
        "--log-level=ERROR",
        f"--icon={os.path.join(project_root, 'build_assets', 'mosh.ico')}",
        f"--workpath={local_work}",
        f"--distpath={local_dist}",
        f"--specpath={local_spec}",
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

    # --- google-genai: namespace package fix ---
    # google.genai lives in the user roaming site-packages. Because 'google' is a
    # namespace package (no __init__.py), PyInstaller's --collect-all can miss it.
    # We manually locate the package and add it with --add-data + hidden-imports.
    import site, importlib.util
    user_site = site.getusersitepackages()
    genai_pkg_dir = os.path.join(user_site, "google", "genai")
    if os.path.isdir(genai_pkg_dir):
        # Bundle the entire google/genai folder into google/genai inside the EXE
        args.append(f"--add-data={genai_pkg_dir}{sep}google/genai")
    else:
        # Fallback: let PyInstaller try to collect it normally
        args.append("--collect-all=google.genai")

    # Hidden imports for every known google.genai submodule
    for _mod in [
        "google", "google.genai", "google.genai.types", "google.genai.errors",
        "google.genai.client", "google.genai.models", "google.genai.chats",
        "google.genai.files", "google.genai.batches", "google.genai.caches",
        "google.genai.tokens", "google.genai.tunings", "google.genai.operations",
        "google.genai.pagers", "google.genai.live", "google.genai._api_client",
        "google.genai._transformers", "google.genai._common",
        "google.genai._extra_utils", "google.genai._adapters",
        "google.auth", "google.auth.transport", "google.auth.transport.requests",
        "google.oauth2", "google.oauth2.credentials",
    ]:
        args.append(f"--hidden-import={_mod}")

    args.append("--copy-metadata=google-genai")
    args.append("--copy-metadata=google-auth")
    # --- end google-genai fix ---
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
        # warning-only optional modules/hooks
        "pycparser.lextab",
        "pycparser.yacctab",
        "tzdata",
        "darkdetect._mac_detect",
        "mcp",
        "mcp.types",
        "IPython",
        "IPython.display",
        # optional async/network extras
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

    # Copy final exe back into the project dist folder for existing workflows.
    project_dist = os.path.join(os.getcwd(), "dist")
    os.makedirs(project_dist, exist_ok=True)
    built_exe = os.path.join(local_dist, f"{output_name}.exe")
    if os.path.exists(built_exe):
        shutil.copy2(built_exe, os.path.join(project_dist, f"{output_name}.exe"))

    print("\nBuild Complete!")
    print(f"Check the 'dist' folder for the executable.")


if __name__ == "__main__":
    build()
