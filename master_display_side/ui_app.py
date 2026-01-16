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

import tkinter as tk
import customtkinter as ctk
from tkdial import Meter

from config_manager import ConfigManager
from channel_manager import ChannelManager
from socket_controller import SocketController
from PacketBuilder import dataEntry, errorEntry  # referenced in queue processing

class SimulatorApp:
    def __init__(self, config_path: str | Path, channel_mgr: ChannelManager, socket_ctrl: SocketController):
        self.current_dir = Path(__file__).resolve().parent
        self.config = ConfigManager(config_path)  # also accessible, but kept for compatibility
        self.channel_mgr = channel_mgr
        self.socket_ctrl = socket_ctrl

        # runtime settings shortcut
        rs = self.config.runtime_settings
        self.error_stack_max_len = rs["error_stack_max_len"]
        self.enable_verbose_logging = rs["enable_verbose_logging"]
        self.ai_LPF_boxcar_length = rs["ai_LPF_boxcar_length"]
        self.poll_buffer_period_ms = rs["poll_buffer_period_ms"]

        # UI state
        self.error_stack = deque(maxlen=self.error_stack_max_len)
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
        self.root.title("GCC Compressor Simulator v1.0")
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # exception handler integration for Tk
        self.root.report_callback_exception = self.exception_handler

        # proper shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _build_frames(self):
        # main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
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

        self._ai_columns_count = 3
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

            bg_color = self.root._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
            meter_holder = tk.Frame(meter_frame, bg=bg_color)
            meter_holder.pack(expand=True, fill="both", padx=6, pady=6)

            meter = Meter(
                meter_holder,
                scroll_steps=0,
                interactive=False,
                radius=140,
                text_font=("Consolas", 14),
                integer=False
            )
            meter.pack(expand=True, fill="both")

            label = ctk.CTkLabel(meter_frame, text=name, font=("Consolas", 14))
            label.pack(pady=(4, 0))

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
        frame.grid_columnconfigure(0, minsize=70)
        frame.grid_columnconfigure(1, minsize=100)
        frame.grid_columnconfigure(2, minsize=120)
        frame.grid_columnconfigure(3, minsize=80)
        frame.grid_columnconfigure(4, minsize=80)
        
        # Center signal name within 5-character width
        centered_name = name.center(5)
        label = ctk.CTkLabel(frame, text=centered_name, font=("Consolas", 12))
        label.grid(row=0, column=0, padx=5, sticky="ew")

        # enable renaming only for dynamically-added AO
        if removable:
            label.bind("<Button-1>", lambda e, n=name, lbl=label: self.prompt_rename(n, lbl))

        input_value_entry = ctk.CTkEntry(frame, width=100)
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
            remove_btn.grid(row=0, column=6, padx=0)



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

        # Use the same column/row math as populate to avoid replacing existing meters
        idx = len(self.ai_meter_objects)
        currCol = idx % self._ai_columns_count
        currRow = idx // self._ai_columns_count

        meter_frame = ctk.CTkFrame(self.ai_grid_container, fg_color="transparent", corner_radius=20)
        meter_frame.grid(column=currCol, row=currRow, padx=8, pady=8, sticky="nsew")
        meter_frame.grid_columnconfigure(0, weight=1)
        meter_frame.grid_rowconfigure(0, weight=1)

        # Create a plain Tkinter frame as the Meter's container (inside the CTk frame)
        
        meter_parent = tk.Frame(meter_frame)
        meter_parent.grid(row=0, column=0, sticky="nsew")

        # Create a small plain tk.Frame *inside* the CTkFrame for compatibility
        bg_color = self.root._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        meter_holder = tk.Frame(meter_frame, bg=bg_color)
        meter_holder.grid(row=0, column=0, sticky="nsew")

        # Now put the Meter inside that holder
        meter = Meter(
            meter_holder,
            scroll_steps=0,
            interactive=False,
            radius=140,
            text_font=("Consolas", 14),  # tkmeter only supports standard font tuples
            integer=False
        )
        meter.pack(expand=True, fill="both", padx=6, pady=6)
        label = ctk.CTkLabel(meter_frame, text=selection, font=("Consolas", 14))
        label.grid(row=1, column=0, pady=(4, 0))
        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))

        

        remove_btn = ctk.CTkButton(
            meter_frame,
            text="Remove",
            fg_color="darkred",
            command=lambda n=selection, f=meter_frame: self._remove_ai_meter(n, f)
        )
        remove_btn.grid(row=2, column=0, pady=(4, 6))

        self.ai_meter_objects[selection] = meter

        # Update dropdown: remove the added one
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

        label = ctk.CTkLabel(container, text=ch_entry.name, width=30, anchor="w", font=("Consolas", 11))
        label.pack(side="left")
        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))

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

        label = ctk.CTkLabel(frame, text=ch_entry.name, width=30, anchor="w", font=("Consolas", 12))
        label.pack(side="left")
        label.bind("<Button-1>", lambda e, n=selection, lbl=label: self.prompt_rename(n, lbl))

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
        top.geometry("300x150")

        ctk.CTkLabel(top, text=f"Rename {original_name}").pack(pady=10)

        entry = ctk.CTkEntry(top)
        entry.pack(pady=5)
        
        # move popup to the front
        top.after(100, top.lift)
        # Pre-fill with existing renamed value or the original name
        entry.insert(0, self.display_name_map.get(original_name, original_name))

        def submit():
            new_name = entry.get().strip()
            if new_name:
                self.display_name_map[original_name] = new_name

                # Switch widgets use .configure(text=...)
                label_widget.configure(text=new_name)

            top.destroy()

        ctk.CTkButton(top, text="OK", command=submit).pack(pady=10)



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
        if ch.getGPIOStr() is None:
            return
        numRemoved = self.socket_ctrl.clear_all_entries_with_gpio_str(ch.getGPIOStr())
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
            self.error_stack.append(message)
        if len(self.error_stack) >= self.error_stack_max_len:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)}+)")
        else:
            self.error_frame_label.configure(text=f"Errors ({len(self.error_stack)})")

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
                        gpio_str = sockResp.description.split(":")[1].strip()
                        chEntry_to_blame = self.channel_mgr.get_channel_from_gpio(gpio_str)
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
                chEntry = self.channel_mgr.get_channel_from_gpio(sockResp.gpio_str)
                if chEntry is None:
                    if sockResp.gpio_str == "ack":
                        print("received ack packet")
                    continue
                if chEntry.sig_type.lower() == "ai":
                    meterObj = self.ai_meter_objects[chEntry.name]
                    meterObj.set(chEntry.mA_to_EngineeringUnits(sockResp.val))
                elif chEntry.sig_type.lower() == "di":
                    if int(sockResp.val) == 1:
                        self.di_label_objects[chEntry.name].configure(fg_color="green")
                    else:
                        self.di_label_objects[chEntry.name].configure(fg_color="gray")
                elif chEntry.sig_type.lower() == "do":
                    # response is ack from RPi
                    self.do_switches[chEntry.name].configure(state="normal")
                elif "ao" in chEntry.sig_type.lower():
                    labelObj = self.ao_label_objects.get(chEntry.name)
                    if sockResp.val == "NAK":
                        labelObj.configure(text="ERR")
                    else:
                        labelObj.configure(text=f"{sockResp.val:.1f} mA")

        # schedule periodic reads for ai and di channels
        for name, meter in self.ai_meter_objects.items():
            ch = self.channel_mgr.get_channel_entry(name)
            if ch.getGPIOStr() is None:
                continue
            self.socket_ctrl.place_single_mA(ch2send=ch, mA_val=self.ai_LPF_boxcar_length, time=time.time())

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
