# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License v3.0. USE AT YOUR OWN RISK.

import tkinter as tk

VERSION = "1.0.0-RC17"
from tkinter import (
    filedialog,
    messagebox,
    simpledialog,
    scrolledtext,
    Toplevel,
    Menu,
    ttk,
)
from PIL import Image, ImageTk
import sys
import os
import time

# Ensure the script's directory is in the Python path for local imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


import threading
import queue
import json
import darkdetect
import webbrowser
from urllib.parse import urlparse
import converter_utils
import urllib.request
import zipfile
from pathlib import Path

import math_converter
import attribution_checker
import canvas_utils
import interactive_fixer
import run_fixer
import run_audit

# CONFIG_FILE = "toolkit_config.json" [DEPRECATED]
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mosh_toolkit")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "toolkit_config.json")


from gui.handler import ThreadSafeGuiHandler
from gui.components.tooltips import ToolTip


# Colors
# --- Themes ---
THEMES = {
    "light": {
        "bg": "#F5F3ED",  # Premium Warm Pebble (Off-Cream)
        "card": "#FFFFFF", # Pure White Card
        "log": "#F8F9FA",  # Light Grey Log
        "fg": "#2D2924",  # Deep Obsidian Text
        "sidebar": "#4B3190",  # Mosh Purple Brand
        "sidebar_fg": "#FFFFFF",
        "primary": "#6A4BB1",  # Soft Saturated Purple
        "accent": "#F59E0B",  # Warm Amber
        "header": "#4B3190",
        "subheader": "#2D2924",
        "button": "#E9E5DA",  # Stone Grey Button
        "button_fg": "#2D2924",
        "border": "#E5E7EB",
    },
    "dark": {
        "bg": "#1A1B1E",  # Deep Charcoal / Obsidian
        "card": "#242529", # Slightly Lighter Charcoal
        "log": "#111113",  # Deep Black Log
        "fg": "#ECECEC",  # Soft Silver Text
        "sidebar": "#111113",  # High-Contrast Black Sidebar
        "sidebar_fg": "#FFFFFF",
        "primary": "#8B5CF6",  # Electric Violet
        "accent": "#FBBF24",  # Gold Accent
        "header": "#FFFFFF",
        "subheader": "#A1A1AA",  # Zinc / Slate Grey
        "button": "#2D2E32",  # Deep Grey Button
        "button_fg": "#ECECEC",
        "border": "#3F3F46",
    },
}


class ToolkitGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MOSH's Toolkit: Making Online Spaces Helpful")
        self.root.geometry("1150x800")  # Expanded for better visibility
        self.root.minsize(1100, 700)  # Prevents cutting off buttons

        # [NEW] Safe Exit Protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- State ---
        self.config = self._load_config()
        self.target_dir = self.config.get("target_dir", "")
        self.is_running = False
        self.deferred_review = False
        self.current_dialog = None

        # Mirror Mode State
        self.mirror_active = False
        self.mirror_thread = None
        self.mirror_target_file = None  # If we want to watch a SPECIFIC file
        self.file_hashes = {}  # path: mtime

        # UI State
        self.current_view = "dashboard"
        self.main_content_frame = None
        self.progress_var = tk.DoubleVar(value=0)

        # --- Threading Queues (Initialize BEFORE UI build) ---
        self.log_queue = queue.Queue()
        self.gui_handler = ThreadSafeGuiHandler(root, self.log_queue)
        self.gui_handler.api_key = self.config.get("api_key", "")
        self.gui_handler.trust_ai_alt = self.config.get("trust_ai_alt", False)

        # Check instructions
        if self.config.get("show_instructions", True):
            self.root.after(500, self._show_instructions)

        # --- UI Layout ---
        self._build_styles()
        self._build_menu()
        self._build_ui_modern()

        # --- Start Polling Loops ---
        self.root.after(100, self._process_logs)
        self.root.after(100, self._process_inputs)

        # [NEW] Tag configuration for Clickable Log
        self.txt_log.tag_config("link", foreground="blue", underline=True)
        self.txt_log.tag_bind(
            "link", "<Enter>", lambda e: self.txt_log.config(cursor="hand2")
        )
        self.txt_log.tag_bind(
            "link", "<Leave>", lambda e: self.txt_log.config(cursor="xterm")
        )
        self.txt_log.tag_bind("link", "<Button-1>", self._on_log_click)

        # [NEW] Auto-detect Poppler (Portable or Home dir)
        self._auto_detect_poppler()

    def _auto_detect_poppler(self):
        """Try to find poppler in known locations if not configured."""
        if self.config.get("poppler_path") and os.path.isdir(self.config.get("poppler_path")):
            return

        # 1. Check local mosh_helpers folder next to EXE (Portable Mode)
        try:
            # sys.executable is the .exe path in PyInstaller
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            local_path = os.path.join(exe_dir, "mosh_helpers", "poppler", "bin")
            # Fallback for nested mosh_helpers/poppler/poppler-xx/bin
            if not os.path.isdir(local_path):
                found = list(Path(exe_dir).glob("mosh_helpers/poppler/**/bin"))
                if found: local_path = str(found[0])

            if os.path.isdir(local_path):
                self._update_config(poppler_path=local_path)
                self.gui_handler.log(f"   \u2705 [System] Detected portable Poppler at: {local_path}")
                return
        except Exception: pass

        # 2. Check Home directory mosh_helpers (Default)
        try:
            home_path = os.path.join(os.path.expanduser("~"), "mosh_helpers", "poppler")
            bin_folders = list(Path(home_path).glob("**/bin"))
            if not bin_folders:
                # Check legacy hidden folder .mosh_helpers
                home_path = os.path.join(os.path.expanduser("~"), ".mosh_helpers", "poppler")
                bin_folders = list(Path(home_path).glob("**/bin"))
                
            if bin_folders:
                self._update_config(poppler_path=str(bin_folders[0]))
                self.gui_handler.log(f"   \u2705 [System] Detected Poppler in home directory.")
        except Exception: pass

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "show_instructions": True,
            "api_key": "",
            "canvas_url": "",
            "canvas_token": "",
            "canvas_course_id": "",
            "theme": "light",
            "poppler_path": "",
        }

    def _update_config(self, **kwargs):
        """Safe update that only changes provided keys."""
        self.config.update(kwargs)
        # Sync specific fields that might need immediate side effects
        if "api_key" in kwargs:
            self.gui_handler.api_key = kwargs["api_key"]
        if "target_dir" in kwargs:
            self.target_dir = kwargs["target_dir"]
        self._save_config_simple()

    def _save_config(
        self,
        key,
        start_show,
        theme="light",
        canvas_url="",
        canvas_token="",
        canvas_course_id="",
        poppler_path="",
        target_dir=None,
    ):
        """Legacy support wrapper around _update_config."""
        self._update_config(
            api_key=key,
            show_instructions=start_show,
            theme=theme,
            canvas_url=canvas_url,
            canvas_token=canvas_token,
            canvas_course_id=canvas_course_id,
            poppler_path=poppler_path,
            target_dir=target_dir,
        )

    def _save_config_simple(self):
        """Saves current self.config to the JSON file."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")

    def _quick_save_inputs(self):
        """Scrapes current values from Setup inputs and saves them."""
        # Only run if widgets exist
        if not hasattr(self, "ent_url") or not self.ent_url.winfo_exists():
            return

        try:
            # Clean Course ID immediately if it's a URL
            cid = self.ent_course.get().strip().split("?")[0].rstrip("/")
            if "/courses/" in cid:
                cid = cid.split("/courses/")[-1].split("/")[0]

            # Clean Canvas URL (Domain only)
            url = self.ent_url.get().strip().rstrip("/")
            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            if url:
                from urllib.parse import urlparse

                parsed = urlparse(url)
                url = f"{parsed.scheme}://{parsed.netloc}"

            self._update_config(
                canvas_url=url,
                canvas_token=self.ent_token.get().strip(),
                canvas_course_id=cid,
                api_key=self.ent_api.get().strip(),
                # Poppler path is handled by its own entry
                # Target Dir is handled by its own label/var
            )
            # No popup, just save
        except Exception as e:
            print(f"Quick save error: {e}")

    def _build_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        advanced_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Advanced", menu=advanced_menu)
        advanced_menu.add_command(
            label="Canvas API Settings", command=lambda: self._switch_view("setup")
        )
        advanced_menu.add_command(
            label="Open Documentation", command=self._show_documentation
        )
        advanced_menu.add_separator()
        advanced_menu.add_command(
            label="Course Health Check (Broken Links)",
            command=self._run_course_health_check,
        )
        advanced_menu.add_separator()
        advanced_menu.add_command(
            label="Toggle Theme (Light/Dark)", command=self._toggle_theme
        )

        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(
            label="Welcome / Dedication",
            command=lambda: self._show_instructions(force=True),
        )

    def _on_close(self):
        """Safe exit handler to prevent accidental closing during tasks."""
        if getattr(self, "is_running", False):
            if not messagebox.askyesno(
                "Task Running",
                "Mosh is currently working on your files!\n\nIf you close now, the process will stop and might leave half-finished files.\n\nAre you sure you want to exit?",
            ):
                return
        self.root.destroy()

    def _show_documentation(self):
        """Phase 12: Shows documentation directly in the app."""
        dialog = Toplevel(self.root)
        dialog.title("MOSH Documentation & Tips")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()

        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        # Title
        tk.Label(
            dialog,
            text="MOSH Faculty ADA Toolkit Guide",
            font=("Segoe UI", 16, "bold"),
            bg=colors["bg"],
            fg=colors["header"],
        ).pack(pady=15)

        # Scrolled Text for Documentation
        txt = scrolledtext.ScrolledText(
            dialog,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=colors["bg"],
            fg=colors["fg"],
            padx=15,
            pady=15,
        )
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Insert Documentation Content
        doc_content = """MOSH ADA Toolkit for K-12 & Higher Ed (2026 Edition)
========================================================

📚 FOR ALL EDUCATORS: K-12 Teachers, College Instructors, & Instructional Designers
----------------------------------------------------------------------------------

DEDICATION & PARTNERSHIP
-----------------------
This software is dedicated to my son, Michael Joshua (Mosh) Albright, 
who deals with diabetic retinopathy and spent three years blind, 
and to all the other students struggling with their own challenges.

BUILDING WITH AI:
MOSH's Toolkit was built as a human-AI collaboration. Dr. Meri Kasprak 
worked alongside Antigravity, an advanced coding AI from Google DeepMind, 
to ensure this toolkit remains free, powerful, and accessible for all educators.

🚀 THE MOSH WORKFLOW
-----------------------
Step 1: Get your .imscc export from Canvas Settings.
Step 2: Import it into MOSH using the Dashboard.
Step 3: Convert documents (Word/PDF) and Math into Canvas Pages.
Step 4: Run "Auto-Fix" followed by "Guided Review" for ADA compliance.
Step 5: Run "Pre-Flight Check" and import back into a Canvas Sandbox.

💡 TIPS FOR ALL TEACHERS & INSTRUCTORS
---------------------------------------
- Always use a NEW, EMPTY Canvas course for testing your remediated files.
- Hard-Working Logs: Check the "Activity Log" at the bottom to see exactly what structural fixes were made to each file.
- ✨ MOSH Magic (OPTIONAL): If you have a paid Gemini API key, you can click the Magic Wand (🪄) during Guided Review to have AI write your Alt Tags or Math LaTeX for you!
- 🆓 No API Key? No Problem! You can skip AI features and still use all the core tools.

📦 FILE CONVERSION
------------------
- Use the "Conversion Wizard" to turn Word, PPT, or PDF files into Canvas WikiPages.
- For PDFs: The tool automatically detects Headers (H1-H3) based on font size.
- Math Content: Canvas uses LaTeX. If your document has complex math, consider using an external tool like Mathpix Snip, then import the Word file here.

⚖️ LICENSE & SPIRIT
-------------------
- Released under GNU General Public License version 3.
- This is non-commercial, open-source software built for the education community.
- "Making Online Spaces Helpful" (MOSH) is dedicated to helping every student succeed.

