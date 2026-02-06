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
        self.target_dir = os.getcwd()
        self.config = self._load_config()
        self.is_running = False
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
        return {"show_instructions": True, "api_key": ""}

    def _save_config(self, key, start_show, theme="light"):
        self.config["api_key"] = key
        self.config["show_instructions"] = start_show
        self.config["theme"] = theme
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
- Use the "Conversion Wizard" to turn Word, PPT, or PDF files into Canvas-ready HTML.
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
        lbl_logo = ttk.Label(sidebar, text="MOSH'S\nTOOLKIT", style="Sidebar.TLabel", font=("Segoe UI", 16, "bold"), justify="center")
        lbl_logo.pack(pady=20, padx=10)
        
        ttk.Label(sidebar, text="v2026.1", style="Sidebar.TLabel", font=("Segoe UI", 8)).pack(pady=(0, 20))
        
        # Stop Button (Persistent)
        self.btn_stop = ttk.Button(sidebar, text="🛑 STOP PROCESSING", command=self._request_stop, style="TButton")
        self.btn_stop.pack(pady=5, padx=10, fill="x")
        self.btn_stop.config(state='disabled')

        # [NEW] Viral/Mission Button
        self.btn_share = ttk.Button(sidebar, text="📣 SPREAD THE WORD", command=self._show_share_dialog, style="Action.TButton")
        self.btn_share.pack(pady=20, padx=10, fill="x")

        # 2. Main Content Area
        content = ttk.Frame(self.root, padding="20 20 20 20")
        content.pack(side="right", fill="both", expand=True)

        # -- Target Project Section --
        ttk.Label(content, text="1. Select Project", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_dir = ttk.Frame(content)
        frame_dir.pack(fill="x", pady=(5, 15))
        
        # Row 1: Import Button (New)
        btn_import = ttk.Button(
            frame_dir, 
            text="📦 Import Course Package (.imscc / .zip)", 
            command=self._import_package,
            style="Action.TButton"
        )
        btn_import.pack(side="top", fill="x", pady=(0, 5))
        
        # Row 1b: Export Button (New)
        btn_export = ttk.Button(
            frame_dir, 
            text="📤 Repackage Course (.imscc)", 
            command=self._export_package,
            style="Action.TButton"
        )
        btn_export.pack(side="top", fill="x", pady=(0, 5))
        
        # Row 2: Folder Browser
        frame_browse = ttk.Frame(frame_dir)
        frame_browse.pack(fill="x")
        
        mode = self.config.get("theme", "light")
        colors = THEMES[mode]
        
        self.lbl_dir = tk.Entry(frame_browse, bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])
        self.lbl_dir.insert(0, self.target_dir)
        self.lbl_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ttk.Button(frame_browse, text="Browse Folder...", command=self._browse_folder).pack(side="right")


        # -- Remediation Actions (Grid) --
        ttk.Label(content, text="2. Fix & Review", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_actions = ttk.Frame(content)
        frame_actions.pack(fill="x", pady=(10, 20))
        
        # Friendly Button Names
        self.btn_auto = ttk.Button(frame_actions, text="Auto-Fix Issues\n(Headings, Tables)", command=self._run_auto_fixer, style="Action.TButton")
        self.btn_auto.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_inter = ttk.Button(frame_actions, text="Guided Review\n(Alt Tags, Links, File Names)", command=self._run_interactive, style="Action.TButton")
        self.btn_inter.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Row 2 (Audit)
        self.btn_audit = ttk.Button(frame_actions, text="Quick Report\n(Audit JSON)", command=self._run_audit, style="Action.TButton")
        self.btn_audit.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        frame_actions.columnconfigure(0, weight=1)
        frame_actions.columnconfigure(1, weight=1)
        frame_actions.columnconfigure(2, weight=1)


        # -- Converters --
        ttk.Label(content, text="3. Convert Files", style="SubHeader.TLabel").pack(anchor="w")
        
        frame_convert = ttk.Frame(content)
        frame_convert.pack(fill="x", pady=(10, 20))
        
        self.btn_wizard = ttk.Button(frame_convert, text="🪄 Conversion Wizard (Word/PPT -> HTML)", command=self._show_conversion_wizard, style="Action.TButton")
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

        # Batch Everything (Risky)
        self.btn_batch = ttk.Button(frame_convert, text="🎲 Roll the Dice: Convert Everything (Risky) 🎲", 
                                    command=self._run_batch_conversion, style="Action.TButton")
        self.btn_batch.pack(fill="x", pady=(10, 0))


        # -- Logs --
        ttk.Label(content, text="Activity Log", style="SubHeader.TLabel").pack(anchor="w")
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
        messagebox.showinfo("Import Complete", f"Package extracted successfully!\n\nTarget Project updated to:\n{extract_to}")

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

            # [STRICT FIX] Always remove visual markers at the end
            self.gui_handler.log("\n--- 🧹 Finalizing: Cleaning Visual Markers ---")
            import run_fixer
            strip_results = run_fixer.batch_strip_markers(self.target_dir)
            total_stripped = sum(strip_results.values())
            self.gui_handler.log(f"   Done! Stripped {total_stripped} temporary [ADA FIX] markers.")

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

    def _run_cleanup_markers(self):
        """Removes all [ADA FIX] visual labels from HTML files."""
        if not messagebox.askyesno("Confirm Cleanup", 
            "This will permanently REMOVE all red visual markers ([ADA FIX]) from your HTML files.\n\n"
            "Use this only when you are satisfied with the remediation and ready to upload to Canvas.\n\n"
            "Proceed?"):
            return

        def task():
            self.gui_handler.log(f"--- 🧹 Cleaning Visual Markers: {os.path.basename(self.target_dir)} ---")
            import run_fixer
            results = run_fixer.batch_strip_markers(self.target_dir)
            
            total = sum(results.values())
            self.gui_handler.log(f"   Done! Stripped {total} markers from {len(results)} files.")
            for file, count in results.items():
                self.gui_handler.log(f"    - {file}: {count}")
            
            self.root.after(0, lambda: messagebox.showinfo("Cleanup Complete", f"Successfully removed {total} visual markers from {len(results)} files."))

        self._run_task_in_thread(task, "Marker Cleanup")

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
                self.gui_handler.log(f"[{i+1}/{len(files)}] Processing: {fname}...")
                
                # 1. Convert
                output_path = None
                err = None
                
                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(fpath)
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                     output_path, err = converter_utils.convert_ppt_to_html(fpath)
                elif ext == "pdf":
                     output_path, err = converter_utils.convert_pdf_to_html(fpath)
                
                if err or not output_path:
                    self.gui_handler.log(f"   [ERROR] Failed to convert: {err}")
                    continue
                
                self.gui_handler.log(f"   Converted to: {os.path.basename(output_path)}")
                
                # 2. Preview (Open both)
                try:
                    os.startfile(fpath) # Open Original
                    os.startfile(output_path) # Open New HTML
                except Exception as e:
                    self.gui_handler.log(f"   [WARNING] Could not auto-open files: {e}")
                
                # 3. Prompt user (Keep/Discard?)
                msg = (f"Reviewing: {fname}\n\n"
                       f"I have opened both the original and the new HTML file.\n"
                       f"Do you want to KEEP this new HTML version?")
                
                keep = self.gui_handler.confirm(msg)
                
                if not keep:
                    # Delete and continue
                    try:
                        os.remove(output_path)
                        self.gui_handler.log("   Discarded.")
                    except:
                        pass
                    continue
                
                kept_files.append(output_path)

                # 4. Prompt Update Links
                msg_link = (f"Excellent. The original file is untouched.\n\n"
                            f"Would you like to SCAN ALL OTHER FILES in this folder\n"
                            f"and update any links to point to this new HTML file instead?")
                
                if self.gui_handler.confirm(msg_link):
                    count = converter_utils.update_links_in_directory(self.target_dir, fpath, output_path)
                    self.gui_handler.log(f"   Updated links in {count} files.")

                # 5. Prompt Archiving (NEW)
                msg_archive = (f"To maintain Canvas compliance, original files ({ext.upper()}) should not be uploaded to your course.\n\n"
                               f"Would you like to move '{fname}' to the archive folder?\n"
                               f"(It will be safe in '_ORIGINALS_DO_NOT_UPLOAD_', but won't be exported to Canvas.)")
                
                if self.gui_handler.confirm(msg_archive):
                    new_archive_path = converter_utils.archive_source_file(fpath)
                    if new_archive_path:
                        self.gui_handler.log(f"   Original moved to archive: {converter_utils.ARCHIVE_FOLDER_NAME}")
                
                self.gui_handler.log("   Done.")
            
            self.gui_handler.log("--- Wizard Complete ---")
            
            # --- 5. NEW: Post-Conversion Audit/Fix ---
            if kept_files:
                msg_fix = (f"Conversion finished for {len(kept_files)} files.\n\n"
                           f"Would you like to run the GUIDED REVIEW (Accessibility Check) on these new files now?\n"
                           f"(Highly Recommended for Alt Text & Links)")
                           
                if self.gui_handler.confirm(msg_fix):
                     self.gui_handler.log("\n--- Starting Post-Conversion Review ---")
                     for fp in kept_files:
                         interactive_fixer.scan_and_fix_file(fp, self.gui_handler, self.target_dir)
                     
                     self.gui_handler.log("--- Review Complete ---")
            
            messagebox.showinfo("Done", "All selected files have been processed!")

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

        
        self.gui_handler.log(f"Converting {os.path.basename(file_path)}...")
        
        def task():
            output_path, err = None, None
            
            if ext == "docx":
                output_path, err = converter_utils.convert_docx_to_html(file_path)
            elif ext == "xlsx":
                output_path, err = converter_utils.convert_excel_to_html(file_path)
            elif ext == "pptx":
                output_path, err = converter_utils.convert_ppt_to_html(file_path)
            elif ext == "pdf":
                output_path, err = converter_utils.convert_pdf_to_html(file_path)
            
            if err:
                 self.gui_handler.log(f"[ERROR] Conversion failed: {err}")
                 return


            self.gui_handler.log(f"[SUCCESS] Created: {os.path.basename(output_path)}")
            
            # 2. Preview (Open both)
            try:
                os.startfile(file_path) # Open Original
                os.startfile(output_path) # Open New HTML
            except Exception as e:
                self.gui_handler.log(f"   [WARNING] Could not auto-open files: {e}")
            
            # 3. Prompt user (Keep/Discard?)
            msg = (f"Reviewing: {os.path.basename(file_path)}\n\n"
                   f"I have opened both the original and the new HTML file.\n"
                   f"Do you want to KEEP this new HTML version?")
            
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
                        f"and update any links to point to this new HTML file instead?")
            
            if self.gui_handler.confirm(msg_link):
                count = converter_utils.update_links_in_directory(self.target_dir, file_path, output_path)
                self.gui_handler.log(f"   Updated links in {count} files.")

                # [NEW] Update Manifest
                rel_old = os.path.relpath(file_path, self.target_dir)
                rel_new = os.path.relpath(output_path, self.target_dir)
                m_success, m_msg = converter_utils.update_manifest_resource(self.target_dir, rel_old, rel_new)
                if m_success:
                    self.gui_handler.log(f"   [MANIFEST] {m_msg}")
            
            # 6. Archive Original (NEW)
            msg_archive = (f"To maintain Canvas compliance, original files should not be uploaded to your course.\n\n"
                           f"Move '{os.path.basename(file_path)}' to the safety archive folder?\n"
                           f"(It will be safe on your computer but hidden from Canvas.)")
            if self.gui_handler.confirm(msg_archive):
                converter_utils.archive_source_file(file_path)
                self.gui_handler.log(f"Original moved to {converter_utils.ARCHIVE_FOLDER_NAME}")
            
            
        self._run_task_in_thread(task, f"Convert {ext.upper()}")

    def _run_batch_conversion(self):
        """Processes ALL convertible files in one go without per-file verification."""
        # 1. Scary Warning
        msg = ("🎲 ROLL THE DICE: BATCH CONVERSION 🎲\n\n"
               "WARNING: This will convert EVERY Word, PPT, Excel, and PDF file in your project to HTML automatically.\n\n"
               "- It is NOT perfect. Layouts may break.\n"
               "- Original files will be moved to the archive folder for safety.\n"
               "- Links will be updated throughout your project.\n\n"
               "YOU are responsible for reviewing the resulting HTML pages. "
               "Are you sure you want to take this gamble?")
        
        if not messagebox.askyesno("🎲 Feeling Lucky?", msg):
            return

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
                self.gui_handler.log(f"[{i+1}/{len(found_files)}] Converting: {fname}")
                
                output_path = None
                err = None
                
                if ext == "docx":
                    output_path, err = converter_utils.convert_docx_to_html(fpath)
                elif ext == "xlsx":
                    output_path, err = converter_utils.convert_excel_to_html(fpath)
                elif ext == "pptx":
                    output_path, err = converter_utils.convert_ppt_to_html(fpath)
                elif ext == "pdf":
                    output_path, err = converter_utils.convert_pdf_to_html(fpath)
                
                if output_path:
                    success_count += 1
                    
                    # Run Auto-Fixer on the document immediately
                    self.gui_handler.log(f"   [FIXING] Running Auto-Fixer on new HTML...")
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
            
            # [NEW] Integrated Interactive Checker
            msg_review = ("Batch conversion is finished!\n\n"
                         "Would you like to start the Guided Review (Interactive Checker) now?\n"
                         "This will help you quickly fix image descriptions and check links.")
            
            # Use after() to show dialog on main thread
            def ask_review():
                if messagebox.askyesno("Step 2: Guided Review", msg_review):
                    self.btn_inter.invoke() # Trigger the existing Guided Review logic
            
            self.root.after(0, ask_review)

            # [STRICT FIX] Always remove visual markers at the end
            self.gui_handler.log("\n--- 🧹 Finalizing: Cleaning Visual Markers ---")
            import run_fixer
            strip_results = run_fixer.batch_strip_markers(self.target_dir)
            total_stripped = sum(strip_results.values())
            self.gui_handler.log(f"   Done! Stripped {total_stripped} temporary [ADA FIX] markers.")
            
            self.gui_handler.log("\n🛡️ Remember: Check the files in Canvas before publishing!")
            messagebox.showinfo("Gamble Complete", f"Processed {len(found_files)} files.\nCheck the logs for details.")

        self._run_task_in_thread(task, "Batch Gamble")

if __name__ == "__main__":
    root = tk.Tk()
    app = ToolkitGUI(root)
    root.mainloop()
