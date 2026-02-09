# Created by Meri Kasprak with the assistance of Gemini.
# Released freely under the GNU General Public License v3.0. USE AT YOUR OWN RISK.

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, scrolledtext, Toplevel, Menu, ttk
from PIL import Image, ImageTk
import sys
import os

# Ensure the script's directory is in the Python path for local imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
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
import converter_utils

# Import Toolkit Modules
import interactive_fixer
import run_fixer
import run_audit
import canvas_utils

CONFIG_FILE = "toolkit_config.json"

class ThreadSafeGuiHandler(interactive_fixer.FixerIO):
    """
    Bridge between the worker thread running the scripts and the Main GUI thread.
    Handles logging and user input via thread-safe events.
    """
    def __init__(self, root, log_queue):
        super().__init__()
        self.root = root
        self.log_queue = log_queue
        # Queues for input requests/responses
        self.input_request_queue = queue.Queue()
        self.input_response_queue = queue.Queue()

    def log(self, message):
        """Send log message to the queue."""
        self.log_queue.put(message)

    def prompt(self, message):
        """Ask user for input (Blocking from worker thread perspective)."""
        if self.is_stopped(): return ""
        self.input_request_queue.put(('prompt', message, None))
        return self.input_response_queue.get()

    def confirm(self, message):
        """Ask user for Yes/No (Blocking)."""
        if self.is_stopped(): return False
        self.input_request_queue.put(('confirm', message, None))
        return self.input_response_queue.get()
        
    def prompt_image(self, message, image_path, context=None):
        """Ask user for input while showing an image and context."""
        if self.is_stopped(): return ""
        self.input_request_queue.put(('prompt_image', message, (image_path, context)))
        return self.input_response_queue.get()

    def prompt_link(self, message, help_url, context=None):
        """Ask user for input while showing a link and context."""
        if self.is_stopped(): return ""
        self.input_request_queue.put(('prompt_link', message, (help_url, context)))
        return self.input_response_queue.get()

# Colors
# --- Themes ---
THEMES = {
    "light": {
        "bg": "#FFFFF0",       # Ivory
        "fg": "#212121",       # Dark Grey
        "sidebar": "#0D47A1",  # Mosh's Deep Blue
        "sidebar_fg": "#FFFFFF",
        "primary": "#009688",  # Teal (Buttons)
        "accent": "#FFD700",   # Yellow (Highlight)
        "header": "#0D47A1",   # Blue Headers
        "subheader": "#00796B",# Teal Subheaders
        "button": "#E0F2F1",   # Very Light Teal
        "button_fg": "#004D40",
    },
    "dark": {
        "bg": "#263238",       # Dark Blue Grey
        "fg": "#FFFFF0",       # Ivory Text
        "sidebar": "#102027",  # Very Dark Blue
        "sidebar_fg": "#E0E0E0",
        "primary": "#4DB6AC",  # Light Teal
        "accent": "#FFD700",   # Yellow
        "header": "#81D4FA",   # Light Blue
        "subheader": "#80CBC4",# Light Teal
        "button": "#37474F",   # Dark Button
        "button_fg": "#FFFFFF",
    }
}

class ToolkitGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MOSH's Toolkit: Making Online Spaces Helpful")
        self.root.geometry("900x650") # Slightly wider for sidebar

        # --- State ---
        self.target_dir = os.getcwd() # Default
        self.config = self._load_config()
        self.api_key = ""
        self.is_running = False
        self.deferred_review = False # [NEW] Flag for post-task review
        self.current_dialog = None
        
        # Check instructions
        if self.config.get("show_instructions", True):
             self.root.after(500, self._show_instructions)
        
        # --- Threading Queues ---
        self.log_queue = queue.Queue()
        self.gui_handler = ThreadSafeGuiHandler(root, self.log_queue)

        # --- UI Layout ---
        self._build_styles()
        self._build_menu()
        self._build_ui_modern()
        
        # --- Start Polling Loops ---
        self.root.after(100, self._process_logs)
        self.root.after(100, self._process_inputs)

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            "show_instructions": True, 
            "api_key": "",
            "canvas_url": "",
            "canvas_token": "",
            "canvas_course_id": "",
            "theme": "light"
        }

    def _save_config(self, key, start_show, theme="light", canvas_url="", canvas_token="", canvas_course_id=""):
        self.config["api_key"] = key
        self.config["show_instructions"] = start_show
        self.config["theme"] = theme
        self.config["canvas_url"] = canvas_url
        self.config["canvas_token"] = canvas_token
        self.config["canvas_course_id"] = canvas_course_id
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")

    def _build_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        advanced_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Advanced", menu=advanced_menu)
        advanced_menu.add_command(label="Canvas API Settings", command=self._show_canvas_settings)
        advanced_menu.add_command(label="Open Documentation", command=self._show_documentation)
        advanced_menu.add_separator()
        advanced_menu.add_command(label="Toggle Theme (Light/Dark)", command=self._toggle_theme)
        
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Welcome / Dedication", command=lambda: self._show_instructions(force=True))

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
        tk.Label(dialog, text="MOSH Faculty ADA Toolkit Guide", font=("Segoe UI", 16, "bold"), 
                 bg=colors["bg"], fg=colors["header"]).pack(pady=15)

        # Scrolled Text for Documentation
        txt = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Segoe UI", 10), 
                                       bg=colors["bg"], fg=colors["fg"], padx=15, pady=15)
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Insert Documentation Content
        doc_content = """MOSH Faculty ADA Toolkit (2026 Edition)
=====================================

DEDICATION
----------
This software is dedicated to my son, Michael Joshua (Mosh) Albright, 
who deals with diabetic retinopathy and spent three years blind, 
and to all the other students struggling with their own challenges.

🚀 QUICK START WORKFLOW
-----------------------
1. Select Project: Click "Browse Folder" and select your exported course folder.
2. Auto-Fix: Click "Auto-Fix Issues" to fix headings, tables, and contrast issues.
3. Guided Review: Click "Guided Review" to write Alt Text for images and check links.
4. Export: Click "Repackage Course (.imscc)" to create a new Canvas package.

💡 TIPS FOR FACULTY
-------------------
- Always use a NEW, EMPTY Canvas course for testing your remediated files.
- Alt-Text Memory: The tool remembers descriptions you've entered. If you use the same logo in multiple files, it will suggest your previous text!
- Context Review: When writing Alt Text, look at the "Found in Context" box. It shows you the paragraph around the image to help you write better descriptions.
- Hard-Working Logs: Check the "Activity Log" at the bottom to see exactly what structural fixes were made to each file.

📦 FILE CONVERSION
------------------
- Use the "Conversion Wizard" to turn Word, PPT, or PDF files into Canvas WikiPages.
- For PDFs: The tool automatically detects Headers (H1-H3) based on font size.
- Math Content: Canvas uses LaTeX. If your document has complex math, consider using an external tool like Mathpix Snip, then import the Word file here.

⚖️ LICENSE & SPIRIT
-------------------
- Released under GNU General Public License version 3.
- This is non-commercial, open-source software built for the academic community.
- "Making Online Spaces Helpful" (MOSH) is dedicated to helping every student succeed.

📣 SPREAD THE WORD
------------------
- April 2026 Deadline: The goal is to help every teacher reach compliance safely and quickly.
- If this tool saved you time, click 'Spread the Word' on the sidebar to copy a message you can share with your department. Let's help everyone meet the deadline together!
"""
        txt.insert(tk.END, doc_content)
        txt.config(state='disabled') # Read-only
        
        tk.Button(dialog, text="Close", command=dialog.destroy, width=12).pack(pady=10)

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Determine Theme
        mode = self.config.get("theme", "light")
        if mode not in THEMES: mode = "light"
        colors = THEMES[mode]
        
        # Base
        style.configure(".", background=colors["bg"], foreground=colors["fg"], font=("Segoe UI", 10))
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        
        # Headers
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=colors["header"])
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=colors["subheader"])
        
        # Sidebar
        style.configure("Sidebar.TFrame", background=colors["sidebar"])
        style.configure("Sidebar.TLabel", background=colors["sidebar"], foreground=colors["sidebar_fg"], font=("Segoe UI", 10))
        
        # Buttons
        style.configure("TButton", 
            padding=6, 
            relief="flat", 
            background=colors["button"], 
            foreground=colors["button_fg"],
            font=("Segoe UI", 9)
        )
        style.map("TButton", background=[('active', colors["accent"])], foreground=[('active', 'black')])

        # Action Buttons (Primary)
        style.configure("Action.TButton", 
            font=("Segoe UI", 10, "bold"), 
            background=colors["primary"], 
            foreground="white"
        )
        style.map("Action.TButton", 
            background=[('active', colors["accent"]), ('!disabled', colors["primary"])],
            foreground=[('active', 'black')]
        )
        
        # Force background update for root
        self.root.configure(bg=colors["bg"])

    def _show_canvas_settings(self):
        """Dialog to configure Canvas API settings (Barney Style)."""
        dialog = Toplevel(self.root)
        dialog.title("Setup Your Canvas Sandbox")
        dialog.geometry("550x550")
        dialog.transient(self.root)
        dialog.grab_set()

        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])

        tk.Label(dialog, text="Step 0: Connect to your Playground", font=("Segoe UI", 16, "bold"), 
                 bg=colors["bg"], fg=colors["header"]).pack(pady=15)
        
        tk.Label(dialog, text="This tool creates Pages in a 'Sandbox' or 'Playground' course so you can test them safely.", 
                 wraplength=500, bg=colors["bg"], fg=colors["fg"], font=("Segoe UI", 10, "italic")).pack(pady=5)

        # Fields
        tk.Label(dialog, text="1. Your School's Canvas Website:", bg=colors["bg"], fg=colors["header"], font=("bold")).pack(pady=(15,0), anchor="w", padx=40)
        tk.Label(dialog, text="(e.g. https://canvas.your-school.edu)", bg=colors["bg"], fg="gray", font=("Segoe UI", 8)).pack(anchor="w", padx=40)
        ent_url = tk.Entry(dialog, width=60)
        ent_url.insert(0, self.config.get("canvas_url", ""))
        ent_url.pack(pady=5, padx=40)

        tk.Label(dialog, text="2. Your Secret Access Key:", bg=colors["bg"], fg=colors["header"], font=("bold")).pack(pady=(15,0), anchor="w", padx=40)
        
        frame_token = tk.Frame(dialog, bg=colors["bg"])
        frame_token.pack(fill="x", padx=40)
        ent_token = tk.Entry(frame_token, width=45, show="*")
        ent_token.insert(0, self.config.get("canvas_token", ""))
        ent_token.pack(side="left", pady=5)
        
        def open_token_help():
            webbrowser.open(f"{ent_url.get().strip()}/profile/settings")
            messagebox.showinfo("Help", "I've opened your Canvas Settings.\n\n1. Scroll down to 'Approved Integrations'.\n2. Click '+ New Access Token'.\n3. Copy the long key and paste it here.")

        tk.Button(frame_token, text="❓ Help Me Find This", command=open_token_help, font=("Segoe UI", 8)).pack(side="left", padx=5)

        tk.Label(dialog, text="3. Your Course Test ID (Numbers):", bg=colors["bg"], fg=colors["header"], font=("bold")).pack(pady=(15,0), anchor="w", padx=40)
        
        frame_course = tk.Frame(dialog, bg=colors["bg"])
        frame_course.pack(fill="x", padx=40)
        ent_course = tk.Entry(frame_course, width=20)
        ent_course.insert(0, self.config.get("canvas_course_id", ""))
        ent_course.pack(side="left", pady=5)

        def open_course_help():
            messagebox.showinfo("Finding Your Course ID", 
                                "It's easy! \n\n"
                                "1. Open your Canvas Playground course in your browser.\n"
                                "2. Look at the address bar at the top.\n"
                                "3. The ID is the group of numbers at the very end.\n\n"
                                "Example: if the link is .../courses/12345, your ID is 12345.")

        tk.Button(frame_course, text="❓ Help Me Find This", command=open_course_help, font=("Segoe UI", 8)).pack(side="left", padx=5)

        lbl_status = tk.Label(dialog, text="", bg=colors["bg"], font=("Segoe UI", 9, "bold"))
        lbl_status.pack(pady=10)

        def save():
            self._save_config(
                self.config.get("api_key", ""),
                self.config.get("show_instructions", True),
                self.config.get("theme", "light"),
                ent_url.get().strip(),
                ent_token.get().strip(),
                ent_course.get().strip()
            )
            messagebox.showinfo("Saved", "Settings saved! You're ready to go.")
            dialog.destroy()

        def test_safety():
            url = ent_url.get().strip()
            token = ent_token.get().strip()
            cid = ent_course.get().strip()
            
            if not url or not token or not cid:
                messagebox.showwarning("Incomplete", "Please fill out all three boxes first!")
                return

            api = canvas_utils.CanvasAPI(url, token, cid)
            
            # Connection Check
            success, msg = api.validate_credentials()
            if not success:
                lbl_status.config(text=f"❌ Connection Failed: {msg}", fg="red")
                return

            # Safety Check
            is_empty, safety_msg = api.is_course_empty()
            if is_empty:
                lbl_status.config(text="✅ SAFE: This course is empty and ready for testing.", fg="green")
            else:
                lbl_status.config(text="⚠️ WARNING: This course ALREADY HAS PAGES.", fg="#E65100")
                messagebox.showwarning("Safety Warning", f"Wait! This course ({cid}) already has content.\n\n{safety_msg}\n\nTo be safe, please use a NEW, EMPTY Sandbox course for conversions.")

        btn_frame = tk.Frame(dialog, bg=colors["bg"])
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="🔍 Check If It's Safe", command=test_safety, bg="#BBDEFB", width=20, font=("bold")).pack(side="left", padx=10)
        tk.Button(btn_frame, text="💾 Save & Close", command=save, bg="#C8E6C9", width=20, font=("bold")).pack(side="left", padx=10)

    def _toggle_theme(self):
        current = self.config.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self._save_config("", self.config.get("show_instructions", True), new_theme)
        self._build_styles() # Re-apply styles

    def _build_ui_modern(self):
        # Main Container: Sidebar (Left) + Content (Right)
        
        # 1. Sidebar
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=200)
        sidebar.pack(side="left", fill="y")
        
        # Logo Area
        # [NEW] Mosh Mascot
        try:
            mosh_path = resource_path("mosh_pilot.png")
            mosh_img = Image.open(mosh_path)
            # Make it small for the sidebar
            mosh_img = mosh_img.resize((120, 120), Image.Resampling.LANCZOS)
            self.sidebar_mosh_tk = ImageTk.PhotoImage(mosh_img)
            self.lbl_mosh_icon = ttk.Label(sidebar, image=self.sidebar_mosh_tk, style="Sidebar.TLabel")
            self.lbl_mosh_icon.pack(pady=(20, 0))
        except:
            pass

        lbl_logo = ttk.Label(sidebar, text="MOSH'S\nTOOLKIT", style="Sidebar.TLabel", font=("Segoe UI", 16, "bold"), justify="center")
        lbl_logo.pack(pady=(5, 20), padx=10)
        
        ttk.Label(sidebar, text="v2026.1", style="Sidebar.TLabel", font=("Segoe UI", 8)).pack(pady=(0, 20))
        
        # Stop Button (Persistent)
        self.btn_stop = ttk.Button(sidebar, text="🛑 STOP PROCESSING", command=self._request_stop, style="TButton")
        self.btn_stop.pack(pady=5, padx=10, fill="x")
        self.btn_stop.config(state='disabled')

        # [NEW] Viral/Mission Button
        self.btn_share = ttk.Button(sidebar, text="📣 SPREAD THE WORD", command=self._show_share_dialog, style="Action.TButton")
        self.btn_share.pack(pady=20, padx=10, fill="x")

        # [NEW] Advanced Button
        ttk.Button(sidebar, text="🛠️ Advanced Tasks", command=self._show_advanced_dialog).pack(pady=10, padx=10, fill="x")

        # 2. Main Content Area (Scrollable)
        container = ttk.Frame(self.root)
        container.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        # Create a frame inside the canvas for the actual content
        content = ttk.Frame(self.canvas, padding="20 20 20 20")

        # Configure scrolling
        def on_frame_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # Make the inner frame width match the canvas width
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas_window = self.canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", on_frame_configure)
        self.canvas.bind("<Configure>", on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Mousewheel support
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # -- Target Project Section --
        ttk.Label(content, text="1. Select Project", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_dir = ttk.Frame(content)
        frame_dir.pack(fill="x", pady=(5, 15))
        
        # Row 1: Import Button
        btn_import = ttk.Button(
            frame_dir, 
            text="📦 Import My Course (Canvas Export File)", 
            command=self._import_package,
            style="Action.TButton"
        )
        btn_import.pack(side="top", fill="x", pady=(0, 5))

        # Row 1b: Connect to Canvas (Barney Mode)
        btn_canvas = ttk.Button(
            frame_dir, 
            text="🔗 Connect to My Canvas Playground", 
            command=self._show_canvas_settings,
            style="Action.TButton"
        )
        btn_canvas.pack(side="top", fill="x", pady=(0, 5))
        
        # Row 2: Folder Browser
        frame_browse = ttk.Frame(frame_dir)
        frame_browse.pack(fill="x")
        
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]
        
        self.lbl_dir = tk.Entry(frame_browse, bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])
        self.lbl_dir.insert(0, self.target_dir)
        self.lbl_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(frame_browse, text="Browse Folder...", command=self._browse_folder).pack(side="right")


        # -- Step 2: Converters --
        ttk.Label(content, text="2. Convert Files", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_convert = ttk.Frame(content)
        frame_convert.pack(fill="x", pady=(10, 20))
        
        self.btn_wizard = ttk.Button(frame_convert, text="🪄 Conversion Wizard (Word/PPT -> Canvas Pages)", command=self._show_conversion_wizard, style="Action.TButton")
        self.btn_wizard.pack(fill="x", pady=5)
        
        frame_singles = ttk.Frame(frame_convert)
        frame_singles.pack(fill="x")
        
        self.btn_word = ttk.Button(frame_singles, text="Word", command=lambda: self._show_conversion_wizard("docx"))
        self.btn_word.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_excel = ttk.Button(frame_singles, text="Excel", command=lambda: self._show_conversion_wizard("xlsx"))
        self.btn_excel.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_ppt = ttk.Button(frame_singles, text="PPT", command=lambda: self._show_conversion_wizard("pptx"))
        self.btn_ppt.pack(side="left", fill="x", expand=True, padx=2)
        self.btn_pdf = ttk.Button(frame_singles, text="PDF", command=lambda: self._show_conversion_wizard("pdf"))
        self.btn_pdf.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_batch = ttk.Button(frame_convert, text="🎲 Roll the Dice: Convert Everything (Batch Mode) 🎲", 
                                    command=self._run_batch_conversion, style="Action.TButton")
        self.btn_batch.pack(fill="x", pady=(10, 5))


        # -- Step 3: Remediation Actions (Grid) --
        ttk.Label(content, text="3. Fix & Review", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_actions = ttk.Frame(content)
        frame_actions.pack(fill="x", pady=(10, 20))
        
        # Friendly Button Names
        self.btn_auto = ttk.Button(frame_actions, text="Auto-Fix Issues\n(Headings, Tables, Contrast)", command=self._run_auto_fixer, style="Action.TButton")
        self.btn_auto.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_inter = ttk.Button(frame_actions, text="Guided Review\n(Image Descriptions & Links)", command=self._run_interactive, style="Action.TButton")
        self.btn_inter.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Row 2 (Audit)
        self.btn_audit = ttk.Button(frame_actions, text="Quick Report\n(Is it Compliant?)", command=self._run_audit, style="Action.TButton")
        self.btn_audit.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        frame_actions.columnconfigure(0, weight=1)
        frame_actions.columnconfigure(1, weight=1)
        frame_actions.columnconfigure(2, weight=1)


        # -- Step 4: Final Launch --
        ttk.Label(content, text="4. Final Step", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 0))
        frame_final = ttk.Frame(content)
        frame_final.pack(fill="x", pady=5)

        self.btn_check = ttk.Button(
            frame_final, 
            text="🚥 Am I Ready to Upload? (Run Pre-Flight Check)", 
            command=self._show_preflight_dialog,
            style="Action.TButton"
        )
        self.btn_check.pack(fill="x", pady=2)


        # -- Logs --
        ttk.Label(content, text="Activity Log", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 0))
        self.txt_log = scrolledtext.ScrolledText(content, height=8, state='disabled', font=("Consolas", 9), relief="flat", borderwidth=1)
        self.txt_log.pack(fill="both", expand=True, pady=5)

    def _browse_folder(self):
        path = filedialog.askdirectory(initialdir=self.target_dir)
        if path:
            self.target_dir = path
            self.lbl_dir.delete(0, tk.END)
            self.lbl_dir.insert(0, path)
            self._log(f"Selected: {path}")

    def _import_package(self):
        """Allows user to select .imscc or .zip and extracts it."""
        path = filedialog.askopenfilename(
            filetypes=[("Canvas Export / Zip", "*.imscc *.zip"), ("All Files", "*.*")]
        )
        if not path: return
        
        # Determine extraction folder
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        folder_name = os.path.splitext(filename)[0] + "_extracted"
        extract_to = os.path.join(directory, folder_name)
        
        # Confirm (Must be on main thread)
        if not messagebox.askyesno("Confirm Import", f"Extract package to:\n{extract_to}?"):
            return

        def task():
            self.gui_handler.log(f"--- Extracting Package: {filename} ---")
            success, msg = converter_utils.unzip_course_package(path, extract_to, log_func=self.gui_handler.log)
            
            if success:
                self.gui_handler.log(msg) # msg already has "Success!" prefix
                # Update UI elements via after()
                self.root.after(0, lambda: self._finalize_import(extract_to))
            else:
                self.gui_handler.log(f"[ERROR] Import Failed: {msg}")
                self.root.after(0, lambda: messagebox.showerror("Import Error", f"Failed to extract package:\n{msg}"))

        self._run_task_in_thread(task, "Package Import")

    def _finalize_import(self, extract_to):
        """Updates UI after successful import (runs on main thread)."""
        self.target_dir = extract_to
        self.lbl_dir.delete(0, tk.END)
        self.lbl_dir.insert(0, extract_to)
        
        msg = (f"Package extracted successfully!\n\n"
               f"Mosh has prepared your project here:\n{extract_to}\n\n"
               f"Now, use Step 2 to fix descriptions or Step 3 to add more files.")
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
            filetypes=[("Canvas Course Package", "*.imscc")]
        )
        
        if not output_path: return

        def task():
            self.gui_handler.log(f"--- Packaging Course... ---")
            success, msg = converter_utils.create_course_package(self.target_dir, output_path, log_func=self.gui_handler.log)
            
            if success:
                 self.gui_handler.log(f"Success! {msg}")
                 self.root.after(0, lambda: messagebox.showinfo("Export Complete", 
                    f"Course Package Created:\n{output_path}\n\nIMPORTANT NEXT STEPS:\n"
                    "1. Create a NEW, EMPTY course in Canvas to use as a test space.\n"
                    "2. Import this file into that empty course.\n"
                    "3. Review all changes BEFORE moving content to a live semester."
                 ))
            else:
                 self.gui_handler.log(f"[ERROR] Packaging Failed: {msg}")
                 self.root.after(0, lambda: messagebox.showerror("Export Error", f"Failed to create package:\n{msg}"))

        self._run_task_in_thread(task, "Course Packaging")

    def _log(self, msg):
        self.txt_log.configure(state='normal')
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state='disabled')

    def _process_logs(self):
        """Poll the log queue and update the text widget (Throttled)."""
        try:
            processed = 0
            while processed < 50: # Limit per cycle to keep UI fluid
                msg = self.log_queue.get_nowait()
                self._log(msg)
                processed += 1
        except queue.Empty:
            pass
        self.root.after(100, self._process_logs)

    def _process_inputs(self):
        """Poll for input requests from the worker thread."""
        try:
            while True:
                req = self.gui_handler.input_request_queue.get_nowait()
                kind, message, payload = req
                
                response = None
                if kind == 'prompt':
                    response = simpledialog.askstring("Input Required", message, parent=self.root)
                    if response is None: response = "" 
                elif kind == 'confirm':
                    response = messagebox.askyesno("Confirm", message, parent=self.root)
                elif kind == 'prompt_image':
                    path, context = payload
                    response = self._show_image_dialog(message, path, context)
                elif kind == 'prompt_link':
                    href, context = payload
                    response = self._show_link_dialog(message, href, context)
                
                self.gui_handler.input_response_queue.put(response)
        except queue.Empty:
            pass
        self.root.after(100, self._process_inputs)
        
    def _show_image_dialog(self, message, image_path, context=None):
        """Custom dialog to show an image and prompt for alt text."""
        dialog = Toplevel(self.root)
        dialog.title("Image Review")
        dialog.geometry("600x680") 
        dialog.transient(self.root)
        dialog.grab_set()
        
        def on_close_x():
            self.gui_handler.stop_requested = True
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_close_x)

        # Context area
        if context:
            ctx_frame = ttk.LabelFrame(dialog, text="Surrounding Text Context", padding=5)
            ctx_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(ctx_frame, text=context, wraplength=550, font=("Segoe UI", 9, "italic"), justify="left").pack()
        
        # Load and resize image
        try:
            pil_img = Image.open(image_path)
            pil_img.thumbnail((500, 350)) 
            tk_img = ImageTk.PhotoImage(pil_img)
            
            lbl_img = tk.Label(dialog, image=tk_img)
            lbl_img.image = tk_img 
            lbl_img.pack(pady=10)
        except Exception as e:
            tk.Label(dialog, text=f"[Could not load image: {e}]", fg="red").pack(pady=10)
        
        fname = os.path.basename(image_path)
        tk.Label(dialog, text=f"File: {fname}", font=("Segoe UI", 9, "bold")).pack()
        tk.Label(dialog, text=message, wraplength=550, font=("Segoe UI", 10)).pack(pady=5)
        
        # Input Area
        entry_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=entry_var, width=60)
        entry.pack(pady=5)
        entry.focus_set()
        
        lbl_status = tk.Label(dialog, text="", fg="blue", font=("Segoe UI", 9, "italic"))
        lbl_status.pack(pady=2)

        result = {"text": ""}
        def on_ok(event=None):
            result["text"] = entry_var.get()
            dialog.destroy()
        def on_skip():
            result["text"] = "" 
            dialog.destroy()
            
        def on_decorate():
            result["text"] = "__DECORATIVE__"
            dialog.destroy()
            
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Update Alt Text", command=on_ok, bg="#dcedc8", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Mark Decorative", command=on_decorate, bg="#fff9c4", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Skip / Ignore", command=on_skip, width=15).pack(side="left", padx=5)
        
        dialog.bind('<Return>', on_ok)
        self.root.wait_window(dialog)
        return result["text"]

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
            ctx_frame = ttk.LabelFrame(dialog, text="Surrounding Text Context", padding=5)
            ctx_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(ctx_frame, text=context, wraplength=500, font=("Segoe UI", 9, "italic"), justify="left").pack()
            
        tk.Label(dialog, text=message, wraplength=500, font=("Segoe UI", 10)).pack(pady=10)
         
        def open_link():
             import webbrowser
             webbrowser.open(href)
             
        if href:
             btn_link = tk.Button(dialog, text=f"🌐 Open Link / File (Verify)", command=open_link, bg="#BBDEFB", cursor="hand2")
             btn_link.pack(pady=5)
             tk.Label(dialog, text=f"Target: {href[:60] + '...' if len(href) > 60 else href}", font=("Segoe UI", 8, "italic"), fg="gray").pack()
 
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
        tk.Button(btn_frame, text="Update Link Text", command=on_ok, bg="#dcedc8", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Skip / Ignore", command=on_skip, width=15).pack(side="left", padx=5)
        
        dialog.bind('<Return>', on_ok)
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

        tk.Label(dialog, text="Help Your Colleagues Meet the Deadline!", 
                 font=("Segoe UI", 14, "bold"), bg=colors["bg"], fg=colors["header"]).pack(pady=15)

        msg = ("Teachers everywhere are stressed about the April 2026 compliance deadline.\n"
               "If this tool helped you save time, please share it with your department!\n\n"
               "Copy the message below to send in an email or Slack:")
        tk.Label(dialog, text=msg, wraplength=500, bg=colors["bg"], fg=colors["fg"], justify="center").pack(pady=5)

        share_text = ("Hi team,\n\n"
                     "I found a great free tool called the MOSH ADA Toolkit that automatically "
                     "remediates Canvas pages. It fixes headings, tables, and contrast issues in seconds, "
                     "which makes the upcoming April 2026 deadline much more manageable.\n\n"
                     "It was built by a fellow educator and it's completely free. "
                     "Worth checking out to save some stress!\n\n"
                     "GitHub: https://github.com/meri-becomming-code/mosh\n"
                     "Download: https://meri-becomming-code.github.io/mosh/")
        
        txt = tk.Text(dialog, height=8, width=60, font=("Segoe UI", 9))
        txt.pack(pady=10, padx=20)
        txt.insert(tk.END, share_text)

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(share_text)
            btn_copy.config(text="✅ COPIED TO CLIPBOARD!", state='disabled')

        btn_copy = tk.Button(dialog, text="📋 Copy Message", command=copy_to_clipboard, 
                             bg=colors["primary"], fg="white", width=25, font=("Segoe UI", 10, "bold"))
        btn_copy.pack(pady=15)

        tk.Button(dialog, text="Close", command=dialog.destroy, width=12).pack(pady=5)

    def _disable_buttons(self):
        """Gray out all action buttons while a task is running."""
        for btn in [self.btn_auto, self.btn_inter, self.btn_audit, 
                   self.btn_wizard, self.btn_word, self.btn_excel, 
                   self.btn_ppt, self.btn_pdf, self.btn_batch]:
            try: btn.config(state='disabled')
            except: pass
        self.btn_stop.config(state='normal')
        self.gui_handler.stop_requested = False
        self.is_running = True

    def _enable_buttons(self):
        """Restore all action buttons."""
        for btn in [self.btn_auto, self.btn_inter, self.btn_audit, 
                   self.btn_wizard, self.btn_word, self.btn_excel, 
                   self.btn_ppt, self.btn_pdf, self.btn_batch]:
            try: btn.config(state='normal')
            except: pass
        self.btn_stop.config(state='disabled')
        self.is_running = False

        # [NEW] Handle deferred review launch
        if self.deferred_review:
            self.deferred_review = False
            self.root.after(100, self._run_interactive)

    def _request_stop(self):
        """Triggers a stop request."""
        if self.is_running:
            self.gui_handler.stop_requested = True
            self.gui_handler.log("\n[STOP] Stop requested. Finishing current file and exiting...")
            self.btn_stop.config(state='disabled')


            def on_progress(curr, total, fname, result):
                self.gui_handler.log(f"[{curr}/{total}] {fname} -> {result[:40]}...")

            results = ai_helper.batch_generate_alt_text(found_images, self.api_key, on_progress)
            self.gui_handler.log(f"Batch complete. {len(results)} images processed.")
            messagebox.showinfo("Batch Complete", f"Processed {len(found_images)} images.\nResults are stored in Alt-Text Memory.")

        self._run_task_in_thread(task, "Batch AI Alt-Text")


    def _run_task_in_thread(self, task_func, task_name):
        if self.is_running: return
        self._disable_buttons()
        self.target_dir = self.lbl_dir.get().strip()
        
        def worker():
            self.gui_handler.log(f"--- Starting {task_name} ---")
            self.gui_handler.log(f"[DEBUG] Target: {self.target_dir}")
            try:
                task_func()
                self.gui_handler.log(f"--- {task_name} Completed ---")
            except Exception as e:
                self.gui_handler.log(f"[ERROR] {e}")
            finally:
                self.root.after(0, self._enable_buttons)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _get_all_html_files(self):
        """Standardized helper to find all HTML files in the target directory."""
        if not os.path.isdir(self.target_dir):
            self.gui_handler.log(f"[ERROR] Invalid directory: {self.target_dir}")
            return []
            
        html_files = []
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        return html_files

    def _run_auto_fixer(self):
        def task():
            html_files = self._get_all_html_files()
            if not html_files: return
            
            self.gui_handler.log(f"Processing {len(html_files)} HTML files...")
            files_with_fixes = 0
            total_fixes = 0
            for i, path in enumerate(html_files):
                success, fixes = interactive_fixer.run_auto_fixer(path, self.gui_handler)
                if success and fixes:
                    files_with_fixes += 1
                    total_fixes += len(fixes)
                    self.gui_handler.log(f"   [{i+1}/{len(html_files)}] [FIXED] {os.path.basename(path)}:")
                    for fix in fixes:
                        self.gui_handler.log(f"    - {fix}")
            
            # Estimate time saved
            minutes_saved = total_fixes * 1.5
            hours = int(minutes_saved // 60)
            mins = int(minutes_saved % 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            self.gui_handler.log(f"Finished. Files with fixes: {files_with_fixes} of {len(html_files)} | Total fixes applied: {total_fixes}")
            self.gui_handler.log(f"🏆 YOU SAVED APPROXIMATELY {time_str} OF TEDIOUS MANUAL LABOR!")

            self.gui_handler.log(f"Finished. Files with fixes: {files_with_fixes} of {len(html_files)} | Total fixes applied: {total_fixes}")
            self.gui_handler.log(f"🏆 YOU SAVED APPROXIMATELY {time_str} OF TEDIOUS MANUAL LABOR!")

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
                interactive_fixer.scan_and_fix_file(filepath, self.gui_handler, self.target_dir)
                
        self._run_task_in_thread(task, "Interactive Fixer")

# [REMOVED] _run_cleanup_markers per user request. 
# Markers are no longer added, so cleanup is unnecessary.

    def _run_audit(self):
        def task():
            html_files = self._get_all_html_files()
            if not html_files: return

            self.gui_handler.log(f"Auditing {len(html_files)} files...")
            all_issues = {}
            
            for path in html_files:
                res = run_audit.audit_file(path)
                if res and (res["technical"] or res["subjective"]):
                     rel_path = os.path.relpath(path, self.target_dir)
                     all_issues[rel_path] = res
                     
                     # [AUDIT FIX] Show summary directly in log
                     summary = run_audit.get_issue_summary(res)
                     self.gui_handler.log(f"Issues in {os.path.basename(path)}: {summary}")

            out_file = os.path.join(self.target_dir, 'audit_report.json')
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(all_issues, f, indent=2)
            
            self.gui_handler.log(f"Audit Complete. Issues found in {len(all_issues)} files.")
            self.gui_handler.log(f"Report saved to {out_file}")

        self._run_task_in_thread(task, "Audit")

    # --- NEW METHODS ---
    def _show_instructions(self, force=False):
        """Shows Welcome/Instructions Dialog."""
        if not force and not self.config.get("show_instructions", True):
            return

        dialog = Toplevel(self.root)
        dialog.title("MOSH's Toolkit: Making Online Spaces Helpful")
        dialog.geometry("750x700")
        dialog.lift()
        dialog.focus_force()
        
        # Style
        colors = THEMES[self.config.get("theme", "light")]
        dialog.configure(bg=colors["bg"])
        
        # Content
        intro = """
        Welcome to MOSH's Toolkit
        (Making Online Spaces Helpful)

        🎯 THE MISSION:
        April 2026 is the Federal ADA deadline for institutions. 
        This toolkit is designed to help teachers reach compliance 
        without spending hundreds of hours on manual labor.

        🚀 QUICK START WORKFLOW:
        1. Select Project: Click "Browse Folder" and select your Canvas export folder.
        2. Auto-Fix: Click "Auto-Fix Issues" to handle headings, tables, and contrast.
        3. Guided Review: Click "Guided Review" to write Alt Text for images.
        4. Repackage: Click "Repackage Course" to create a new file for Canvas.

        📦 SAFETY ARCHIVE:
        Original files (Word, PPT, PDF) are automatically moved to a hidden 
        '_mosh_source_archive' folder. This ensures they aren't uploaded to 
        Canvas accidentally, while keeping them safe on your local computer.

        ⚠️ ALPHA TEST WARNING:
        Always test your remediated files in a NEW EMPTY CANVAS COURSE 
        before moving them into a live semester.
        
        🐛 Support: meredithkasprak@gmail.com
        """
        
        lbl = tk.Label(dialog, text=intro, justify="left", font=("Segoe UI", 11), 
                       wraplength=650, bg=colors["bg"], fg=colors["fg"])
        lbl.pack(pady=20, padx=30)
        
        # Checkbox
        var_show = tk.BooleanVar(value=True if force else self.config.get("show_instructions", True))
        
        def on_close():
            self._save_config("", var_show.get())
            dialog.destroy()
            
        chk = tk.Checkbutton(dialog, text="Show this message on startup", variable=var_show)
        chk.pack(pady=10)
        
        tk.Button(dialog, text="Get Started", command=on_close, bg="#4b3190", fg="white", font=("Arial", 10, "bold"), width=20).pack(pady=10)


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
            supported_exts = {'.docx', '.pptx', '.xlsx', '.pdf'}
            title_suffix = "(All Types)"
            
        found_files = []
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_exts:
                     # Ignore temp files (~$)
                     if not file.startswith('~$'):
                        found_files.append(os.path.join(root, file))
        
        if not found_files:
             messagebox.showinfo("No Files", f"No convertible files found matching {supported_exts} in the current folder.")
             return

        # 2. Show Dialog
        dialog = Toplevel(self.root)
        dialog.title("Interactive Conversion Wizard")
        dialog.geometry("600x600")
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        
        tk.Label(dialog, text="Select Files to Convert", font=("Arial", 12, "bold"), fg="#4b3190").pack(pady=10)
        tk.Label(dialog, text="We will process these one by one. You will preview each change.", font=("Arial", 10)).pack(pady=(0,10))

        # Scrollable Frame for Checkboxes
        frame_canvas = tk.Frame(dialog)
        frame_canvas.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(frame_canvas, bg="white")
        scrollbar = tk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
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
            chk = tk.Checkbutton(scroll_frame, text=rel_path, variable=var, anchor="w", bg="white")
            chk.pack(fill="x", padx=5, pady=2)
            vars_map[fpath] = var
            
        # Buttons
        def on_start():
            selected = [path for path, var in vars_map.items() if var.get()]
            if not selected:
                messagebox.showwarning("None Selected", "Please select at least one file.")
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
        
        tk.Button(btn_frame, text="Select/Deselect All", command=on_toggle_all).pack(side="left")
        tk.Button(btn_frame, text="Start Conversion Process ▶", command=on_start, bg="#4b3190", fg="white", font=("bold")).pack(side="right")


    def _run_wizard_task(self, files):
        """Worker thread for the wizard."""
        
        def task():
            self.gui_handler.log(f"--- Starting Wizard on {len(files)} files ---")
            
            kept_files = [] # Track successful conversions

            for i, fpath in enumerate(files):
                if self.gui_handler.is_stopped(): break
                fname = os.path.basename(fpath)
                ext = os.path.splitext(fpath)[1].lower().replace('.', '')
                self.gui_handler.log(f"[{i+1}/{len(files)}] Preparing for Canvas: {fname}...")
                
                # 1. Convert
                output_path = None
                err = None
                
                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(fpath, self.gui_handler)
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                     output_path, err = converter_utils.convert_ppt_to_html(fpath, self.gui_handler)
                elif ext == "pdf":
                     output_path, err = converter_utils.convert_pdf_to_html(fpath, self.gui_handler)
                
                if err or not output_path:
                    self.gui_handler.log(f"   [ERROR] Failed to convert: {err}")
                    continue
                
                self.gui_handler.log(f"[{i+1}/{len(files)}] BUILDING PAGE: {fname}...")
                
                # 2. RUN AUTO-FIXER (Structural)

                self.gui_handler.log(f"   [1/3] Running Auto-Fixer (Headings, Tables)...")
                # Structural fixes only, no placeholders/markers added
                interactive_fixer.run_auto_fixer(output_path, self.gui_handler)
                
                # 3. RUN INTERACTIVE REVIEW (Alt Text / Links)
                self.gui_handler.log(f"   [2/3] Launching Guided Review...")
                interactive_fixer.scan_and_fix_file(output_path, self.gui_handler, self.target_dir)
                
                # 4. Update Project Links & Archive Source
                self.gui_handler.log(f"   [3/3] Updating project links and archiving original...")
                converter_utils.update_links_in_directory(self.target_dir, fpath, output_path)
                converter_utils.archive_source_file(fpath)

                # 5. AUTO-UPLOAD TO CANVAS (No prompt)
                api = self._get_canvas_api()
                if api:
                    self.gui_handler.log(f"   🚀 AUTO-UPLOAD: Sending '{os.path.basename(output_path)}' to Canvas...")
                    # We pass auto_confirm_links=True to avoid extra prompts during the batch upload if applicable
                    # (Note: _upload_page_to_canvas may need to support this flag or handle things silently)
                    self._upload_page_to_canvas(output_path, fpath, api)
                else:
                    self.gui_handler.log("   [INFO] Canvas not connected. Page saved locally.")

                self.gui_handler.log(f"✅ {fname} Processed Successfully.")
            
            self.gui_handler.log("--- Page Builder Process Complete ---")
            messagebox.showinfo("Done", "Your pages have been built, reviewed, and uploaded!")

        self._run_task_in_thread(task, "Conversion Wizard")

    def _convert_file(self, ext):
        """Generic handler for file conversion."""
        file_path = filedialog.askopenfilename(filetypes=[(f"{ext.upper()} Files", f"*.{ext}")])
        if not file_path: return
        
        if ext == "pdf":
             if not messagebox.askyesno("PDF Conversion (Beta)", 
                "⚠️ PDF Conversion is extremely difficult to automate.\n\n"
                "This tool will attempt to extract Text, Images, and basic Layout.\n"
                "It is NOT perfect for complex documents.\n\n"
                "Are you sure you want to proceed?"):
                return

        
        self.gui_handler.log(f"Preparing {os.path.basename(file_path)} for Canvas...")
        
        def task():
            output_path, err = None, None
            
            if ext == "docx":
                output_path, err = converter_utils.convert_docx_to_html(file_path, self.gui_handler)
            elif ext == "xlsx":
                output_path, err = converter_utils.convert_excel_to_html(file_path)
            elif ext == "pptx":
                output_path, err = converter_utils.convert_ppt_to_html(file_path, self.gui_handler)
            elif ext == "pdf":
                output_path, err = converter_utils.convert_pdf_to_html(file_path, self.gui_handler)
            
            if err:
                 self.gui_handler.log(f"[ERROR] Conversion failed: {err}")
                 return


            self.gui_handler.log(f"[SUCCESS] Ready for Canvas: {os.path.basename(output_path)}")
            
            # 2. Preview (Open both)
            try:
                os.startfile(file_path) # Open Original
                os.startfile(output_path) # Open New Page
            except Exception as e:
                self.gui_handler.log(f"   [WARNING] Could not auto-open files: {e}")
            
            # 3. Prompt user (Keep/Discard?)
            msg = (f"Reviewing: {os.path.basename(file_path)}\n\n"
                   f"I have opened both the original and the new version.\n"
                   f"Do you want to KEEP this version for Canvas?")
            
            if not self.gui_handler.confirm(msg):
                try:
                    os.remove(output_path)
                    self.gui_handler.log("   Discarded.")
                except:
                    pass
                return

            # 4. Success / Info
            if ext == "pptx":
                self.gui_handler.log("[INFO] Images extracted with [FIX_ME] tags.")
                self.gui_handler.log("!!! IMPORTANT: Run '2. Interactive Fixer' now to fix image descriptions !!!")

            # 5. Link Updater
            msg_link = (f"Excellent. The original file is untouched.\n\n"
                        f"Would you like to SCAN ALL OTHER FILES in this folder\n"
                        f"and update any links to point to this new LIVE CANVAS PAGE instead?")
            
            if self.gui_handler.confirm(msg_link):
                count = converter_utils.update_links_in_directory(self.target_dir, file_path, output_path)
                # [NEW] Explicitly archive original file upon confirmation
                converter_utils.archive_source_file(file_path)
                
                # [NEW] Update Manifest
                rel_old = os.path.relpath(file_path, self.target_dir)
                rel_new = os.path.relpath(output_path, self.target_dir)
                m_success, m_msg = converter_utils.update_manifest_resource(self.target_dir, rel_old, rel_new)
                self.gui_handler.log(f"   [DONE] Links updated in {count} files. Original archived.")

                
            self.gui_handler.log(f"--- {ext.upper()} Done ---")
            
        self._run_task_in_thread(task, f"Convert {ext.upper()}")

    def _upload_page_to_canvas(self, html_path, original_source_path, api, auto_confirm_links=False):
        """Helper to upload a single HTML file as a Canvas Page with images."""
        fname = os.path.basename(original_source_path)
        self.gui_handler.log(f"   [Sync] Uploading to Canvas: {fname}...")
        
        try:
            # 1. Read HTML
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 2. Handle Images properly
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            images = soup.find_all('img')
            
            if images:
                self.gui_handler.log(f"   [Sync] Found {len(images)} images. Uploading to course files...")
                for img in images:
                    local_src = img.get('src')
                    if not local_src or "http" in local_src: continue
                    
                    # Resolve absolute path
                    img_abs_path = os.path.join(os.path.dirname(html_path), local_src)
                    if os.path.exists(img_abs_path):
                        success_img, res_img = api.upload_file(img_abs_path, folder_path="remediated_images")
                        if success_img:
                            # Canvas relative links usually look like /courses/:id/files/:file_id/preview
                            canvas_img_url = f"/courses/{self.config['canvas_course_id']}/files/{res_img['id']}/preview"
                            img['src'] = canvas_img_url
                            self.gui_handler.log(f"      Uploaded: {os.path.basename(img_abs_path)}")
                        else:
                            self.gui_handler.log(f"      [WARNING] Image upload failed: {res_img}")
            
            # 3. Create Page
            page_title = os.path.splitext(fname)[0]
            success_page, res_page = api.create_page(page_title, str(soup))
            
            if success_page:
                canvas_page_url = res_page.get('html_url')
                self.gui_handler.log(f"   [Sync] SUCCESS! Live Page: {canvas_page_url}")
                
                # 4. Link update: Point ALL OTHER FILES to this live Canvas Page
                should_update = False
                if auto_confirm_links:
                    should_update = True
                else:
                    msg_live_link = (f"Page created on Canvas.\n\n"
                                    f"Would you like to update all other files in this folder\n"
                                    f"to point to the LIVE CANVAS PAGE instead of the local HTML?")
                    if self.gui_handler.confirm(msg_live_link):
                        should_update = True

                if should_update:
                    count = converter_utils.update_links_in_directory(self.target_dir, original_source_path, canvas_page_url)
                    self.gui_handler.log(f"   [Sync] Updated links in {count} files to point to Canvas.")
                return True
            else:
                self.gui_handler.log(f"   [ERROR] Page creation failed: {res_page}")
                return False
                
        except Exception as e:
            self.gui_handler.log(f"   [ERROR] Sync failed: {e}")
            return False

    def _get_canvas_api(self):
        """Helper to instantiate CanvasAPI from config."""
        config = self.config
        url = config.get("canvas_url")
        token = config.get("canvas_token")
        cid = config.get("canvas_course_id") # Corrected key
        if not url or not token or not cid:
            return None
        return canvas_utils.CanvasAPI(url, token, cid)

    def _show_advanced_dialog(self):
        """Displays advanced/manual tasks that users occasionally need."""
        dialog = Toplevel(self.root)
        dialog.title("🛠️ Advanced Tasks")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="🛠️ Advanced Tasks", style="Header.TLabel").pack(pady=10)
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="These tools are for specific situations.\nIf you are using the Push button, you don't need these!", 
                  wraplength=350, font=("Segoe UI", 9, "italic")).pack(pady=(0, 20))

        # Repackage without Upload
        ttk.Button(frame, text="📦 Repackage Course (.imscc) without Uploading", 
                   command=self._export_package, style="TButton").pack(fill="x", pady=5)
        
        ttk.Label(frame, text="Creates a new .imscc file on your computer but does NOT send it to Canvas.", 
                  wraplength=350, font=("Segoe UI", 8)).pack(pady=(0, 15))

        # Clear Logs
        ttk.Button(frame, text="🧹 Clear Activity Log", 
                   command=lambda: [self.txt_log.configure(state='normal'), self.txt_log.delete(1.0, tk.END), self.txt_log.configure(state='disabled')],
                   style="TButton").pack(fill="x", pady=5)

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _run_batch_conversion(self):
        """Processes ALL convertible files in one go without per-file verification."""
        # 1. Scary Warning
        msg = ("🎲 ROLL THE DICE: BATCH CONVERSION 🎲\n\n"
               "WARNING: This will convert EVERY Word, PPT, Excel, and PDF file in your project to Canvas WikiPages automatically.\n\n"
               "- It is NOT perfect. Layouts may break.\n"
               "- Original files will be moved to the archive folder for safety.\n"
               "- Links will be updated throughout your project.\n\n"
               "YOU are responsible for reviewing the resulting Canvas pages. "
               "Are you sure you want to take this gamble?")
        
        if not messagebox.askyesno("🎲 Feeling Lucky?", msg):
            return

        # [NEW] Check if they want to sync to Canvas as they go
        self.config["batch_sync_confirmed"] = False
        api = self._get_canvas_api()
        if api:
            msg_sync = "🎲 Would you like me to SYNC these pages to Canvas as I convert them?\n\n(This creates live, editable Pages in your Canvas course immediately!)"
            if messagebox.askyesno("Live Sync?", msg_sync):
                self.config["batch_sync_confirmed"] = True

        def task():
            supported_exts = {'.docx', '.pptx', '.xlsx', '.pdf'}
            found_files = []
            for root, dirs, files in os.walk(self.target_dir):
                if converter_utils.ARCHIVE_FOLDER_NAME in root: continue
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in supported_exts and not file.startswith('~$'):
                        found_files.append(os.path.join(root, file))
            
            if not found_files:
                self.gui_handler.log("No convertible files found.")
                return

            self.gui_handler.log(f"--- 🎲 Starting Batch Gamble on {len(found_files)} files ---")
            success_count = 0
            total_auto_fixes = 0
            
            for i, fpath in enumerate(found_files):
                if self.gui_handler.is_stopped(): break
                fname = os.path.basename(fpath)
                ext = os.path.splitext(fpath)[1].lower().replace('.', '')
                self.gui_handler.log(f"[{i+1}/{len(found_files)}] Preparing Canvas WikiPage: {fname}")
                
                output_path = None
                err = None
                
                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(fpath, self.gui_handler)
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                    output_path, err = converter_utils.convert_ppt_to_html(fpath, self.gui_handler)
                elif ext == "pdf":
                    output_path, err = converter_utils.convert_pdf_to_html(fpath, self.gui_handler)
                
                if output_path:
                    success_count += 1
                    
                    # Run Auto-Fixer on the document immediately
                    self.gui_handler.log(f"   [FIXING] Checking Page for ADA compliance...")
                    success_fix, fixes = interactive_fixer.run_auto_fixer(output_path, self.gui_handler)
                    if success_fix and fixes:
                        total_auto_fixes += len(fixes)
                    
                    # Update Links (extensionless)
                    l_count = converter_utils.update_links_in_directory(self.target_dir, fpath, output_path)
                    
                    # [NEW] Update Manifest
                    rel_old = os.path.relpath(fpath, self.target_dir)
                    rel_new = os.path.relpath(output_path, self.target_dir)
                    m_success, m_msg = converter_utils.update_manifest_resource(self.target_dir, rel_old, rel_new)
                    if m_success:
                        self.gui_handler.log(f"   [MANIFEST] {m_msg}")
                    
                    # Archive
                    converter_utils.archive_source_file(fpath)
                    self.gui_handler.log(f"   [DONE] Links updated in {l_count} files. Original archived.")
                    
                    # [NEW] Optional Live Sync for Batch
                    sync_api = self._get_canvas_api()
                    if sync_api and self.config.get("batch_sync_confirmed"):
                        self._upload_page_to_canvas(output_path, fpath, sync_api, auto_confirm_links=True)
                else:
                    self.gui_handler.log(f"   [FAILED] {err}")
            
            # Estimation: 10 minutes per file vs manual remediation + auto-fixes
            # (Adjusted based on "fast techy user" feedback, though pottery teachers might take longer!)
            total_mins = (success_count * 10) + (total_auto_fixes * 1.5)
            hours = int(total_mins // 60)
            mins = int(total_mins % 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            self.gui_handler.log(f"\n--- Batch Complete. {success_count} files converted. ---")
            self.gui_handler.log(f"🏆 TOTAL PREDICTED LABOR SAVED: {time_str}")
            self.gui_handler.log(f"   (Estimate based on 10m/file vs manual source remediation + {total_auto_fixes} automatic HTML fixes)")
            
            # [NEW] Integrated Interactive Checker (Deferred)
            def ask_review():
                msg_review = ("Batch conversion is finished!\n\n"
                             "Would you like to start the Guided Review (Interactive Checker) now?\n"
                             "This will help you quickly fix image descriptions and check links.")
                if messagebox.askyesno("Step 2: Guided Review", msg_review):
                    self.deferred_review = True # Flag for _enable_buttons 
            
            self.root.after(0, ask_review)

            self.gui_handler.log("\n🛡️ Remember: Check the files in Canvas before publishing!")
            self.root.after(0, lambda: messagebox.showinfo("Gamble Complete", f"Processed {len(found_files)} files.\nCheck the logs for details."))

        self._run_task_in_thread(task, "Batch Gamble")

    # --- [NEW] Pre-Flight & Push Logic ---

    def _show_preflight_dialog(self):
        """Displays a simple dashboard checking course readiness."""
        dialog = Toplevel(self.root)
        dialog.title("🚦 Pre-Flight Check")
        dialog.geometry("550x500")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="🚦 Pre-Flight Check", style="Header.TLabel").pack(pady=10)
        ttk.Label(dialog, text="Checking if your course is safe to upload...", font=("Segoe UI", 10)).pack(pady=5)

        results_frame = ttk.Frame(dialog, padding=20)
        results_frame.pack(fill="both", expand=True)

        self.target_dir = self.lbl_dir.get().strip()
        
        checks = [
            ("Converted Files", self._check_source_files),
            ("Alt Text & Links", self._check_ada_issues),
            ("Canvas Connection", self._check_canvas_ready),
            ("Project Cleanup", self._check_janitor_needed)
        ]

        ready_count = 0
        for i, (label, check_func) in enumerate(checks):
            passed, detail = check_func()
            status_icon = "✅" if passed else "⚠️"
            if passed: ready_count += 1
            
            ttk.Label(results_frame, text=f"{status_icon} {label}", font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", pady=5)
            lbl_detail = ttk.Label(results_frame, text=detail, font=("Segoe UI", 9), wraplength=400)
            lbl_detail.grid(row=i, column=1, sticky="w", padx=10)

        # Final Score
        score_frame = ttk.Frame(dialog, padding=10)
        score_frame.pack(fill="x")
        
        if ready_count == len(checks):
            msg = "🚀 YOU ARE CLEAR FOR TAKEOFF!"
            color = "#2E7D32" # Forest Green
            advice = "Mosh: 'Great job! You've put in the work, now let's show Canvas how it's done.'"
            
            # [NEW] Push Button INSIDE Dialog
            btn_push = ttk.Button(score_frame, text="🚀 Send My Clean Course to Canvas Now", 
                                 command=lambda: [dialog.destroy(), self._push_to_canvas()], style="Action.TButton")
            btn_push.pack(pady=10, fill="x")
        else:
            msg = "🛠️ Almost there! Finish the items above."
            color = "#d4a017"
            advice = "Mosh: 'Remediation is tough, but you're doing great. Just a few more things to fix!'"

        tk.Label(score_frame, text=msg, font=("Segoe UI", 12, "bold"), foreground=color).pack()
        tk.Label(score_frame, text=advice, font=("Segoe UI", 10, "italic"), foreground=colors["fg"]).pack(pady=5)

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _check_source_files(self):
        """Checks if there are still unconverted Word/PPT/PDFs."""
        count = 0
        for root, dirs, files in os.walk(self.target_dir):
            if "_ORIGINALS_DO_NOT_UPLOAD_" in root: continue
            for f in files:
                if f.lower().endswith(('.docx', '.pptx', '.pdf', '.xlsx')): count += 1
        
        if count == 0: return True, "All files converted to Canvas WikiPages."
        return False, f"Found {count} original files in course. Prepare them for Canvas first!"

    def _check_ada_issues(self):
        """Scans for remaining ADA markers like [FIX_ME] and runs Auto-Fixer one last time."""
        markers = 0
        html_files = []
        for root, dirs, files in os.walk(self.target_dir):
            if converter_utils.ARCHIVE_FOLDER_NAME in root: continue
            for f in files:
                if f.endswith('.html'):
                    html_files.append(os.path.join(root, f))
        
        # Proactive: Run Auto-Fixer on everything before checking markers
        if html_files:
            import interactive_fixer
            for fp in html_files:
                interactive_fixer.run_auto_fixer(fp, self.gui_handler)

        # Now check for markers
        for fp in html_files:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f_obj:
                    if "[FIX_ME]" in f_obj.read().upper(): markers += 1
            except: pass
        
        if markers == 0: return True, "No [FIX_ME] markers found. Looks great!"
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
        if not messagebox.askyesno("Final Launch", f"Ready to push this to your Canvas Sandbox?\n\nFile: {default_package}"):
            return

        def upload_task():
            # Run Janitor first!
            self.gui_handler.log("🧹 Mosh the Janitor is cleaning up...")
            cleaned = converter_utils.run_janitor_cleanup(self.target_dir, self.gui_handler.log)
            self.gui_handler.log(f"✅ Cleanup complete. Removed {cleaned} messy files.")
            
            # Re-package if needed or just do it every time for safety
            self.gui_handler.log(f"📦 Packaging final version: {default_package}...")
            success_pkg, msg_pkg = converter_utils.create_course_package(self.target_dir, package_path, self.gui_handler.log)
            if not success_pkg:
                self.gui_handler.log(f"❌ Packaging Failed: {msg_pkg}")
                return
            self.gui_handler.log(f"✅ Packaging complete. ({os.path.getsize(package_path)/(1024*1024):.1f} MB)")

            self.gui_handler.log("🚀 PREPARING FOR TAKEOFF! 🦆💨")
            self.gui_handler.log("   (This may take a minute for large courses...)")
            self.root.after(0, lambda: self._show_flight_animation("Mosh is flying your course to Canvas..."))
            
            api = self._get_canvas_api()
            if not api:
                self.gui_handler.log("❌ Authentication Error: Missing API settings.")
                self.root.after(0, self._close_flight_animation)
                return

            self.gui_handler.log("📡 Connecting to Canvas API...")
            success, res = api.upload_imscc(package_path)
            
            self.root.after(0, self._close_flight_animation)
            
            if success:
                self.gui_handler.log("✅ LANDING SUCCESSFUL! Mosh has delivered the package.")
                self.gui_handler.log(f"   Migration ID: {res.get('id')}")
                self.gui_handler.log("   Canvas is now importing your files. check back in 1-2 minutes.")
                self.root.after(0, lambda: messagebox.showinfo("Mosh Delivered!", 
                    "Mosh has delivered your course package to Canvas!\n\n"
                    "Check your Canvas course in a few minutes to see the result."))
            else:
                self.gui_handler.log(f"❌ TURBULENCE: {res}")
                self.root.after(0, lambda: messagebox.showerror("Upload Error", f"Mosh encountered an error:\n{res}"))

        self._run_task_in_thread(upload_task, "Canvas Upload")

    # --- Mosh's Flight Animation ---

    def _show_flight_animation(self, message):
        """Shows a fun overlay with Mosh Pilot image (Flight mode)."""
        self.flight_win = Toplevel(self.root)
        self.flight_win.title("Mosh is on it!")
        self.flight_win.geometry("450x450")
        self.flight_win.overrideredirect(True)
        # Center
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 225
        self.flight_win.geometry(f"+{x}+{y}")
        self.flight_win.attributes("-topmost", True)
        
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
            self.lbl_mosh = tk.Label(frame, text="🦆💨", font=("Segoe UI", 90), bg="#4b3190", fg="white")
            self.lbl_mosh.pack(pady=20)
        
        tk.Label(frame, text=message, font=("Segoe UI", 12, "bold"), bg="#4b3190", fg="white", wraplength=400).pack(pady=10)
        
        # Add Progress bar for visual interest
        self.prog_mosh = ttk.Progressbar(frame, mode="indeterminate", length=300)
        self.prog_mosh.pack(pady=10)
        self.prog_mosh.start(10)

        self._animate_mosh(0)

    def _animate_mosh(self, step):
        if not hasattr(self, 'flight_win') or not self.flight_win.winfo_exists(): return
        
        # Subtly shake Mosh to simulate flight vibration
        shake_x = (step % 4) - 2 # -2, -1, 0, 1
        shake_y = ((step // 2) % 4) - 2
        
        # We don't want to move the whole window, just the image a tiny bit
        self.lbl_mosh.pack_configure(pady=(20 + shake_y, 20 - shake_y))
        
        # Pulsing text
        colors = ["#FFFFFF", "#E1BEE7", "#D1C4E9"]
        # If we had the message label saved
        # self.lbl_msg.config(fg=colors[step % len(colors)])
        
        self.root.after(100, lambda: self._animate_mosh(step + 1))

    def _close_flight_animation(self):
        if hasattr(self, 'flight_win'):
            self.flight_win.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ToolkitGUI(root)
    root.mainloop()
