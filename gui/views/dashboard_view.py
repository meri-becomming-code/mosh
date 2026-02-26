"""
Dashboard View - Main landing page for MOSH Toolkit.
Shows tool selection cards and quick access.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from gui.base_view import BaseView


class ToolTip:
    """Simple tooltip widget."""
    
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
    
    def enter(self, event: Any = None) -> None:
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
        )
        label.pack(ipadx=1)
    
    def leave(self, event: Any = None) -> None:
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class DashboardView(BaseView):
    """Main dashboard view with tool selection."""
    
    def build(self) -> None:
        """Build the dashboard UI."""
        # Clear parent frame
        for widget in self.parent_frame.winfo_children():
            widget.destroy()
        
        # Create main frame
        self.main_frame = tk.Frame(self.parent_frame, bg=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True)
        
        # Header
        self._build_header()
        
        # Tool selection cards
        self._build_tool_cards()
        
        # Info section
        self._build_info_section()
    
    def refresh(self) -> None:
        """Refresh the dashboard (no-op for dashboard)."""
        pass
    
    def _build_header(self) -> None:
        """Build the dashboard header."""
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", padx=20, pady=(20, 30))
        
        # Title
        tk.Label(
            header,
            text="MOSH's Toolkit: Making Online Spaces Helpful",
            font=("Segoe UI", 24, "bold"),
            fg=self.colors["header"],
            bg=self.colors["bg"],
        ).pack(anchor="w")
        
        # Subtitle
        tk.Label(
            header,
            text="Automate accessibility remediation for Canvas in minutes",
            font=("Segoe UI", 12),
            fg=self.colors["text_muted"],
            bg=self.colors["bg"],
        ).pack(anchor="w", pady=(5, 0))
    
    def _build_tool_cards(self) -> None:
        """Build the tool selection cards."""
        cards_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        cards_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Create grid for cards
        card_frame = tk.Frame(cards_frame, bg=self.colors["bg"])
        card_frame.pack(fill="both", expand=True)
        card_frame.columnconfigure(0, weight=1)
        card_frame.columnconfigure(1, weight=1)
        card_frame.columnconfigure(2, weight=1)
        
        # Tool 1: Canvas Remediation
        self._create_tool_card(
            card_frame,
            row=0,
            col=0,
            emoji="🎨",
            title="Canvas Remediation",
            description="Bulk fix entire course projects.",
            color=self.colors["primary"],
            callback=lambda: self._switch_view("course"),
        )
        
        # Tool 2: File Conversion
        self._create_tool_card(
            card_frame,
            row=0,
            col=1,
            emoji="📄",
            title="File Conversion",
            description="Standard PPT/Word to HTML.",
            color=self.colors["secondary"],
            callback=lambda: self._switch_view("files"),
        )
        
        # Tool 3: Math Conversion
        self._create_tool_card(
            card_frame,
            row=0,
            col=2,
            emoji="📐",
            title="Math Conversion",
            description="Handwritten to Canvas LaTeX.",
            color=self.colors["accent"],
            callback=lambda: self._switch_view("math"),
        )
    
    def _create_tool_card(
        self,
        parent: tk.Frame,
        row: int,
        col: int,
        emoji: str,
        title: str,
        description: str,
        color: str,
        callback: Callable[[], None],
    ) -> None:
        """Create a single tool card."""
        card = tk.Frame(
            parent,
            bg="white",
            padx=20,
            pady=25,
            highlightbackground=color,
            highlightthickness=1,
        )
        card.grid(row=row, column=col, padx=10, sticky="nsew", pady=(0, 20))
        
        # Emoji
        tk.Label(
            card,
            text=emoji,
            font=("Segoe UI", 36),
            bg="white",
        ).pack()
        
        # Title
        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 13, "bold"),
            bg="white",
            fg=color,
        ).pack(pady=5)
        
        # Description
        tk.Label(
            card,
            text=description,
            font=("Segoe UI", 9),
            bg="white",
            fg="gray",
        ).pack()
        
        # Button
        btn = ttk.Button(
            card,
            text="OPEN TOOL",
            command=callback,
            style="Action.TButton",
        )
        btn.pack(pady=10)
        
        ToolTip(btn, f"Open the {title} tool")
    
    def _build_info_section(self) -> None:
        """Build informational section at bottom."""
        info = tk.Frame(self.main_frame, bg=self.colors["bg"])
        info.pack(fill="x", padx=20, pady=(20, 20))
        
        # Quick info
        tk.Label(
            info,
            text="💡 TIP: Start with Setup (top menu) to configure your Canvas and API keys.",
            font=("Segoe UI", 10),
            fg=self.colors["text_muted"],
            bg=self.colors["bg"],
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Label(
            info,
            text="Need help? Check the guides in the Help menu →",
            font=("Segoe UI", 10),
            fg=self.colors["text_muted"],
            bg=self.colors["bg"],
        ).pack(anchor="w")