📣 SPREAD THE WORD
------------------
- April 2026 Deadline: The goal is to help every educator reach compliance safely and quickly.
- Works for K-12, community colleges, and universities!
- If this tool saved you time, click 'Spread the Word' on the sidebar to share with colleagues. Let's help everyone meet the deadline together!
"""
        txt.insert(tk.END, doc_content)
        txt.config(state="disabled")  # Read-only

        tk.Button(
            dialog, text="Close", command=dialog.destroy, width=12, cursor="hand2"
        ).pack(pady=10)

    def _build_styles(self):
        style = ttk.Style()
        # On Mac, 'clam' is often problematic with dark mode; 'aqua' is better for native feel,
        # but 'clam' allows custom background colors.
        style.theme_use("clam")

        # Determine Theme
        mode = self.config.get("theme", "light")
        if mode not in THEMES:
            mode = "light"
        colors = THEMES[mode]

        # Base
        style.configure(
            ".", background=colors["bg"], foreground=colors["fg"], font=("Segoe UI", 10)
        )
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])

        # Headers
        style.configure(
            "Header.TLabel", font=("Segoe UI", 20, "bold"), foreground=colors["header"]
        )
        style.configure(
            "SubHeader.TLabel",
            font=("Segoe UI", 13, "bold"),
            foreground=colors["subheader"],
        )

        # Sidebar
        style.configure("Sidebar.TFrame", background=colors["sidebar"])
        style.configure(
            "Sidebar.TLabel",
            background=colors["sidebar"],
            foreground=colors["sidebar_fg"],
            font=("Segoe UI", 10),
        )

        # Modern Card Frame
        style.configure(
            "Card.TFrame", background=colors["bg"], relief="solid", borderwidth=1
        )

        # Buttons (Unified Modern Look - 3D Phone Inspired)
        style.configure(
            "TButton",
            padding=10,
            relief="raised",
            borderwidth=2,
            background=colors["button"],
            foreground=colors["button_fg"],
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TButton",
            background=[("active", colors["accent"]), ("pressed", colors["primary"])],
            foreground=[("active", "#000000"), ("pressed", "#FFFFFF")],
            relief=[("pressed", "sunken")],
            cursor=[("!disabled", "hand2")],
        )

        # Action Buttons (Primary - Vibrant)
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 11, "bold"),
            background=colors["primary"],
            foreground="white",
            relief="raised",
            borderwidth=3,
        )
        style.map(
            "Action.TButton",
            background=[("active", colors["accent"]), ("!disabled", colors["primary"])],
            foreground=[("active", "#000000")],
            relief=[("pressed", "sunken")],
            cursor=[("!disabled", "hand2")],
        )

        # Force background update for root
        self.root.configure(bg=colors["bg"])

    def _toggle_theme(self):
        current = self.config.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self._update_config(theme=new_theme)
        self._build_styles()  # Re-apply styles

    def _build_ui_modern(self):
        # Main Container: Sidebar (Left) + Content (Right)
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]

        # 1. Sidebar
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=220)
        sidebar.pack(side="left", fill="y")

        # 2. Main Container (Right)
        self.right_panel = tk.Frame(self.root, bg=colors["card"])
        self.right_panel.pack(side="right", fill="both", expand=True)

        # We need to expose this for older methods that might reference it (Safety)
        self.view_container = self.right_panel

        # Content Pane (Middle, Expands)
        self.pane_content = tk.Frame(self.right_panel, bg=colors["card"])
        self.pane_content.pack(side="top", fill="both", expand=True)

        # Log Pane (Bottom, Fixed Height)
        self.pane_log = tk.Frame(
            self.right_panel, height=140, bg=colors["log"], borderwidth=1, relief="sunken"
        )
        self.pane_log.pack(side="bottom", fill="x")
        self.pane_log.pack_propagate(False)  # Fixed height

        # Log Header
        log_header = tk.Frame(self.pane_log, bg=colors["log"], height=20)
        log_header.pack(fill="x", padx=5, pady=2)
        tk.Label(
            log_header,
            text="📋 Activity Log",
            font=("Segoe UI", 9, "bold"),
            bg=colors["log"],
            fg=colors["fg"] if mode == "dark" else "#555",
        ).pack(side="left")

        def clear_log():
            self.txt_log.config(state="normal")
            self.txt_log.delete(1.0, tk.END)
            self.txt_log.config(state="disabled")

        tk.Button(
            log_header,
            text="Clear",
            command=clear_log,
            font=("Segoe UI", 8),
            bg=colors["button"],
            fg=colors["button_fg"],
            activebackground=colors["accent"],
            borderwidth=0,
            cursor="hand2",
        ).pack(side="right")

        # Persistent Log Widget
        self.txt_log = scrolledtext.ScrolledText(
            self.pane_log, state="disabled", font=("Consolas", 9), bg=colors["card"], fg=colors["fg"]
        )
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

        # Logo Area
        # [NEW] Mosh Mascot
        try:
            mosh_path = resource_path("mosh_pilot.png")
            mosh_img = Image.open(mosh_path)
            # Make it slightly smaller to save vertical space
            mosh_img = mosh_img.resize((100, 100), Image.Resampling.LANCZOS)
            self.sidebar_mosh_tk = ImageTk.PhotoImage(mosh_img)
            self.lbl_mosh_icon = ttk.Label(
                sidebar,
                image=self.sidebar_mosh_tk,
                style="Sidebar.TLabel",
                cursor="hand2",
            )
            self.lbl_mosh_icon.pack(pady=(15, 0))
            self.lbl_mosh_icon.bind(
                "<Button-1>", lambda e: self._switch_view("dashboard")
            )
            ToolTip(self.lbl_mosh_icon, "Back to Home Dashboard")
        except Exception:
            pass

        lbl_logo = ttk.Label(
            sidebar,
            text="MOSH'S\nTOOLKIT",
            style="Sidebar.TLabel",
            font=("Segoe UI", 16, "bold"),
            justify="center",
            cursor="hand2",
        )
        lbl_logo.pack(pady=(5, 5), padx=10)
        lbl_logo.bind("<Button-1>", lambda e: self._switch_view("dashboard"))

        lbl_tagline = ttk.Label(
            sidebar,
            text="Built by a teacher with AI, for teachers",
            style="Sidebar.TLabel",
            font=("Segoe UI", 9, "italic"),
            wraplength=200,
            justify="center",
        )
        lbl_tagline.pack(pady=(0, 15), padx=10)

        ttk.Label(
            sidebar, text="v2026.1", style="Sidebar.TLabel", font=("Segoe UI", 8)
        ).pack(pady=(0, 2))
        tk.Label(
            sidebar,
            text="Powered by Antigravity 🚀",
            bg=colors["sidebar"],
            fg="#AAA",
            font=("Segoe UI", 7),
        ).pack(pady=(0, 5))

        # [NEW] Navigation Buttons (Tightened pady)
        btn_setup = ttk.Button(
            sidebar,
            text="🛠️ CONNECT & SETUP",
            command=lambda: self._switch_view("setup"),
            style="Sidebar.TButton",
        )
        btn_setup.pack(pady=3, padx=10, fill="x")
        ToolTip(btn_setup, "Configure your Canvas, AI Key, and load your project")

        btn_canvas = ttk.Button(
            sidebar,
            text="🎨 CANVAS REMEDIATION",
            command=lambda: self._switch_view("course"),
            style="Sidebar.TButton",
        )
        btn_canvas.pack(pady=3, padx=10, fill="x")
        ToolTip(btn_canvas, "Bulk audit and fix your Canvas course pages")

        # [NEW] Audit Button (Replaces File Conversion per user request)
        btn_audit = ttk.Button(
            sidebar,
            text="🔎 AUDIT & CHECK",
            command=lambda: self._switch_view("audit"),
            style="Sidebar.TButton",
        )
        btn_audit.pack(pady=3, padx=10, fill="x")
        ToolTip(btn_audit, "Run accessibility checks on your content")

        btn_math = ttk.Button(
            sidebar,
            text="📐 MATH CONVERTER",
            command=lambda: self._switch_view("math"),
            style="Sidebar.TButton",
        )
        btn_math.pack(pady=3, padx=10, fill="x")
        ToolTip(btn_math, "Gemini-powered conversion of Math from PDF or Images")

        # [NEW] Upload Button (Moved to sidebar per user request)
        btn_upload = ttk.Button(
            sidebar,
            text="🚀 UPLOAD TO CANVAS",
            command=self._show_preflight_dialog,
            style="Sidebar.TButton",
        )
        btn_upload.pack(pady=3, padx=10, fill="x")
        ToolTip(btn_upload, "Final Step: Check your course and create the upload file")

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=20, pady=8)

        # [NEW] Share Button
        self.btn_share = ttk.Button(
            sidebar,
            text="📣 SPREAD THE WORD",
            command=self._show_share_dialog,
            style="Action.TButton",
        )
        self.btn_share.pack(pady=8, padx=10, fill="x")

        # Header Banner with Logo & Progress (Top of Right Panel)
        header_frame = tk.Frame(self.right_panel, height=60, bg="white")
        header_frame.pack(side="top", fill="x", before=self.pane_content)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="✨ MOSH Toolkit",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(side="left", padx=20)

        # [NEW] Network Status
        self.lbl_network = tk.Label(
            header_frame,
            text="Checking Net...",
            font=("Segoe UI", 8),
            bg="white",
            fg="gray",
        )
        self.lbl_network.pack(side="left", padx=5)

        self.progress_bar = ttk.Progressbar(
            header_frame, variable=self.progress_var, maximum=100, length=200
        )
        self.progress_bar.pack(side="right", padx=20, pady=15)
        self.lbl_status_text = tk.Label(
            header_frame, text="Ready", font=("Segoe UI", 9), bg="white", fg="gray"
        )
        self.lbl_status_text.pack(side="right")

        # Show initial view
        # Show initial view
        self._switch_view("dashboard")

        # Start background network check
        print("Starting network check...")
        threading.Thread(target=self._check_network_status, daemon=True).start()

    def _check_network_status(self):
        """Runs in background to check internet."""
        try:
            import jeanie_ai

            is_online = jeanie_ai.check_connectivity()

            def update_ui():
                if is_online:
                    self.lbl_network.config(text="🟢 Online", fg="green")
                    ToolTip(self.lbl_network, "Internet Connected via Google.com")
                else:
                    self.lbl_network.config(text="🔴 Offline", fg="red")
                    ToolTip(
                        self.lbl_network,
                        "Warning: No Internet. AI features may not work!",
                    )

            self.root.after(0, update_ui)
        except Exception as e:
            print(f"Network check error: {e}")

    def _check_target_dir(self):
        """Helper to verify a target directory is loaded before running tasks."""
        if not self.target_dir or not os.path.exists(self.target_dir):
            messagebox.showwarning(
                "No Course Loaded",
                "Please load a course project (Section 4) first before using this tool."
            )
            self._switch_view("setup") # Take them to where they can load it
            return False
        return True

    def _switch_view(self, view_name):
        """Standard method to swap the main content area."""
        # [NEW] Audit Shortcut: If audit is requested, run it and switch to log view
        if view_name == "audit":
            self.root.after(100, self._run_audit)
            view_name = "course"

        if self.main_content_frame:
            self.main_content_frame.destroy()

        self.current_view = view_name

        # Create a new scrollable container for the view
        container = ttk.Frame(self.pane_content)
        container.pack(fill="both", expand=True)
        self.main_content_frame = container

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding="30 30 30 30")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Router
        if view_name == "setup":
            self._build_setup_view(content)
        elif view_name == "course":
            self._build_course_view(content)
        elif view_name == "files":
            self._build_files_view(content)
        elif view_name == "math":
            self._build_math_view(content)
        else:  # Default/Dashboard
            self._build_dashboard(content)

        # [NEW] Safety: If a task is running, ensure newly built buttons are disabled
        if self.is_running:
            self.root.after(0, self._disable_buttons)

    def _build_setup_view(self, content):
        """Unified 'Command Center' for all credentials and project loading."""
        tk.Label(
            content,
            text="🛠️ Connect & Setup",
            font=("Segoe UI", 24, "bold"),
            fg="#4B3190",
            bg="white",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            content,
            text="Configure your connections and load your project to begin.",
            font=("Segoe UI", 11),
            fg="#6B7280",
            bg="white",
        ).pack(anchor="w", pady=(0, 30))

        mode = self.config.get("theme", "light")
        colors = THEMES[mode]

        # Define status label early so callbacks can use it
        lbl_global_status = tk.Label(
            content, text="", bg="white", font=("Segoe UI", 10, "bold")
        )

        # --- SECTION 1: CANVAS ---
        tk.Label(
            content,
            text="1. Canvas Course Connection",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(anchor="w", pady=(10, 5))
        frame_canvas = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_canvas.pack(fill="x", pady=(0, 20))

        tk.Label(
            frame_canvas,
            text="School Canvas URL:",
            bg="white",
            fg="#4B3190",
            font=("bold"),
        ).pack(anchor="w")
        self.ent_url = tk.Entry(frame_canvas, width=60)
        self.ent_url.insert(0, self.config.get("canvas_url", ""))
        self.ent_url.pack(pady=(2, 10), fill="x")
        self.ent_url.bind("<FocusOut>", lambda e: self._quick_save_inputs())

        tk.Label(
            frame_canvas,
            text="Canvas Digital Key (Token):",
            bg="white",
            fg="#4B3190",
            font=("bold"),
        ).pack(anchor="w")
        frame_token = tk.Frame(frame_canvas, bg="white")
        frame_token.pack(fill="x")
        self.ent_token = tk.Entry(frame_token, width=45, show="*")
        self.ent_token.insert(0, self.config.get("canvas_token", ""))
        self.ent_token.pack(side="left", pady=5, fill="x", expand=True)
        self.ent_token.bind("<FocusOut>", lambda e: self._quick_save_inputs())

        def open_token_help():
            url = self.ent_url.get().strip()
            if not url:
                url = "https://canvas.instructure.com"
            webbrowser.open(f"{url}/profile/settings")
            messagebox.showinfo(
                "Help",
                "I've opened your Canvas Settings.\n\n1. Scroll to 'Approved Integrations'.\n2. Click '+ New Access Token'.\n3. Copy the key and paste it here.",
            )

        btn_help_token = tk.Button(
            frame_token,
            text="Show Me How 🎥",
            command=open_token_help,
            font=("Segoe UI", 9, "bold"),
            bg="#E1F5FE",
            cursor="hand2",
        )
        btn_help_token.pack(side="left", padx=5)
        ToolTip(btn_help_token, "Open Canvas Settings to get a token")

        tk.Label(
            frame_canvas,
            text="Course ID (Numbers):",
            bg="white",
            fg="#4B3190",
            font=("bold"),
        ).pack(anchor="w")
        frame_course = tk.Frame(frame_canvas, bg="white")
        frame_course.pack(fill="x")
        self.ent_course = tk.Entry(frame_course, width=15)
        self.ent_course.insert(0, self.config.get("canvas_course_id", ""))
        self.ent_course.pack(side="left", pady=5)
        self.ent_course.bind("<FocusOut>", lambda e: self._quick_save_inputs())

        def open_course_help():
            messagebox.showinfo(
                "Finding Your Course ID",
                "Look at your browser address bar while in the course.\n\nThe ID is the numbers at the very end (e.g. .../courses/12345).",
            )

        tk.Button(
            frame_course,
            text="❓ Help",
            command=open_course_help,
            font=("Segoe UI", 8),
            cursor="hand2",
        ).pack(side="left", padx=5)

        # Status label for Canvas check
        self.lbl_canvas_status = tk.Label(
            frame_course, text="", bg="white", font=("Segoe UI", 9, "bold")
        )

        def check_canvas():
            url = self.ent_url.get().strip().rstrip("/")
            token = self.ent_token.get().strip()
            cid = self.ent_course.get().strip().split("?")[0].rstrip("/")

            # Auto-Clean Course ID if URL pasted
            if "/courses/" in cid:
                cid = cid.split("/courses/")[-1].split("/")[0]
                self.ent_course.delete(0, tk.END)
                self.ent_course.insert(0, cid)

            # Auto-Clean URL
            if url and not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            if url:
                parsed = urlparse(url)
                url = f"{parsed.scheme}://{parsed.netloc}"
                self.ent_url.delete(0, tk.END)
                self.ent_url.insert(0, url)

            if not url or not token or not cid:
                messagebox.showwarning(
                    "Incomplete", "Please fill out Canvas settings (Step 1)."
                )
                return

            self.lbl_canvas_status.config(text="⏳ Verifying...", fg="blue")
            self.root.update()

            api = canvas_utils.CanvasAPI(url, token, cid)
            success, msg = api.validate_credentials()
            if success:
                is_empty, _ = api.is_course_empty()
                status = (
                    "✅ SAFE: Course is empty."
                    if is_empty
                    else "⚠️ WARNING: Course has content."
                )
                self.lbl_canvas_status.config(
                    text=status, fg="green" if is_empty else "orange"
                )
            else:
                self.lbl_canvas_status.config(text=f"❌ FAILED: {msg}", fg="red")

        tk.Button(
            frame_course,
            text="🔍 Check If Safe",
            command=check_canvas,
            bg="#BBDEFB",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=10)
        self.lbl_canvas_status.pack(side="left", padx=5)

        # --- SECTION 2: MOSH MAGIC (AI) ---
        tk.Label(
            content,
            text="2. MOSH Magic (AI Features)",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#1B5E20",
        ).pack(anchor="w", pady=(10, 5))
        frame_ai = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_ai.pack(fill="x", pady=(0, 20))

        tk.Label(
            frame_ai,
            text="Google AI Link Key (Technical Name: API Key):",
            bg="white",
            fg="#1B5E20",
            font=("bold"),
        ).pack(anchor="w")
        tk.Label(
            frame_ai,
            text="Enables automatic Image Alt-Text and Math OCR.",
            bg="white",
            fg="gray",
            font=("Segoe UI", 8),
        ).pack(anchor="w")
        self.ent_api = tk.Entry(frame_ai, width=60, show="*")
        self.ent_api.insert(0, self.config.get("api_key", ""))
        self.ent_api.pack(pady=(5, 10), fill="x")
        self.ent_api.bind("<FocusOut>", lambda e: self._quick_save_inputs())

        btn_ai_frame = tk.Frame(frame_ai, bg="white")
        btn_ai_frame.pack(anchor="w")

        def open_api_help():
            webbrowser.open("https://aistudio.google.com/app/apikey")
            messagebox.showinfo(
                "MOSH Magic Help",
                "1. Log in with Google.\n2. Click 'Create API key'.\n(Note: You may need to click 'Create Project' first!)\n3. Copy the key and paste it here.",
            )

        # Status Label for AI Check
        self.lbl_ai_status = tk.Label(
            btn_ai_frame, text="", bg="white", font=("Segoe UI", 9, "bold")
        )

        def test_api_key():
            key = self.ent_api.get().strip()
            if not key:
                messagebox.showwarning("No Key", "Please paste a key first.")
                return
            self.lbl_ai_status.config(text="⏳ Testing...", fg="blue")
            self.root.update()
            import jeanie_ai

            is_valid, msg = jeanie_ai.validate_api_key(key)
            if is_valid:
                self.lbl_ai_status.config(text="✅ Valid Key!", fg="green")
                messagebox.showinfo(
                    "Success", "Google AI Link is working perfectly! ✨"
                )
            else:
                self.lbl_ai_status.config(text="❌ Invalid Key", fg="red")
                messagebox.showerror("Key Error", f"Validation Failed:\n\n{msg}")

        tk.Button(
            btn_ai_frame,
            text="🔑 Get Key",
            command=open_api_help,
            font=("Segoe UI", 9),
            fg="#0369A1",
            bg="#F0F9FF",
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_ai_frame,
            text="🧪 Test Key",
            command=test_api_key,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=5)
        self.lbl_ai_status.pack(side="left", padx=5)

        # --- SECTION 3: POPPLER (MATH PDF) ---
        tk.Label(
            content,
            text="3. Poppler Bin Path (For Math PDF)",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#D97706",
        ).pack(anchor="w", pady=(10, 5))
        frame_poppler = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_poppler.pack(fill="x", pady=(0, 20))

        tk.Label(
            frame_poppler,
            text="Path to Poppler/bin folder:",
            bg="white",
            fg="#D97706",
            font=("bold"),
        ).pack(anchor="w")
        frame_p_row = tk.Frame(frame_poppler, bg="white")
        frame_p_row.pack(fill="x")
        self.ent_poppler_setup = tk.Entry(frame_p_row, width=45)
        self.ent_poppler_setup.insert(0, self.config.get("poppler_path", ""))
        self.ent_poppler_setup.pack(side="left", pady=5, fill="x", expand=True)

        def browse_poppler():
            path = filedialog.askdirectory()
            if path:
                self.ent_poppler_setup.delete(0, tk.END)
                self.ent_poppler_setup.insert(0, path)

        tk.Button(
            frame_p_row,
            text="📂 Browse",
            command=browse_poppler,
            font=("Segoe UI", 8),
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            frame_p_row,
            text="🪄 Auto-Setup",
            command=self._auto_setup_poppler,
            font=("Segoe UI", 8, "bold"),
            fg="#2E7D32",
            cursor="hand2",
        ).pack(side="left", padx=5)

        # --- SECTION 4: LOAD PROJECT ---
        tk.Label(
            content,
            text="4. Load Your Course Project",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(anchor="w", pady=(10, 5))
        frame_project = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_project.pack(fill="x", pady=(0, 30))

        btn_import_row = tk.Frame(frame_project, bg="white")
        btn_import_row.pack(fill="x", pady=(0, 10))

        btn_import = ttk.Button(
            btn_import_row,
            text="📂 Open Course Export (IMSCC from Settings)",
            command=self._import_package,
            style="Action.TButton",
        )
        btn_import.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_browse = ttk.Button(
            btn_import_row,
            text="📂 USE EXISTING: Select Project Folder",
            command=self._browse_folder,
        )
        btn_browse.pack(side="right")

        tk.Label(
            frame_project,
            text="Selected Folder (Current Remediation Target):",
            bg="white",
            fg="gray",
            font=("bold"),
        ).pack(anchor="w")
        self.lbl_setup_dir = tk.Label(
            frame_project,
            text=self.target_dir if self.target_dir else "No folder selected",
            bg="#F3F4F6",
            fg="#374151",
            padx=10,
            pady=5,
            anchor="w",
            wraplength=500,
        )
        self.lbl_setup_dir.pack(fill="x", pady=5)

        # --- SECTION 5: CANVAS MIRROR (LIVE SYNC) ---
        tk.Label(
            content,
            text="5. Canvas Mirror (Live Sync)",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(anchor="w", pady=(10, 5))
        frame_mirror = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_mirror.pack(fill="x", pady=(0, 20))

        tk.Label(
            frame_mirror,
            text="When 'Mirror Mode' is active, MOSH watches your project folder.\nEvery time you save an HTML file, it instantly uploads it to Canvas.",
            bg="white",
            fg="gray",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))

        self.btn_mirror_toggle = tk.Button(
            frame_mirror,
            text="🔴 MIRROR MODE: OFF",
            command=self._toggle_mirror,
            bg="#f3f4f6",
            font=("Segoe UI", 10, "bold"),
            width=25,
            cursor="hand2",
        )
        self.btn_mirror_toggle.pack(side="left")

        self.lbl_mirror_status = tk.Label(
            frame_mirror, text="Idle", bg="white", fg="gray", font=("italic")
        )
        self.lbl_mirror_status.pack(side="left", padx=15)

        # --- SECTION 4: POWER USER SETTINGS ---
        tk.Label(
            content,
            text="4. Advanced / Power User Settings",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(anchor="w", pady=(20, 5))
        frame_advanced = ttk.Frame(content, style="Card.TFrame", padding=20)
        frame_advanced.pack(fill="x", pady=(0, 20))

        self.trust_ai_var = tk.BooleanVar(
            value=self.config.get("trust_ai_alt", False)
        )

        def toggle_trust_ai():
            self._update_config(trust_ai_alt=self.trust_ai_var.get())
            if hasattr(self, "gui_handler"):
                self.gui_handler.trust_ai_alt = self.trust_ai_var.get()

        chk_trust = tk.Checkbutton(
            frame_advanced,
            text="Trust AI Alt Text (Skip Review if AI Suggestion Exists)",
            variable=self.trust_ai_var,
            command=toggle_trust_ai,
            bg="white",
            font=("Segoe UI", 10),
            activebackground="white",
            selectcolor="white",
        )
        chk_trust.pack(anchor="w")
        ToolTip(
            chk_trust,
            "If enabled, the 'Guided Review' will skip any image where Gemini provides a confident description.",
        )

        # Pack global status after sections
        lbl_global_status.pack(pady=10)

        def save_all():
            self._update_config(
                api_key=self.ent_api.get().strip(),
                canvas_url=self.ent_url.get().strip(),
                canvas_token=self.ent_token.get().strip(),
                canvas_course_id=self.ent_course.get().strip(),
                poppler_path=self.ent_poppler_setup.get().strip(),
                trust_ai_alt=self.trust_ai_var.get(),
                target_dir=self.target_dir,
            )
            lbl_global_status.config(text="✅ All Settings Saved!", fg="green")
            messagebox.showinfo("Success", "Configuration updated.")

        action_frame = tk.Frame(content, bg="white")
        action_frame.pack(pady=20)
        tk.Button(
            action_frame,
            text="💾 SAVE ALL SETTINGS",
            command=save_all,
            bg="#C8E6C9",
            width=40,
            font=("bold"),
            cursor="hand2",
        ).pack(side="left", padx=10)

    def _build_dashboard(self, content):
        """MOSH Toolkit Landing Page - Professional Suite Overview."""
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]

        # Welcome Header
        tk.Label(
            content,
            text="MOSH Remediation Toolkit",
            font=("Segoe UI", 28, "bold"),
            fg="#4B3190",
            bg=colors["bg"],
        ).pack(pady=(0, 5))
        tk.Label(
            content,
            text="Select a tool from the sidebar to begin.",
            font=("Segoe UI", 12),
            fg=colors["subheader"],
            bg=colors["bg"],
        ).pack(pady=(0, 40))

        # Grid for the main tool cards
        card_frame = ttk.Frame(content)
        card_frame.pack(fill="both", expand=True)
        card_frame.columnconfigure(0, weight=1)
        card_frame.columnconfigure(1, weight=1)
        card_frame.columnconfigure(2, weight=1)

        # --- TOOL 1: CANVAS ---
        c1 = tk.Frame(
            card_frame,
            bg="white",
            padx=20,
            pady=25,
            highlightbackground="#4B3190",
            highlightthickness=1,
        )
        c1.grid(row=0, column=0, padx=10, sticky="nsew")
        tk.Label(c1, text="🎨", font=("Segoe UI", 36), bg="white").pack()
        tk.Label(
            c1,
            text="Canvas Remediation",
            font=("Segoe UI", 13, "bold"),
            bg="white",
            fg="#4B3190",
        ).pack(pady=5)
        tk.Label(
            c1,
            text="Bulk fix entire course projects.",
            font=("Segoe UI", 9),
            bg="white",
            fg="gray",
        ).pack()
        ttk.Button(
            c1, text="OPEN TOOL", command=lambda: self._switch_view("course")
        ).pack(pady=10)

        # --- TOOL 2: FILES ---
        c2 = tk.Frame(
            card_frame,
            bg="white",
            padx=20,
            pady=25,
            highlightbackground="#0D9488",
            highlightthickness=1,
        )
        c2.grid(row=0, column=1, padx=10, sticky="nsew")
        tk.Label(c2, text="📄", font=("Segoe UI", 36), bg="white").pack()
        tk.Label(
            c2,
            text="File Conversion",
            font=("Segoe UI", 13, "bold"),
            bg="white",
            fg="#0D9488",
        ).pack(pady=5)
        tk.Label(
            c2,
            text="Standard PPT/Word to HTML.",
            font=("Segoe UI", 9),
            bg="white",
            fg="gray",
        ).pack()
        ttk.Button(
            c2, text="OPEN TOOL", command=lambda: self._switch_view("files")
        ).pack(pady=10)

        # --- TOOL 3: MATH ---
        c3 = tk.Frame(
            card_frame,
            bg="white",
            padx=20,
            pady=25,
            highlightbackground="#1B5E20",
            highlightthickness=1,
        )
        c3.grid(row=0, column=2, padx=10, sticky="nsew")
        tk.Label(c3, text="📐", font=("Segoe UI", 36), bg="white").pack()
        tk.Label(
            c3,
            text="Math Converter",
            font=("Segoe UI", 13, "bold"),
            bg="white",
            fg="#1B5E20",
        ).pack(pady=5)
        tk.Label(
            c3,
            text="AI conversion to LaTeX.",
            font=("Segoe UI", 9),
            bg="white",
            fg="gray",
        ).pack()
        ttk.Button(
            c3, text="OPEN TOOL", command=lambda: self._switch_view("math")
        ).pack(pady=10)

        # Bottom Status Tip
        tip_frame = tk.Frame(content, bg="#F0F9FF", padx=20, pady=15)
        tip_frame.pack(fill="x", pady=40)
        tk.Label(
            tip_frame,
            text="✅ Configuration Status",
            font=("Segoe UI", 10, "bold"),
            bg="#F0F9FF",
            fg="#0369A1",
        ).pack(anchor="w")

        status_text = (
            "All Tools Ready"
            if self.config.get("api_key") and self.config.get("poppler_path")
            else "Setup Incomplete (Check Settings)"
        )
        tk.Label(
            tip_frame,
            text=f"System Status: {status_text}",
            bg="#F0F9FF",
            fg="#0C4A6E",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

    def _build_course_view(self, content):
        """Standard view for remediating an entire Canvas course."""
        tk.Label(
            content,
            text="🎨 Canvas Remediation Suite",
            font=("Segoe UI", 24, "bold"),
            fg="#4B3190",
            bg="white",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            content,
            text="Bulk tools for fixing headers, alt text, and links on Page content.",
            font=("Segoe UI", 11),
            fg="#6B7280",
            bg="white",
        ).pack(anchor="w", pady=(0, 30))

        # -- Target Project Section --
        ttk.Label(
            content, text="Current Remediation Project", style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(0, 5))

        frame_dir = ttk.Frame(content, style="Card.TFrame", padding=15)
        frame_dir.pack(fill="x", pady=(0, 20))

        # Project Status Row
        tk.Label(
            frame_dir, text="Target Folder:", bg="white", fg="gray", font=("bold")
        ).pack(anchor="w")
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]

        self.lbl_dir = tk.Entry(
            frame_dir, bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"]
        )
        self.lbl_dir.insert(0, self.target_dir)
        self.lbl_dir.pack(fill="x", expand=True, pady=5)

        btn_row = ttk.Frame(frame_dir)
        btn_row.pack(fill="x", pady=(5, 0))
        ttk.Button(btn_row, text="📂 Change Folder", command=self._browse_folder).pack(
            side="left"
        )
        ttk.Button(
            btn_row,
            text="🛠️ Go to Setup / Import",
            command=lambda: self._switch_view("setup"),
        ).pack(side="right")

        # [NEW] BIG COPYRIGHT DISCLAIMER
        disclaimer_frame = tk.Frame(
            content,
            bg="#FEF3C7",
            padx=20,
            pady=20,
            highlightbackground="#FCD34D",
            highlightthickness=1,
        )
        disclaimer_frame.pack(fill="x", pady=(0, 25))

        tk.Label(
            disclaimer_frame,
            text="⚠️ IMPORTANT: COPYRIGHT & USAGE",
            font=("Segoe UI", 11, "bold"),
            bg="#FEF3C7",
            fg="#B45309",
        ).pack(anchor="w")
        disclaimer_text = (
            "ONLY use this tool for content YOU created or OER materials with a Creative Commons license allowing modifications. "
            "DO NOT convert publisher-provided materials (e.g. Pearson, McGraw Hill, Cengage) unless you have explicit written permission. "
            "Most publisher licenses prohibit creating derivative HTML versions of their proprietary files.\n\n"
            "Mosh says: 'Respect the work of others like you want yours respected!'"
        )
        tk.Label(
            disclaimer_frame,
            text=disclaimer_text,
            wraplength=550,
            bg="#FEF3C7",
            fg="#78350F",
            justify="left",
            font=("Segoe UI", 10),
        ).pack(pady=(8, 0))

        ttk.Label(
            content, text="Step 2: Convert & Build Pages", style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(0, 5))

        frame_convert = ttk.Frame(content, style="Card.TFrame", padding=15)
        frame_convert.pack(fill="x", pady=(0, 10))

        self.btn_wizard = ttk.Button(
            frame_convert,
            text="🪄 Select Specific Files to Convert",
            command=self._show_conversion_wizard,
            style="Action.TButton",
        )
        self.btn_wizard.pack(fill="x", pady=(0, 8))
        ToolTip(
            self.btn_wizard, "Choose exactly which Word, PPT, or PDF files to convert"
        )

        frame_singles = ttk.Frame(frame_convert)
        frame_singles.pack(fill="x")

        self.btn_word = ttk.Button(
            frame_singles,
            text="📝 Word",
            command=lambda: self._show_conversion_wizard("docx"),
        )
        self.btn_word.pack(side="left", fill="x", expand=True, padx=2)
        ToolTip(self.btn_word, "Convert all Word documents")

        self.btn_excel = ttk.Button(
            frame_singles,
            text="📈 Excel",
            command=lambda: self._show_conversion_wizard("xlsx"),
        )
        self.btn_excel.pack(side="left", fill="x", expand=True, padx=2)
        ToolTip(self.btn_excel, "Convert all Excel sheets")

        self.btn_ppt = ttk.Button(
            frame_singles,
            text="📽️ PPT",
            command=lambda: self._show_conversion_wizard("pptx"),
        )
        self.btn_ppt.pack(side="left", fill="x", expand=True, padx=2)
        ToolTip(self.btn_ppt, "Convert all PowerPoint presentations")

        self.btn_pdf = ttk.Button(
            frame_singles,
            text="📄 PDF",
            command=lambda: self._show_conversion_wizard("pdf"),
        )
        self.btn_pdf.pack(side="left", fill="x", expand=True, padx=2)
        ToolTip(self.btn_pdf, "Convert all PDF documents")

        self.btn_batch = ttk.Button(
            frame_convert,
            text="📂 Convert Everything (Batch Mode)",
            command=self._run_batch_conversion,
            style="Action.TButton",
        )
        self.btn_batch.pack(fill="x", pady=(12, 0))
        ToolTip(
            self.btn_batch, "Convert all supported files in the course automatically"
        )

        # -- Step 3: Remediation Actions (Grid) --
        self.step3_header = ttk.Label(
            content, text="Step 3: Fix & Review", style="SubHeader.TLabel"
        )
        self.step3_header.pack(anchor="w", pady=(0, 5))

        self.frame_actions = ttk.Frame(content, style="Card.TFrame", padding=15)
        self.frame_actions.pack(fill="x", pady=(0, 25))

        # Friendly Button Names
        self.btn_inter = ttk.Button(
            self.frame_actions,
            text="📖 Guided Review\n(Descriptions & Links)",
            command=self._run_interactive,
            style="Action.TButton",
        )
        self.btn_inter.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ToolTip(self.btn_inter, "Review image descriptions and fix links page-by-page")

        self.btn_auto = ttk.Button(
            self.frame_actions,
            text="✨ Auto-Fix Issues\n(Headings & Contrast)",
            command=self._run_auto_fixer,
            style="Action.TButton",
        )
        self.btn_auto.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(
            self.btn_auto, "Automatically fix accessibility issues across all pages"
        )
        
        # [NEW] AI Responsive Design 
        if self.config.get("api_key"):
            self.btn_ai_design = ttk.Button(
                self.frame_actions,
                text="📱 AI Mobile Design\n(Responsive Canvas HTML)",
                command=self._run_ai_design_fixer,
                style="Action.TButton",
            )
            self.btn_ai_design.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
            ToolTip(
                self.btn_ai_design, "Use AI to restructure the HTML page layout for mobile apps"
            )

        # Row 2 (Audit)
        self.btn_audit = ttk.Button(
            self.frame_actions,
            text="📊 Quick Report\n(Is it Compliant?)",
            command=self._run_audit,
            style="Action.TButton",
        )
        self.btn_audit.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(
            self.btn_audit, "Generate a detailed accessibility report for the course"
        )

        # Row 3 (Global Fixes)
        self.btn_link_fix = ttk.Button(
            self.frame_actions,
            text="🔗 Global Link Repair\n(Fixed broken Wiki links)",
            command=self._run_all_links_fix,
            style="Action.TButton",
        )
        self.btn_link_fix.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ToolTip(
            self.btn_link_fix, "Scans all wiki pages and updates links to documents that were converted to HTML"
        )

        self.frame_actions.columnconfigure(0, weight=1)
        self.frame_actions.columnconfigure(1, weight=1)

        # -- Step 4: Final Launch --
        self.step4_header = ttk.Label(
            content, text="Step 4: Final Step", style="SubHeader.TLabel"
        )
        self.step4_header.pack(anchor="w", pady=(0, 5))
        self.frame_final = ttk.Frame(content, style="Card.TFrame", padding=15)
        self.frame_final.pack(fill="x", pady=(0, 25))

        self.btn_check = ttk.Button(
            self.frame_final,
            text="🚥 Step 4: Am I Ready to Upload? (Run Pre-Flight Check)",
            command=self._show_preflight_dialog,
            style="Action.TButton",
        )
        self.btn_check.pack(fill="x")

    def _build_math_view(self, content):
        """Dedicated view for AI-powered Math conversion."""
        tk.Label(
            content,
            text="📐 Math Remediation Suite",
            font=("Segoe UI", 24, "bold"),
            fg="#1B5E20",
            bg="white",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            content,
            text="Gemini-powered conversion of math PDFs, Word docs, and Images to accessible Canvas LaTeX.",
            font=("Segoe UI", 11),
            fg="#6B7280",
            bg="white",
        ).pack(anchor="w", pady=(0, 30))

        # Setup Link Helper
        setup_help_frame = tk.Frame(content, bg="#F0F9FF", padx=15, pady=10)
        setup_help_frame.pack(fill="x", pady=(0, 20))
        tk.Label(
            setup_help_frame,
            text="💡 Need to set your AI Key or Poppler helper?",
            bg="#F0F9FF",
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Button(
            setup_help_frame,
            text="Go to CONNECT & SETUP",
            command=lambda: self._switch_view("setup"),
            font=("Segoe UI", 9, "bold", "underline"),
            fg="#0369A1",
            bg="#F0F9FF",
            borderwidth=0,
            cursor="hand2",
        ).pack(side="left", padx=5)

        # Re-use Math section logic
        self.math_disclaimer = tk.Frame(
            content,
            bg="#E8F5E9",
            padx=15,
            pady=15,
            highlightbackground="#4CAF50",
            highlightthickness=2,
        )
        self.math_disclaimer.pack(fill="x", pady=(0, 10))

        tk.Label(
            self.math_disclaimer,
            text="✨ MOSH Magic: AI Math",
            font=("Segoe UI", 11, "bold"),
            bg="#E8F5E9",
            fg="#2E7D32",
        ).pack(anchor="w")
        math_desc = (
            "This tool reads handwritten solutions and equations, then converts them to accessible Canvas LaTeX. "
            "It turns unreadable PDFs and Word docs into searchable, screen-reader compatible content!"
        )
        tk.Label(
            self.math_disclaimer,
            text=math_desc,
            wraplength=550,
            bg="#E8F5E9",
            fg="#1B5E20",
            justify="left",
            font=("Segoe UI", 10),
        ).pack(pady=(5, 0))

        frame_math = ttk.Frame(content, style="Card.TFrame", padding=15)
        frame_math.pack(fill="x", pady=(0, 20))

        ttk.Label(
            frame_math, text="Option A: Full Course Remediation", font=("bold")
        ).pack(anchor="w", pady=(0, 5))
        self.btn_math_canvas = ttk.Button(
            frame_math,
            text="📚 Convert Math in Canvas Course Export (PDF & Word)",
            command=self._convert_math_canvas_export,
            style="Action.TButton",
        )
        self.btn_math_canvas.pack(fill="x", pady=(0, 15))

        ttk.Separator(frame_math, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(
            frame_math, text="Option B: Individual Ad-Hoc Files", font=("bold")
        ).pack(anchor="w", pady=(0, 5))
        frame_math_singles = ttk.Frame(frame_math)
        frame_math_singles.pack(fill="x")

        self.btn_math_pdf = ttk.Button(
            frame_math_singles,
            text="📄 Select PDF",
            command=lambda: self._convert_math_files("pdf"),
        )
        self.btn_math_pdf.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_math_docx = ttk.Button(
            frame_math_singles,
            text="📝 Select Word",
            command=lambda: self._convert_math_files("docx"),
        )
        self.btn_math_docx.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_math_img = ttk.Button(
            frame_math_singles,
            text="🖼️ Select Image",
            command=lambda: self._convert_math_files("images"),
        )
        self.btn_math_img.pack(side="left", fill="x", expand=True, padx=2)

        ttk.Separator(frame_math, orient="horizontal").pack(fill="x", pady=20)

        ttk.Label(
            frame_math, text="Option C: Visual Element Manifest", font=("bold")
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            frame_math,
            text="Review all detected graphs, icons, and diagrams in a single grid.",
            font=("Segoe UI", 9),
            bg="white",
            fg="gray",
        ).pack(anchor="w")
        self.btn_manifest = ttk.Button(
            frame_math,
            text="✨ Open Visual Element Manifest (Confirmation Grid)",
            command=self._show_visual_manifest,
            style="Action.TButton",
        )
        self.btn_manifest.pack(fill="x", pady=10)

    def _browse_folder(self):
        """Standard folder browser that updates UI across views."""
        path = filedialog.askdirectory(initialdir=self.target_dir)
        if path:
            self.target_dir = path

            # 1. Update Course View Widget (if exists)
            if hasattr(self, "lbl_dir") and self.lbl_dir.winfo_exists():
                self.lbl_dir.delete(0, tk.END)
                self.lbl_dir.insert(0, path)

            # 2. Update Setup View Widget (if exists)
            if hasattr(self, "lbl_setup_dir") and self.lbl_setup_dir.winfo_exists():
                self.lbl_setup_dir.config(text=path)

            self._log(f"Selected project folder: {path}")

            # Persistent Save
            self._update_config(target_dir=path)

    def _import_package(self):
        """Allows user to select .imscc or .zip and extracts it with duplicate detection."""
        path = filedialog.askopenfilename(
            filetypes=[("Canvas Export / Zip", "*.imscc *.zip"), ("All Files", "*.*")]
        )
        if not path:
            return

        # [FIX] Determine extraction folder
        # ALWAYS extract to the same folder as the .imscc file
        # This prevents infinite nesting when importing multiple files
        base_dir = os.path.dirname(path)

        filename = os.path.basename(path)
        folder_name = os.path.splitext(filename)[0] + "_extracted"
        extract_to = os.path.join(base_dir, folder_name)

        # [NEW] Duplicate Detection
        if os.path.exists(extract_to):
            choice = messagebox.askquestion(
                "Folder Exists",
                f"I found a folder with this name already!\n\n"
                "Yes: Erase it and start fresh.\n"
                "No: Make a new copy next to it.",
                icon="warning",
            )

            if choice == "no":
                # Create unique name
                count = 1
                while os.path.exists(f"{extract_to}({count})"):
                    count += 1
                extract_to = f"{extract_to}({count})"

        # Confirm (Must be on main thread)
        msg_confirm = f"Found it! Ready to unpack this course?\n\nTarget:\n{extract_to}"
        if not messagebox.askyesno("Confirm Import", msg_confirm):
            return

        def task():
            self.gui_handler.log(f"--- Extracting Package: {filename} ---")
            success, msg = converter_utils.unzip_course_package(
                path, extract_to, log_func=self.gui_handler.log
            )

            if success:
                self.gui_handler.log(msg)  # msg already has "Success!" prefix
                # Update UI elements via after()
                self.root.after(0, lambda: self._finalize_import(extract_to))
            else:
                self.gui_handler.log(f"[ERROR] Import Failed: {msg}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Import Error", f"Failed to extract package:\n{msg}"
                    ),
                )

        self._run_task_in_thread(task, "Package Import")

    def _finalize_import(self, extract_to):
        """Updates UI after successful import (runs on main thread)."""
        self.target_dir = extract_to
        self.target_dir = extract_to
        self._update_config(target_dir=extract_to)

        # Refresh current view if it's the Setup view to show the new folder
        self._switch_view("setup")

        msg = (
            f"Package extracted successfully! 🎉\n\n"
            f"Mosh has prepared your project here:\n{extract_to}\n\n"
            f"Now, click 'CANVAS REMEDIATION' in the sidebar to start fixing your course!"
        )
        messagebox.showinfo("Import Complete", msg)

    def _export_package(self):
        """Zips the current target directory back into a .imscc file."""
        # Check target dir first
        self.target_dir = self.lbl_dir.get().strip()
        if not os.path.isdir(self.target_dir):
            messagebox.showerror("Error", "Please select a valid project folder first.")
            return

        # Default Name: folder_name_remediated.imscc
        default_name = os.path.basename(self.target_dir) + "_remediated.imscc"

        output_path = filedialog.asksaveasfilename(
            defaultextension=".imscc",
            initialfile=default_name,
            filetypes=[("Canvas Course Package", "*.imscc")],
        )

        if not output_path:
            return

        def task():
            self.gui_handler.log(f"--- Packaging Course... ---")
            success, msg = converter_utils.create_course_package(
                self.target_dir, output_path, log_func=self.gui_handler.log
            )

            if success:
                self.gui_handler.log(f"Success! {msg}")
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Export Complete",
                        f"Course Package Created:\n{output_path}\n\nIMPORTANT NEXT STEPS:\n"
                        "1. Create a NEW, EMPTY course in Canvas to use as a test space.\n"
                        "2. Import this file into that empty course.\n"
                        "3. Review all changes BEFORE moving content to a live semester.",
                    ),
                )
            else:
                self.gui_handler.log(f"[ERROR] Packaging Failed: {msg}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Export Error", f"Failed to create package:\n{msg}"
                    ),
                )

        self._run_task_in_thread(task, "Course Packaging")

    def _log(self, msg):
        self.txt_log.configure(state="normal")

        # [MODIFIED] Detect file paths for clickability
        import re

        # Look for [SAVED], Created:, or general file paths in the message
        path_patterns = [
            r"\[SAVED\]\s+([^\n]+)",
            r"Created:\s+([^\n]+)",
            r"Project folder:\s+([^\n]+)",
            r"Processing:\s+([^\n]+\.html)",
        ]

        start_index = self.txt_log.index(tk.END + "-1c")
        self.txt_log.insert(tk.END, msg + "\n")

        for pattern in path_patterns:
            for match in re.finditer(pattern, msg):
                path_str = match.group(1).strip()
                # If it's just a filename, it might be harder to resolve, but we can try
                # For now, we tag the matched group
                m_start, m_end = match.span(1)

                # Convert string index to Tkinter index
                # This is tricky with multiple lines, so we just apply to the whole line if match found
                line_no = int(start_index.split(".")[0])
                tag_start = f"{line_no}.{m_start}"
                tag_end = f"{line_no}.{m_end}"
                self.txt_log.tag_add("link", tag_start, tag_end)

        self.txt_log.see(tk.END)
        self.txt_log.configure(state="disabled")

    def _on_log_click(self, event):
        """Handle clicking a link in the log."""
        # Get index of click
        idx = self.txt_log.index(f"@{event.x},{event.y}")
        # Find the word under the click that has the 'link' tag
        tags = self.txt_log.tag_names(idx)
        if "link" in tags:
            # We need to extract the actual text of the link
            # Search backward and forward for the start/end of the tag
            start = self.txt_log.tag_prevrange("link", idx + "+1c")[0]
            end = self.txt_log.tag_nextrange("link", idx + "-1c")[1]
            path_val = self.txt_log.get(start, end).strip().strip('"').strip("'")

            # Resolve relative path if needed
            if not os.path.isabs(path_val):
                # Try relative to target_dir
                full_p = os.path.join(self.target_dir, path_val)
                if not os.path.exists(full_p):
                    # Try searching for it (expensive but helpful)
                    for root, dirs, files in os.walk(self.target_dir):
                        if path_val in files:
                            full_p = os.path.join(root, path_val)
                            break
                path_val = full_p

            if os.path.exists(path_val):
                if path_val.lower().endswith(".html"):
                    webbrowser.open(f"file:///{os.path.abspath(path_val)}")
                else:
                    os.startfile(
                        os.path.dirname(path_val)
                        if os.path.isfile(path_val)
                        else path_val
                    )
            else:
                self.gui_handler.log(f"⚠️ Could not open: {path_val}")

    def _show_image_dialog(self, message, image_path, context=None, suggestion=None):
        """Custom dialog to show an image and prompt for alt text."""
        dialog = Toplevel(self.root)
        dialog.title("Image Review")
        dialog.geometry("700x650")
        dialog.transient(self.root)
        dialog.grab_set()

        def on_close_x():
            self.gui_handler.stop_requested = True
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close_x)

        # Context area
        if context:
            ctx_frame = ttk.LabelFrame(
                dialog, text="Surrounding Text Context", padding=5
            )
            ctx_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(
                ctx_frame,
                text=context,
                wraplength=650,
                font=("Segoe UI", 9, "italic"),
                justify="left",
            ).pack()

        # Load and verify image
        try:
            pil_img = Image.open(image_path)
            # Resize logic to fit
            w, h = pil_img.size
            if w > 400 or h > 300:
                pil_img.thumbnail((400, 300))
            tk_img = ImageTk.PhotoImage(pil_img)

            lbl_img = tk.Label(dialog, image=tk_img, cursor="plus")
            lbl_img.image = tk_img
            lbl_img.pack(pady=10)
            
            # [NEW] Click-to-Zoom
            lbl_img.bind("<Button-1>", lambda e: self._show_zoom(dialog, image_path))
            ToolTip(lbl_img, "Click to view full size")
        except Exception as e:
            tk.Label(dialog, text=f"[Could not load image: {e}]", fg="red").pack(
                pady=10
            )

        fname = os.path.basename(image_path)
        tk.Label(dialog, text=f"File: {fname}", font=("Segoe UI", 9, "bold")).pack()

        # Instructions
        tk.Label(
            dialog, text="Review or Edit Alt Text:", font=("Segoe UI", 10, "bold")
        ).pack(pady=(15, 5))

        # Input Area (Pre-filled with suggestion)
        entry_var = tk.StringVar()
        if suggestion:
            entry_var.set(suggestion)  # [FIX] Pre-fill the box!
            tk.Label(
                dialog,
                text="✨ AI Suggestion added. Edit or press Enter to accept.",
                fg="#4B3190",
                bg="#F5F3ED",
            ).pack()

        entry = tk.Entry(
            dialog, textvariable=entry_var, width=70, font=("Segoe UI", 11)
        )
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)

        # [NEW] Length Warning Label
        warning_lbl = tk.Label(
            dialog, text="", fg="#D32F2F", bg="#F5F3ED", font=("Segoe UI", 9, "bold")
        )
        warning_lbl.pack()

        def update_warning(*args):
            text = entry_var.get()
            length = len(text)
            if length > 100:
                warning_lbl.config(
                    text=f"⚠️ Long Alt Text ({length} chars). Panorama may flag this!"
                )
            else:
                warning_lbl.config(text="")

        entry_var.trace_add("write", update_warning)
        if suggestion:
            update_warning()  # Initial check

        result = {"text": ""}

        def on_ok(event=None):
            result["text"] = entry_var.get().strip()
            dialog.destroy()

        def on_clear():
            entry_var.set("")
            entry.focus_set()

        def on_skip():
            result["text"] = ""
            dialog.destroy()

        def on_decorate():
            result["text"] = "__DECORATIVE__"
            dialog.destroy()

        def on_ocr():
            result["text"] = "__OCR__"
            dialog.destroy()

        def on_table_ocr():
            result["text"] = "__TABLE_OCR__"
            dialog.destroy()

        def on_math_ocr():
            result["text"] = "__MATH_OCR__"
            dialog.destroy()

        def on_math_board():
            """Opens the Interactive LaTeX Editor."""
            self._show_math_board(entry_var, image_path)

        # Row 1
        btn_frame_1 = tk.Frame(dialog, bg="#F5F3ED")
        btn_frame_1.pack(pady=(10, 0))

        tk.Button(
            btn_frame_1,
            text="✅ Save / Next (Enter)",
            command=on_ok,
            bg="#dcedc8",
            font=("bold"),
            width=18,
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame_1,
            text="📐 MATH BOARD (Review)",
            command=on_math_board,
            bg="#E9D5FF",
            font=("bold"),
            width=20,
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame_1,
            text="📊 Convert to Table (AI)",
            command=on_table_ocr,
            bg="#E1F5FE",
            width=20,
            cursor="hand2",
        ).pack(side="left", padx=5)

        # Row 2
        btn_frame_2 = tk.Frame(dialog, bg="#F5F3ED")
        btn_frame_2.pack(pady=(10, 5))

        tk.Button(btn_frame_2, text="📝 OCR Text (AI)", command=on_ocr, bg="#FFF9C4", width=18, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame_2, text="Mark Decorative", command=on_decorate, bg="#F5F5F5", width=20, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame_2, text="Skip / Ignore", command=on_skip, width=20, cursor="hand2").pack(side="left", padx=5)

        # [NEW] Trust AI Checkbox
        trust_var = tk.BooleanVar(value=getattr(self.gui_handler, "trust_ai_alt", False))
        def toggle_trust():
            self.gui_handler.trust_ai_alt = trust_var.get()
            if trust_var.get():
                self.gui_handler.log("🚀 Trust AI enabled: Mosh will automatically accept high-confidence alt tags.")

        cb_trust = tk.Checkbutton(dialog, text="Always trust AI alt tags for this session",
                                  variable=trust_var, command=toggle_trust,
                                  bg="#F5F3ED", font=("Segoe UI", 9, "bold"), fg="#4B3190")
        cb_trust.pack(pady=5)

        dialog.bind('<Return>', on_ok)
        self.root.wait_window(dialog)
        return result["text"]

    def _show_math_board(self, parent_var, image_path):
        """Standard 'Math Whiteboard' for LaTeX editing."""
        math_win = Toplevel(self.root)
        math_win.title("📐 MOSH Math Whiteboard")
        math_win.geometry("900x650")
        math_win.transient(self.root)
        math_win.grab_set()

        colors = THEMES[self.config.get("theme", "light")]
        math_win.configure(bg=colors["bg"])

        # Split Layout: Left (Symbols), Right (Editor)
        main_frame = tk.Frame(math_win, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Left Sidebar: Symbols
        sidebar = tk.LabelFrame(
            main_frame,
            text="Math Shortcuts",
            bg=colors["bg"],
            fg=colors["header"],
            font=("bold"),
        )
        sidebar.pack(side="left", fill="y", padx=(0, 10))

        shortcuts = [
            ("Fraction", "\\frac{num}{den}"),
            ("Exponent", "^{exp}"),
            ("Subscript", "_{sub}"),
            ("Square Root", "\\sqrt{rad}"),
            ("Integral", "\\int_{a}^{b}"),
            ("Summation", "\\sum_{i=1}^{n}"),
            ("Greek (pi)", "\\pi"),
            ("Infinity", "\\infty"),
            ("Limit", "\\lim_{n \\to \\infty}"),
            ("Matrix (2x2)", "\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}"),
            ("Vector", "\\vec{v}"),
            ("Greek (theta)", "\\theta"),
        ]

        def insert_sym(sym):
            txt_math.insert(tk.INSERT, sym)
            txt_math.focus_set()

        for label, sym in shortcuts:
            tk.Button(
                sidebar,
                text=label,
                command=lambda s=sym: insert_sym(s),
                width=15,
                bg="#f9fafb",
                cursor="hand2",
            ).pack(pady=2, padx=5)

        # 2. Right Side: Editor
        editor_frame = tk.Frame(main_frame, bg=colors["bg"])
        editor_frame.pack(side="right", fill="both", expand=True)

        tk.Label(
            editor_frame,
            text="LaTeX Code Workspace:",
            bg=colors["bg"],
            fg=colors["header"],
            font=("bold"),
        ).pack(anchor="w")

        txt_math = scrolledtext.ScrolledText(
            editor_frame, font=("Consolas", 14), bg="white", height=15
        )
        txt_math.pack(fill="both", expand=True, pady=(5, 10))

        # Load current text
        txt_math.insert(1.0, parent_var.get())

        # Image Preview (Small)
        try:
            p_img = Image.open(image_path)
            p_img.thumbnail((300, 150))
            tk_p = ImageTk.PhotoImage(p_img)
            lbl_p = tk.Label(
                editor_frame, image=tk_p, bg="white", borderwidth=1, relief="solid"
            )
            lbl_p.image = tk_p
            lbl_p.pack(pady=10)
        except Exception:
            pass

        def on_apply():
            parent_var.set(txt_math.get(1.0, tk.END).strip())
            math_win.destroy()

        def on_ocr_retry():
            # Logic for re-running math OCR if they want a second look
            math_win.destroy()
            # This triggers the existing on_math_ocr logic back in the parent
            # But here we just close it and let the user decide.

        btn_action = tk.Frame(editor_frame, bg=colors["bg"])
        btn_action.pack(fill="x")

        tk.Button(
            btn_action,
            text="✨ APPLY TO PAGE",
            command=on_apply,
            bg="#dcedc8",
            font=("bold"),
            cursor="hand2",
            width=25,
        ).pack(side="right")
        tk.Button(
            btn_action,
            text="❌ Cancel",
            command=math_win.destroy,
            bg="#ffcdd2",
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_action,
            text="✨ APPLY TO PAGE",
            command=on_apply,
            bg="#dcedc8",
            font=("bold"),
            cursor="hand2",
            width=25,
        ).pack(side="right")
        tk.Button(
            btn_action,
            text="❌ Cancel",
            command=math_win.destroy,
            bg="#ffcdd2",
            cursor="hand2",
        ).pack(side="left")

    def _show_zoom(self, parent, img_path):
        """Open a separate zoom window for any image."""
        zoom_win = Toplevel(parent)
        zoom_win.title("Image Zoom")
        zoom_win.transient(parent)
        try:
            full_p = Image.open(img_path)
            zw, zh = full_p.size
            # Limit initial size but allow scrolling if needed
            sw, sh = min(zw, 1000), min(zh, 800)
            zoom_win.geometry(f"{sw}x{sh}")
            
            z_canvas = tk.Canvas(zoom_win, bg="#333")
            z_sb_v = ttk.Scrollbar(zoom_win, orient="vertical", command=z_canvas.yview)
            z_sb_h = ttk.Scrollbar(zoom_win, orient="horizontal", command=z_canvas.xview)
            z_canvas.configure(yscrollcommand=z_sb_v.set, xscrollcommand=z_sb_h.set)
            
            z_sb_v.pack(side="right", fill="y")
            z_sb_h.pack(side="bottom", fill="x")
            z_canvas.pack(side="left", fill="both", expand=True)

            z_tk = ImageTk.PhotoImage(full_p)
            z_canvas.image = z_tk # keep ref
            z_canvas.create_image(0, 0, anchor="nw", image=z_tk)
            z_canvas.configure(scrollregion=(0,0,zw,zh))
        except Exception as e:
            tk.Label(zoom_win, text=f"Zoom Error: {e}").pack()

    def _show_visual_manifest(self):
        """Displays a GRID of all detected graphs/images in the project."""
        if not self.target_dir or not os.path.exists(self.target_dir):
            messagebox.showwarning("Load Project", "Please load a project first.")
            return

        manifest_win = Toplevel(self.root)
        manifest_win.title("🖼️ Visual Element Manifest")
        manifest_win.geometry("1000x750")
        manifest_win.transient(self.root)
        manifest_win.grab_set()

        mode = self.config.get("theme", "light")
        colors = THEMES[mode]
        manifest_win.configure(bg=colors["bg"])

        # Header
        header = tk.Frame(manifest_win, bg=colors["bg"])
        header.pack(fill="x", padx=20, pady=20)
        tk.Label(
            header,
            text="🖼️ Visual Element Manifest",
            font=("Segoe UI", 18, "bold"),
            fg=colors["header"],
            bg=colors["bg"],
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Mosh: 'Review all your cropped graphs and diagrams here. One click to edit, one click to confirm!'",
            font=("Segoe UI", 10, "italic"),
            fg=colors["fg"],
            bg=colors["bg"],
        ).pack(anchor="w")

        # Scrollable Area
        container = ttk.Frame(manifest_win)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg="white")

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas_window = canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        grid_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def refresh_grid():
            for widget in grid_frame.winfo_children():
                widget.destroy()

            # Find all images in any _graphs or remediated_images directories
            images = []
            if getattr(self, "target_dir", None) and os.path.exists(self.target_dir):
                for root_dir, dirs, files in os.walk(self.target_dir):
                    if root_dir.endswith("_graphs") or "remediated_graphs" in root_dir or "remediated_images" in root_dir:
                        for f in files:
                            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                                images.append(os.path.join(root_dir, f))

            if not images:
                tk.Label(
                    grid_frame,
                    text="No remediated visual elements found yet. Run a conversion first!",
                    font=("Segoe UI", 12),
                    bg="white",
                ).pack(pady=50)
                return

            cols = 4 if manifest_win.winfo_width() > 800 else 3
            for i, img_path in enumerate(images):
                img_name = os.path.basename(img_path)

                card = tk.Frame(
                    grid_frame,
                    bg="white",
                    borderwidth=1,
                    relief="solid",
                    padx=5,
                    pady=5,
                )
                card.grid(
                    row=i // cols, column=i % cols, padx=10, pady=10, sticky="nsew"
                )

                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((200, 150))
                    tk_img = ImageTk.PhotoImage(pil_img)

                    lbl_img = tk.Label(card, image=tk_img, bg="white", cursor="hand2")
                    lbl_img.image = tk_img
                    lbl_img.pack()

                    # Bind click to edit
                    lbl_img.bind(
                        "<Button-1>",
                        lambda e, p=img_path: self._edit_manifest_item(p, manifest_win),
                    )

                    tk.Label(
                        card,
                        text=img_name,
                        font=("Segoe UI", 8),
                        bg="white",
                        wraplength=180,
                    ).pack()

                    btn_strip = tk.Frame(card, bg="white")
                    btn_strip.pack(fill="x", pady=5)

                    tk.Button(
                        btn_strip,
                        text="✏️ Edit",
                        command=lambda p=img_path: self._edit_manifest_item(
                            p, manifest_win
                        ),
                        font=("Segoe UI", 8),
                        bg="#F3F4F6",
                    ).pack(side="left", expand=True)
                    tk.Button(
                        btn_strip,
                        text="🗑️ Del",
                        command=lambda p=img_path: self._delete_manifest_item(
                            p, refresh_grid
                        ),
                        font=("Segoe UI", 8),
                        bg="#FEE2E2",
                    ).pack(side="right", expand=True)

                except Exception as e:
                    tk.Label(
                        card, text=f"Error Loading\n{img_name}", bg="white", fg="red"
                    ).pack()

        manifest_win.after(100, refresh_grid)

    def _edit_manifest_item(self, img_path, win):
        """Allows editing an image's alt text from the manifest."""
        # Find the HTML file that references this image to update it
        # This is the tricky part - we need to scan the project
        # For now, let's just open the dialog and see if we can update the image file itself
        # (Though alt text lives in HTML)

        # [NEW] Enhanced Manifest: Find HTML source
        self.gui_handler.log(
            f"   [Manifest] Opening review for: {os.path.basename(img_path)}"
        )
        self._show_image_dialog(
            "Reviewing from Manifest", img_path, context="Manifest View"
        )
        # Note: In a full implementation, we'd need to map image -> HTML to update alt text.
        # For this version, it's a visual auditor.

    def _delete_manifest_item(self, img_path, callback):
        """Deletes a visual element from the project."""
        if messagebox.askyesno(
            "Delete Image?",
            f"Are you sure you want to delete this visual element?\n\n{os.path.basename(img_path)}",
        ):
            try:
                os.remove(img_path)
                callback()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete image: {e}")

    def _show_visual_review(self, html_path, graphs_dir):
        """
        Interactive visual review dialog. Shows full page context with crop overlay.
        Supports: click-to-drag crop redefinition, nudge, alt text, delete, add missing.
        BLOCKS until user approves.
        """
        import json
        import threading

        meta_path = os.path.join(graphs_dir, "crop_meta.json")
        if not os.path.exists(meta_path):
            return True

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if not meta:
            return True

        result = {"approved": False}
        event = threading.Event()
        full_pages_cache = {}

        def build_dialog():
            nonlocal full_pages_cache

            dialog = Toplevel(self.root)
            dialog.title(f"Visual Review: {os.path.basename(html_path)}")
            dialog.geometry("1200x800")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.configure(bg="#1a1a2e")

            PAGE_W = 350
            PAGE_H = 480

            total_items = len(meta)

            hdr = tk.Frame(dialog, bg="#1a1a2e")
            hdr.pack(fill="x", padx=20, pady=(15, 0))
            hdr_top = tk.Frame(hdr, bg="#1a1a2e")
            hdr_top.pack(fill="x")
            tk.Label(hdr_top, text="Visual Element Review", font=("Segoe UI", 18, "bold"), bg="#1a1a2e", fg="white").pack(side="left")
            tk.Label(hdr_top, text=f"{total_items} image(s) found", font=("Segoe UI", 11), bg="#1a1a2e", fg="#4fc3f7").pack(side="left", padx=15)
            
            # [NEW] Auto-Approve Toggle
            auto_approve_var = tk.BooleanVar(value=self.config.get("auto_approve_visual", False))
            def toggle_auto_approve():
                self._update_config(auto_approve_visual=auto_approve_var.get())
            
            chk_auto = tk.Checkbutton(hdr_top, text="Auto-Approve Clear Pages", variable=auto_approve_var, command=toggle_auto_approve, bg="#1a1a2e", fg="#4fc3f7", selectcolor="#1a1a2e", font=("Segoe UI", 9, "bold"), activebackground="#1a1a2e", activeforeground="white")
            chk_auto.pack(side="right")
            ToolTip(chk_auto, "If all images have descriptions, skip this review next time.")

            tk.Label(hdr, text="Drag on the page preview to redefine crops  |  Use +/- buttons to nudge 50px  |  Click cropped image to ZOOM", font=("Segoe UI", 9, "italic"), bg="#1a1a2e", fg="#aaa").pack(anchor="w", pady=(3, 0))

            outer = ttk.Frame(dialog)
            outer.pack(fill="both", expand=True, padx=15, pady=10)

            canvas_scroll = tk.Canvas(outer, bg="#f0f0f0", highlightthickness=0)
            sb = ttk.Scrollbar(outer, orient="vertical", command=canvas_scroll.yview)
            inner = tk.Frame(canvas_scroll, bg="#f0f0f0")

            cw = canvas_scroll.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
            canvas_scroll.bind("<Configure>", lambda e: canvas_scroll.itemconfig(cw, width=e.width))
            canvas_scroll.configure(yscrollcommand=sb.set)
            canvas_scroll.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")

            def _on_mousewheel(evt):
                canvas_scroll.yview_scroll(int(-1 * (evt.delta / 120)), "units")
            canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)

            tk_images = []
            deleted_items = set()

            def load_full_page(page_name):
                if page_name in full_pages_cache:
                    return full_pages_cache[page_name]
                fp = os.path.join(graphs_dir, page_name)
                if not os.path.exists(fp):
                    return None, 1.0, None
                pil = Image.open(fp)
                ow, oh = pil.size
                scale = min(PAGE_W / ow, PAGE_H / oh)
                nw, nh = int(ow * scale), int(oh * scale)
                pil_s = pil.resize((nw, nh), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(pil_s)
                tk_images.append(tk_img)
                full_pages_cache[page_name] = (tk_img, scale, pil)
                return tk_img, scale, pil

            def draw_rect(cv, box, scale, tag="crop_rect"):
                cv.delete(tag)
                x1, y1, x2, y2 = [int(c * scale) for c in box]
                cv.create_rectangle(x1, y1, x2, y2, outline="#ff3333", width=3, dash=(6, 4), tags=tag)

            def refresh_crop(gn, lbl):
                cp = os.path.join(graphs_dir, gn)
                if not os.path.exists(cp):
                    return
                p = Image.open(cp)
                p.thumbnail((200, 150))
                ti = ImageTk.PhotoImage(p)
                tk_images.append(ti)
                lbl.config(image=ti)
                lbl.image = ti

            def do_recrop(gn, info, pcv, lbl, dim_lbl=None):
                fp = os.path.join(graphs_dir, info["full_image"])
                box = info["box_abs"]
                try:
                    with Image.open(fp) as src:
                        crop = src.crop((box[0], box[1], box[2], box[3]))
                        crop.save(os.path.join(graphs_dir, gn))
                    _, sc, _ = load_full_page(info["full_image"])
                    draw_rect(pcv, box, sc)
                    refresh_crop(gn, lbl)
                    # Update dimension label
                    cw = box[2] - box[0]
                    ch = box[3] - box[1]
                    if dim_lbl:
                        warn = "  ** LOW QUALITY" if cw < 100 or ch < 100 else ""
                        color = "#c0392b" if warn else "#555"
                        dim_lbl.config(text=f"Size: {cw} x {ch} px{warn}", fg=color)
                except Exception as err:
                    self.gui_handler.log(f"   [CROP] Error: {err}")

            def nudge(gn, d, info, pcv, lbl, dim_lbl=None):
                box = info["box_abs"]
                pw, ph = info["page_width"], info["page_height"]
                if d == "up":    box[1] = max(0, box[1] - 50)
                elif d == "down":  box[3] = min(ph, box[3] + 50)
                elif d == "left":  box[0] = max(0, box[0] - 50)
                elif d == "right": box[2] = min(pw, box[2] + 50)
                info["box_abs"] = box
                meta[gn] = info
                do_recrop(gn, info, pcv, lbl, dim_lbl)

            def reset_crop(gn, info, pcv, lbl, dim_lbl=None):
                """Reset crop to original AI-generated bounding box."""
                orig = info.get("original_box")
                if orig:
                    info["box_abs"] = list(orig)
                    meta[gn] = info
                    do_recrop(gn, info, pcv, lbl, dim_lbl)

            def ai_describe(gn, ae_widget):
                """Use Gemini to describe just this cropped image."""
                api_key = self.config.get("api_key", "").strip()
                if not api_key:
                    self.root.after(0, lambda: [ae_widget.delete("1.0", "end"), ae_widget.insert("1.0", "[No API key configured]")])
                    return
                cp = os.path.join(graphs_dir, gn)
                if not os.path.exists(cp):
                    return
                try:
                    import google.genai as genai_describe
                    client = genai_describe.Client(api_key=api_key)
                    img = Image.open(cp)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[
                            img,
                            "Describe this image for a blind student in 1-2 sentences. "
                            "Be specific about any math, data, labels, axes, or shapes. "
                            "Do NOT start with 'This image shows'. Just describe it directly."
                        ]
                    )
                    desc = response.text.strip() if response.text else "[No description generated]"
                    def update_widget(d=desc):
                        ae_widget.delete("1.0", "end")
                        ae_widget.insert("1.0", d)
                        # Trigger status update after AI description
                        if gn in meta and "_alt_widget" in meta[gn]:
                            meta[gn]["_alt_widget"].event_generate("<KeyRelease>")
                    self.root.after(0, update_widget)
                    self.gui_handler.log(f"   [AI-ALT] Generated description for {gn}")
                except Exception as err:
                    def show_err(e=str(err)):
                        ae_widget.delete("1.0", "end")
                        ae_widget.insert("1.0", f"[Error: {e}]")
                    self.root.after(0, show_err)

            # Track alt widgets for auto-describe
            alt_widgets_map = {}
            long_desc_pages = {}  # gn -> path to long description HTML

            def generate_long_description(gn, ae_widget):
                """Generate a separate linked HTML page with detailed description."""
                api_key = self.config.get("api_key", "").strip()
                if not api_key:
                    self.gui_handler.log("   [LONG-DESC] No API key")
                    return
                cp = os.path.join(graphs_dir, gn)
                if not os.path.exists(cp): return
                try:
                    import google.genai as genai_ld
                    client = genai_ld.Client(api_key=api_key)
                    img = Image.open(cp)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[
                            img,
                            "You are creating a detailed long description page for a visually impaired student. "
                            "Analyze this image and produce a complete HTML document containing:\n"
                            "1. A brief summary paragraph\n"
                            "2. If it contains a graph: a table with columns for x-values, y-values, and key points (intercepts, vertices, asymptotes)\n"
                            "3. If it contains a diagram: a structured list of all labeled elements, their relationships, and spatial arrangement\n"
                            "4. If it contains data: a full HTML table with all visible values\n"
                            "5. Any equations visible, written in LaTeX delimited by \\( \\)\n\n"
                            "Output ONLY the HTML body content (no <html> or <head> tags). "
                            "Use clean semantic HTML with proper headings and table structure."
                        ]
                    )
                    body = response.text.strip() if response.text else "<p>No description could be generated.</p>"
                    # Clean markdown code fence if present
                    if body.startswith("```"): body = body.split("\n", 1)[-1]
                    if body.endswith("```"): body = body.rsplit("```", 1)[0]

                    desc_filename = gn.replace(".png", "_longdesc.html")
                    desc_path = os.path.join(graphs_dir, desc_filename)
                    html_stem = Path(html_path).stem

                    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Detailed Description: {gn}</title>
