# ui_app.py
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
        self.error_label.pack(padx=10, pady=5, side="left")
        self.error_clear_btn = ctk.CTkButton(self.error_frame, text="x", fg_color="red", hover_color="red", width=40, command=self.pop_error)
        self.error_clear_btn.pack_forget()

        self.connector_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.connector_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.connector_frame, text="Connection Status", font=("Consolas", 16)).pack(pady=(5, 2))
        self.status_label = ctk.CTkLabel(self.connector_frame, text="Unknown", text_color="gray", font=("Consolas", 15))
        self.status_label.pack(padx=10, pady=5)

        # analog outputs scroll area
        self.analog_outputs_label = ctk.CTkLabel(self.analog_outputs_frame, text="Analog Outputs", font=("Consolas", 16))
        self.analog_outputs_label.pack(pady=10)
        self.scrollable_frame = ctk.CTkScrollableFrame(master=self.analog_outputs_frame, width=500)
        self.scrollable_frame.pack(fill="both", expand=True)

        # analog inputs label in its frame
        self.ai_label = ctk.CTkLabel(self.analog_inputs_frame, text="Analog Inputs", font=("Consolas", 16))
        self.ai_label.grid(row=0, column=0, pady=10, sticky="nsew")

    def _populate_analog_inputs(self):
        currCol = 0
        currRow = 0
        numInCurrCol = 0
        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "ai" or not ch_entry.showOnGUI:
                continue
            meter_frame = ctk.CTkFrame(self.analog_inputs_frame)
            meter_frame.grid(column=currCol, row=currRow+1, padx=10, pady=0, sticky="nsew")
            meter = Meter(meter_frame, scroll_steps=0, interactive=False, radius=170, text_font = ctk.CTkFont("Consolas", size=14), integer=False)
            meter.grid(row=0,column=0, padx=10, pady=10, sticky="nsew")
            l = ctk.CTkLabel(meter_frame, text=f"{name} ({ch_entry.units})", font=("Consolas", 12))
            l.grid(row=1, column=0, pady=10, sticky="s")
            self.ai_meter_objects[name] = meter

            numInCurrCol += 1
            currRow = (currRow + 1) % 2
            if numInCurrCol == 2:
                numInCurrCol = 0
                currCol += 1

    def _populate_analog_outputs(self):
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

        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "ao" or not ch_entry.showOnGUI:
                continue
            frame = ctk.CTkFrame(self.scrollable_frame)
            frame.pack(pady=5, fill='x')
            ctk.CTkLabel(frame, text=f"{name}").grid(row=0, column=0, padx=5, sticky="w")
            input_value_entry = ctk.CTkEntry(frame, width=100)
            input_value_entry.grid(row=0, column=1, padx=5)

            unitSelector = ctk.CTkSegmentedButton(frame, values=[f"{ch_entry.units}", "mA"], selected_color="green", selected_hover_color="green")
            unitSelector.set(f"{ch_entry.units}")

            send_btn = ctk.CTkButton(frame, text="Send", fg_color="blue",
                                     command=lambda n=name, e=input_value_entry, s=unitSelector: self.place_single(n, e, s))
            send_btn.grid(row=0, column=3, padx=5)

            dropdown_frame, ddminLabel, ddminEntry, ddmaxLabel, ddmaxEntry, ddrateLabel, ddrateEntry, sendBtn = create_dropdown(self.scrollable_frame, name)
            arrow_button = ctk.CTkButton(frame, text="⬇ Ramp", width=20)
            arrow_button.configure(command=lambda f=dropdown_frame, p=frame, b=send_btn, ab=arrow_button: self.toggle_dropdown(f, p, b, ab))
            arrow_button.grid(row=0, column=4, padx=5)
            dropdown_frame.pack_forget()

            sendBtn.configure(command=lambda n=name, dmin=ddminEntry, dmax=ddmaxEntry, drate=ddrateEntry, us=unitSelector: self.place_ramp(n, dmin, dmax, drate, us))

            unitSelector.configure(command=lambda unit=unitSelector.get(), dmin=ddminLabel, dmax=ddmaxLabel, drate=ddrateLabel: segmented_button_callback(unit, dmin, dmax, drate))
            segmented_button_callback(ch_entry.units, ddminLabel, ddmaxLabel, ddrateLabel)
            unitSelector.grid(row=0, column=2, padx=5)

            lastSentLabel = ctk.CTkLabel(frame, text="")
            lastSentLabel.grid(row=0, column=5, padx=5, sticky="e")
            self.ao_label_objects[name] = lastSentLabel

    def _populate_digital_outputs(self):
        ctk.CTkLabel(self.digital_outputs_frame, text="Digital Outputs", font=("Consolas", 16)).pack(pady=10)

        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "do" or not ch_entry.showOnGUI:
                continue
            motor_status_switch = ctk.CTkSwitch(self.digital_outputs_frame, text=ch_entry.name, onvalue=1, offvalue=0)
            motor_status_switch.configure(command=lambda n=name, switchObj=motor_status_switch: self.toggle_do_switch(n, switchObj))
            motor_status_switch.pack(side="left", padx=10, expand=True)
            motor_status_switch.select()
            self.do_switches[name] = motor_status_switch

    def _populate_digital_inputs(self):
        ctk.CTkLabel(self.digital_inputs_frame, text="Digital Inputs", font=("Consolas", 16)).pack(pady=10)
        for name, ch_entry in self.channel_mgr.channels.items():
            if ch_entry.sig_type.lower() != "di" or not ch_entry.showOnGUI:
                continue
            indicator_frame = ctk.CTkFrame(self.digital_inputs_frame)
            indicator_frame.pack(pady=10, padx=20, side="left", expand=True)
            indicator_label = ctk.CTkLabel(indicator_frame, text=ch_entry.name)
            indicator_label.pack(side="left", padx=10)
            indicator_light = ctk.CTkLabel(indicator_frame, text="", width=20, height=20, corner_radius=10, fg_color="gray")
            self.di_label_objects[name] = indicator_light
            indicator_light.pack(side="left")

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
            self.error_clear_btn.pack(padx=0, pady=5, side="right")
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

    def shutdown(self):
        try:
            self.socket_ctrl.close()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()
