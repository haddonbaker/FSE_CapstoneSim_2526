# ui_app.py
# created by Haddon Baker 10/7/25 with assistance from ChatGPT. Refactored from original simulator_gui.py for modularity
"""
ui_app.py: main GUI app wrapped in a SimulatorApp class.
This class constructs the CTk UI, wires events to the SocketController and ChannelManager,
and runs the mainloop.
"""
import os
import time
import logging
import traceback
from collections import deque
from pathlib import Path
from typing import Dict
from datetime import datetime
from error_log import ErrorLog

import tkinter as tk
import customtkinter as ctk
from tkdial import Meter
from signal_masterkey import SignalMasterKey
from config_manager import ConfigManager
from channel_manager import ChannelManager
from socket_controller import SocketController
from PacketBuilder import dataEntry, errorEntry  # referenced in queue processing
from PIL import Image

debug_statements = 1

class SimulatorApp:
    def __init__(self, config_path: str | Path, channel_mgr: ChannelManager, socket_ctrl: SocketController):
        self.current_dir = Path(__file__).resolve().parent
        self.config = ConfigManager(config_path)  # also accessible, but kept for compatibility
        self.channel_mgr = channel_mgr
        self.socket_ctrl = socket_ctrl

         # Load icon
        icon_path = self.current_dir / "icons" / "info.png"
        if icon_path.exists():
            self.info_icon = ctk.CTkImage(
                light_image=Image.open(str(icon_path)),
                dark_image=Image.open(str(icon_path)),
                size=(20, 20)
            )
        else:
            self.info_icon = None

        # Load pencil icon for renaming
        pencil_icon_path = self.current_dir / "icons" / "pencil.png"
        if pencil_icon_path.exists():
            self.pencil_icon = ctk.CTkImage(
                light_image=Image.open(str(pencil_icon_path)),
                dark_image=Image.open(str(pencil_icon_path)),
                size=(16, 16)
            )
        else:
            self.pencil_icon = None

        # runtime settings shortcut
        rs = self.config.runtime_settings
        self.error_stack_max_len = rs["error_stack_max_len"]
        self.enable_verbose_logging = rs["enable_verbose_logging"]
        self.ai_LPF_boxcar_length = rs["ai_LPF_boxcar_length"]
        self.poll_buffer_period_ms = rs["poll_buffer_period_ms"]

        # UI state
        self.error_stack = deque(maxlen=self.error_stack_max_len)  # Now stores dicts: {"message": str, "timestamp": str}
        self.ai_meter_objects: Dict[str, Meter] = {}
        self.ao_label_objects: Dict[str, ctk.CTkLabel] = {}
        self.di_label_objects: Dict[str, ctk.CTkLabel] = {}
        self.do_switches: Dict[str, ctk.CTkSwitch] = {}
        self.display_name_map = {}     # original_name → UI_display_name


        # queue for responses from socket controller
        self.socketRespQueue = self.socket_ctrl.response_queue

        # build UI
        self._setup_logging()
        self._build_root_window()
        self._build_frames()
        self._populate_analog_inputs()
        self._populate_analog_outputs()
        self._populate_digital_outputs()
        self._populate_digital_inputs()

        # initialize connection status and error pane
        self.show_error("")
        self.show_connection_status(online=None)

        # start queue processing
        self.root.after(0, self.process_queue)

        # set SSM loopDelay small to improve responsiveness
        try:
            self.socket_ctrl.loop_delay = 0.1
        except Exception:
            pass

    def _setup_logging(self):
        logs_dir = Path("./logs")
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / f"instance_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
        logging.basicConfig(filename=str(log_file), encoding='utf-8', level="CRITICAL")
        self.root_exception_handler_installed = False

    def exception_handler(self, exc_type, exc_value, exc_tb):
        for line in traceback.TracebackException(exc_type, exc_value, exc_tb).format(chain=True):
            logging.exception(line)
            print(line)
        logging.exception(exc_value)
        print(exc_value)

    def _build_root_window(self):
        self.root = ctk.CTk()
        icon_path = self.current_dir / "app_icon.ico"
        if icon_path.exists():
            try:
                self.root.wm_iconbitmap(str(icon_path))
            except Exception:
                pass
        self.root.title("GCC Compressor Simulator v2.0")
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
        self.root.grid_rowconfigure(0, weight=0)  # top bar - no weight
        self.root.grid_rowconfigure(1, weight=1)  # main content - expandable
        self.root.grid_columnconfigure(0, weight=1)

        # exception handler integration for Tk
        self.root.report_callback_exception = self.exception_handler

        # proper shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

                # create top bar with help button
        self.top_bar = ctk.CTkFrame(self.root, height=40, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.help_btn = ctk.CTkButton(
            self.top_bar,
            image=self.info_icon if self.info_icon else None,
            text="ⓘ Signal Masterkey" if not self.info_icon else "Signal Masterkey",
            font=("Consolas", 12),
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=self.open_signal_config_popup
        )
        self.help_btn.pack(side="left", padx=5)
        
        # Add hover text tooltip
        self._create_tooltip(self.help_btn, "view signal masterkey")

        # Error button
        error_icon_path = self.current_dir / "icons" / "circle-alert.png"
        if error_icon_path.exists():
            self.error_icon = ctk.CTkImage(
                light_image=Image.open(str(error_icon_path)),
                dark_image=Image.open(str(error_icon_path)),
                size=(20, 20)
            )
        else:
            self.error_icon = None
        
        self.error_btn = ctk.CTkButton(
            self.top_bar,
            image=self.error_icon if self.error_icon else None,
            text="⚠ Error Log" if not self.error_icon else "Error Log",
            font=("Consolas", 12),
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=self.open_error_log_popup
        )
        self.error_btn.pack(side="left", padx=5)
        self._create_tooltip(self.error_btn, "view error log")
    
    def _create_tooltip(self, widget, text):
        """Create a simple tooltip for a widget with proper cleanup."""
        tooltip_ref = {"tooltip": None, "after_id": None}
        
        def create_tooltip(x, y):
            # Clean up any existing tooltip
            if tooltip_ref["tooltip"] is not None:
                try:
                    tooltip_ref["tooltip"].destroy()
                except:
                    pass
            
            tooltip = ctk.CTkToplevel(self.root)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x + 10}+{y + 10}")
            label = ctk.CTkLabel(tooltip, text=text, text_color="white", fg_color="#333333")
            label.pack(padx=5, pady=3)
            tooltip_ref["tooltip"] = tooltip
        
        def on_enter(event):
            # Cancel any pending tooltip creation
            if tooltip_ref["after_id"] is not None:
                self.root.after_cancel(tooltip_ref["after_id"])
            
            # Destroy existing tooltip if any
            if tooltip_ref["tooltip"] is not None:
                try:
                    tooltip_ref["tooltip"].destroy()
                except:
                    pass
                tooltip_ref["tooltip"] = None
            
            # Create tooltip with small delay
            tooltip_ref["after_id"] = self.root.after(500, create_tooltip, event.x_root, event.y_root)
        
        def on_leave(event):
            # Cancel pending tooltip creation
            if tooltip_ref["after_id"] is not None:
                self.root.after_cancel(tooltip_ref["after_id"])
                tooltip_ref["after_id"] = None
            
            # Destroy existing tooltip
            if tooltip_ref["tooltip"] is not None:
                try:
                    tooltip_ref["tooltip"].destroy()
                except:
                    pass
                tooltip_ref["tooltip"] = None
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _build_frames(self):

        
        # main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=1, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.main_frame.grid_columnconfigure((0, 1), weight=1)

        # create subframes
        self.analog_outputs_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.analog_outputs_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.analog_inputs_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.analog_inputs_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.digital_outputs_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.digital_outputs_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.digital_inputs_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.digital_inputs_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # error & connection
        self.error_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.error_frame.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        self.error_frame_label = ctk.CTkLabel(self.error_frame, text="Errors", font=("Consolas", 16))
        self.error_frame_label.pack(pady=(5, 2))
        self.error_label = ctk.CTkLabel(self.error_frame, text="", text_color="red", font=("Consolas", 15), wraplength=400, justify="left")
        self.error_label.pack(side="left", expand=True, fill="x")
        self.error_clear_btn = ctk.CTkButton(self.error_frame, text="x", fg_color="red", hover_color="darkred", width=40, command=self.pop_error,anchor="center")
        self.error_clear_btn.pack_forget()

        self.connector_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.connector_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.connector_frame, text="Connection Status", font=("Consolas", 16)).pack(pady=(5, 2))
        self.status_label = ctk.CTkLabel(self.connector_frame, text="Unknown", text_color="gray", font=("Consolas", 15))
        self.status_label.pack(padx=10, pady=5)

        # analog outputs scroll area
        # --- Analog Outputs header row (label + dropdown on same line) ---
        self.ao_header_frame = ctk.CTkFrame(self.analog_outputs_frame, fg_color="transparent")
        self.ao_header_frame.pack(fill="x", pady=(10, 5), padx=10)

        self.analog_outputs_label = ctk.CTkLabel(
            self.ao_header_frame, text="Analog Outputs", font=("Consolas", 16)
        )
        self.analog_outputs_label.pack(side="left")

        # Dropdown aligned to right of the label
        hidden_aos = [
            name for name, ch in self.channel_mgr.channels.items()
            if ch.sig_type.lower() == "ao" and not ch.showOnGUI
        ]
        if hidden_aos:
            self.add_ao_dropdown = ctk.CTkOptionMenu(
                self.ao_header_frame,
                values=hidden_aos,
                command=self._add_selected_ao,
                width=200
            )
            self.add_ao_dropdown.pack(side="right", padx=5)
            self.add_ao_dropdown.set("Add More AO Channels")
        else:
            self.add_ao_dropdown = None

        # Scrollable area for AO channel widgets
        self.scrollable_ao_frame = ctk.CTkScrollableFrame(self.analog_outputs_frame)
        self.scrollable_ao_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # === ANALOG INPUTS – FULL WIDTH SCROLLABLE ===
        self.ai_header = ctk.CTkFrame(self.analog_inputs_frame, fg_color="transparent")
        self.ai_header.grid(row=0, column=0, sticky="ew", pady=(10, 5), padx=10)
        self.ai_header.grid_columnconfigure(0, weight=1)

        self.ai_label = ctk.CTkLabel(self.ai_header, text="Analog Inputs", font=("Consolas", 16))
        self.ai_label.grid(row=0, column=0, sticky="w")

        hidden_ais = [
            name for name, ch in self.channel_mgr.channels.items()
            if ch.sig_type.lower() == "ai" and not ch.showOnGUI
        ]
        if hidden_ais:
            self.add_ai_dropdown = ctk.CTkOptionMenu(
                self.ai_header,
                values=hidden_ais,
                command=self._add_selected_ai,
                width=200
            )
            self.add_ai_dropdown.grid(row=0, column=1, sticky="e", padx=10)
            self.add_ai_dropdown.set("Add More AI Channels")
        else:
            self.add_ai_dropdown = None

        # Critical: Make the analog_inputs_frame expand properly
        self.analog_inputs_frame.grid_rowconfigure(1, weight=1)
        self.analog_inputs_frame.grid_columnconfigure(0, weight=1)

        # Scrollable frame that takes full width
        self.scrollable_ai_frame = ctk.CTkScrollableFrame(
            self.analog_inputs_frame,
            corner_radius=10
        )
        self.scrollable_ai_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))

        # Inner container for grid layout
        self.ai_grid_container = ctk.CTkFrame(self.scrollable_ai_frame, fg_color="transparent")
        self.ai_grid_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._ai_columns_count = 4
        for i in range(self._ai_columns_count):
            self.ai_grid_container.grid_columnconfigure(i, weight=1, uniform="ai_col")


    def _populate_analog_inputs(self):
        """Populate AI meters in a scrollable grid."""
        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "ai" or not ch_entry.showOnGUI:
                continue

            idx = len(self.ai_meter_objects)
            col = idx % self._ai_columns_count
            row = idx // self._ai_columns_count

            meter_frame = ctk.CTkFrame(self.ai_grid_container, fg_color="transparent", corner_radius=20)
            meter_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            meter_frame.grid_propagate(False)

            bg_color = self.root._apply_appearance_mode(
                ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            )

            # Centered vertical container for meter + label
            content = tk.Frame(meter_frame, bg=bg_color)
            content.pack(expand=True)

            meter = Meter(
                content,
                scroll_steps=0,
                interactive=False,
                radius=140,
                text_font=("Consolas", 14),
                integer=False
            )
            meter.pack(pady=(0, 6))

            label = ctk.CTkLabel(
                content,
                text=name,
                font=("Consolas", 14)
            )
            label.pack()

            self.ai_meter_objects[name] = meter




    def _create_single_ao_row(self, name, ch_entry, removable=False):
        def create_dropdown(parent, name):
            frame = ctk.CTkFrame(parent)
            ddminLabel = ctk.CTkLabel(frame, text="Minimum Value")
            ddminLabel.pack()
            ddminEntry = ctk.CTkEntry(frame, width=100)
            ddminEntry.pack()
            ddmaxLabel = ctk.CTkLabel(frame, text="Maximum Value")
            ddmaxLabel.pack()
            ddmaxEntry = ctk.CTkEntry(frame, width=100)
            ddmaxEntry.pack()
            ddrateLabel = ctk.CTkLabel(frame, text="Rate")
            ddrateLabel.pack()
            ddrateEntry = ctk.CTkEntry(frame, width=100)
            ddrateEntry.pack()

            button_frame = ctk.CTkFrame(frame)
            button_frame.pack(pady=5)
            sendBtn = ctk.CTkButton(button_frame, text="Send", fg_color="blue")
            sendBtn.pack(side="left", padx=5)
            clear_btn = ctk.CTkButton(button_frame, text="Cancel", fg_color="red",
                                    command=lambda f=frame, n=name: self.cancel_ramp_callback(sigName=n))
            clear_btn.pack(side="left", padx=5)
            return [frame, ddminLabel, ddminEntry, ddmaxLabel, ddmaxEntry, ddrateLabel, ddrateEntry, sendBtn]

        def segmented_button_callback(unit, dminLabel, dmaxLabel, drateLabel):
            dminLabel.configure(text=f"Start ({unit})")
            dmaxLabel.configure(text=f"Stop ({unit})")
            drateLabel.configure(text=f"Rate ({unit}/s)")

        frame = ctk.CTkFrame(self.scrollable_ao_frame)
        existing_names = sorted(self.ao_label_objects.keys(), key=self._natural_sort_key)
        insert_before = None
        for existing in existing_names:
            if self._natural_sort_key(name) < self._natural_sort_key(existing):
                insert_before = self.ao_label_objects[existing].master  # get parent frame
                break

        if insert_before is not None:
            frame.pack(pady=5, fill='x', before=insert_before)
        else:
            frame.pack(pady=5, fill='x')
        # Configure grid columns for consistent alignment
        frame.grid_columnconfigure(0, minsize=130)  # Reserve space for name + icon
        frame.grid_columnconfigure(1, minsize=110)  # Reserve space for 100px entry
        frame.grid_columnconfigure(2, minsize=120)
        frame.grid_columnconfigure(3, minsize=80)
        frame.grid_columnconfigure(4, minsize=80)
        frame.grid_columnconfigure(5, minsize=75)
        frame.grid_columnconfigure(6, weight=1)

        # --- Name Label + Rename Icon/Placeholder ---
        # This frame has a fixed width to ensure all rows align vertically.
        name_frame = ctk.CTkFrame(frame, fg_color="transparent", width=65, height=28)
        name_frame.grid(row=0, column=0, padx=(5, 0), sticky="w")
        name_frame.grid_propagate(False)  # Prevent child widgets from resizing this frame

        # Use an inner grid to position the label and icon/placeholder
        name_frame.grid_columnconfigure(0, weight=1)  # Name column
        name_frame.grid_columnconfigure(1, weight=0)  # Icon column

        display_name = self.display_name_map.get(name, name)
        label = ctk.CTkLabel(name_frame, text=display_name, font=("Consolas", 12))

        if removable:
            # Left-align name for removable signals
            label.configure(anchor="w")
            label.grid(row=0, column=0, sticky="w")

            # Pencil icon as a button for hover effects
            pencil_button = ctk.CTkButton(
                name_frame,
                text="",
                image=self.pencil_icon,
                width=22,
                height=22,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda n=name, lbl=label: self.prompt_rename(n, lbl)
            )
            pencil_button.grid(row=0, column=1, padx=(2, 0))

            # Bind rename to text label as well
            label.bind("<Button-1>", lambda e, n=name, lbl=label: self.prompt_rename(n, lbl))
            label.configure(cursor="hand2")
            pencil_button.configure(cursor="hand2")
            self._create_tooltip(label, "Click to rename")
            self._create_tooltip(pencil_button, "Click to rename")
        else:
            # Right-align name for pre-loaded signals to reduce gap to input field
            label.configure(anchor="e")
            label.grid(row=0, column=0, sticky="ew", padx=(0, 4))

            # Add a placeholder to ensure alignment with pencil icons in other rows
            placeholder = ctk.CTkFrame(name_frame, fg_color="transparent", width=24, height=24)
            placeholder.grid(row=0, column=1)

        input_value_entry = ctk.CTkEntry(frame, width=60)
        input_value_entry.grid(row=0, column=1, padx=5, sticky="ew")

        unitSelector = ctk.CTkSegmentedButton(
            frame,
            values=[ch_entry.units, "mA"],
            width=110,
            dynamic_resizing=False,
            selected_color="green",
            selected_hover_color="green"
        )


        unitSelector.set(ch_entry.units)

        send_btn = ctk.CTkButton(
            frame, text="Send", fg_color="blue", width=80,
            command=lambda n=name, e=input_value_entry, s=unitSelector: self.place_single(n, e, s)
        )
        send_btn.grid(row=0, column=3, padx=5, sticky="ew")

        dropdown_frame, ddminLabel, ddminEntry, ddmaxLabel, ddmaxEntry, ddrateLabel, ddrateEntry, sendBtn = create_dropdown(self.scrollable_ao_frame, name)
        arrow_button = ctk.CTkButton(frame, text="⬇ Ramp", width=80)
        arrow_button.configure(command=lambda f=dropdown_frame, p=frame, b=send_btn, ab=arrow_button: self.toggle_dropdown(f, p, b, ab))
        arrow_button.grid(row=0, column=4)
        dropdown_frame.pack_forget()

        sendBtn.configure(command=lambda n=name, dmin=ddminEntry, dmax=ddmaxEntry, drate=ddrateEntry, us=unitSelector:
                        self.place_ramp(n, dmin, dmax, drate, us))

        unitSelector.configure(command=lambda unit=unitSelector.get(), dmin=ddminLabel, dmax=ddmaxLabel, drate=ddrateLabel:
                            segmented_button_callback(unit, dmin, dmax, drate))
        segmented_button_callback(ch_entry.units, ddminLabel, ddmaxLabel, ddrateLabel)
        unitSelector.grid(row=0, column=2, padx=5, sticky="ew")

        if removable:
            remove_btn = ctk.CTkButton(
                frame,
                text="Remove",
                width=70,
                fg_color="darkred",
                command=lambda n=name, f=frame, df=dropdown_frame: self._remove_ao_row(n, f, df)
            )
            remove_btn.grid(row=0, column=5, padx=(5))

        lastSentLabel = ctk.CTkLabel(frame, text="")
        lastSentLabel.grid(row=0, column=5, padx=5, sticky="e")
        self.ao_label_objects[name] = lastSentLabel


    def _populate_analog_outputs(self):
        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() == "ao" and ch_entry.showOnGUI:
                self._create_single_ao_row(name, ch_entry)

    def _add_selected_ao(self, selection: str):
        """Triggered when the user picks a hidden AO from the dropdown."""
        if selection == "Add more AO channels...":
            return

        ch_entry = self.channel_mgr.channels.get(selection)
        if ch_entry is None:
            self.show_error(f"Channel {selection} not found in config.")
            return

        # Mark as visible and create its UI
        ch_entry.showOnGUI = True
        self._create_single_ao_row(selection, ch_entry, removable=True)

        # Update dropdown: remove the added one
        remaining = [v for v in self.add_ao_dropdown.cget("values") if v != selection]
        if remaining:
            self.add_ao_dropdown.configure(values=remaining)
            self.add_ao_dropdown.set("Add more AO channels...")
        else:
            self.add_ao_dropdown.destroy()
            self.add_ao_dropdown = None

    def _remove_ao_row(self, name, frame, dropdown_frame):
        """Remove a dynamically added AO row."""
        # Destroy widgets
        frame.destroy()
        dropdown_frame.destroy()

        # Update label tracking
        if name in self.ao_label_objects:
            del self.ao_label_objects[name]

        # Update the channel’s visibility state
        ch_entry = self.channel_mgr.channels.get(name)
        if ch_entry:
            ch_entry.showOnGUI = False

        # Recreate dropdown if missing
        if not self.add_ao_dropdown:
            self.add_ao_dropdown = ctk.CTkOptionMenu(
                self.ao_header_frame,
                values=[name],
                command=self._add_selected_ao
            )
            self.add_ao_dropdown.set("Add more AO channels...")
            self.add_ao_dropdown.pack(side="right",padx=5)
        else:
            # Add this name back into dropdown
            current_values = list(self.add_ao_dropdown.cget("values"))
            if name not in current_values:
                current_values.append(name)
                current_values.sort(key=self._natural_sort_key)
                self.add_ao_dropdown.configure(values=current_values)


    def _add_selected_ai(self, selection: str):
        """Triggered when the user picks a hidden AI from the dropdown."""
        if selection == "Add more AI channels...":
            return

        ch_entry = self.channel_mgr.channels.get(selection)
        if ch_entry is None:
            self.show_error(f"Channel {selection} not found in config.")
            return

        # Mark as visible
        ch_entry.showOnGUI = True

        # Same row/column logic as initial populate
        idx = len(self.ai_meter_objects)
        currCol = idx % self._ai_columns_count
        currRow = idx // self._ai_columns_count

        meter_frame = ctk.CTkFrame(
            self.ai_grid_container,
            fg_color="transparent",
            corner_radius=20
        )
        meter_frame.grid(column=currCol, row=currRow, padx=8, pady=8, sticky="nsew")

        meter_frame.grid_columnconfigure(0, weight=1)
        meter_frame.grid_rowconfigure(0, weight=1)

        # Appearance-correct background for tk widgets
        bg_color = self.root._apply_appearance_mode(
            ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        )

        # ---- CENTERED CONTENT (meter + name) ----
        content = tk.Frame(meter_frame, bg=bg_color)
        content.grid(row=0, column=0, sticky="n")

        meter = Meter(
            content,
            scroll_steps=0,
            interactive=False,
            radius=140,
            text_font=("Consolas", 14),
            integer=False
        )
        meter.pack(pady=(6, 4))

        # ---- NAME + RENAME BUTTON (centered under meter) ----
        name_frame = ctk.CTkFrame(content, fg_color="transparent")
        name_frame.pack()

        display_name = self.display_name_map.get(selection, selection)
        label = ctk.CTkLabel(name_frame, text=display_name, font=("Consolas", 14))
        label.pack(side="left")

        pencil_button = ctk.CTkButton(
            name_frame,
            text="",
            image=self.pencil_icon,
            width=22,
            height=22,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            command=lambda n=selection, lbl=label: self.prompt_rename(n, lbl)
        )
        pencil_button.pack(side="left", padx=(2, 0))

        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))
        label.configure(cursor="hand2")
        pencil_button.configure(cursor="hand2")
        self._create_tooltip(label, "Click to rename")
        self._create_tooltip(pencil_button, "Click to rename")

        # ---- REMOVE BUTTON ----
        remove_btn = ctk.CTkButton(
            meter_frame,
            text="Remove",
            fg_color="darkred",
            command=lambda n=selection, f=meter_frame: self._remove_ai_meter(n, f)
        )
        remove_btn.grid(row=1, column=0, pady=(4, 6))

        self.ai_meter_objects[selection] = meter

        # Update dropdown
        remaining = [v for v in self.add_ai_dropdown.cget("values") if v != selection]
        if remaining:
            self.add_ai_dropdown.configure(values=remaining)
            self.add_ai_dropdown.set("Add more AI channels...")
        else:
            self.add_ai_dropdown.destroy()
            self.add_ai_dropdown = None

    def _remove_ai_meter(self, name, frame):
        """Remove a dynamically added AI meter."""
        frame.destroy()

        if name in self.ai_meter_objects:
            del self.ai_meter_objects[name]

        ch_entry = self.channel_mgr.channels.get(name)
        if ch_entry:
            ch_entry.showOnGUI = False

        # Recreate dropdown if needed
        if not self.add_ai_dropdown:
            self.add_ai_dropdown = ctk.CTkOptionMenu(
                self.ai_header,
                values=[name],
                command=self._add_selected_ai,
                width=200
            )
            self.add_ai_dropdown.grid(row=0, column=1, sticky="e", padx=10)
            self.add_ai_dropdown.set("Add More AI Channels")
        else:
            current_values = list(self.add_ai_dropdown.cget("values"))
            if name not in current_values:
                current_values.append(name)
                current_values.sort(key=self._natural_sort_key)
                self.add_ai_dropdown.configure(values=current_values)

        self._refresh_ai_layout()


    def _refresh_ai_layout(self):
        """Repack AI meters in a consistent grid layout with fixed sizing."""
        # Clear existing grid placements
        for widget in self.ai_grid_container.winfo_children():
            widget.grid_forget()

        # Grid all meters in sorted order
        for i, (name, meter) in enumerate(sorted(self.ai_meter_objects.items(), key=lambda x: self._natural_sort_key(x[0]))):
            frame = meter.master.master  # go up from meter -> holder -> CTkFrame
            curr_col = i % self._ai_columns_count
            curr_row = i // self._ai_columns_count
            frame.grid(column=curr_col, row=curr_row, padx=10, pady=10, sticky="nsew")

        # Ensure consistent sizing
        for c in range(self._ai_columns_count):
            self.ai_grid_container.grid_columnconfigure(c, weight=1, uniform="col")
        for r in range((len(self.ai_meter_objects) + self._ai_columns_count - 1) // self._ai_columns_count):
            self.ai_grid_container.grid_rowconfigure(r, weight=1, uniform="row")

    def _add_selected_do(self, selection: str):
        """Triggered when the user picks a hidden DO from the dropdown."""
        if selection == "Add more DO channels...":
            return

        ch_entry = self.channel_mgr.channels.get(selection)
        if ch_entry is None:
            self.show_error(f"Channel {selection} not found in config.")
            return

        # Mark as visible
        ch_entry.showOnGUI = True

        container = ctk.CTkFrame(self.scrollable_do_frame, fg_color="transparent")
        container.pack(side="left", padx=8, pady=8)

        name_frame = ctk.CTkFrame(container, fg_color="transparent")
        name_frame.pack(side="left")

        display_name = self.display_name_map.get(ch_entry.name, ch_entry.name)
        label = ctk.CTkLabel(name_frame, text=display_name, width=30, anchor="w", font=("Consolas", 11))
        label.pack(side="left")

        pencil_button = ctk.CTkButton(name_frame, text="", image=self.pencil_icon, width=20, height=20,
                                      fg_color="transparent", hover_color=("gray85", "gray25"),
                                      command=lambda n=selection, lbl=label: self.prompt_rename(n, lbl))
        pencil_button.pack(side="left", padx=(2, 0))

        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))
        label.configure(cursor="hand2")
        pencil_button.configure(cursor="hand2")
        self._create_tooltip(label, "Click to rename")
        self._create_tooltip(pencil_button, "Click to rename")

        switch = ctk.CTkSwitch(container, text="", width=50, height=26)
        switch.pack(side="right", padx=(0, 8))

        switch.configure(command=lambda n=selection, s=switch: self.toggle_do_switch(n, s))
        switch.select()
        self.do_switches[selection] = switch

        # Update dropdown
        remaining = [v for v in self.add_do_dropdown.cget("values") if v != selection]
        if remaining:
            self.add_do_dropdown.configure(values=remaining)
            self.add_do_dropdown.set("Add more DO channels...")
        else:
            self.add_do_dropdown.destroy()
            self.add_do_dropdown = None

    def _add_selected_di(self, selection: str):
        """Triggered when the user picks a hidden DI from the dropdown."""
        if selection == "Add more DI channels...":
            return

        ch_entry = self.channel_mgr.channels.get(selection)
        if ch_entry is None:
            self.show_error(f"Channel {selection} not found in config.")
            return

        # Mark as visible
        ch_entry.showOnGUI = True

        frame = ctk.CTkFrame(self.scrollable_di_frame)
        frame.pack(side="left", padx=10, pady=10)

        name_frame = ctk.CTkFrame(frame, fg_color="transparent")
        name_frame.pack(side="left")

        display_name = self.display_name_map.get(ch_entry.name, ch_entry.name)
        label = ctk.CTkLabel(name_frame, text=display_name, width=30, anchor="w", font=("Consolas", 12))
        label.pack(side="left")

        pencil_button = ctk.CTkButton(name_frame, text="", image=self.pencil_icon, width=20, height=20,
                                      fg_color="transparent", hover_color=("gray85", "gray25"),
                                      command=lambda n=selection, lbl=label: self.prompt_rename(n, lbl))
        pencil_button.pack(side="left", padx=(2, 0))

        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))
        label.configure(cursor="hand2")
        pencil_button.configure(cursor="hand2")
        self._create_tooltip(label, "Click to rename")
        self._create_tooltip(pencil_button, "Click to rename")

        light = ctk.CTkLabel(frame, text="", width=26, height=26, corner_radius=13, fg_color="gray")
        light.pack(side="left", padx=5)

        self.di_label_objects[selection] = light

        # Update dropdown
        remaining = [v for v in self.add_di_dropdown.cget("values") if v != selection]
        if remaining:
            self.add_di_dropdown.configure(values=remaining)
            self.add_di_dropdown.set("Add more DI channels...")
        else:
            self.add_di_dropdown.destroy()
            self.add_di_dropdown = None

    def _populate_digital_outputs(self):
        # Header frame for Digital Outputs (title + dropdown)
        do_header = ctk.CTkFrame(self.digital_outputs_frame, fg_color="transparent")
        do_header.pack(fill="x", pady=(10, 5), padx=10)
        ctk.CTkLabel(do_header, text="Digital Outputs", font=("Consolas", 16)).pack(side="left")

        hidden_dos = [
            name for name, ch in self.channel_mgr.channels.items()
            if ch.sig_type.lower() == "do" and not ch.showOnGUI
        ]
        if hidden_dos:
            self.add_do_dropdown = ctk.CTkOptionMenu(
                do_header,
                values=hidden_dos,
                command=self._add_selected_do,
                width=200
            )
            self.add_do_dropdown.pack(side="right")
            self.add_do_dropdown.set("Add More DO Channels")
        else:
            self.add_do_dropdown = None

        self.scrollable_do_frame = ctk.CTkScrollableFrame(
            self.digital_outputs_frame,
            orientation="horizontal",
            height=50,           # same height as your DI
            corner_radius=10
        )
        self.scrollable_do_frame.pack(fill="x", expand=True, padx=15, pady=(0,15))

        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "do" or not ch_entry.showOnGUI:
                continue
            container = ctk.CTkFrame(self.scrollable_do_frame, fg_color="transparent")
            container.pack(side="left", padx=8, pady=8)
            label = ctk.CTkLabel(container, text=ch_entry.name, width=30, anchor="w", font=("Consolas", 11))
            label.pack(side="left")
            switch = ctk.CTkSwitch(container, text="", width=20, height=26)
            switch.pack(side="right", padx=(0, 8))
            switch.configure(command=lambda n=name, s=switch: self.toggle_do_switch(n, s))
            switch.select()
            self.do_switches[name] = switch

    def _populate_digital_inputs(self):
       # Header frame for Digital Inputs (title + dropdown)
        di_header = ctk.CTkFrame(self.digital_inputs_frame, fg_color="transparent")
        di_header.pack(fill="x", pady=(10, 5), padx=10)
        ctk.CTkLabel(di_header, text="Digital Inputs", font=("Consolas", 16)).pack(side="left")

        hidden_dis = [
            name for name, ch in self.channel_mgr.channels.items()
            if ch.sig_type.lower() == "di" and not ch.showOnGUI
        ]
        if hidden_dis:
            self.add_di_dropdown = ctk.CTkOptionMenu(
                di_header,
                values=hidden_dis,
                command=self._add_selected_di,
                width=200
            )
            self.add_di_dropdown.pack(side="right")
            self.add_di_dropdown.set("Add More DI Channels")
        else:
            self.add_di_dropdown = None

        self.scrollable_di_frame = ctk.CTkScrollableFrame(
            self.digital_inputs_frame,
            orientation="horizontal",
            height=50,
            corner_radius=10
        )
        self.scrollable_di_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))



        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "di" or not ch_entry.showOnGUI:
                continue

            # Create indicator inside the scrollable frame
            frame = ctk.CTkFrame(self.scrollable_di_frame)
            frame.pack(side="left", padx=22, pady=10)

            label = ctk.CTkLabel(frame, text=ch_entry.name, width=30, anchor="w", font=("Consolas", 12))
            label.pack(side="left")

            light = ctk.CTkLabel(frame, text="", width=26, height=26, corner_radius=13, fg_color="gray")
            light.pack(side="left", padx=10)

            self.di_label_objects[name] = light

    def prompt_rename(self, original_name: str, label_widget):
        """Popup dialog allowing user to rename only dynamically-added signals."""
        top = ctk.CTkToplevel(self.root)
        top.title("Rename Signal")
        top.geometry("300x200")

        ctk.CTkLabel(top, text=f"Rename {original_name}").pack(pady=10)

        entry = ctk.CTkEntry(top)
        entry.pack(pady=5)
        
        # Error message label
        error_label = ctk.CTkLabel(top, text="", text_color="red", font=("Consolas", 10))
        error_label.pack(pady=5)
        
        # move popup to the front
        top.after(100, top.lift)
        # Pre-fill with existing renamed value or the original name
        current_name = self.display_name_map.get(original_name, original_name)
        entry.insert(0, current_name)

        submit_btn = ctk.CTkButton(top, text="OK")
        submit_btn.pack(pady=10)

        def validate_and_update(*args):
            """Validate input and update error message and button state."""
            new_name = entry.get().strip()
            
            if len(new_name) > 5:
                error_label.configure(text=f"Max 5 characters ({len(new_name)}/5)")
                submit_btn.configure(state="disabled")
            else:
                error_label.configure(text="")
                submit_btn.configure(state="normal")

        def submit():
            new_name = entry.get().strip()
            if new_name and len(new_name) <= 5:
                self.display_name_map[original_name] = new_name
                # Switch widgets use .configure(text=...)
                label_widget.configure(text=new_name)
            top.destroy()

        # Bind validation to every keystroke
        entry.bind("<KeyRelease>", validate_and_update)
        
        # Run validation once on initial load
        validate_and_update()
        
        submit_btn.configure(command=submit)

    def open_signal_config_popup(self):
        # Prevent multiple popups
        if hasattr(self, "signal_cfg_popup") and self.signal_cfg_popup.winfo_exists():
            self.signal_cfg_popup.lift()
            return

        self.signal_cfg_popup = ctk.CTkToplevel(self.root)
        self.signal_cfg_popup.title("Signal Configuration")
        self.signal_cfg_popup.geometry(f"{self.root.winfo_screenwidth()-50}x{self.root.winfo_screenheight()-50}")

        # Keep popup on top of main window
        self.signal_cfg_popup.transient(self.root)
        self.signal_cfg_popup.grab_set()

        # Build signal config page inside popup, passing display_name_map for renamed signals
        signal_page = SignalMasterKey(
            self.signal_cfg_popup,
            self.config.raw.get("signals", []),
            display_name_map=self.display_name_map
        )
        signal_page.pack(fill="both", expand=True, padx=10, pady=10)

    # UI helpers and command handlers
    def toggle_dropdown(self, frame, parent_frame, sendBtn, arrowBtn):
        if frame.winfo_ismapped():
            sendBtn.configure(state="normal")
            frame.pack_forget()
            arrowBtn.configure(text="⬇ Ramp")
        else:
            frame.pack(after=parent_frame, pady=5)
            sendBtn.configure(state="disabled")
            arrowBtn.configure(text="⬆")

    def cancel_ramp_callback(self, sigName: str):
        ch = self.channel_mgr.get_channel_entry(sigName)
        if ch.get_logical_id() is None:
            return
        numRemoved = self.socket_ctrl.clear_all_entries_with_logical_id(ch.get_logical_id())
        if self.enable_verbose_logging:
            print(f"cancelled {numRemoved} entries for {sigName}")

    def place_single(self, name: str, entry_widget, segmentedUnitButton):
        try:
            val = float(entry_widget.get())
        except Exception:
            return
        unit = str(segmentedUnitButton.get())
        ch = self.channel_mgr.get_channel_entry(name)
        if unit == "mA":
            success, err = self.socket_ctrl.place_single_mA(ch2send=ch, mA_val=float(val), time=time.time())
        else:
            success, err = self.socket_ctrl.place_single_EngineeringUnits(ch2send=ch, val_in_eng_units=float(val), time=time.time())
        if success:
            entry_widget.delete(0, ctk.END)
        else:
            # push an errorEntry into queue for existing processing logic to display
            self.socketRespQueue.put(errorEntry(f"{name} single input", criticalityLevel="medium", description=err))

    def place_ramp(self, name: str, startEntry, stopEntry, rateEntry, segmentedUnitButton):
        try:
            startVal = float(startEntry.get())
            stopVal = float(stopEntry.get())
            rateVal = float(rateEntry.get())
        except Exception:
            return
        unit = str(segmentedUnitButton.get())
        chEntry = self.channel_mgr.get_channel_entry(name)
        if unit != "mA":
            startVal = chEntry.EngineeringUnits_to_mA(startVal)
            stopVal = chEntry.EngineeringUnits_to_mA(stopVal)
            rateVal = chEntry.EngineeringUnitsRate_to_mARate(rateVal)
        success = self.socket_ctrl.place_ramp(ch2send=chEntry, start_mA=startVal, stop_mA=stopVal, stepPerSecond_mA=rateVal)
        if success:
            startEntry.delete(0, ctk.END)
            stopEntry.delete(0, ctk.END)
            rateEntry.delete(0, ctk.END)
        else:
            if unit == "mA":
                self.socketRespQueue.put(errorEntry(f"{name} ramp input", criticalityLevel="medium", description=f"Invalid ramp command for {chEntry.name}. Valid range: 4 - 20 mA."))
            else:
                self.socketRespQueue.put(errorEntry(f"{name} ramp input", criticalityLevel="medium", description=f"Invalid ramp command for {chEntry.name}. Valid range: {chEntry.realUnitsLowAmount} - {chEntry.realUnitsHighAmount} {chEntry.units}"))

    def toggle_do_switch(self, name: str, ctkSwitch):
        val = ctkSwitch.get()
        success, errorString = self.socket_ctrl.place_single_EngineeringUnits(ch2send=self.channel_mgr.get_channel_entry(name), val_in_eng_units=int(val), time=time.time())
        if success:
            ctkSwitch.configure(state="disabled")
        else:
            self.show_error(errorString)

    def pop_error(self):
        if len(self.error_stack) == 0:
            self.show_error("")
            return
        # original code appended and popped twice; preserve behaviour
        self.error_stack.pop()
        if len(self.error_stack) == 0:
            self.show_error("")
            return
        err_to_show = self.error_stack.pop()
        self.show_error(err_to_show)

    def show_error(self, message: str):
        self.error_label.configure(text=message)
        self.error_label.configure(text_color="red")
        if message == "":
            self.error_clear_btn.pack_forget()
        else:
            self.error_clear_btn.pack(padx=10, side="right")
            # Store error with timestamp
            error_entry = {
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.error_stack.append(error_entry)
        if len(self.error_stack) >= self.error_stack_max_len:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)}+)")
        else:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)})")
    def open_error_log_popup(self):
        # Prevent multiple popups
        if hasattr(self, "error_log_popup") and self.error_log_popup.winfo_exists():
            self.error_log_popup.lift()
            return

        self.error_log_popup = ctk.CTkToplevel(self.root)
        self.error_log_popup.title("Error Log")
        self.error_log_popup.geometry(f"{self.root.winfo_screenwidth()-50}x{self.root.winfo_screenheight()-50}")

        # Keep popup on top of main window
        self.error_log_popup.transient(self.root)
        self.error_log_popup.grab_set()

        # Build error log page inside popup
        error_log_page = ErrorLog(
            self.error_log_popup,
            self.error_stack,
            on_update=self._on_error_log_update
        )
        error_log_page.pack(fill="both", expand=True, padx=10, pady=10)

    def _on_error_log_update(self):
        """Callback when error log changes."""
        if len(self.error_stack) >= self.error_stack_max_len:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)}+)")
        else:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)})")
            
        if len(self.error_stack) == 0:
            self.show_error("")

    def show_connection_status(self, online: bool | None, message: str = ""):
        if online is None:
            self.status_label.configure(text="Unknown")
            self.status_label.configure(text_color="gray")
            return
        if online:
            self.status_label.configure(text=f"Connected ✓{message}")
            self.status_label.configure(text_color="green")
        else:
            self.status_label.configure(text=f"No Connection ❌{message}")
            self.status_label.configure(text_color="red")

    def process_queue(self):
        # read all responses in the queue
        while not self.socketRespQueue.empty():
            sockResp = self.socketRespQueue.get()
            
            if self.enable_verbose_logging:
                print(f"sockResp is {sockResp}")
            if isinstance(sockResp, errorEntry):
                # analog channel errors usually prefix 'a' and include gpio_str in description after ':'
                
                if sockResp.source.lower()[0] == "a":
                    try:
                        logical_id = sockResp.description.split(":")[1].strip()
                        chEntry_to_blame = self.channel_mgr.get_channel_from_logical_id(logical_id)
                        if "Encountered unexpected exception" in sockResp.description:
                            self.show_error(message=f"Encountered unexpected exception for {chEntry_to_blame.name} at board slot {chEntry_to_blame.boardSlotPosition}")
                        if "SPI communication error detected" in sockResp.description:
                            errMessage = sockResp.description.split(":")[0]
                            self.show_error(message=f"{errMessage} for {chEntry_to_blame.name} at board slot {chEntry_to_blame.boardSlotPosition}")
                    except Exception:
                        self.show_error(message=sockResp.description)
                elif "ethernet" in sockResp.source.lower():
                    self.show_connection_status(online=False)
                    self.show_error(message=sockResp.description)
                else:
                    self.show_error(message=sockResp.description)
            elif isinstance(sockResp, dataEntry):
                self.show_connection_status(online=True)
                chEntry = self.channel_mgr.get_channel_from_logical_id(sockResp.logical_id)
                if chEntry is None:
                    if sockResp.logical_id == "ack":
                        print("received ack packet")
                    continue
                if chEntry.sig_type.lower() == "ai":
                    if debug_statements == 1:
                        print(f"DEBUG [UI Received]: Signal={chEntry.name}, Val={sockResp.val:.2f} mA")
                    if chEntry.name in self.ai_meter_objects:
                        meterObj = self.ai_meter_objects[chEntry.name]
                        meterObj.set(chEntry.mA_to_EngineeringUnits(sockResp.val))
                elif chEntry.sig_type.lower() == "di":
                    if debug_statements == 1:
                        print(f"DEBUG [UI Received]: Signal={chEntry.name}, Val={sockResp.val}")
                    if chEntry.name in self.di_label_objects:
                        if int(sockResp.val) == 1:
                            self.di_label_objects[chEntry.name].configure(fg_color="green")
                        else:
                            self.di_label_objects[chEntry.name].configure(fg_color="gray")
                elif chEntry.sig_type.lower() == "do":
                    # response is ack from RPi
                    if chEntry.name in self.do_switches:
                        self.do_switches[chEntry.name].configure(state="normal")
                elif "ao" in chEntry.sig_type.lower():
                    labelObj = self.ao_label_objects.get(chEntry.name)
                    if labelObj:
                        if sockResp.val == "NAK":
                            labelObj.configure(text="ERR")
                        else:
                            labelObj.configure(text=f"{sockResp.val:.1f} mA")

        # schedule periodic reads for ai and di channels
        for name, meter in self.ai_meter_objects.items():
            ch = self.channel_mgr.get_channel_entry(name)
            if ch.get_logical_id() is None:
                continue
            success, err = self.socket_ctrl.place_single_mA(ch2send=ch, mA_val=self.ai_LPF_boxcar_length, time=time.time())
            if not success and self.enable_verbose_logging:
                print(f"Polling error for {name}: {err}")

        for name, label_obj in self.di_label_objects.items():
            try:
                success, errString = self.socket_ctrl.place_single_EngineeringUnits(ch2send=self.channel_mgr.get_channel_entry(name), val_in_eng_units=0, time=time.time())
                if not success:
                    self.show_error(errString)
            except Exception as e:
                print(f"Encountered error while polling DI: {e}")

        # rearm timer
        self.root.after(self.poll_buffer_period_ms, self.process_queue)

    def _natural_sort_key(self, name: str):
        """Extract numerical parts of a channel name for natural sorting."""
        import re
        parts = re.split(r'(\d+)', name)
        return [int(p) if p.isdigit() else p.lower() for p in parts]

    def shutdown(self):
        try:
            self.socket_ctrl.close()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()
