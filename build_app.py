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
    # 'google' is a namespace package (no __init__.py) split across user + system
    # site-packages. PyInstaller cannot auto-detect namespace packages reliably.
    # Solution:
    #   1. Create a temporary synthetic google/__init__.py so Python treats it as
    #      a regular package inside the frozen EXE.
    #   2. Manually add google/genai, google/auth, google/oauth2 via --add-data.
    #   3. Use custom hooks + a runtime hook to patch google.__path__.
    import site as _site, tempfile as _tempfile
    user_site = _site.getusersitepackages()

    # Custom hooks directory
    hooks_dir = os.path.join(project_root, "pyinstaller_hooks")
    if os.path.isdir(hooks_dir):
        args.append(f"--additional-hooks-dir={hooks_dir}")

    # Write a temporary __init__.py for the 'google' namespace shim
    google_shim_dir = os.path.join(_tempfile.gettempdir(), "mosh_google_shim", "google")
    os.makedirs(google_shim_dir, exist_ok=True)
    google_init = os.path.join(google_shim_dir, "__init__.py")
    with open(google_init, "w") as _f:
        _f.write("# Namespace package shim for PyInstaller\n__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n")

    # Add the shim __init__.py as google/__init__.py in the EXE
    args.append(f"--add-data={google_init}{sep}google")

    # Bundle google/genai, google/auth, google/oauth2 from user roaming site-packages
    for _pkg in ("genai", "auth", "oauth2"):
        _pkg_dir = os.path.join(user_site, "google", _pkg)
        if os.path.isdir(_pkg_dir):
            args.append(f"--add-data={_pkg_dir}{sep}google/{_pkg}")

    # Also check system site-packages as fallback for auth/oauth2
    try:
        sys_site = _site.getsitepackages()[0]
        for _pkg in ("auth", "oauth2"):
            _sys_pkg_dir = os.path.join(sys_site, "google", _pkg)
            _user_pkg_dir = os.path.join(user_site, "google", _pkg)
            if os.path.isdir(_sys_pkg_dir) and not os.path.isdir(_user_pkg_dir):
                args.append(f"--add-data={_sys_pkg_dir}{sep}google/{_pkg}")
    except Exception:
        pass

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

    # Runtime hook: patches google.__path__ inside frozen EXE so that
    # 'import google.genai' resolves to the data files we bundled above.
    rthook = os.path.join(project_root, "rthook_google_ns.py")
    if os.path.isfile(rthook):
        args.append(f"--runtime-hook={rthook}")
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