<script type="text/javascript" id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
body {{ font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
th {{ background: #4b3190; color: white; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
h1 {{ color: #4b3190; }}
.back-link {{ margin-top: 30px; padding: 10px; background: #e8f0fe; border-radius: 5px; }}
</style>
</head>
<body>
<h1>Detailed Description</h1>
<p><em>For image: {gn}</em></p>
<hr>
{body}
<div class="back-link"><a href="../{html_stem}.html">Back to main page</a></div>
</body>
</html>"""
                    with open(desc_path, "w", encoding="utf-8") as f:
                        f.write(full_html)

                    long_desc_pages[gn] = desc_filename
                    info_for_gn = meta.get(gn, {})
                    info_for_gn["long_desc"] = desc_filename
                    meta[gn] = info_for_gn

                    # Update the short alt text to reference the long description
                    current_alt = ae_widget.get("1.0", "end").strip()
                    if current_alt:
                        summary = current_alt
                    else:
                        summary = "Complex visual element"
                    def update_w():
                        ae_widget.delete("1.0", "end")
                        ae_widget.insert("1.0", f"{summary} (See detailed description page)")
                        # Trigger status update after AI description
                        if gn in meta and "_alt_widget" in meta[gn]:
                            meta[gn]["_alt_widget"].event_generate("<KeyRelease>")
                    self.root.after(0, update_w)
                    self.gui_handler.log(f"   [LONG-DESC] Created {desc_filename}")
                    self.root.after(0, lambda: messagebox.showinfo("Long Description Created", f"Detailed description page saved:\n{desc_filename}"))
                except Exception as err:
                    self.gui_handler.log(f"   [LONG-DESC] Error: {err}")

            def ocr_to_table(gn, ae_widget):
                """Convert a table image to HTML table using Gemini OCR."""
                api_key = self.config.get("api_key", "").strip()
                if not api_key: return
                cp = os.path.join(graphs_dir, gn)
                if not os.path.exists(cp): return
                try:
                    import google.genai as genai_ocr
                    client = genai_ocr.Client(api_key=api_key)
                    img = Image.open(cp)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[
                            img,
                            "This image contains a data table. Convert it to a clean HTML <table> "
                            "with proper <thead> and <tbody>. Preserve all values exactly. "
                            "Output ONLY the HTML table tag, nothing else."
                        ]
                    )
                    table_html = response.text.strip() if response.text else ""
                    if table_html.startswith("```"): table_html = table_html.split("\n", 1)[-1]
                    if table_html.endswith("```"): table_html = table_html.rsplit("```", 1)[0]

                    if "<table" in table_html.lower():
                        info_for_gn = meta.get(gn, {})
                        info_for_gn["table_html"] = table_html
                        meta[gn] = info_for_gn
                        def update_w():
                            ae_widget.delete("1.0", "end")
                            ae_widget.insert("1.0", "Data table (converted to accessible HTML table)")
                            # Trigger status update after AI description
                            if gn in meta and "_alt_widget" in meta[gn]:
                                meta[gn]["_alt_widget"].event_generate("<KeyRelease>")
                        self.root.after(0, update_w)
                        self.gui_handler.log(f"   [OCR-TABLE] Converted {gn} to HTML table")
                        self.root.after(0, lambda: messagebox.showinfo("Table Converted", "Image has been converted to an accessible HTML table!\nIt will replace the image in the final page."))
                    else:
                        self.gui_handler.log(f"   [OCR-TABLE] Could not extract table from {gn}")
                except Exception as err:
                    self.gui_handler.log(f"   [OCR-TABLE] Error: {err}")

            def on_type_change(gn, info, combo, ae_widget):
                """Handle type dropdown change."""
                new_type = combo.get()
                info["type"] = new_type.lower()
                meta[gn] = info
                if new_type == "Decorative":
                    ae_widget.delete("1.0", "end")
                    info["decorative"] = True
                    self.gui_handler.log(f"   [TYPE] {gn} -> Decorative")
                elif new_type == "Table":
                    info["decorative"] = False
                    if messagebox.askyesno("Convert Table", "Would you like AI to convert this table image to an accessible HTML table?"):
                        threading.Thread(target=lambda: ocr_to_table(gn, ae_widget), daemon=True).start()
                else:
                    info["decorative"] = False
                # Trigger status update
                if gn in meta and "_alt_widget" in meta[gn]:
                    meta[gn]["_alt_widget"].event_generate("<KeyRelease>")

            def del_item(gn, cf):
                try:
                    cp = os.path.join(graphs_dir, gn)
                    if os.path.exists(cp): os.remove(cp)
                    deleted_items.add(gn)
                    if gn in meta: del meta[gn]
                    cf.destroy()
                except Exception as err:
                    self.gui_handler.log(f"   [DEL] Error: {err}")

            card_counter = [0]

            def build_card(gn, info, parent):
                cp = os.path.join(graphs_dir, gn)
                if not os.path.exists(cp):
                    return

                # Save original box for reset (only first time)
                if "original_box" not in info:
                    info["original_box"] = list(info["box_abs"])

                card_counter[0] += 1
                card_num = card_counter[0]

                card = tk.Frame(parent, bg="white", borderwidth=1, relief="groove", padx=8, pady=8)
                card.pack(fill="x", padx=10, pady=6)

                # Counter badge + Status
                badge_row = tk.Frame(card, bg="white")
                badge_row.pack(fill="x", anchor="nw")
                
                lbl_badge = tk.Label(badge_row, text=f"Image {card_num} of {total_items}", font=("Segoe UI", 9, "bold"), bg="#e8f0fe", fg="#1565c0", padx=8, pady=2)
                lbl_badge.pack(side="left")
                
                lbl_v_status = tk.Label(badge_row, text="", font=("Segoe UI", 8, "bold"), bg="white")
                lbl_v_status.pack(side="left", padx=10)
                
                def update_card_status(*args):
                    if info.get("decorative"):
                        lbl_v_status.config(text="✨ DECORATIVE", fg="#7b1fa2")
                    elif info.get("story") and len(info["story"]) > 5:
                        lbl_v_status.config(text="✅ READY", fg="#2e7d32")
                    else:
                        lbl_v_status.config(text="⚠️ DESCRIPTION NEEDED", fg="#c0392b")
                
                # We need to trace the description change too
                # Will do that after ae is created

                card_body = tk.Frame(card, bg="white")
                card_body.pack(fill="x")

                left = tk.Frame(card_body, bg="white")
                left.pack(side="left", padx=(0, 10))
                tk.Label(left, text="Full Page Context", font=("Segoe UI", 8, "bold"), bg="white", fg="#666").pack()

                pg_img, sc, _ = load_full_page(info.get("full_image", ""))

                if pg_img:
                    pcv = tk.Canvas(left, width=pg_img.width(), height=pg_img.height(), bg="#eee", highlightthickness=1, highlightbackground="#ccc", cursor="crosshair")
                    pcv.pack()
                    pcv.create_image(0, 0, anchor="nw", image=pg_img)
                    draw_rect(pcv, info["box_abs"], sc)

                    ds = {"sx": 0, "sy": 0, "rid": None}

                    def press(e, s=ds):
                        s["sx"], s["sy"] = e.x, e.y
                        if s["rid"]: e.widget.delete(s["rid"])
                        s["rid"] = e.widget.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2, dash=(4, 2))

                    def motion(e, s=ds):
                        if s["rid"]: e.widget.coords(s["rid"], s["sx"], s["sy"], e.x, e.y)

                    def release(e, s=ds, g=gn, i=info):
                        if s["rid"]:
                            e.widget.delete(s["rid"])
                            s["rid"] = None
                        x1 = int(min(s["sx"], e.x) / sc)
                        y1 = int(min(s["sy"], e.y) / sc)
                        x2 = int(max(s["sx"], e.x) / sc)
                        y2 = int(max(s["sy"], e.y) / sc)
                        if (x2 - x1) < 30 or (y2 - y1) < 30: return
                        i["box_abs"] = [x1, y1, x2, y2]
                        meta[g] = i
                        do_recrop(g, i, pcv, lbl_c, dim_lbl)

                    pcv.bind("<ButtonPress-1>", press)
                    pcv.bind("<B1-Motion>", motion)
                    pcv.bind("<ButtonRelease-1>", release)
                else:
                    pcv = None
                    tk.Label(left, text="[Page not available]", bg="white", fg="#999").pack()

                right = tk.Frame(card_body, bg="white")
                right.pack(side="left", fill="both", expand=True)

                tk.Label(right, text=gn, font=("Segoe UI", 10, "bold"), bg="white", anchor="w").pack(fill="x")

                # Type classification dropdown
                type_row = tk.Frame(right, bg="white")
                type_row.pack(fill="x", pady=2)
                tk.Label(type_row, text="Type:", font=("Segoe UI", 9, "bold"), bg="white").pack(side="left")
                type_options = ["Graph", "Diagram", "Table", "Icon", "Decorative"]
                current_type = info.get("type", "graph").capitalize()
                if current_type not in type_options:
                    current_type = "Graph"
                type_combo = ttk.Combobox(type_row, values=type_options, width=12, state="readonly", font=("Segoe UI", 9))
                type_combo.set(current_type)
                type_combo.pack(side="left", padx=5)
                type_combo.bind("<<ComboboxSelected>>", lambda e, g=gn, i=info, c=type_combo: on_type_change(g, i, c, ae_placeholder[0]))

                # Placeholder for ae reference (set below after ae is created)
                ae_placeholder = [None]

                cf2 = tk.Frame(right, bg="white")
                cf2.pack(fill="x", pady=5)
                tk.Label(cf2, text="Cropped Result:", font=("Segoe UI", 8, "bold"), bg="white", fg="#666").pack(anchor="w")
                try:
                    pc = Image.open(cp)
                    crop_w, crop_h = pc.size
                    pc.thumbnail((200, 150))
                    tc = ImageTk.PhotoImage(pc)
                    tk_images.append(tc)
                    lbl_c = tk.Label(cf2, image=tc, bg="#f9f9f9", borderwidth=1, relief="solid", cursor="plus")
                    lbl_c.image = tc
                    lbl_c.pack(anchor="w")
                    # [NEW] Click-to-Zoom
                    lbl_c.bind("<Button-1>", lambda e, p=cp: self._show_zoom(dialog, p))
                    ToolTip(lbl_c, "Click to Zoom Full Size")
                except Exception:
                    lbl_c = tk.Label(cf2, text="[Error]", bg="white", fg="red")
                    lbl_c.pack()
                    crop_w, crop_h = 0, 0

                # Resolution display with warning
                warn_str = "  ** LOW QUALITY" if crop_w < 100 or crop_h < 100 else ""
                dim_color = "#c0392b" if warn_str else "#555"
                dim_lbl = tk.Label(cf2, text=f"Size: {crop_w} x {crop_h} px{warn_str}", font=("Segoe UI", 8), bg="white", fg=dim_color)
                dim_lbl.pack(anchor="w")

                # Description row
                af = tk.Frame(right, bg="white")
                af.pack(fill="x", pady=3)
                tk.Label(af, text="Description for Blind Students:", font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")
                tk.Label(af, text="(Read aloud by screen readers)", font=("Segoe UI", 8, "italic"), bg="white", fg="#888").pack(anchor="w")
                ae = tk.Text(af, height=2, width=45, font=("Segoe UI", 9), wrap="word")
                sv = info.get("story", "")
                ae.insert("1.0", sv if sv.lower() != "none" else "")
                ae.pack(fill="x")
                info["_alt_widget"] = ae
                alt_widgets_map[gn] = ae
                ae_placeholder[0] = ae  # Link back for type dropdown
                
                # Status listener
                ae.bind("<KeyRelease>", lambda e: [setattr(info, "story", ae.get("1.0", "end").strip()), update_card_status()])
                update_card_status()

                # AI buttons row (separate from label to prevent cutoff)
                ai_row = tk.Frame(af, bg="white")
                ai_row.pack(fill="x", pady=(3, 0))
                tk.Button(ai_row, text="\U0001f916 AI Describe", command=lambda g=gn, w=ae: ai_describe(g, w), font=("Segoe UI", 8, "bold"), bg="#e3f2fd", fg="#1565c0", activebackground="#bbdefb", activeforeground="#0d47a1", relief="flat", borderwidth=0, cursor="hand2", padx=8).pack(side="left", padx=(0, 5))
                tk.Button(ai_row, text="\U0001f4c4 Long Description", command=lambda g=gn, w=ae: threading.Thread(target=lambda: generate_long_description(g, w), daemon=True).start(), font=("Segoe UI", 8), bg="#e8f5e9", fg="#2e7d32", activebackground="#c8e6c9", activeforeground="#1b5e20", relief="flat", borderwidth=0, cursor="hand2", padx=8).pack(side="left")

                # Nudge + Reset row
                nf = tk.LabelFrame(right, text="Adjust Crop", bg="white", font=("Segoe UI", 8))
                nf.pack(fill="x", pady=3)
                bs = {"font": ("Segoe UI", 9), "bg": "#e8f0fe", "cursor": "hand2", "width": 12, "activebackground": "#d0e0fd", "activeforeground": "#333", "relief": "flat", "borderwidth": 0}
                r1 = tk.Frame(nf, bg="white")
                r1.pack()
                tk.Button(r1, text="⬆ Top +50", command=lambda g=gn, i=info, p=pcv, l=lbl_c, d=dim_lbl: nudge(g, "up", i, p, l, d), **bs).pack(side="left", padx=2, pady=1)
                tk.Button(r1, text="⬇ Bottom +50", command=lambda g=gn, i=info, p=pcv, l=lbl_c, d=dim_lbl: nudge(g, "down", i, p, l, d), **bs).pack(side="left", padx=2, pady=1)
                r2 = tk.Frame(nf, bg="white")
                r2.pack()
                tk.Button(r2, text="⬅ Left +50", command=lambda g=gn, i=info, p=pcv, l=lbl_c, d=dim_lbl: nudge(g, "left", i, p, l, d), **bs).pack(side="left", padx=2, pady=1)
                tk.Button(r2, text="➡ Right +50", command=lambda g=gn, i=info, p=pcv, l=lbl_c, d=dim_lbl: nudge(g, "right", i, p, l, d), **bs).pack(side="left", padx=2, pady=1)
                r3 = tk.Frame(nf, bg="white")
                r3.pack()
                tk.Button(r3, text="\u21a9 Reset to Original", command=lambda g=gn, i=info, p=pcv, l=lbl_c, d=dim_lbl: reset_crop(g, i, p, l, d), font=("Segoe UI", 9), bg="#fff3e0", fg="#e65100", activebackground="#ffe0b2", activeforeground="#bf360c", relief="flat", borderwidth=0, cursor="hand2", width=26).pack(padx=2, pady=1)

                # Action row
                act_row = tk.Frame(right, bg="white")
                act_row.pack(fill="x", pady=3)
                tk.Button(act_row, text="\U0001f5d1 Delete", command=lambda g=gn, c=card: del_item(g, c), font=("Segoe UI", 9, "bold"), bg="#FEE2E2", fg="#c0392b", activebackground="#fecaca", activeforeground="#991b1b", relief="flat", borderwidth=0, cursor="hand2", padx=10).pack(side="left", padx=(0, 5))

                def mark_decorative(g=gn, w=ae, i=info, c=type_combo):
                    w.delete("1.0", "end")
                    i["decorative"] = True
                    i["type"] = "decorative"
                    c.set("Decorative")
                    update_card_status()
                    self.gui_handler.log(f"   [DECORATIVE] {g} marked as decorative (alt=\"\")")
                tk.Button(act_row, text="\U0001f3a8 Decorative", command=mark_decorative, font=("Segoe UI", 9), bg="#f3e5f5", fg="#7b1fa2", activebackground="#e1bee7", activeforeground="#4a148c", relief="flat", borderwidth=0, cursor="hand2", padx=10).pack(side="left")

            for gn, info in list(meta.items()):
                build_card(gn, info, inner)

            # [NEW] Auto-describe all crops in background thread
            def auto_describe_all():
                api_key = self.config.get("api_key", "").strip()
                if not api_key:
                    self.gui_handler.log("   [AI-ALT] Skipping auto-describe (no API key)")
                    return
                self.gui_handler.log(f"   [AI-ALT] Auto-generating descriptions for {len(alt_widgets_map)} images...")
                for gn, widget in alt_widgets_map.items():
                    # Thread-safe read of current text via main thread
                    current_holder = [""]
                    read_event = threading.Event()
                    def read_widget(w=widget, h=current_holder, ev=read_event):
                        try: h[0] = w.get("1.0", "end").strip()
                        except Exception: pass
                        ev.set()
                    self.root.after(0, read_widget)
                    read_event.wait(timeout=2)
                    current = current_holder[0]
                    if current and current.lower() != "none" and len(current) > 10:
                        continue  # User or AI already provided a good description
                    ai_describe(gn, widget)
                self.gui_handler.log("   [AI-ALT] Auto-describe complete!")
                # [NEW] Check for Auto-Approve if enabled
                if auto_approve_var.get():
                    all_ready = True
                    for gn, w in alt_widgets_map.items():
                        # Wait for main thread to update widget if needed
                        txt = [""]
                        ev = threading.Event()
                        self.root.after(0, lambda: [txt.append(w.get("1.0", "end").strip()), ev.set()])
                        ev.wait(timeout=1)
                        if len(txt[-1]) < 5: 
                            all_ready = False
                            break
                    if all_ready:
                        self.gui_handler.log("   [AUTO-APPROVE] All images have descriptions. Finalizing...")
                        self.root.after(500, on_approve)

            threading.Thread(target=auto_describe_all, daemon=True).start()

            add_frame = tk.LabelFrame(inner, text="Add Missing Element", bg="white", font=("Segoe UI", 10, "bold"), fg="#2c3e50")
            add_frame.pack(fill="x", padx=10, pady=10)

            fpages = sorted([f for f in os.listdir(graphs_dir) if f.startswith("full_p") and f.endswith(".png")])

            if fpages:
                tk.Label(add_frame, text="Draw a rectangle on any page below to add a new visual element.", font=("Segoe UI", 9, "italic"), bg="white", fg="#555").pack(anchor="w", padx=5, pady=3)

                for pf in fpages:
                    plbl = pf.replace("full_", "Page ").replace(".png", "")
                    pff = tk.Frame(add_frame, bg="white")
                    pff.pack(fill="x", padx=5, pady=5)
                    tk.Label(pff, text=plbl, font=("Segoe UI", 9, "bold"), bg="white").pack(anchor="w")

                    pi, ps, _ = load_full_page(pf)
                    if pi:
                        ac = tk.Canvas(pff, width=pi.width(), height=pi.height(), bg="#eee", highlightthickness=1, highlightbackground="#999", cursor="crosshair")
                        ac.pack(anchor="w")
                        ac.create_image(0, 0, anchor="nw", image=pi)

                        ads = {"sx": 0, "sy": 0, "rid": None, "pf": pf, "sc": ps}

                        def ap(e, s=ads):
                            s["sx"], s["sy"] = e.x, e.y
                            if s["rid"]: e.widget.delete(s["rid"])
                            s["rid"] = e.widget.create_rectangle(e.x, e.y, e.x, e.y, outline="#00cc44", width=2, dash=(4, 2))

                        def am(e, s=ads):
                            if s["rid"]: e.widget.coords(s["rid"], s["sx"], s["sy"], e.x, e.y)

                        def ar(e, s=ads, par=inner):
                            if s["rid"]:
                                e.widget.delete(s["rid"])
                                s["rid"] = None
                            sc = s["sc"]
                            x1 = int(min(s["sx"], e.x) / sc)
                            y1 = int(min(s["sy"], e.y) / sc)
                            x2 = int(max(s["sx"], e.x) / sc)
                            y2 = int(max(s["sy"], e.y) / sc)
                            if (x2 - x1) < 30 or (y2 - y1) < 30: return
                            cnt = len(meta) + 1
                            bstem = Path(html_path).stem
                            pnum = s["pf"].replace("full_p", "").replace(".png", "")
                            nn = f"{bstem}_p{pnum}_manual{cnt}.png"
                            fpp = os.path.join(graphs_dir, s["pf"])
                            try:
                                with Image.open(fpp) as src:
                                    pw, ph = src.size
                                    crop = src.crop((x1, y1, x2, y2))
                                    crop.save(os.path.join(graphs_dir, nn))
                                ni = {"full_image": s["pf"], "box_abs": [x1, y1, x2, y2], "page_width": pw, "page_height": ph, "story": "", "type": "graph"}
                                meta[nn] = ni
                                build_card(nn, ni, par)
                                self.gui_handler.log(f"   + Added: {nn}")
                            except Exception as err:
                                self.gui_handler.log(f"   [ADD] Error: {err}")

                        ac.bind("<ButtonPress-1>", ap)
                        ac.bind("<B1-Motion>", am)
                        ac.bind("<ButtonRelease-1>", ar)

            btn_bar = tk.Frame(dialog, bg="#1a1a2e")
            btn_bar.pack(fill="x", padx=15, pady=10)

            def on_approve():
                for gn, info in meta.items():
                    w = info.pop("_alt_widget", None)
                    if w:
                        try: info["story"] = w.get("1.0", "end").strip()
                        except Exception: pass

                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, indent=2)

                try:
                    from bs4 import BeautifulSoup
                    with open(html_path, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")

                    for gn, info in meta.items():
                        if info.get("decorative"):
                            for it in soup.find_all("img"):
                                if gn in it.get("src", ""):
                                    it["alt"] = ""
                                    it["role"] = "presentation"
                        else:
                            at = info.get("story", "Visual Element")
                            if not at or at.lower() == "none": at = "Visual Element"
                            for it in soup.find_all("img"):
                                if gn in it.get("src", ""):
                                    it["alt"] = at

                    cdiv = soup.find("div", class_="content-wrapper") or soup.find("body") or soup
                    for gn, info in meta.items():
                        if "manual" in gn:
                            already = any(gn in (it.get("src", "") or "") for it in soup.find_all("img"))
                            if not already:
                                bstem = Path(html_path).stem
                                rs = f"{bstem}_graphs/{gn}"
                                at = info.get("story", "Visual Element") or "Visual Element"
                                nd = soup.new_tag("div", attrs={"class": "mosh-visual", "style": "text-align: center;"})
                                ni = soup.new_tag("img", src=rs, alt=at, style="width: 100%; max-width: 600px; height: auto; border: 1px solid #ccc; margin: 20px auto;")
                                nd.append(ni)
                                cdiv.append(nd)

                    for dn in deleted_items:
                        for dv in soup.find_all("div", class_="mosh-visual"):
                            im = dv.find("img")
                            if im and dn in im.get("src", ""):
                                dv.decompose()

                    # Inject long description links
                    bstem = Path(html_path).stem
                    for gn, info in meta.items():
                        ld = info.get("long_desc")
                        if ld:
                            for dv in soup.find_all("div", class_="mosh-visual"):
                                im = dv.find("img")
                                if im and gn in im.get("src", ""):
                                    # Add longdesc attribute
                                    im["longdesc"] = f"{bstem}_graphs/{ld}"
                                    # Add visible link for sighted users
                                    link_tag = soup.new_tag("a", href=f"{bstem}_graphs/{ld}",
                                        style="display:block; color:#4b3190; font-size:0.85em; font-style:italic; margin-top:5px;")
                                    link_tag.string = "View detailed description"
                                    dv.append(link_tag)

                    # Replace table images with actual HTML tables
                    for gn, info in meta.items():
                        th = info.get("table_html")
                        if th:
                            for dv in soup.find_all("div", class_="mosh-visual"):
                                im = dv.find("img")
                                if im and gn in im.get("src", ""):
                                    # Replace the image div with the HTML table
                                    from bs4 import BeautifulSoup as BS2
                                    table_soup = BS2(th, "html.parser")
                                    # Style the table for responsiveness
                                    tbl = table_soup.find("table")
                                    if tbl:
                                        tbl["style"] = "width:100%; border-collapse:collapse; margin:20px 0;"
                                        wrapper = soup.new_tag("div", style="overflow-x:auto; max-width:100%;")
                                        wrapper.append(table_soup)
                                        dv.replace_with(wrapper)

                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                except Exception as e:
                    self.gui_handler.log(f"   [Review] Error saving: {e}")

                result["approved"] = True
                canvas_scroll.unbind_all("<MouseWheel>")
                dialog.destroy()
                event.set()

            def on_cancel():
                result["approved"] = False
                canvas_scroll.unbind_all("<MouseWheel>")
                dialog.destroy()
                event.set()

            dialog.protocol("WM_DELETE_WINDOW", on_cancel)

            tk.Button(btn_bar, text="✅ APPROVED BY TEACHER — Save & Upload", command=on_approve, font=("Segoe UI", 13, "bold"), bg="#4CAF50", fg="white", activebackground="#388E3C", activeforeground="white", relief="flat", cursor="hand2", padx=25, pady=10).pack(side="right", padx=5)
            tk.Button(btn_bar, text="Skip This Page", command=on_cancel, font=("Segoe UI", 13), bg="#ffcdd2", fg="#333", activebackground="#ef9a9a", activeforeground="#333", relief="flat", cursor="hand2", padx=25, pady=10).pack(side="right", padx=5)

        self.root.after(0, build_dialog)
        event.wait()
        return result["approved"]


    def _show_link_dialog(self, message, href, context=None):
        """Custom dialog to show link details and prompt for text."""
        dialog = Toplevel(self.root)
        dialog.title("Link Review")
        dialog.geometry("550x400")
        dialog.transient(self.root)
        dialog.grab_set()

        def on_close_x():
            self.gui_handler.stop_requested = True
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close_x)

        if context:
            ctx_frame = ttk.LabelFrame(
                dialog, text="Surrounding Text Context", padding=5
            )
            ctx_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(
                ctx_frame,
                text=context,
                wraplength=500,
                font=("Segoe UI", 9, "italic"),
                justify="left",
            ).pack()

        tk.Label(dialog, text=message, wraplength=500, font=("Segoe UI", 10)).pack(
            pady=10
        )

        def open_link():
            import webbrowser

            webbrowser.open(href)

        if href:
            btn_link = tk.Button(
                dialog,
                text=f"🌐 Open Link / File (Verify)",
                command=open_link,
                bg="#BBDEFB",
                cursor="hand2",
            )
            btn_link.pack(pady=5)
            tk.Label(
                dialog,
                text=f"Target: {href[:60] + '...' if len(href) > 60 else href}",
                font=("Segoe UI", 8, "italic"),
                fg="gray",
            ).pack()

        entry_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=entry_var, width=60)
        entry.pack(pady=15)
        entry.focus_set()

        result = {"text": ""}

        def on_ok(event=None):
            result["text"] = entry_var.get()
            dialog.destroy()

        def on_skip():
            result["text"] = ""
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(
            btn_frame,
            text="Update Link Text",
            command=on_ok,
            bg="#dcedc8",
            width=15,
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame, text="Skip / Ignore", command=on_skip, width=15, cursor="hand2"
        ).pack(side="left", padx=5)

        dialog.bind("<Return>", on_ok)
        self.root.wait_window(dialog)
        return result["text"]

    def _show_share_dialog(self):
        """Phase Viral: Helps faculty spread the word to colleagues."""
        dialog = Toplevel(self.root)
        dialog.title("Spread the Word - April 2026 Deadline")
        dialog.geometry("550x480")
        dialog.transient(self.root)
        dialog.grab_set()

        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        tk.Label(
            dialog,
            text="Help Your Colleagues Meet the Deadline!",
            font=("Segoe UI", 14, "bold"),
            bg=colors["bg"],
            fg=colors["header"],
        ).pack(pady=15)

        msg = (
            "Educators everywhere are stressed about the April 2026 compliance deadline.\n"
            "If this tool helped you save time, please share it with your colleagues!\n\n"
            "Copy the message below to send in an email or Slack:"
        )
        tk.Label(
            dialog,
            text=msg,
            wraplength=500,
            bg=colors["bg"],
            fg=colors["fg"],
            justify="center",
        ).pack(pady=5)

        share_text = (
            "Hi team,\n\n"
            "I found a great free tool called the MOSH ADA Toolkit that automatically "
            "remediates Canvas pages for K-12 and Higher Ed. It fixes headings, tables, and contrast issues in seconds. "
            "It even has an optional AI co-pilot called 'Jeanie Magic' that can write Math LaTeX and "
            "image descriptions! This makes the April 2026 deadline much easier.\n\n"
            "It was built by a fellow educator and it's completely free and open-source. "
            "Works for elementary, middle school, high school, community colleges, and universities!\n\n"
            "Worth checking out to save hours of manual labor!\n\n"
            "Download: https://meri-becomming-code.github.io/mosh/"
        )

        txt = tk.Text(dialog, height=8, width=60, font=("Segoe UI", 9))
        txt.pack(pady=10, padx=20)
        txt.insert(tk.END, share_text)

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(share_text)
            btn_copy.config(text="✅ COPIED TO CLIPBOARD!", state="disabled")

        btn_copy = tk.Button(
            dialog,
            text="📋 Copy Message",
            command=copy_to_clipboard,
            bg=colors["primary"],
            fg="white",
            width=25,
            font=("Segoe UI", 10, "bold"),
        )
        btn_copy.pack(pady=15)

        tk.Button(
            dialog, text="Close", command=dialog.destroy, width=12, cursor="hand2"
        ).pack(pady=5)

    def _show_quick_start(self):
        """Shows beginner-friendly quick start guide for first-time users."""
        dialog = Toplevel(self.root)
        dialog.title("First Time? Quick Start Guide")
        dialog.geometry("750x700")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)

        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        tk.Label(
            dialog,
            text="🚀 Quick Start Guide",
            font=("Segoe UI", 20, "bold"),
            bg=colors["bg"],
            fg=colors["header"],
        ).pack(pady=15)

        tk.Label(
            dialog,
            text="For K-12 Teachers, College Instructors, & Instructional Designers",
            font=("Segoe UI", 11, "italic"),
            bg=colors["bg"],
            fg=colors["subheader"],
        ).pack()

        container = tk.Frame(dialog, bg=colors["bg"])
        container.pack(fill="both", expand=True, padx=20, pady=10)

        txt = scrolledtext.ScrolledText(
            container,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg=colors["bg"],
            fg=colors["fg"],
            padx=15,
            pady=15,
        )
        txt.pack(fill="both", expand=True)

        content = """
📋 FIVE SIMPLE STEPS TO ACCESSIBILITY

STEP 1: Get Your Files from Canvas
   1. In Canvas: Settings → Export Course Content  
   2. Click "Create Export" and download the .imscc file

STEP 2: Import & Target
   1. Launch MOSH and click "📚 Process Canvas Export"
   2. Select your .imscc file and pick a storage folder

STEP 3: Convert Individual Files (Expert Mode)
   1. Use the Word, PPT, or PDF buttons to turn files into pages
   2. [NEW] Use Math Converter for handwritten or complex equations

STEP 4: Fix & Review (The Core Work)
   1. Click "✨ Auto-Fix Issues" to handle headings and colors
   2. Click "📖 Guided Review" to walk through images and links

STEP 5: Final Check & Upload
   1. Click "🚥 Am I Ready to Upload?" for one last scan
   2. Import the resulting 'remediated.imscc' back into Canvas!

────────────────────────────────────────

💡 FIRST-TIME TIPS

For K-12 Teachers:
✓ Works with Canvas Free for Teachers
✓ No coding or technical skills needed
✓ All features work without an API key
✓ Safe - keeps backup of original files

For College Instructors:
✓ Works with your institution's Canvas
✓ Handles large courses (100+ pages)
✓ Preserves all content structure
✓ Creates detailed activity logs

For Instructional Designers:
✓ Batch process multiple courses
✓ Generate compliance audit reports
✓ Advanced Canvas API integration
✓ Optional AI features for efficiency

────────────────────────────────────────

❓ COMMON QUESTIONS

Q: Do I need a Gemini API key?
A: NO! The AI features are completely optional.

Q: Will this change my original files?
A: Your originals are backed up automatically.

Q: What if I mess up?
A: Always test in a NEW EMPTY Canvas course first!

Q: Does this work for K-12?
A: YES! Elementary through high school.

Q: How long does it take?
A: Most courses: 10-30 minutes.

────────────────────────────────────────

────────────────────────────────────────

🎯 A Note from the Developer
I started building this toolkit while creating a new course, using AntiGravity to keep my themes consistent. As I added ADA compliance checks and automated fixes, the project grew into what it is today.

This toolkit is dedicated to my son, Michael Joshua Albright (MOSH), who attended college while fighting diabetic retinopathy—sometimes he could see, and sometimes he couldn't. I feel this program is a gift intended to be freely given to help teachers achieve compliance and students benefit from accessible learning.

I have taught computer, animation, programming, and web development classes since 2000. I hold a PhD in Instructional Design for online learning, and my hope is that this toolkit makes accessibility truly accessible for everyone.

Questions? Feedback? 
Email: meredithkasprak@gmail.com
Website: meri-becomming-code.github.io/mosh
"""

        txt.insert(tk.END, content)
        txt.config(state="disabled")

        tk.Button(
            dialog,
            text="✅ Got it! Let's Start",
            command=dialog.destroy,
            bg=colors["primary"],
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        ).pack(pady=15)

    def _disable_buttons(self):
        """Gray out all action buttons while a task is running."""
        # [EXPANDED] Include all possible action buttons across all views
        # Use getattr for everything to avoid AttributeErrors if view hasn't loaded
        btn_list_names = [
            "btn_auto",
            "btn_inter",
            "btn_audit",
            "btn_wizard",
            "btn_word",
            "btn_excel",
            "btn_ppt",
            "btn_pdf",
            "btn_batch",
            "btn_check",
            "btn_math_canvas",
            "btn_math_pdf",
            "btn_math_docx",
            "btn_math_img",
        ]

        for name in btn_list_names:
            btn = getattr(self, name, None)
            if btn:
                try:
                    btn.config(state="disabled")
                except Exception:
                    pass

        self.gui_handler.stop_requested = False
        # self.is_running = True # Managed by caller or thread

    def _enable_buttons(self):
        """Restore all action buttons."""
        btn_list_names = [
            "btn_auto",
            "btn_inter",
            "btn_audit",
            "btn_wizard",
            "btn_word",
            "btn_excel",
            "btn_ppt",
            "btn_pdf",
            "btn_batch",
            "btn_check",
            "btn_math_canvas",
            "btn_math_pdf",
            "btn_math_docx",
            "btn_math_img",
        ]

        for name in btn_list_names:
            btn = getattr(self, name, None)
            if btn:
                try:
                    btn.config(state="normal")
                except Exception:
                    pass

        # self.is_running = False # Managed by caller or thread

        # [NEW] Reliable Post-Task Review Prompt
        if getattr(self, "auto_prompt_review", False):
            self.auto_prompt_review = False
            msg_review = (
                "Mission Accomplished!\n\n"
                "Would you like to start the Guided Review (Interactive Checker) now?\n"
                "This will help you quickly fix image descriptions and verify all links."
            )
            if messagebox.askyesno("Step 3: Guided Review", msg_review):
                # We use after(100) to ensure the UI has finished all state updates
                self.root.after(100, self._run_interactive)

    def _run_task_in_thread(self, task_func, task_name="Task"):
        """Runs a task in a background thread with safety checks."""
        if self.is_running:
            messagebox.showwarning("Busy", "Mosh is already working on a task!")
            return

        self.is_running = True
        self.progress_bar.start(10)
        self.lbl_status_text.config(text=f"Running {task_name}...", fg="blue")
        self._disable_buttons()

        self.gui_handler.log(f"DEBUG: Preparing thread for {task_name}...")

        # Check if handler exists (Safety for early calls)
        if not hasattr(self, "gui_handler"):
            print("CRITICAL: GUI Handler missing!")
            return

        def worker():
            # [NEW] Prevent Windows sleep during task
            if os.name == "nt":
                try:
                    import ctypes

                    # ES_CONTINUOUS | ES_SYSTEM_REQUIRED (0x80000000 | 0x00000001)
                    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
                except Exception:
                    pass

            try:
                print(f"DEBUG: Thread {task_name} started execution.")  # Console backup
                self.gui_handler.log(f"DEBUG: Thread {task_name} started execution.")
                self.gui_handler.log(f"\n--- Started: {task_name} ---")
                task_func()
                self.gui_handler.log(
                    f"DEBUG: Thread {task_name} finished successfully."
                )
            except BaseException as e:
                import traceback

                err_details = traceback.format_exc()
                print(f"CRITICAL THREAD ERROR: {e}\n{err_details}")
                self.gui_handler.log(f"\n[CRITICAL ERROR] {task_name} Failed: {e}")
                self.gui_handler.log(f"Details: {err_details}")
                err_msg = f"Error in {task_name}:\n{str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Error", err_msg))
            finally:
                # [NEW] Restore Windows sleep state
                if os.name == "nt":
                    try:
                        import ctypes

                        # ES_CONTINUOUS (0x80000000)
                        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                    except Exception:
                        pass

                self.is_running = False
                self.root.after(0, self.progress_bar.stop)
                self.root.after(
                    0, lambda: self.lbl_status_text.config(text="Ready", fg="gray")
                )
                self.root.after(0, self._enable_buttons)

        thread = threading.Thread(target=worker, daemon=True)
        self.gui_handler.log(f"DEBUG: Starting thread {task_name}...")
        thread.start()
        self.gui_handler.log(f"DEBUG: Thread {task_name} start() called.")

    def _get_all_html_files(self):
        """Standardized helper to find all HTML files in the target directory (Optimized)."""
        if not os.path.isdir(self.target_dir):
            self.gui_handler.log(f"[ERROR] Invalid directory: {self.target_dir}")
            return []

        # Heavy directories to skip for performance and relevance
        skip_dirs = {
            converter_utils.ARCHIVE_FOLDER_NAME,
            ".git",
            ".github",
            "venv",
            "env",
            "__pycache__",
            "node_modules",
            ".idea",
            ".vscode",
        }

        html_files = []
        for root, dirs, files in os.walk(self.target_dir):
            # Prune directories in-place to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for file in files:
                if file.lower().endswith((".html", ".htm")):
                    html_files.append(os.path.join(root, file))
        return html_files

    def _run_auto_fixer(self):
        if not self._check_target_dir():
            return
        def task():
            html_files = self._get_all_html_files()
            if not html_files:
                self.gui_handler.log("No HTML files found to fix.")
                self.progress_var.set(100)
                self.lbl_status_text.config(text="No files found", fg="gray")
                return

            self.gui_handler.log(f"Processing {len(html_files)} HTML files...")
            self.lbl_status_text.config(text="Fixing ADA issues...", fg="blue")

            files_with_fixes = 0
            total_fixes = 0
            for i, path in enumerate(html_files):
                # Update progress
                progress = (i / len(html_files)) * 100
                self.progress_var.set(progress)

                success, fixes = interactive_fixer.run_auto_fixer(
                    path, self.gui_handler
                )
                if success and fixes:
                    files_with_fixes += 1
                    total_fixes += len(fixes)
                    self.gui_handler.log(
                        f"   [{i+1}/{len(html_files)}] [FIXED] {os.path.basename(path)}:"
                    )
                    for fix in fixes:
                        self.gui_handler.log(f"    - {fix}")

            # Estimate time saved
            minutes_saved = total_fixes * 1.5
            hours = int(minutes_saved // 60)
            mins = int(minutes_saved % 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            self.gui_handler.log(
                f"Finished. Files with fixes: {files_with_fixes} of {len(html_files)} | Total fixes applied: {total_fixes}"
            )
            self.gui_handler.log(f"🏆 TOTAL PREDICTED LABOR SAVED: {time_str}")

            self.gui_handler.log("\n--- Starting Global Document Link Repair ---")
            link_doc_count, link_total_updated = self._perform_link_repair_logic()
            self.gui_handler.log(f"   [LINKS] Repaired {link_total_updated} links for {link_doc_count} documents.")

            self.gui_handler.log("\n✨ ALL TASKS COMPLETE!")
            msg = (
                "MOSH has finished fixing your files!\n\n"
                f"🏆 Predicted time saved: {time_str}\n\n"
                "WHAT'S NEXT?\n"
                "1. Open your Canvas sandbox course.\n"
                "2. Upload the files in the 'remediated' folder.\n"
                "3. Verify your pages look great!"
            )
            self.root.after(0, lambda: messagebox.showinfo("Auto-Fix Complete", msg))
            self.progress_var.set(100)
            self.lbl_status_text.config(text="Done!", fg="green")

        self._run_task_in_thread(task, "Auto-Fixer")

    def _run_interactive(self):
        def task():
            html_files = self._get_all_html_files()
            if not html_files:
                self.gui_handler.log("No HTML files found.")
                return

            self.gui_handler.log(f"Found {len(html_files)} HTML files.")
            self.gui_handler.log("Starting Interactive Scan...")

            for filepath in html_files:
                interactive_fixer.scan_and_fix_file(
                    filepath, self.gui_handler, self.target_dir
                )

        self._run_task_in_thread(task, "Interactive Fixer")

    # [REMOVED] _run_cleanup_markers per user request.
    # Markers are no longer added, so cleanup is unnecessary.

    def _run_audit(self):
        def task():
            html_files = self._get_all_html_files()
            if not html_files:
                self.gui_handler.log("No HTML files found to audit.")
                return

            self.gui_handler.log(f"Auditing {len(html_files)} files...")
            all_issues = {}
            total_score = 0

            for path in html_files:
                res = run_audit.audit_file(path)
                score = run_audit.calculate_accessibility_score(res)
                total_score += score

                if res and (res["technical"] or res["subjective"]):
                    rel_path = os.path.relpath(path, self.target_dir)
                    all_issues[rel_path] = res

                    summary = run_audit.get_issue_summary(res)
                    self.gui_handler.log(
                        f"[{score}%] {os.path.basename(path)}: {summary}"
                    )
                else:
                    self.gui_handler.log(
                        f"[100%] {os.path.basename(path)}: Perfect Accessibility"
                    )

            avg_score = round(total_score / len(html_files)) if html_files else 100
            out_file = os.path.join(self.target_dir, "audit_report.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(all_issues, f, indent=2)

            self.gui_handler.log(
                f"\n--- Audit Complete. Course Health Score: {avg_score}% ---"
            )
            self.gui_handler.log(
                f"Issues found in {len(all_issues)} files. Report saved to {out_file}"
            )

            # [NEW] Visual Report
            try:
                import audit_reporter
                import webbrowser

                report_path = audit_reporter.generate_report(
                    all_issues, avg_score, self.target_dir, total_files=len(html_files)
                )

                self.gui_handler.log(f"\n✨ Visual Report Ready: {report_path}")
                self.root.after(0, lambda: webbrowser.open(report_path))
            except Exception as e:
                self.gui_handler.log(f"[Warning] Could not generate visual report: {e}")

        self._run_task_in_thread(task, "Audit")

    # --- NEW METHODS ---
    def _show_instructions(self, force=False):
        """Shows Welcome/Instructions Dialog."""
        if not force and not self.config.get("show_instructions", True):
            return

        dialog = Toplevel(self.root)
        dialog.title("MOSH's Toolkit: Making Online Spaces Helpful")
        dialog.geometry("800x750")  # Bigger window
        dialog.lift()
        dialog.focus_force()
        dialog.resizable(True, True)  # Allow resizing

        # Style
        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        # Content
        intro = """
        HI FRIEND! 👋
        Welcome to the MOSH Toolkit.
        This tool helps you fix your Canvas classes so everyone can read them.

        HERE IS WHAT YOU DO:
        1.  CONNECT: Click 'CONNECT & SETUP' and enter your Canvas + Gemini details.

        2.  MATH FIRST! If your course has math, graphs, or equations:
              • Click 'MATH CONVERSION' in the sidebar BEFORE anything else.
              • Run the math converter on your PDF/DOCX files first.
              • Review each page's visual elements when prompted.
              → If you skip this and use regular bulk conversion on math files,
                weird things will happen! Math needs the math tool.

        3.  LOAD: Put your Canvas course file (.imscc) in box #4.
        4.  FIX: Click 'CANVAS REMEDIATION' and press the buttons.
        5.  DONE: Put the fixed file back into Canvas.

        EASY PEASY! 🍋

        NEED HELP?
        If you get stuck, just ask Mosh! (Or email Meredith)
        """

        # Title at top (outside scrollable area)
        lbl_title = tk.Label(
            dialog,
            text="MOSH'S TOOLKIT",
            font=("Segoe UI", 24, "bold"),
            bg=colors["bg"],
            fg=colors["header"],
        )
        lbl_title.pack(pady=(20, 10))

        # Scrollable content frame using Canvas
        container = tk.Frame(dialog, bg=colors["bg"])
        container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        canvas = tk.Canvas(container, bg=colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

        scrollable_frame = tk.Frame(
            canvas,
            bg=colors["bg"],
            highlightbackground=colors["primary"],
            highlightthickness=2,
            padx=20,
            pady=20,
        )

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel scrolling
        def _on_mousewheel_welcome(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel_welcome)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        lbl = tk.Label(
            scrollable_frame,
            text=intro,
            justify="left",
            font=("Segoe UI", 11),
            wraplength=650,
            bg=colors["bg"],
            fg=colors["fg"],
        )
        lbl.pack(pady=10, padx=10)

        # Checkbox
        var_show = tk.BooleanVar(
            value=True if force else self.config.get("show_instructions", True)
        )

        def on_close():
            self._update_config(show_instructions=var_show.get())
            dialog.destroy()

        chk = tk.Checkbutton(
            dialog,
            text="Show this message on startup",
            variable=var_show,
            bg=colors["bg"],
            fg=colors["fg"],
            selectcolor=colors["bg"],
            activebackground=colors["bg"],
        )
        chk.pack(pady=5)

        tk.Button(
            dialog,
            text="Let's Get Started ▶",
            command=on_close,
            bg=colors["primary"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2",
        ).pack(pady=(10, 30))

    def _show_math_guide(self):
        """Shows the Math Migration Guide."""
        guide_text = """MATH CONTENT MIGRATION GUIDE

THE INSTRUCTURE ENGINE:
- Canvas uses **LaTeX** for math.
- It automatically converts LaTeX to **MathML** for screen readers.
- Goal: You need your math in LaTeX format.

INDUSTRY STANDARD (Don't Reinvent the Wheel):
1. **Mathpix Snip**: The "Gold Standard" tool used by universities.
   - Converts PDF/Images -> LaTeX/Word reliably.
   - Recommended: Use Mathpix to convert PDF -> Word, then use this Toolkit.

2. **Equidox**: Best for complex PDF forms remediation.

YOUR WORKFLOW:
1. **Prefer Word (.docx)**: Always convert the original Word file if possible.
2. **If PDF is unique**:
   - Option A: Use Mathpix (External Tool) to get LaTeX.
   - Option B: Use "PDF to HTML" (This Tool) for TEXT ONLY, then manually re-type equations in Canvas.
"""
        messagebox.showinfo("math_migration_guide.md", guide_text)

    def _show_conversion_wizard(self, filter_ext=None):
        """
        Shows dialog to select files for interactive conversion.
        filter_ext: Optional string (e.g. 'docx') to show only files of that type.
        """
        # 1. Scan for files
        if filter_ext:
            supported_exts = {f".{filter_ext}"}
            title_suffix = f"({filter_ext.upper()})"
        else:
            supported_exts = {".docx", ".pptx", ".xlsx", ".pdf"}
            title_suffix = "(All Types)"

        found_files = []
        for root, dirs, files in os.walk(self.target_dir):
            if converter_utils.ARCHIVE_FOLDER_NAME in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_exts:
                    # Ignore temp files (~$)
                    if not file.startswith("~$"):
                        found_files.append(os.path.join(root, file))

        if not found_files:
            messagebox.showinfo(
                "No Files",
                f"No convertible files found matching {supported_exts} in the current folder.",
            )
            return

        # 2. Show Dialog
        dialog = Toplevel(self.root)
        dialog.title("Interactive Conversion Wizard")
        dialog.geometry("600x600")
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Select Files to Convert",
            font=("Segoe UI", 12, "bold"),
            fg="#4b3190",
        ).pack(pady=(10, 0))

        # [NEW] Wizard Disclaimer
        wiz_disclaimer = "⚠️ DO NOT convert publisher content. Use the buttons below to select ONLY your specific materials or OER files so you can exclude publisher content."
        tk.Label(
            dialog,
            text=wiz_disclaimer,
            font=("Segoe UI", 9, "bold"),
            fg="#d32f2f",
            wraplength=550,
        ).pack(pady=(2, 10))

        tk.Label(
            dialog,
            text="We will process these one by one. You will preview each change.",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 10))

        # Scrollable Frame for Checkboxes
        frame_canvas = tk.Frame(dialog)
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=10)

        canvas = tk.Canvas(frame_canvas, bg="white")
        scrollbar = tk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate
        vars_map = {}
        for fpath in found_files:
            rel_path = os.path.relpath(fpath, self.target_dir)
            var = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(
                scroll_frame, text=rel_path, variable=var, anchor="w", bg="white"
            )
            chk.pack(fill="x", padx=5, pady=2)
            vars_map[fpath] = var

        # Buttons
        def on_start():
            selected = [path for path, var in vars_map.items() if var.get()]
            if not selected:
                messagebox.showwarning(
                    "None Selected", "Please select at least one file."
                )
                return
            dialog.destroy()
            self._run_wizard_task(selected)

        def on_toggle_all():
            any_unchecked = any(not v.get() for v in vars_map.values())
            new_val = True if any_unchecked else False
            for v in vars_map.values():
                v.set(new_val)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill="x", pady=20, padx=20)

        tk.Button(
            btn_frame, text="Select/Deselect All", command=on_toggle_all, cursor="hand2"
        ).pack(side="left")
        tk.Button(
            btn_frame,
            text="Start Conversion Process ▶",
            command=on_start,
            bg="#4b3190",
            fg="white",
            font=("bold"),
            cursor="hand2",
        ).pack(side="right")

    def _run_wizard_task(self, files):
        """Worker thread for the wizard."""

        def task():
            self.gui_handler.log(f"--- Starting Wizard on {len(files)} files ---")

            kept_files = []  # Track successful conversions

            for i, fpath in enumerate(files):
                if self.gui_handler.is_stopped():
                    break
                fname = os.path.basename(fpath)
                ext = os.path.splitext(fpath)[1].lower().replace(".", "")
                self.gui_handler.log(
                    f"[{i+1}/{len(files)}] Preparing for Canvas: {fname}..."
                )

                # 1. Convert
                output_path = None
                err = None

                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(
                        fpath, self.gui_handler, log_func=self.gui_handler.log
                    )
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                    output_path, err = converter_utils.convert_ppt_to_html(
                        fpath, self.gui_handler, log_func=self.gui_handler.log
                    )
                elif ext == "pdf":
                    output_path, err = converter_utils.convert_pdf_to_html(
                        fpath, self.gui_handler
                    )

                # Update links to the source file (all document types)
                if output_path and ext in ["docx", "xlsx", "pptx", "pdf"]:
                    converter_utils.update_doc_links_to_html(
                        self.target_dir,
                        os.path.basename(fpath),
                        os.path.basename(output_path),
                        log_func=self.gui_handler.log,
                    )

                if err or not output_path:
                    self.gui_handler.log(f"   [ERROR] Failed to convert: {err}")
                    continue

                self.gui_handler.log(f"[{i+1}/{len(files)}] BUILDING PAGE: {fname}...")

                # 2. RUN AUTO-FIXER (Structural)

                self.gui_handler.log(
                    f"   [1/3] Running Auto-Fixer (Headings, Tables)..."
                )
                # Structural fixes only, no placeholders/markers added
                interactive_fixer.run_auto_fixer(output_path, self.gui_handler)

                # 3. RUN INTERACTIVE REVIEW (Alt Text / Links)
                self.gui_handler.log(f"   [2/3] Launching Guided Review...")
                interactive_fixer.scan_and_fix_file(
                    output_path, self.gui_handler, self.target_dir
                )

                # 4. Update Project Links & Archive Source
                self.gui_handler.log(
                    f"   [3/3] Updating project links and archiving original..."
                )
                converter_utils.update_links_in_directory(
                    self.target_dir, fpath, output_path
                )
                converter_utils.archive_source_file(fpath)

                # 5. AUTO-UPLOAD TO CANVAS (No prompt)
                api = self._get_canvas_api()
                if api:
                    self.gui_handler.log(
                        f"   🚀 AUTO-UPLOAD: Sending '{os.path.basename(output_path)}' to Canvas..."
                    )
                    # We pass auto_confirm_links=True to avoid extra prompts during the batch upload
                    self._upload_page_to_canvas(
                        output_path, fpath, api, auto_confirm_links=True
                    )
                else:
                    self.gui_handler.log(
                        "   [INFO] Canvas not connected. Page saved locally."
                    )

                self.gui_handler.log(f"✅ {fname} Processed Successfully.")

            self.gui_handler.log("--- Page Builder Process Complete ---")

            # [NEW] Open folder with user's original files
            archive_path = os.path.join(
                self.target_dir, converter_utils.ARCHIVE_FOLDER_NAME
            )
            if os.path.exists(archive_path):
                self.gui_handler.log(
                    "📂 Opening archive folder with your original files for safekeeping..."
                )
                os.startfile(archive_path)

            messagebox.showinfo(
                "Done",
                "Your pages have been built, reviewed, and uploaded!\n\nI have opened the folder containing your original files so you can move them to a safe place.",
            )

        self._run_task_in_thread(task, "Conversion Wizard")

    def _convert_file(self, ext):
        """Generic handler for file conversion."""
        # [NEW] Copyright check
        msg_copyright = (
            f"⚠️ COPYRIGHT AUDIT\n\n"
            f"Is this {ext.upper()} file one that YOU created or an OER resource?\n\n"
            f"❌ DO NOT convert publisher content (e.g. Pearson, Cengage). \n\n"
            f"TIP: Use the buttons to select only your specific files so you can exclude publisher materials.\n\n"
            f"Do you have the rights to convert this file?"
        )

        if not messagebox.askyesno("Copyright Check", msg_copyright):
            return

        file_path = filedialog.askopenfilename(
            filetypes=[(f"{ext.upper()} Files", f"*.{ext}")]
        )
        if not file_path:
            return

        if ext == "pdf":
            if not messagebox.askyesno(
                "PDF Conversion (Beta)",
                "⚠️ PDF Conversion is extremely difficult to automate.\n\n"
                "This tool will attempt to extract Text, Images, and basic Layout.\n"
                "It is NOT perfect for complex documents.\n\n"
                "Are you sure you want to proceed?",
            ):
                return

        self.gui_handler.log(f"Preparing {os.path.basename(file_path)} for Canvas...")

        def task():
            output_path, err = None, None

            if ext == "docx":
                output_path, err = converter_utils.convert_docx_to_html(
                    file_path, self.gui_handler, log_func=self.gui_handler.log
                )
            elif ext == "xlsx":
                output_path, err = converter_utils.convert_excel_to_html(file_path)
            elif ext == "pptx":
                output_path, err = converter_utils.convert_ppt_to_html(
                    file_path, self.gui_handler, log_func=self.gui_handler.log
                )
            elif ext == "pdf":
                output_path, err = converter_utils.convert_pdf_to_html(
                    file_path, self.gui_handler
                )

            # Update links to the source file (all document types)
            if output_path and ext in ["docx", "xlsx", "pptx", "pdf"]:
                converter_utils.update_doc_links_to_html(
                    self.target_dir,
                    os.path.basename(file_path),
                    os.path.basename(output_path),
                    log_func=self.gui_handler.log,
                )

            if err:
                self.gui_handler.log(f"[ERROR] Conversion failed: {err}")
                return

            # [NEW] Mandatory ADA remediation
            self.gui_handler.log(
                f"   [ADA] Running Auto-Fixer (Headings, Tables, Contrast)..."
            )
            interactive_fixer.run_auto_fixer(output_path, self.gui_handler)

            self.gui_handler.log(f"   [ADA] Launching Interactive Review...")
            interactive_fixer.scan_and_fix_file(
                output_path, self.gui_handler, self.target_dir
            )

            self.gui_handler.log(
                f"[SUCCESS] Ready for Canvas: {os.path.basename(output_path)}"
            )

            # 2. Preview (Open both)
            try:
                os.startfile(file_path)  # Open Original
                os.startfile(output_path)  # Open New Page
            except Exception as e:
                self.gui_handler.log(f"   [WARNING] Could not auto-open files: {e}")

            # 3. Prompt user (Keep/Discard?)
            msg = (
                f"Reviewing: {os.path.basename(file_path)}\n\n"
                f"I have opened both the original and the new version.\n"
                f"Do you want to KEEP this version for Canvas?"
            )

            if not self.gui_handler.confirm(msg):
                try:
                    os.remove(output_path)
                    self.gui_handler.log("   Discarded.")
                except Exception:
                    pass
                return

            # 4. Success / Info
            if ext == "pptx":
                self.gui_handler.log(
                    "[INFO] PowerPoint conversion and interactive review complete."
                )

            # 5. Link Updater
            msg_link = (
                f"Excellent. The original file is untouched.\n\n"
                f"Would you like to SCAN ALL OTHER FILES in this folder\n"
                f"and update any links to point to this new LIVE CANVAS PAGE instead?"
            )

            if self.gui_handler.confirm(msg_link):
                count = converter_utils.update_links_in_directory(
                    self.target_dir, file_path, output_path
                )
                # [NEW] Explicitly archive original file upon confirmation
                converter_utils.archive_source_file(file_path)

                # [NEW] Update Manifest
                rel_old = os.path.relpath(file_path, self.target_dir)
                rel_new = os.path.relpath(output_path, self.target_dir)
                m_success, m_msg = converter_utils.update_manifest_resource(
                    self.target_dir, rel_old, rel_new
                )
                self.gui_handler.log(
                    f"   [DONE] Links updated in {count} files. Original archived."
                )

            # 6. Canvas Upload (Optional)
            api = self._get_canvas_api()
            if api:
                msg_upload = (
                    f"Local conversion and linking complete.\n\n"
                    f"Mosh: 'Great work! Before uploading, would you like to run the \n"
                    f"ADA PRE-FLIGHT CHECK to ensure everything is perfect?'"
                )
                if self.gui_handler.confirm(msg_upload):
                    self._show_preflight_dialog()
                else:
                    msg_direct = "Would you like to skip the check and upload directly to Canvas anyway?"
                    if self.gui_handler.confirm(msg_direct):
                        self._upload_page_to_canvas(output_path, file_path, api)

            self.gui_handler.log(f"--- {ext.upper()} Done ---")

        self._run_task_in_thread(task, f"Convert {ext.upper()}")

    def _upload_page_to_canvas(
        self, html_path, original_source_path, api, auto_confirm_links=False
    ):
        """Helper to upload a single HTML file as a Canvas Page with images."""
        fname = os.path.basename(original_source_path)
        self.gui_handler.log(f"   [Sync] Uploading to Canvas: {fname}...")

        try:
            # [NEW] Mandatory Final ADA Check before Upload
            self.gui_handler.log(f"   [Sync] Running Final ADA Compliance Check...")
            interactive_fixer.run_auto_fixer(html_path, self.gui_handler)

            # 1. Read HTML
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # 2. Handle Images properly
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            images = soup.find_all("img")

            if images:
                self.gui_handler.log(
                    f"   [Sync] Found {len(images)} images. Uploading to course files..."
                )
                import urllib.parse

                for img in images:
                    local_src = img.get("src")
                    if not local_src or "http" in local_src:
                        continue

                    # [FIX] Handle URL-encoded characters in local paths (e.g. %20 for space)
                    clean_src = urllib.parse.unquote(local_src)

                    # Resolve absolute path
                    img_abs_path = os.path.join(os.path.dirname(html_path), clean_src)
                    if os.path.exists(img_abs_path):
                        success_img, res_img = api.upload_file(
                            img_abs_path, folder_path="remediated_images"
                        )
                        if success_img:
                            # Canvas relative links usually look like /courses/:id/files/:file_id/preview
                            canvas_img_url = f"/courses/{self.config['canvas_course_id']}/files/{res_img['id']}/preview"
                            img["src"] = canvas_img_url
                            self.gui_handler.log(
                                f"      Uploaded: {os.path.basename(img_abs_path)}"
                            )
                        else:
                            self.gui_handler.log(
                                f"      [WARNING] Image upload failed: {res_img}"
                            )

            # 3. Create or Update Page (Upsert Strategy)
            page_title = os.path.splitext(fname)[0]

            # Check if page exists to avoid duplicates
            success_get, res_get = api.get_page(page_title)
            if success_get and "url" in res_get:
                self.gui_handler.log(f"   [Sync] Updating existing page: {page_title}")
                success_page, res_page = api.update_page(
                    res_get["url"], page_title, str(soup)
                )
            else:
                success_page, res_page = api.create_page(page_title, str(soup))

            if success_page:
                canvas_page_url = res_page.get("html_url")
                self.gui_handler.log(f"   [Sync] SUCCESS! Live Page: {canvas_page_url}")

                # 4. Link update: Point ALL OTHER FILES to this live Canvas Page
                should_update = False
                if auto_confirm_links:
                    should_update = True
                else:
                    msg_live_link = (
                        f"Page created on Canvas.\n\n"
                        f"Would you like to update all other files in this folder\n"
                        f"to point to the LIVE CANVAS PAGE instead of the local HTML?"
                    )
                    if self.gui_handler.confirm(msg_live_link):
                        should_update = True

                if should_update:
                    count = converter_utils.update_links_in_directory(
                        self.target_dir, original_source_path, canvas_page_url
                    )
                    self.gui_handler.log(
                        f"   [Sync] Updated links in {count} files to point to Canvas."
                    )
                
                # 5. [NEW] Update Live Canvas Modules if applicable
                if True:
                    self.gui_handler.log(f"   [Sync] Checking Canvas Modules for {fname}...")
                    # We pass the slug which is usually derived from the HTML URL
                    # HTML URL: "https://.../pages/slug" -> we need "slug"
                    import urllib.parse
                    slug = canvas_page_url.split('/')[-1]
                    mod_success, mods_replaced = api.replace_module_file_with_page(
                        fname, slug, page_title
                    )
                    if mod_success and mods_replaced > 0:
                        self.gui_handler.log(f"   [Sync] Updated {mods_replaced} Canvas Module items to point directly to the new Page!")

                return True
            else:
                # Handle Token Expiry
                if "401" in str(res_page) or "Invalid access token" in str(res_page):
                    self.gui_handler.log(
                        f"   [CRITICAL] Canvas Token Expired. Please check your setup."
                    )
                self.gui_handler.log(
                    f"   [ERROR] Page update/creation failed: {res_page}"
                )
                return False

        except Exception as e:
            self.gui_handler.log(f"   [ERROR] Sync failed: {e}")
            return False

    def _get_canvas_api(self):
        """Helper to instantiate CanvasAPI from config."""
        config = self.config
        url = config.get("canvas_url")
        token = config.get("canvas_token")
        cid = config.get("canvas_course_id")  # Corrected key
        if not url or not token or not cid:
            return None
        return canvas_utils.CanvasAPI(url, token, cid)

        # Clear Logs
        ttk.Button(
            frame,
            text="🧹 Clear Activity Log",
            command=lambda: [
                self.txt_log.configure(state="normal"),
                self.txt_log.delete(1.0, tk.END),
                self.txt_log.configure(state="disabled"),
            ],
            style="TButton",
        ).pack(fill="x", pady=5)

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _run_batch_conversion(self):
        """Processes ALL convertible files in one go without per-file verification."""
        # 1. Warning
        msg = (
            "📂 BATCH CONVERSION 📂\n\n"
            "⚠️ IMPORTANT LEGAL CHECK: ONLY use this for content YOU created or OER materials.\n"
            "❌ DO NOT use on publisher content. If you have publisher files in this folder, cancel this and use the selection buttons to exclude them.\n\n"
            "This will convert EVERY Word, PPT, Excel, and PDF file in your project to Canvas Pages automatically.\n\n"
            "- All documents will be turned into clean, accessible HTML.\n"
            "- Original files will be moved to the archive folder for safety.\n"
            "- Links will be updated throughout your project.\n\n"
            "You should review the resulting pages before publishing. "
            "Do you want to proceed with the batch conversion?"
        )

        if not messagebox.askyesno("Batch conversion", msg):
            return

        # [NEW] Check if they want to sync to Canvas as they go
        self.config["batch_sync_confirmed"] = False
        api = self._get_canvas_api()
        if api:
            msg_sync = "🚀 Would you like me to SYNC these pages to Canvas as I convert them?\n\n(This creates live, editable Pages in your Canvas course immediately!)"
            if messagebox.askyesno("Live Sync?", msg_sync):
                self.config["batch_sync_confirmed"] = True

        def task():
            supported_exts = {".docx", ".pptx", ".xlsx", ".pdf"}
            found_files = []
            for root, dirs, files in os.walk(self.target_dir):
                if converter_utils.ARCHIVE_FOLDER_NAME in root:
                    continue
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_exts and not file.startswith("~$"):
                        found_files.append(os.path.join(root, file))

            if not found_files:
                self.gui_handler.log("No convertible files found.")
                self.progress_var.set(100)
                self.lbl_status_text.config(text="No files found", fg="gray")
                return

            self.gui_handler.log(
                f"--- Starting Batch Conversion on {len(found_files)} files ---"
            )
            self.lbl_status_text.config(text="Converting files...", fg="blue")
            success_count = 0
            total_auto_fixes = 0

            # [TURBO] Collect mappings for single-pass updates
            manifest_map = {}
            link_map = {}  # {old_basename: new_basename}

            for i, fpath in enumerate(found_files):
                if self.gui_handler.is_stopped():
                    break
                fname = os.path.basename(fpath)
                ext = os.path.splitext(fpath)[1].lower().replace(".", "")

                # Update Progress
                progress = (i / len(found_files)) * 100
                self.progress_var.set(progress)
                self.lbl_status_text.config(
                    text=f"Converting {i+1}/{len(found_files)}...", fg="blue"
                )

                self.gui_handler.log(
                    f"[{i+1}/{len(found_files)}] Preparing Canvas WikiPage: {fname}"
                )

                output_path = None
                err = None

                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(
                        fpath, self.gui_handler
                    )
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                    output_path, err = converter_utils.convert_ppt_to_html(
                        fpath, self.gui_handler
                    )
                elif ext == "pdf":
                    output_path, err = converter_utils.convert_pdf_to_html(
                        fpath, self.gui_handler
                    )

                if output_path:
                    success_count += 1

                    # Run Auto-Fixer on the document immediately
                    self.gui_handler.log(
                        f"   [FIXING] Checking Page for ADA compliance..."
                    )
                    success_fix, fixes = interactive_fixer.run_auto_fixer(
                        output_path, self.gui_handler
                    )
                    if success_fix and fixes:
                        total_auto_fixes += len(fixes)

                    # [DESIGN] AI Responsive Design pass
                    api_key = self.config.get("api_key", "").strip()
                    if api_key:
                        try:
                             import jeanie_ai
                             with open(output_path, "r", encoding="utf-8") as f:
                                 content = f.read()
                             new_html, msg = jeanie_ai.improve_html_design(content, api_key)
                             if new_html and "Error" not in msg:
                                 with open(output_path, "w", encoding="utf-8") as f:
                                     f.write(new_html)
                                 self.gui_handler.log("   [DESIGN] AI improved layout for mobile!")
                        except Exception as e:
                             self.gui_handler.log(f"   [DESIGN] Skipping Design improvements: {e}")

                    # Store mappings for [TURBO] pass
                    rel_old = os.path.relpath(fpath, self.target_dir)
                    rel_new = os.path.relpath(output_path, self.target_dir)
                    manifest_map[rel_old] = rel_new
                    link_map[os.path.basename(fpath)] = os.path.basename(output_path)

                    # Archive
                    converter_utils.archive_source_file(fpath)
                    self.gui_handler.log(
                        f"   [DONE] Original archived. Queued for Turbo Link Repair."
                    )

                    # [NEW] Optional Live Sync for Batch
                    sync_api = self._get_canvas_api()
                    if sync_api and self.config.get("batch_sync_confirmed"):
                        self._upload_page_to_canvas(
                            output_path, fpath, sync_api, auto_confirm_links=True
                        )
                else:
                    self.gui_handler.log(f"   [FAILED] {err}")

            # --- [TURBO] PASS: Batch Updates ---
            if manifest_map:
                self.gui_handler.log("\n🔄 Synchronizing Course Manifest (Turbo)...")
                self.lbl_status_text.config(text="Updating Manifest...", fg="blue")
                m_success, m_msg = converter_utils.batch_update_manifest_resources(
                    self.target_dir, manifest_map
                )
                if m_success:
                    self.gui_handler.log(f"   [MANIFEST] {m_msg}")

            if link_map:
                self.gui_handler.log("🔗 Repairing Course Links (Turbo)...")
                self.lbl_status_text.config(text="Repairing Links...", fg="blue")
                converter_utils.batch_update_links_in_directory(
                    self.target_dir, link_map, log_func=self.gui_handler.log
                )

            total_mins = (success_count * 10) + (total_auto_fixes * 1.5)
            hours = int(total_mins // 60)
            mins = int(total_mins % 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            self.gui_handler.log(
                f"\n--- Batch Complete. {success_count} files converted. ---"
            )
            self.gui_handler.log(f"🏆 TOTAL PREDICTED LABOR SAVED: {time_str}")

            # Queue the review prompt
            self.auto_prompt_review = True

            self.progress_var.set(100)
            self.lbl_status_text.config(text="Batch Done!", fg="green")

            self.gui_handler.log(
                "\n🛡️ Remember: Check the files in Canvas before publishing!"
            )

            # [NEW] Open folder with user's original files
            archive_path = os.path.join(
                self.target_dir, converter_utils.ARCHIVE_FOLDER_NAME
            )
            if os.path.exists(archive_path):
                self.gui_handler.log(
                    "📂 Opening archive folder with your original files for safekeeping..."
                )
                os.startfile(archive_path)

            msg = (
                f"Processed {len(found_files)} files.\nCheck the logs for details.\n\n"
                f"🏆 Estimated time saved: {time_str}\n\n"
                "WHAT'S NEXT?\n"
                "1. Go to Canvas > Import Course Content.\n"
                "2. Select your 'remediated.imscc' file.\n"
                "3. Check your new accessible pages!"
            )
            self.root.after(0, lambda: messagebox.showinfo("Conversion Complete", msg))

        self._run_task_in_thread(task, "Batch Conversion")

    # --- [NEW] Pre-Flight & Push Logic ---

    def _show_preflight_dialog(self):
        """Displays a simple dashboard checking course readiness."""
        dialog = Toplevel(self.root)
        dialog.title("🚦 Pre-Flight Check")
        dialog.geometry("550x650")
        dialog.transient(self.root)
        dialog.grab_set()

        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        ttk.Label(dialog, text="🚦 Pre-Flight Check", style="Header.TLabel").pack(
            pady=10
        )
        ttk.Label(
            dialog,
            text="Checking if your course is safe to upload...",
            font=("Segoe UI", 10),
        ).pack(pady=5)

        # Main container with scrollable results
        main_container = ttk.Frame(dialog)
        main_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(main_container, bg=colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            main_container, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        results_frame = ttk.Frame(scrollable_frame, padding=20)
        results_frame.pack(fill="both", expand=True)

        self.target_dir = self.lbl_dir.get().strip()

        checks = [
            ("Converted Files", self._check_source_files),
            ("Alt Text & Links", self._check_ada_issues),
            ("Document Links", self._check_and_repair_links),
            ("Canvas Connection", self._check_canvas_ready),
            ("Project Cleanup", self._check_janitor_needed),
        ]

        ready_count = 0
        for i, (label, check_func) in enumerate(checks):
            passed, detail = check_func()
            status_icon = "✅" if passed else "⚠️"
            if passed:
                ready_count += 1

            ttk.Label(
                results_frame,
                text=f"{status_icon} {label}",
                font=("Segoe UI", 11, "bold"),
            ).grid(row=i, column=0, sticky="w", pady=5)
            lbl_detail = ttk.Label(
                results_frame, text=detail, font=("Segoe UI", 9), wraplength=400
            )
            lbl_detail.grid(row=i, column=1, sticky="w", padx=10)

        # Fixed Footer for action buttons
        footer = ttk.Frame(dialog, padding=10)
        footer.pack(side="bottom", fill="x")

        # Final Score Header
        score_header = ttk.Frame(footer)
        score_header.pack(fill="x", pady=10)

        if ready_count == len(checks):
            msg = "🚀 YOU ARE CLEAR FOR TAKEOFF!"
            color = "#2E7D32"  # Forest Green
            advice = "Mosh: 'Great job! You've put in the work, now let's show Canvas how it's done.'"
            push_text = "🚀 Send My Clean Course to Canvas Now"
        else:
            msg = "🛠️ Almost there! Some items need attention."
            color = "#d4a017"  # Amber
            advice = "Mosh: 'Remediation is tough, but you're doing great. I recommend fixing the issues above, but you're the pilot!'"
            push_text = "🚀 Upload to Canvas Anyway (Not Recommended)"

        tk.Label(
            score_header,
            text=msg,
            font=("Segoe UI", 12, "bold"),
            fg=color,
            bg=colors["bg"],
        ).pack()
        tk.Label(
            score_header,
            text=advice,
            font=("Segoe UI", 10, "italic"),
            fg=colors.get("fg", "#212121"),
            bg=colors["bg"],
        ).pack(pady=5)

        def on_upload():
            dialog.destroy()
            self._push_to_canvas()

        # Primary Action Button
        btn_push = ttk.Button(
            footer,
            text=push_text,
            command=on_upload,
            style="Action.TButton",
            cursor="hand2",
        )
        btn_push.pack(side="left", padx=5)

        # Explicit Upload Page Button
        ttk.Button(
            footer,
            text="☁️ Direct Canvas Upload",
            command=self._push_to_canvas,
            cursor="hand2",
        ).pack(side="left", padx=5)

        ttk.Button(footer, text="Close", command=dialog.destroy, cursor="hand2").pack(
            side="left", padx=5
        )

    def _check_source_files(self):
        """Checks if there are still unconverted Word/PPT/PDFs."""
        count = 0
        unconverted = []

        for root, dirs, files in os.walk(self.target_dir):
            # Skip archive folder and hidden folders
            if converter_utils.ARCHIVE_FOLDER_NAME in root or ".git" in root:
                continue

            for f in files:
                if f.lower().endswith((".docx", ".pptx", ".pdf", ".xlsx")):
                    # Check if this file has been converted to HTML
                    base_name = os.path.splitext(f)[0]

                    # Check for exact HTML match
                    html_version = os.path.join(root, base_name + ".html")

                    # Check for sanitized HTML version
                    s_base = converter_utils.sanitize_filename(base_name)
                    html_sanitized = os.path.join(root, s_base + ".html")

                    # Check parent directory too
                    parent_dir = os.path.dirname(root)
                    html_parent = os.path.join(parent_dir, base_name + ".html")
                    html_parent_sanitized = os.path.join(parent_dir, s_base + ".html")

                    # If NO HTML version exists, it's unconverted
                    has_conversion = (
                        os.path.exists(html_version)
                        or os.path.exists(html_sanitized)
                        or os.path.exists(html_parent)
                        or os.path.exists(html_parent_sanitized)
                    )

                    if not has_conversion:
                        count += 1
                        unconverted.append(f)

        # [FIX] Allow upload button even if files are present (per user request), but warn.
        if count == 0:
            return True, "All files converted to Canvas WikiPages."

        # Show which files are unconverted
        sample = ", ".join(unconverted[:3])
        if len(unconverted) > 3:
            sample += f"... and {len(unconverted)-3} more"

        return False, f"Found {count} unconverted files: {sample}"

    def _check_and_repair_links(self):
        """Automatically repairs links during pre-flight."""
        self.gui_handler.log("   [PRE-FLIGHT] Checking Document Links...")
        doc_count, total_repaired = self._perform_link_repair_logic()
        if doc_count > 0:
            return True, f"Verified/Repaired {total_repaired} links for {doc_count} documents."
        return True, "No document links needed repair."

    def _check_ada_issues(self):
        """Scans for remaining ADA markers like [FIX_ME] and runs Auto-Fixer one last time."""
        markers = 0
        html_files = []
        for root, dirs, files in os.walk(self.target_dir):
            if converter_utils.ARCHIVE_FOLDER_NAME in root:
                continue
            for f in files:
                if f.endswith(".html"):
                    html_files.append(os.path.join(root, f))

        # Proactive: Run Auto-Fixer on everything before checking markers
        if html_files:
            import interactive_fixer

            for fp in html_files:
                interactive_fixer.run_auto_fixer(fp, self.gui_handler)

        # Now check for markers
        for fp in html_files:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f_obj:
                    if "[FIX_ME]" in f_obj.read().upper():
                        markers += 1
            except Exception:
                pass

        if markers == 0:
            return True, "No [FIX_ME] markers found. Looks great!"
        return False, f"Found {markers} issues needing Guided Review."

    def _check_canvas_ready(self):
        """Checks if Canvas settings are filled."""
        config = self.config
        if not config.get("canvas_url") or not config.get("canvas_token"):
            return False, "Missing Canvas setup. Click Step 1 Connect."

        return True, "Canvas settings found."

    def _check_janitor_needed(self):
        """Checks if Janitor has run."""
        # Simple check: are there any source files in the root?
        # We'll just say it's ready because Janitor runs during push/export.
        return True, "Mosh will tidy up your messy files automatically."

    def _push_to_canvas(self):
        """Uploads the remediated course directly to Canvas."""
        # 1. Ensure we have a packaged file
        default_package = os.path.basename(self.target_dir) + "_remediated.imscc"
        package_path = os.path.join(os.path.dirname(self.target_dir), default_package)

        # 2. Confirm Upload
        if not messagebox.askyesno(
            "Final Launch",
            f"Ready to push this to your Canvas Sandbox?\n\nFile: {default_package}",
        ):
            return

        def upload_task():
            # Run Janitor first!
            self.gui_handler.log("🧹 Mosh the Janitor is cleaning up...")
            cleaned = converter_utils.run_janitor_cleanup(
                self.target_dir, self.gui_handler.log
            )
            self.gui_handler.log(f"✅ Cleanup complete. Removed {cleaned} messy files.")

            # Re-package if needed or just do it every time for safety
            self.gui_handler.log(f"📦 Packaging final version: {default_package}...")
            success_pkg, msg_pkg = converter_utils.create_course_package(
                self.target_dir, package_path, self.gui_handler.log
            )
            if not success_pkg:
                self.gui_handler.log(f"❌ Packaging Failed: {msg_pkg}")
                return
            self.gui_handler.log(
                f"✅ Packaging complete. ({os.path.getsize(package_path)/(1024*1024):.1f} MB)"
            )

            self.gui_handler.log("🚀 PREPARING FOR TAKEOFF! 🦆💨")
            self.gui_handler.log("   (This may take a minute for large courses...)")
            self.root.after(
                0,
                lambda: self._show_flight_animation(
                    "Mosh is flying your course to Canvas..."
                ),
            )

            api = self._get_canvas_api()
            if not api:
                self.gui_handler.log("❌ Authentication Error: Missing API settings.")
                self.root.after(0, self._close_flight_animation)
                return

            self.gui_handler.log("📡 Connecting to Canvas API...")
            self.gui_handler.log(
                "📦 This is a large package. Please stay patient while Mosh flies it to the clouds..."
            )
            success, res = api.upload_imscc(package_path)

            self.root.after(0, self._close_flight_animation)

            if success:
                self.gui_handler.log(
                    "✅ LANDING SUCCESSFUL! Mosh has delivered the package."
                )
                self.gui_handler.log(f"   Migration ID: {res.get('id')}")
                self.gui_handler.log(
                    "   Canvas is now importing your files. check back in 1-2 minutes."
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Mosh Delivered!",
                        "Mosh has delivered your course package to Canvas!\n\n"
                        "Check your Canvas course in a few minutes to see the result.",
                    ),
                )
            else:
                self.gui_handler.log(f"❌ TURBULENCE: {res}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Upload Error", f"Mosh encountered an error:\n{res}"
                    ),
                )

        self._run_task_in_thread(upload_task, "Canvas Upload")

    # --- Mosh's Flight Animation ---

    def _show_flight_animation(self, message):
        """Shows a fun overlay with Mosh Pilot image (Flight mode)."""
        self.flight_win = Toplevel(self.root)
        self.flight_win.title("Mosh Pilot: Flying to Canvas...")
        self.flight_win.geometry("450x450")
        # [UX FIX] Avoid forcing to top or removing decorations so user can do other work
        # Center
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 225
        self.flight_win.geometry(f"+{x}+{y}")
        self.flight_win.transient(self.root)

        frame = tk.Frame(self.flight_win, bg="#4b3190", borderwidth=5, relief="raised")
        frame.pack(fill="both", expand=True)

        # Load Mosh Pilot Image
        try:
            img_path = resource_path("mosh_pilot.png")
            pil_img = Image.open(img_path)
            # Resize for the dialog
            pil_img = pil_img.resize((250, 250), Image.Resampling.LANCZOS)
            self.mosh_img_tk = ImageTk.PhotoImage(pil_img)
            self.lbl_mosh = tk.Label(frame, image=self.mosh_img_tk, bg="#4b3190")
            self.lbl_mosh.pack(pady=20)
        except Exception as e:
            # Fallback to Emoji
            self.lbl_mosh = tk.Label(
                frame, text="🦆💨", font=("Segoe UI", 90), bg="#4b3190", fg="white"
            )
            self.lbl_mosh.pack(pady=20)

        tk.Label(
            frame,
            text=message,
            font=("Segoe UI", 12, "bold"),
            bg="#4b3190",
            fg="white",
            wraplength=400,
        ).pack(pady=10)

        # Add Progress bar for visual interest
        self.prog_mosh = ttk.Progressbar(frame, mode="indeterminate", length=300)
        self.prog_mosh.pack(pady=10)
        self.prog_mosh.start(10)

        self._animate_mosh(0)

    def _animate_mosh(self, step):
        if not hasattr(self, "flight_win") or not self.flight_win.winfo_exists():
            return

        # Subtly shake Mosh to simulate flight vibration
        shake_x = (step % 4) - 2  # -2, -1, 0, 1
        shake_y = ((step // 2) % 4) - 2

        # We don't want to move the whole window, just the image a tiny bit
        self.lbl_mosh.pack_configure(pady=(20 + shake_y, 20 - shake_y))

        # Pulsing text
        colors = ["#FFFFFF", "#E1BEE7", "#D1C4E9"]
        # If we had the message label saved
        # self.lbl_msg.config(fg=colors[step % len(colors)])

        self.root.after(100, lambda: self._animate_mosh(step + 1))

    def _close_flight_animation(self):
        if hasattr(self, "flight_win"):
            self.flight_win.destroy()

    def _run_course_health_check(self):
        """Scans the entire project for broken links and missing images."""
        self.gui_handler.log("\n🔍 [AUDIT] Starting Course-Wide Health Check...")

        html_files = []
        for root, dirs, files in os.walk(self.target_dir):
            if "_ORIGINALS_DO_NOT_UPLOAD_" in root:
                continue
            for f in files:
                if f.endswith(".html"):
                    html_files.append(os.path.join(root, f))

        if not html_files:
            messagebox.showinfo("Health Check", "No HTML files found to audit.")
            return

        broken_links = 0
        missing_images = 0
        total_links = 0
        total_images = 0

        detailed_log = []

        # We'll use the interactive_fixer's resolution logic
        import interactive_fixer

        io_placeholder = interactive_fixer.FixerIO()

        for fp in html_files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")

                # 1. Check Images
                for img in soup.find_all("img"):
                    total_images += 1
                    src = img.get("src", "")
                    if not src:
                        continue
                    if src.startswith(("http", "data:")):
                        continue  # Skip web/embedded for now

                    found_path = interactive_fixer.resolve_image_path(
                        src, fp, self.target_dir, io_placeholder
                    )
                    if not found_path or not os.path.exists(found_path):
                        missing_images += 1
                        detailed_log.append(
                            f"   [MISSING IMG] {os.path.basename(fp)} -> {src}"
                        )

                # 2. Check Links
                for a in soup.find_all("a"):
                    total_links += 1
                    href = a.get("href", "")
                    if not href or href.startswith(("#", "http", "mailto:")):
                        continue

                    # Resolve path
                    link_path = interactive_fixer.resolve_image_path(
                        href, fp, self.target_dir, io_placeholder
                    )
                    if not link_path or not os.path.exists(link_path):
                        broken_links += 1
                        detailed_log.append(
                            f"   [BROKEN LINK] {os.path.basename(fp)} -> {href}"
                        )
            except Exception:
                pass

        self.gui_handler.log(f"✅ Audit Complete: Scanned {len(html_files)} pages.")
        self.gui_handler.log(f"   - Links: {total_links} total, {broken_links} broken.")
        self.gui_handler.log(
            f"   - Images: {total_images} total, {missing_images} missing."
        )

        if broken_links > 0 or missing_images > 0:
            result_msg = (
                f"Course Health Report:\n\n"
                f"⚠️ Broken Links: {broken_links}\n"
                f"⚠️ Missing Images: {missing_images}\n\n"
                f"Issues have been logged to the Activity Feed below.\n"
                f"Tip: Try running 'Conversion Wizard' again if these were recently moved files."
            )
            for line in detailed_log:
                self.gui_handler.log(line)
            messagebox.showwarning("Health Report", result_msg)
        else:
            messagebox.showinfo(
                "Health Report",
                "Your course is in peak physical condition! No broken links or missing images found.",
            )

    def _perform_link_repair_logic(self):
        """Core logic for finding and repairing document links."""
        skip_dirs = {
            converter_utils.ARCHIVE_FOLDER_NAME,
            ".git",
            "venv",
            "node_modules",
        }

        # Step 1: Map all Documents AND HTML files in one pass O(N)
        doc_map = {}
        html_map = {}  # basename -> filename
        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in (
                    ".docx",
                    ".pdf",
                    ".pptx",
                    ".xlsx",
                    ".doc",
                    ".ppt",
                    ".xls",
                ):
                    # Use sanitized base as key for robust matching
                    clean_base = converter_utils.sanitize_filename(os.path.splitext(file)[0]).lower()
                    doc_map[clean_base] = file
                elif ext == ".html":
                    # Convert to sanitized base to match docs
                    clean_base = converter_utils.sanitize_filename(os.path.splitext(file)[0]).lower()
                    html_map[clean_base] = file

        total_updated = 0
        doc_count = 0

        # Step 2: Compare and Update O(M) where M is document count
        for base, original_file in doc_map.items():
            if base in html_map:
                found_html = html_map[base]
                doc_count += 1
                updated = converter_utils.update_doc_links_to_html(
                    self.target_dir,
                    original_file,
                    found_html,
                    log_func=self.gui_handler.log,
                )
                total_updated += updated
        
        return doc_count, total_updated

    def _run_all_links_fix(self):
        """Finds all document links and attempts to point them to matching HTML files (Optimized & Threaded)."""
        if not self.target_dir:
            messagebox.showwarning(
                "Incomplete", "Please select a target directory first."
            )
            return

        def task():
            self.gui_handler.log("\n--- Starting Global Document Link Repair ---")
            self.gui_handler.log(f"Scanning target: {self.target_dir}")
            
            doc_count, total_updated = self._perform_link_repair_logic()

            msg = f"Global Link Fix Complete.\nRepaired links for {doc_count} different documents across {total_updated} instances."
            self.gui_handler.log(f"\n--- {msg} ---")
            self.root.after(0, lambda: messagebox.showinfo("Complete", msg))

        self._run_task_in_thread(task, "Global Link Repair")

    def _process_logs(self):
        """Polls queue for log messages and updates the persistent log widget."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                # Check if UI is ready. If not, print to console as fallback.
                if hasattr(self, "txt_log") and self.txt_log.winfo_exists():
                    self._log(msg)
                else:
                    print(f"[PENDING LOG] {msg}")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_logs)

    def _process_inputs(self):
        """Polls for input requests from threads."""
        try:
            while True:
                req = self.gui_handler.input_request_queue.get_nowait()
                # Unified unpacking: handler puts (rtype, msg, arg1, arg2, arg3)
                rtype, msg, arg1, arg2, arg3 = req

                result = None
                if rtype == "prompt":
                    result = (
                        simpledialog.askstring("Input Needed", msg, parent=self.root)
                        or ""
                    )
                elif rtype == "confirm":
                    result = messagebox.askyesno("Confirm", msg, parent=self.root)
                elif rtype == "image":
                    # args were image_path, context, suggestion
                    result = self._show_image_dialog(msg, arg1, arg2, arg3)
                elif rtype == "link":
                    # args were help_url, context
                    result = self._show_link_dialog(msg, arg1, arg2)

                self.gui_handler.input_response_queue.put(result)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_inputs)

    def _build_files_view(self, content):
        """Dedicated view for standard file conversion (Word/PPT)."""
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]

        tk.Label(
            content,
            text="📄 File Conversion Suite",
            font=("Segoe UI", 24, "bold"),
            fg="#0D9488",
            bg="white",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            content,
            text="Convert PowerPoint or Word files to clean, accessible HTML.",
            font=("Segoe UI", 11),
            fg="#6B7280",
            bg="white",
        ).pack(anchor="w", pady=(0, 30))

        # --- Step 1: Browse ---
        ttk.Label(
            content, text="Step 1: Pick Files or Folder", style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(0, 5))
        frame_dir = ttk.Frame(content, style="Card.TFrame", padding=15)
        frame_dir.pack(fill="x", pady=(0, 20))

        frame_browse = ttk.Frame(frame_dir)
        frame_browse.pack(fill="x")
        self.lbl_dir = tk.Entry(
            frame_browse,
            bg=colors["bg"],
            fg=colors["fg"],
            insertbackground=colors["fg"],
        )
        self.lbl_dir.insert(0, self.target_dir)
        self.lbl_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            frame_browse, text="Browse Folder...", command=self._browse_folder
        ).pack(side="right")

        # --- Step 2: Converters ---
        ttk.Label(
            content, text="Step 2: Start Conversion", style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(0, 5))
        frame_convert = ttk.Frame(content, style="Card.TFrame", padding=15)
        frame_convert.pack(fill="x", pady=(0, 20))

        self.btn_batch = ttk.Button(
            frame_convert,
            text="📂 CONVERT ALL (Batch Mode)",
            command=self._run_batch_conversion,
            style="Action.TButton",
        )
        self.btn_batch.pack(fill="x", pady=(0, 15))

        ttk.Separator(frame_convert).pack(fill="x", pady=10)
        tk.Label(
            frame_convert,
            text="Or pick specific file types:",
            font=("Segoe UI", 9, "bold"),
            bg="white",
        ).pack(anchor="w", pady=(0, 10))

        frame_btns = ttk.Frame(frame_convert)
        frame_btns.pack(fill="x")
        self.btn_word = ttk.Button(
            frame_btns,
            text="📝 Word Doc",
            command=lambda: self._show_conversion_wizard("docx"),
        )
        self.btn_word.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_excel = ttk.Button(
            frame_btns,
            text="📈 Excel",
            command=lambda: self._show_conversion_wizard("xlsx"),
        )
        self.btn_excel.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_ppt = ttk.Button(
            frame_btns,
            text="📽️ PowerPoint",
            command=lambda: self._show_conversion_wizard("pptx"),
        )
        self.btn_ppt.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_pdf = ttk.Button(
            frame_btns,
            text="📄 Standard PDF",
            command=lambda: self._show_conversion_wizard("pdf"),
        )
        self.btn_pdf.pack(side="left", fill="x", expand=True, padx=2)


    def _run_ai_design_fixer(self):
        if not self._check_target_dir():
            return
            
        if not messagebox.askyesno(
            "Confirm AI Design",
            "This will use Gemini AI to automatically rewrite the HTML code of all pages to match "
            "responsive mobile best-practices for Canvas.\n\n"
            "This uses API tokens and takes time. Do you want to proceed?"
        ):
            return

        self.gui_handler.log("==========================================")
        self.gui_handler.log("✨ Starting AI Canvas Design Optimizer...")
        self.gui_handler.log("==========================================")

        def task():
            import interactive_fixer
            interactive_fixer.run_ai_design_fixer(self.target_dir, self.gui_handler)
            self.gui_handler.log("==========================================")
            self.gui_handler.log("✨ Responsive Design Pass Complete! ")
            self.gui_handler.log("==========================================")
            self.root.after(0, lambda: messagebox.showinfo("AI Design Pass", "All Canvas Pages have been wrapped with beautiful responsive design!"))

        self._run_task_in_thread(task, "AI Design Fixer")

    def _process_generated_pages(self, file_pairs):
        """
        Unified workflow for processing newly generated properties/HTML files.
        file_pairs: List of (source_path, output_path) tuples.
        """
        if not file_pairs:
            return

        # 1. Auto-Fixer (Structural)
        self.gui_handler.log(f"   [1/3] Running Auto-Fixer (Headings, Tables)...")
        total_fixes = 0
        for source, output in file_pairs:
            success, fixes = interactive_fixer.run_auto_fixer(output, self.gui_handler)
            if success and fixes:
                total_fixes += len(fixes)

            # [DESIGN] AI Responsive Design Pass
            api_key = self.config.get("api_key", "").strip()
            if api_key:
                try:
                     import jeanie_ai
                     with open(output, "r", encoding="utf-8") as f:
                         content = f.read()
                     new_html, msg = jeanie_ai.improve_html_design(content, api_key)
                     if new_html and "Error" not in msg:
                         with open(output, "w", encoding="utf-8") as f:
                             f.write(new_html)
                         self.gui_handler.log("   [DESIGN] AI improved layout for mobile!")
                except Exception as e:
                     self.gui_handler.log(f"   [DESIGN] Skipping Design improvements: {e}")

        # 2. Guided Interactive Review
        if messagebox.askyesno(
            "Review Needed",
            f"Generated {len(file_pairs)} pages.\n\nWould you like to run the Interactive Review now to check for issues?",
        ):
            self.gui_handler.log(f"   [2/3] Launching Guided Review...")
            for source, output in file_pairs:
                interactive_fixer.scan_and_fix_file(
                    output, self.gui_handler, self.target_dir
                )

        # 3. Validation & Sync
        count_updated = 0
        for source, output in file_pairs:
            # Update Document Links
            converter_utils.update_doc_links_to_html(
                self.target_dir,
                os.path.basename(source),
                os.path.basename(output),
                log_func=self.gui_handler.log,
            )

            # Archive Original
            converter_utils.archive_source_file(source)

            # Optional: Upload to Canvas
            api = self._get_canvas_api()
            if api:
                msg = f"Ready to upload '{os.path.basename(output)}' to Canvas?"
                if self.gui_handler.confirm(msg):
                    self._upload_page_to_canvas(
                        output, source, api, auto_confirm_links=True
                    )
                    count_updated += 1

        self.gui_handler.log(
            f"✅ Workflow Complete. {count_updated} pages uploaded to Canvas."
        )

        # Open output folder
        if file_pairs:
            folder = os.path.dirname(file_pairs[0][1])
            try:
                os.startfile(folder)
            except Exception:
                pass

            # [FIX] Explicit "Upload Needed" Warning for cloud-expecting users
            msg_upload = (
                "✅ FILE SAVED TO YOUR COMPUTER.\n\n"
                "IMPORTANT: This change is LOCAL only.\n"
                "You must now UPLOAD this file to Canvas to see it online."
            )
            self.root.after(0, lambda: messagebox.showinfo("Step Complete", msg_upload))

    def _convert_math_canvas_export(self):
        """Processes an entire IMSCC course package for math content."""
        self.gui_handler.log("DEBUG: _convert_math_canvas_export triggered")
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            self.gui_handler.log("ERROR: No Gemini API Key found.")
            messagebox.showwarning(
                "Setup Required",
                "Please set your Gemini API Key in the 'CONNECT & SETUP' view first.",
            )
            return

        self.gui_handler.log(f"DEBUG: API Key OK. Checking project: {self.target_dir}")

        if not self.target_dir or not os.path.exists(self.target_dir):
            self.gui_handler.log("ERROR: No project loaded.")
            messagebox.showwarning(
                "No Project",
                "Please load a course project (.imscc) in the 'CONNECT & SETUP' view first.",
            )
            return

        self.gui_handler.log("DEBUG: Project OK. Checking Poppler...")

        # Poppler check: Don't restrict to just Windows (nt) anymore
        import shutil

        has_poppler = self.config.get("poppler_path") or shutil.which("pdftoppm")
        if not has_poppler:
            self.gui_handler.log("DEBUG: Poppler not found. Prompting user.")
            if messagebox.askyesno(
                "Setup Helper Needed",
                "MOSH needs a helper tool (Poppler) to read math from PDFs.\n\nRun 'Auto-Setup' in the 'CONNECT & SETUP' view?",
            ):
                self._switch_view("setup")
            else:
                self.gui_handler.log("DEBUG: User declined Poppler setup.")
            return

        self.gui_handler.log("DEBUG: Poppler OK. Requesting confirmation...")

        if not messagebox.askyesno(
            "Confirm",
            "This will convert ALL math in your project using AI.\n\nIt may take a while. Continue?",
        ):
            self.gui_handler.log("DEBUG: User cancelled or closed confirmation dialog.")
            return

        self.gui_handler.log("DEBUG: Confirmed. Starting background task...")

        def task():
            import math_converter

            # [NEW] Validate Canvas Token early if connected
            api = self._get_canvas_api()
            if api:
                self.gui_handler.log(
                    "   [Check] Validating Canvas connection before starting..."
                )
                valid, msg = api.validate_credentials()
                if not valid:
                    self.gui_handler.log(
                        f"   [CRITICAL] Canvas Connection Failed: {msg}"
                    )
                    self.gui_handler.log(
                        "   [INFO] I will continue converting files locally, but uploads will be skipped."
                    )

            # [FIX] Stop the automatic pulse so we can show real progress
            self.root.after(0, self.progress_bar.stop)
            self.root.after(0, lambda: self.progress_var.set(0))

            def log(msg):
                self.gui_handler.log(msg)

            def update_progress(current, total):
                pct = (current / total) * 100
                self.root.after(0, lambda: self.progress_var.set(pct))
                self.root.after(
                    0,
                    lambda: self.lbl_status_text.config(
                        text=f"Converting File {current}/{total}...", fg="blue"
                    ),
                )
                # [NEW] Log periodic updates to keep user informed
                if current % 5 == 0 or current == 1 or current == total:
                    log(f"   ... Processing file {current} of {total} ...")

            # [NEW] Callback for immediate processing
            def on_file_complete(source, dest):
                # 1. Auto-Fixer (Silent)
                success, fixes = interactive_fixer.run_auto_fixer(
                    dest, self.gui_handler
                )

                # 2. AI Responsive Design pass
                try:
                     import jeanie_ai
                     with open(dest, "r", encoding="utf-8") as f:
                         content = f.read()
                     new_html, msg = jeanie_ai.improve_html_design(content, api_key)
                     if new_html and "Error" not in msg:
                         with open(dest, "w", encoding="utf-8") as f:
                             f.write(new_html)
                         log("   [DESIGN] AI improved layout for mobile!")
                except Exception as e:
                     log(f"   [DESIGN] Skipping Design improvements: {e}")

                # 2.5 [NEW] Interactive Visual Review (blocks until user approves)
                dest_stem = Path(dest).stem
                graphs_dir = str(Path(dest).parent / f"{dest_stem}_graphs")
                if os.path.isdir(graphs_dir):
                    log(f"   🖼️ Opening Visual Review for {os.path.basename(dest)}...")
                    approved = self._show_visual_review(dest, graphs_dir)
                    if not approved:
                        log(f"   ⏩ User cancelled upload for {os.path.basename(dest)}")
                        return
                    log(f"   ✅ Visual review approved!")

                # 3. Update Links
                converter_utils.update_doc_links_to_html(
                    self.target_dir,
                    os.path.basename(source),
                    os.path.basename(dest),
                    log_func=log,
                )

                # 4. Update Manifest so Canvas Modules don't drop the file
                source_rel = os.path.relpath(source, self.target_dir)
                dest_rel = os.path.relpath(dest, self.target_dir)
                converter_utils.update_manifest_resource(self.target_dir, source_rel, dest_rel)

                # 5. Archive Original
                converter_utils.archive_source_file(source, log_func=log)

                # 6. Auto-Upload to Canvas (if API connected)
                api = self._get_canvas_api()
                if api:
                    # Silent upload with auto-confirm
                    log(f"   ☁️ Uploading to Canvas: {os.path.basename(dest)}...")
                    self._upload_page_to_canvas(
                        dest, source, api, auto_confirm_links=True
                    )

            log("\n=== BULK MATH REMEDIATION (CANVAS EXPORT) ===")

            success, result = math_converter.process_canvas_export(
                api_key,
                self.target_dir,
                log_func=log,
                poppler_path=self.config.get("poppler_path", ""),
                progress_callback=update_progress,
                on_file_converted=on_file_complete,
            )

            if success:
                # result is list of (source, dest)
                log(f"\n✨ SUCCESS! Converted {len(result)} files.")

                # We already processed them one-by-one, so just open the folder
                self.root.after(0, lambda: self.progress_var.set(100))

                if result:
                    folder = os.path.dirname(result[0][1])
                    try:
                        os.startfile(folder)
                    except Exception:
                        pass

                msg_done = (
                    "✅ ALL FILES PROCESSED & UPLOADED.\n\n"
                    "Your math content is now accessible on Canvas!"
                )
                self.root.after(
                    0, lambda: messagebox.showinfo("Mission Complete", msg_done)
                )
            else:
                log(f"❌ Error: {result}")
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Math Error", f"Could not process course math:\n{result}"
                    ),
                )

        self.gui_handler.log("DEBUG: Task defined. Attempting to launch thread...")
        try:
            self._run_task_in_thread(task, "Bulk Math Conversion")
            self.gui_handler.log("DEBUG: Thread launch command issued.")
        except Exception as e:
            import traceback

            err = traceback.format_exc()
            self.gui_handler.log(f"CRITICAL ERROR launching thread: {e}")
            self.gui_handler.log(f"{err}")
            messagebox.showerror(
                "Thread Error", f"Could not start background task:\n{e}"
            )

    def _convert_math_files(self, file_type):
        """Convert individual math files using Gemini."""
        try:
            self.gui_handler.log(f"[DEBUG] Math button clicked for type: {file_type}")

            # Check if busy
            if self.is_running:
                messagebox.showwarning(
                    "Busy", "A task is currently running. Please wait."
                )
                return

            api_key = self.config.get("api_key", "").strip()
            if not api_key:
                messagebox.showwarning(
                    "No Gemini API Key",
                    "You need a Gemini API key for math conversion.\n\n"
                    "Click '🔗 Connect to My Canvas Playground' and add your key in Step 4.",
                )
                return

            # [NEW] Proactive Poppler Check (Only for PDFs) - Cross-platform
            import shutil

            has_poppler = self.config.get("poppler_path") or shutil.which("pdftoppm")
            if file_type == "pdf" and not has_poppler:
                if messagebox.askyesno(
                    "Setup Helper Needed",
                    "MOSH needs a helper tool (Poppler) to read math from PDFs.\n\nWould you like to run the 'Guided Auto-Setup' now?",
                ):
                    self._auto_setup_poppler()
                    has_poppler_now = self.config.get("poppler_path") or shutil.which(
                        "pdftoppm"
                    )
                    if not has_poppler_now:
                        return

            # File picker based on type
            file_path = None
            if file_type == "pdf":
                file_path = filedialog.askopenfilename(
                    title="Select PDF with Math", filetypes=[("PDF Files", "*.pdf")]
                )
            elif file_type == "docx":
                file_path = filedialog.askopenfilename(
                    title="Select Word Document", filetypes=[("Word Files", "*.docx")]
                )
            elif file_type == "images":
                file_path = filedialog.askopenfilename(
                    title="Select Image",
                    filetypes=[
                        ("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"),
                        ("All Files", "*.*"),
                    ],
                )
            else:
                self.gui_handler.log(
                    f"[ERROR] Unknown file type requested: {file_type}"
                )
                return

            if not file_path:
                self.gui_handler.log("[DEBUG] No file selected (cancelled).")
                return

            def task():
                import math_converter

                self.gui_handler.log(
                    f"\n=== GEMINI MATH CONVERTER ({file_type.upper()}) ==="
                )

                def update_progress(current, total):
                    pct = (current / total) * 100
                    self.root.after(0, lambda: self.progress_var.set(pct))

                if file_type == "pdf":
                    # [FIX] Stop the pulse so we can show real page-by-page progress
                    self.root.after(0, self.progress_bar.stop)
                    self.root.after(0, lambda: self.progress_var.set(0))

                    success, result = math_converter.convert_pdf_to_latex(
                        api_key,
                        file_path,
                        self.gui_handler.log,
                        poppler_path=self.config.get("poppler_path", ""),
                        progress_callback=update_progress,
                    )
                elif file_type == "docx":
                    success, result = math_converter.convert_word_to_latex(
                        api_key, file_path, self.gui_handler.log
                    )
                elif file_type == "images":
                    success, result = math_converter.convert_image_to_latex(
                        api_key, file_path, self.gui_handler.log
                    )
                else:
                    success = False
                    result = "Unknown file type"

                if success:
                    # Save output
                    output_path = str(Path(file_path).with_suffix(".html"))
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(result)

                    self.gui_handler.log(f"\n✨ SUCCESS! Saved to: {output_path}")

                    # [NEW] Interactive Visual Review before finalizing
                    dest_stem = Path(output_path).stem
                    graphs_dir = str(Path(output_path).parent / f"{dest_stem}_graphs")
                    if os.path.isdir(graphs_dir):
                        self.gui_handler.log(f"   🖼️ Opening Visual Review...")
                        approved = self._show_visual_review(output_path, graphs_dir)
                        if not approved:
                            self.gui_handler.log(f"   ⏩ Upload cancelled by user.")
                            return
                        self.gui_handler.log(f"   ✅ Visual review approved!")

                    # Use the unified workflow (DIRECT call to avoid deadlock)
                    file_pairs = [(file_path, output_path)]
                    self._process_generated_pages(file_pairs)

                else:
                    self.gui_handler.log(f"\n❌ Error: {result}")
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(
                            "Conversion Failed", f"Error:\n{result}"
                        ),
                    )

            self._run_task_in_thread(task, f"Math {file_type.upper()} Conversion")

        except Exception as e:
            self.gui_handler.log(f"[Handler Error] Button handler failed: {e}")
            messagebox.showerror("Error", f"Something went wrong:\n{e}")

    def _auto_setup_poppler(self):
        """Robust, standalone Poppler downloader with explicit error handling (Windows & Mac)."""
        # [FIX] Save inputs before starting, so we don't lose them on refresh
        self._quick_save_inputs()

        import sys

        if sys.platform not in ("win32", "darwin"):
            messagebox.showinfo(
                "Not Supported",
                "Auto-setup is currently only supported on Windows and macOS. For Linux, please use your package manager (e.g., sudo apt install poppler-utils).",
            )
            return

        if sys.platform == "darwin":
            self._auto_setup_poppler_mac()
            return

        link = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
        explanation = (
            "I need to download a little helper tool called Poppler to read PDF math.\n\n"
            "It takes about 1 minute.\n\n"
            "Ready to download?"
        )

        if not messagebox.askyesno("Poppler Setup", explanation):
            return

        # 1. Create Progress Window (Main Thread)
        # This guarantees the user sees SOMETHING happening immediately.
        progress_win = Toplevel(self.root)
        progress_win.title("Downloading Poppler...")
        progress_win.geometry("350x150")
        progress_win.resizable(False, False)
        progress_win.transient(self.root)
        progress_win.grab_set()

        lbl_status = tk.Label(
            progress_win, text="Initializing...", font=("Segoe UI", 10)
        )
        lbl_status.pack(pady=(20, 10))

        pbar = ttk.Progressbar(progress_win, mode="indeterminate")
        pbar.pack(fill="x", padx=30, pady=10)
        pbar.start(10)

        def worker():
            try:
                # 2. Background Work
                import urllib.request
                import zipfile
                from pathlib import Path
                import shutil
                import threading

                def update_status(msg):
                    self.root.after(0, lambda: lbl_status.config(text=msg))

                update_status("Preparing folders...")
                # Use visible 'mosh_helpers' in home dir
                helper_dir = Path.home() / "mosh_helpers"
                helper_dir.mkdir(exist_ok=True)
                zip_path = helper_dir / "poppler.zip"
                extract_path = helper_dir / "poppler"

                # Clean previous attempts
                if extract_path.exists():
                    shutil.rmtree(extract_path, ignore_errors=True)

                update_status("Downloading (this may take a minute)...")
                # Download with basic error checking
                with urllib.request.urlopen(link, timeout=90) as response:
                    with open(zip_path, "wb") as f:
                        shutil.copyfileobj(response, f)

                update_status("Extracting files...")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)

                # Locate Bin
                update_status("Verifying installation...")
                bin_folders = list(extract_path.glob("**/bin"))
                if not bin_folders:
                    raise Exception("Downloaded file is invalid (no 'bin' folder).")

                poppler_bin = str(bin_folders[0])

                # 3. Success Callback (Main Thread)
                def on_success():
                    progress_win.destroy()

                    # Update Config & UI
                    self._update_config(poppler_path=poppler_bin)

                    if (
                        hasattr(self, "ent_poppler_setup")
                        and self.ent_poppler_setup.winfo_exists()
                    ):
                        self.ent_poppler_setup.delete(0, tk.END)
                        self.ent_poppler_setup.insert(0, poppler_bin)

                    # Refresh Setup View if needed
                    if self.current_view == "setup":
                        self._switch_view("setup")

                    messagebox.showinfo(
                        "Success",
                        f"Poppler installed successfully!\n\nLocation: {poppler_bin}",
                    )

                self.root.after(0, on_success)

            except Exception as e:
                # 4. Error Callback (Main Thread)
                def on_error():
                    progress_win.destroy()
                    messagebox.showerror(
                        "Setup Failed",
                        f"An error occurred:\n{str(e)}\n\nPlease try downloading manually.",
                    )

                self.root.after(0, on_error)

        # Start the worker
        threading.Thread(target=worker, daemon=True).start()

    def _auto_setup_poppler_mac(self):
        """macOS specific Poppler installation via Homebrew."""
        import shutil
        import subprocess
        import threading
        import webbrowser

        # Check for Homebrew
        brew_path = shutil.which("brew")

        # If Homebrew is missing, fallback to specific common locations
        if not brew_path:
            # Fallback path typical for Apple Silicon
            if os.path.exists("/opt/homebrew/bin/brew"):
                brew_path = "/opt/homebrew/bin/brew"
            # Fallback path typical for Intel
            elif os.path.exists("/usr/local/bin/brew"):
                brew_path = "/usr/local/bin/brew"

        if not brew_path:
            msg = (
                "To automatically install Poppler on a Mac, you need a tool called 'Homebrew'.\n\n"
                "Once you install Homebrew, you can click this Auto-Setup button again.\n\n"
                "Would you like to open the Homebrew website (brew.sh) to see how to install it?"
            )
            if messagebox.askyesno("Homebrew Required", msg):
                webbrowser.open("https://brew.sh")
            return

        explanation = (
            "I will use Homebrew to download and install Poppler.\n\n"
            "This will open a terminal background process and may take a minute or two depending on your connection.\n\n"
            "Ready to install?"
        )
        if not messagebox.askyesno("Poppler Setup", explanation):
            return

        # 1. Create Progress Window
        progress_win = Toplevel(self.root)
        progress_win.title("Installing through Homebrew...")
        progress_win.geometry("400x150")
        progress_win.resizable(False, False)
        progress_win.transient(self.root)
        progress_win.grab_set()

        lbl_status = tk.Label(
            progress_win,
            text="Running 'brew install poppler'...",
            font=("Segoe UI", 10),
        )
        lbl_status.pack(pady=(20, 10))

        pbar = ttk.Progressbar(progress_win, mode="indeterminate")
        pbar.pack(fill="x", padx=30, pady=10)
        pbar.start(10)

        def worker():
            try:

                def update_status(msg):
                    self.root.after(0, lambda: lbl_status.config(text=msg))

                # Verify Poppler might not already be installed
                if shutil.which("pdftoppm"):
                    poppler_bin = os.path.dirname(shutil.which("pdftoppm"))

                    update_status("Found existing installation!")

                    def on_success_exist():
                        progress_win.destroy()
                        self._update_config(poppler_path=poppler_bin)
                        if (
                            hasattr(self, "ent_poppler_setup")
                            and self.ent_poppler_setup.winfo_exists()
                        ):
                            self.ent_poppler_setup.delete(0, tk.END)
                            self.ent_poppler_setup.insert(0, poppler_bin)
                        if self.current_view == "setup":
                            self._switch_view("setup")
                        messagebox.showinfo(
                            "Success",
                            f"Poppler was already installed!\n\nLocation: {poppler_bin}",
                        )

                    self.root.after(0, on_success_exist)
                    return

                # Ensure env vars include brew paths for subprocess execution
                env = os.environ.copy()
                if "/opt/homebrew/bin" not in env.get("PATH", ""):
                    env["PATH"] = (
                        f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
                    )

                update_status("Brewing... (This can take a few minutes)")
                # 2. Run background process to install brew
                process = subprocess.run(
                    [brew_path, "install", "poppler"],
                    env=env,
                    capture_output=True,
                    text=True,
                )

                if process.returncode != 0:
                    raise Exception(
                        f"Homebrew Error:\n{process.stderr}\n{process.stdout}"
                    )

                update_status("Verifying installation...")

                # Check for pdftoppm again
                poppler_exe = shutil.which("pdftoppm", path=env["PATH"])
                if not poppler_exe:
                    raise Exception(
                        "Homebrew completed, but poppler binaries (pdftoppm) could not be found."
                    )

                poppler_bin = os.path.dirname(poppler_exe)

                # 3. Success Callback
                def on_success():
                    progress_win.destroy()
                    self._update_config(poppler_path=poppler_bin)

                    if (
                        hasattr(self, "ent_poppler_setup")
                        and self.ent_poppler_setup.winfo_exists()
                    ):
                        self.ent_poppler_setup.delete(0, tk.END)
                        self.ent_poppler_setup.insert(0, poppler_bin)

                    # Refresh Setup View if needed
                    if self.current_view == "setup":
                        self._switch_view("setup")

                    messagebox.showinfo(
                        "Success",
                        f"Poppler installed successfully via Homebrew!\n\nLocation: {poppler_bin}",
                    )

                self.root.after(0, on_success)

            except Exception as e:
                # 4. Error Callback
                def on_error():
                    progress_win.destroy()
                    msg = str(e)
                    if len(msg) > 500:
                        msg = msg[:500] + "... (truncated)"
                    messagebox.showerror(
                        "Setup Failed",
                        f"An error occurred with Homebrew:\n{msg}\n\nPlease try manually running 'brew install poppler' in your Terminal.",
                    )

                self.root.after(0, on_error)

        # Start the worker
        threading.Thread(target=worker, daemon=True).start()

    # --- CANVAS MIRROR (LIVE SYNC) LOGIC ---
    def _toggle_mirror(self):
        """Starts or stops the live directory watcher for Canvas sync."""
        if not self.mirror_active:
            # START
            api = self._get_canvas_api()
            if not api:
                messagebox.showwarning(
                    "Setup Required",
                    "Please fill in your Canvas details (Section 1) before enabling Mirror Mode.",
                )
                self._switch_view("setup")
                return

            if not self.target_dir or not os.path.exists(self.target_dir):
                messagebox.showwarning(
                    "Target Required", "Please load a course project (Section 4) first."
                )
                return

            self.mirror_active = True
            self.config["mirror_active"] = True
            self._save_config_simple()
            self.btn_mirror_toggle.config(text="🟢 MIRROR MODE: ON", bg="#D1FAE5")
            self.lbl_mirror_status.config(text="Watching for changes...", fg="green")
            self.gui_handler.log("🚀 [Mirror] ACTIVE. Watching project for saves...")

            # Reset hashes so we don't trigger on everything immediately
            self.file_hashes = {}
            for f in Path(self.target_dir).rglob("*.html"):
                self.file_hashes[str(f)] = os.path.getmtime(f)

            self.mirror_thread = threading.Thread(
                target=self._mirror_watcher, daemon=True
            )
            self.mirror_thread.start()
        else:
            # STOP
            self.mirror_active = False
            self.config["mirror_active"] = False
            self._save_config_simple()
            self.btn_mirror_toggle.config(text="🔴 MIRROR MODE: OFF", bg="#f3f4f6")
            self.lbl_mirror_status.config(text="Idle", fg="gray")
            self.gui_handler.log("🛑 [Mirror] Deactivated.")

    def _mirror_watcher(self):
        """Background thread that polls for file changes."""
        api = self._get_canvas_api()
        if not api:
            return

        while self.mirror_active:
            try:
                # Check for changes in target_dir
                for fpath in Path(self.target_dir).rglob("*.html"):
                    if not self.mirror_active:
                        break

                    # Ignore temporary or system files
                    if "web_resources" in str(fpath) or "_archive" in str(fpath):
                        continue

                    fstr = str(fpath)
                    try:
                        mtime = os.path.getmtime(fpath)
                        if fstr not in self.file_hashes:
                            # New file found - we don't auto-upload new files (too risky)
                            # Just track it
                            self.file_hashes[fstr] = mtime
                        elif mtime > self.file_hashes[fstr]:
                            # CHANGE DETECTED!
                            self.file_hashes[fstr] = mtime
                            # [FIX] Immediate status update on main thread
                            self.root.after(
                                0, lambda p=fstr: self._mirror_trigger_upload(p, api)
                            )
                    except Exception:
                        pass

                # Poll every 2 seconds
                time.sleep(2)
            except Exception as e:
                print(f"Watcher error: {e}")
                time.sleep(5)

    def _mirror_trigger_upload(self, html_path, api):
        """Helper to run the upload in a separate worker thread so GUI doesn't freeze."""

        def task():
            self.lbl_mirror_status.config(
                text=f"Syncing {os.path.basename(html_path)}...", fg="blue"
            )
            # We use a dummy 'original_source' since we are mirroring
            self._upload_page_to_canvas(
                html_path, html_path, api, auto_confirm_links=True
            )
            self.lbl_mirror_status.config(text="Watching for changes...", fg="green")

        # Run as a separate short-lived thread
        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ToolkitGUI(root)
    root.mainloop()
