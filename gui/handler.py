import queue
import threading
import os
import interactive_fixer

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

    def is_stopped(self):
        return self.stop_requested

    def log(self, message):
        """Send log message to the queue."""
        self.log_queue.put(message)

    def prompt(self, message):
        """Ask user for input (Blocking from worker thread perspective)."""
        if self.is_stopped():
            return ""
        self.input_request_queue.put(("prompt", message, None, None, None))
        return self.input_response_queue.get()

    def confirm(self, message):
        """Ask user for Yes/No (Blocking)."""
        if self.is_stopped():
            return False
        self.input_request_queue.put(("confirm", message, None, None, None))
        return self.input_response_queue.get()

    def prompt_image(self, message, image_path, context=None, suggestion=None):
        """Ask user for input while showing an image and context."""
        if self.is_stopped():
            return ""
        
        # [NEW] Power User Bypass - Trust AI auto-accept
        # Note: This is also handled in interactive_fixer.py now, but keeping here for robustness
        if getattr(self, "trust_ai_alt", False) and suggestion:
            preview = suggestion if len(suggestion) <= 80 else suggestion[:77] + "..."
            self.log(f"   ✅ [Auto-Alt] {os.path.basename(image_path)}: \"{preview}\"")
            return suggestion

        self.input_request_queue.put(
            ("image", message, image_path, context, suggestion)
        )
        return self.input_response_queue.get()

    def prompt_link(self, message, help_url, context=None):
        """Ask user for input while showing a link and context."""
        if self.is_stopped():
            return ""
        self.input_request_queue.put(("link", message, help_url, context, None))
        return self.input_response_queue.get()
