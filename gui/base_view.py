"""
Base class for MOSH GUI views.
Provides common functionality and theming.
"""

import tkinter as tk
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any

# Theme colors
THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "header": "#1a1a1a",
        "subheader": "#444444",
        "primary": "#4B3190",
        "secondary": "#0D9488",
        "accent": "#ea580c",
        "border": "#cccccc",
        "text": "#1a1a1a",
        "text_muted": "#666666",
        "error": "#dc2626",
        "success": "#16a34a",
        "warning": "#ea580c",
    },
    "dark": {
        "bg": "#1e1e1e",
        "header": "#ffffff",
        "subheader": "#e0e0e0",
        "primary": "#a78bfa",
        "secondary": "#14b8a6",
        "accent": "#f97316",
        "border": "#333333",
        "text": "#e0e0e0",
        "text_muted": "#999999",
        "error": "#ef4444",
        "success": "#22c55e",
        "warning": "#f97316",
    },
}


class BaseView(ABC):
    """Abstract base class for all MOSH GUI views."""
    
    def __init__(
        self,
        parent_frame: tk.Frame,
        config: Dict[str, Any],
        on_view_change: Optional[Callable[[str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the view.
        
        Args:
            parent_frame: The parent Tkinter frame to build in
            config: Application configuration dictionary
            on_view_change: Callback to switch to another view
            on_log: Callback for logging messages
        """
        self.parent_frame = parent_frame
        self.config = config
        self.on_view_change = on_view_change or (lambda x: None)
        self.on_log = on_log or (lambda x: None)
        self.theme_mode = config.get("theme", "light")
        self.colors = THEMES[self.theme_mode]
        self.main_frame = None
    
    @abstractmethod
    def build(self) -> None:
        """Build the view UI. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def refresh(self) -> None:
        """Refresh the view when returning to it. Optional implementation."""
        pass
    
    def _switch_view(self, view_name: str) -> None:
        """Switch to another view."""
        self.on_view_change(view_name)
    
    def _log(self, message: str) -> None:
        """Log a message."""
        self.on_log(message)
    
    def _create_header(self, title: str, emoji: str = "") -> tk.Frame:
        """
        Create a standard header for this view.
        
        Args:
            title: The header title text
            emoji: Optional emoji/icon for the header
        
        Returns:
            The header frame
        """
        header = tk.Frame(self.main_frame, bg=self.colors["bg"])
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        title_text = f"{emoji} {title}" if emoji else title
        tk.Label(
            header,
            text=title_text,
            font=("Segoe UI", 18, "bold"),
            fg=self.colors["header"],
            bg=self.colors["bg"],
        ).pack(anchor="w")
        
        return header
    
    def _create_section(self, parent: tk.Widget, title: str = "") -> tk.Frame:
        """
        Create a standard section/card.
        
        Args:
            parent: Parent widget
            title: Optional section title
        
        Returns:
            The section frame
        """
        section = tk.Frame(parent, bg=self.colors["bg"])
        section.pack(fill="x", padx=20, pady=(10, 0))
        
        if title:
            tk.Label(
                section,
                text=title,
                font=("Segoe UI", 12, "bold"),
                fg=self.colors["subheader"],
                bg=self.colors["bg"],
            ).pack(anchor="w", pady=(10, 5))
        
        return section
    
    def destroy(self) -> None:
        """Clean up the view."""
        if self.main_frame and self.main_frame.winfo_exists():
            self.main_frame.destroy()
