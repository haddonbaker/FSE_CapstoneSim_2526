# created by Haddon Baker 3/9 with assistance from Gemini Code Assist
# created by Haddon Baker 3/9 with assistance from Gemini Code Assist
import customtkinter as ctk

class SignalHistory(ctk.CTkFrame):
    """Displays a history of values sent to analog outputs with filtering."""
    
    def __init__(self, parent, history_stack):
        super().__init__(parent)
        self.history_stack = history_stack
        self.filter_vars = {}
        self.checkboxes = {}

        # --- Layout ---
        self.grid_columnconfigure(0, weight=0, minsize=200)  # Filter panel
        self.grid_columnconfigure(1, weight=1)              # Main content
        self.grid_rowconfigure(0, weight=1)

        # --- Filter Frame (Left) ---
        self.filter_frame = ctk.CTkScrollableFrame(self, corner_radius=10, label_text="Filters")
        self.filter_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        # --- Main Content Frame (Right) ---
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")
        
        # Top bar
        self.top_bar = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=10, pady=10)
        
        self.title = ctk.CTkLabel(self.top_bar, text="Signal History", font=ctk.CTkFont(size=22, weight="bold"))
        self.title.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(self.top_bar, text="Refresh", width=80, command=self._refresh_all)
        self.refresh_btn.pack(side="right", padx=5)
        
        self.clear_btn = ctk.CTkButton(self.top_bar, text="Clear All", width=80, fg_color="darkred", hover_color="red", command=self._clear_all)
        self.clear_btn.pack(side="right", padx=5)
        
        # Scrollable list for history entries
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_content_frame, corner_radius=10)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self._setup_filters()
        self._rebuild_list()

    def _setup_filters(self):
        """Create or update the filter checkboxes based on available signals."""
        # Clear old filters
        for widget in self.filter_frame.winfo_children():
            widget.destroy()
        self.filter_vars.clear()
        self.checkboxes.clear()

        # "All" checkbox
        self.all_var = ctk.IntVar(value=1)
        all_cb = ctk.CTkCheckBox(self.filter_frame, text="All Signals", variable=self.all_var, command=self._on_all_checked, font=ctk.CTkFont(weight="bold"))
        all_cb.pack(anchor="w", padx=20, pady=(10, 5))
        self.checkboxes["all"] = all_cb

        # Separator
        ctk.CTkFrame(self.filter_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=5)

        # Individual signal checkboxes
        signal_names = sorted(list(set(entry["signal"] for entry in self.history_stack)))
        for name in signal_names:
            var = ctk.IntVar(value=0)
            cb = ctk.CTkCheckBox(self.filter_frame, text=name, variable=var, command=self._on_filter_checked)
            cb.pack(anchor="w", padx=20, pady=5)
            self.filter_vars[name] = var
            self.checkboxes[name] = cb

    def _on_all_checked(self):
        if self.all_var.get() == 1:
            # If "All" is checked, uncheck all others
            for var in self.filter_vars.values():
                var.set(0)
        else:
            # If "All" is manually unchecked, but nothing else is checked, re-check it.
            # This prevents a state with no selection.
            if not any(var.get() == 1 for var in self.filter_vars.values()):
                self.all_var.set(1)

        self._rebuild_list()

    def _on_filter_checked(self):
        if any(var.get() == 1 for var in self.filter_vars.values()):
            # If any individual filter is checked, uncheck "All"
            self.all_var.set(0)
        else:
            # If all individual filters are unchecked, check "All"
            self.all_var.set(1)
        
        self._rebuild_list()
        
    def _clear_all(self):
        self.history_stack.clear()
        self._setup_filters()  # Re-setup filters as there are no signals now
        self._rebuild_list()

    def _refresh_all(self):
        """Rebuilds filters and list. Useful if history was updated in the background."""
        self._setup_filters()
        self._rebuild_list()
        
    def _rebuild_list(self):
        """Clears and repopulates the history list based on current filter selections."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Determine active filters
        show_all = self.all_var.get() == 1
        active_filters = {name for name, var in self.filter_vars.items() if var.get() == 1}

        # Filter history
        display_history = []
        if self.history_stack:
            for entry in reversed(list(self.history_stack)):
                if show_all or entry["signal"] in active_filters:
                    display_history.append(entry)
            
        if not display_history:
            ctk.CTkLabel(self.scrollable_frame, text="No history recorded or matches filters", text_color="gray").pack(pady=20)
            return
            
        # Display filtered entries
        for entry in display_history:
            self._create_row(entry)
            
    def _create_row(self, entry):
        row = ctk.CTkFrame(self.scrollable_frame, corner_radius=6, fg_color="#2a2a2a")
        row.pack(fill="x", padx=5, pady=5)
        
        # Timestamp and Signal Name
        header = ctk.CTkFrame(row, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(5,0))
        
        ctk.CTkLabel(header, text=entry["timestamp"], font=("Consolas", 10), text_color="#B8A569").pack(side="left")
        ctk.CTkLabel(header, text=entry["signal"], font=("Consolas", 12, "bold")).pack(side="left", padx=10)
        
        # Action and Details
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=(0,5))
        
        action_color = "lightblue" if entry["action"] == "Single" else "orange"
        ctk.CTkLabel(content, text=entry["action"], text_color=action_color, font=("Consolas", 12)).pack(side="left")
        ctk.CTkLabel(content, text=entry["details"], font=("Consolas", 12)).pack(side="left", padx=10)