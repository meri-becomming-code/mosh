import tkinter as tk
from typing import Any

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
        # Handle cases where event is None or doesn't have x_root/y_root
        try:
            x = event.x_root + 10
            y = event.y_root + 10
        except AttributeError:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            
        tw.wm_geometry(f"+{x}+{y}")
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
