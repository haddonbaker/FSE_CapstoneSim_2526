# error_log.py
# Created by Haddon Baker 1/20/26 with assistance from ChatGPT

import customtkinter as ctk
from datetime import datetime


class ErrorLog(ctk.CTkFrame):
    """Displays error log with timestamps and ability to clear individual errors."""
    
    def __init__(self, parent, error_stack, on_update=None):
        super().__init__(parent)

        self.error_stack = error_stack  # Reference to the deque
        self.on_update = on_update
        self.error_widgets = {}  # Track error widgets by index

        # Create top bar with title and refresh button
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=10, pady=10)

        self.title = ctk.CTkLabel(
            self.top_bar,
            text="Error Log",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            self.top_bar,
            text="Refresh",
            width=80,
            height=30,
            command=self._rebuild_error_list
        )
        self.refresh_btn.pack(side="right", padx=5)

        self.clear_all_btn = ctk.CTkButton(
            self.top_bar,
            text="Clear All",
            width=80,
            height=30,
            fg_color="darkred",
            hover_color="red",
            command=self._clear_all_errors
        )
        self.clear_all_btn.pack(side="right", padx=5)

        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.empty_label = None

        # Initial build
        self._rebuild_error_list()

    def _clear_all_errors(self):
        """Clear all errors from the stack."""
        self.error_stack.clear()
        self._rebuild_error_list()
        if self.on_update:
            self.on_update()

    def _rebuild_error_list(self):
        """Rebuild the entire error list."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.error_widgets.clear()
        self.empty_label = None

        if not self.error_stack:
            self.empty_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No errors",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            self.empty_label.pack(pady=20)
        else:
            # Display errors in reverse order (newest first)
            for idx, error_entry in enumerate(reversed(list(self.error_stack))):
                self._create_error_row(idx, error_entry)

    def _create_error_row(self, idx: int, error_entry: dict):
        """Create a row for a single error with timestamp and clear button."""
        row_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=8, fg_color="#2a2a2a")
        row_frame.pack(fill="x", padx=10, pady=8)

        # Timestamp
        timestamp_text = error_entry.get("timestamp", "Unknown")
        timestamp_label = ctk.CTkLabel(
            row_frame,
            text=timestamp_text,
            font=ctk.CTkFont(size=10),
            text_color="#B8A569"
        )
        timestamp_label.pack(anchor="w", padx=10, pady=(8, 2))

        # Error message
        message = error_entry.get("message", "")
        message_label = ctk.CTkLabel(
            row_frame,
            text=message,
            font=ctk.CTkFont(size=12),
            text_color="red",
            wraplength=500,
            justify="left"
        )
        message_label.pack(anchor="w", padx=10, pady=(0, 8))

        # Clear button
        clear_btn = ctk.CTkButton(
            row_frame,
            text="Clear",
            width=60,
            height=24,
            fg_color="darkred",
            hover_color="red",
            font=ctk.CTkFont(size=10),
            command=lambda msg=message: self._on_clear(msg)
        )
        clear_btn.pack(anchor="e", padx=10, pady=5)

        self.error_widgets[idx] = row_frame

    def _on_clear(self, message: str):
        """Remove an error from the stack by message."""
        # Find and remove the error with this message
        for i, error_entry in enumerate(list(self.error_stack)):
            if error_entry.get("message") == message:
                self.error_stack.remove(error_entry)
                break
        
        # Rebuild the list
        self._rebuild_error_list()
        if self.on_update:
            self.on_update()