"""
Created on 2026-02-12 by Jacob Schroeder with the assistance of ChatGPT

SN54LS138_Demux: Controls a SN54LS138 3-to-8 line demultiplexer/decoder for chip selection.

The SN54LS138 is a high-speed 3-to-8 line decoder/demultiplexer with:
- 3 address input lines (A, B, C) to select one of 8 outputs (Y0-Y7)
- 3 enable lines (G1, G2A, G2B) for gating control
- Active-low outputs (outputs are LOW when selected, HIGH when not selected)

Truth table for address lines:
- C B A → Output (all others HIGH)
- 0 0 0 → Y0 (LOW)
- 0 0 1 → Y1 (LOW)
- 0 1 0 → Y2 (LOW)
- 0 1 1 → Y3 (LOW)
- 1 0 0 → Y4 (LOW)
- 1 0 1 → Y5 (LOW)
- 1 1 0 → Y6 (LOW)
- 1 1 1 → Y7 (LOW)
"""

import gpiozero
from typing import Union


class SN54LS138_Demux:
    """Controls a SN54LS138 3-to-8 demultiplexer for chip selection."""

    def __init__(self, a_pin: Union[str, gpiozero.DigitalOutputDevice],
                 b_pin: Union[str, gpiozero.DigitalOutputDevice],
                 c_pin: Union[str, gpiozero.DigitalOutputDevice],
                 g1_pin: Union[str, gpiozero.DigitalOutputDevice] = None):
        """
        Initialize the SN54LS138 demultiplexer controller.
        
        Note: G2A and G2B are grounded (no GPIO control needed).
        
        :param a_pin: GPIO pin for A (LSB) - string like "GPIO22" or DigitalOutputDevice
        :param b_pin: GPIO pin for B - string like "GPIO23" or DigitalOutputDevice
        :param c_pin: GPIO pin for C (MSB) - string like "GPIO24" or DigitalOutputDevice
        :param g1_pin: GPIO pin for G1 enable (active HIGH) - optional, defaults to "GPIO25"
        """
        # Convert string pins to DigitalOutputDevice if needed
        if isinstance(a_pin, str):
            self.a = gpiozero.DigitalOutputDevice(a_pin, initial_value=0)
        else:
            self.a = a_pin

        if isinstance(b_pin, str):
            self.b = gpiozero.DigitalOutputDevice(b_pin, initial_value=0)
        else:
            self.b = b_pin

        if isinstance(c_pin, str):
            self.c = gpiozero.DigitalOutputDevice(c_pin, initial_value=0)
        else:
            self.c = c_pin

        # Enable pin (optional, default to GPIO7)
        if g1_pin is None:
            self.g1 = gpiozero.DigitalOutputDevice("GPIO27", initial_value=1)  # G1 active HIGH
        elif isinstance(g1_pin, str):
            self.g1 = gpiozero.DigitalOutputDevice(g1_pin, initial_value=1)
        else:
            self.g1 = g1_pin

        self.current_output = None

    def select_output(self, output_index: int) -> None:
        """
        Set the demux address lines to select a specific output (0-7).
        
        The SN54LS138 has active-LOW outputs, but this function abstracts that away.
        When you select an output, only that output will be driven LOW; all others HIGH.
        
        :param output_index: The demux output to select (0-7)
        :raises ValueError: if output_index is not in range [0, 7]
        """
        if not 0 <= output_index <= 7:
            raise ValueError(f"Demux output must be 0-7, got {output_index}")

        # Set address lines based on binary representation of output_index
        # Note: For SN54LS138, outputs are active-LOW
        self.a.value = bool(output_index & 0b001)  # LSB
        self.b.value = bool(output_index & 0b010)  # Middle bit
        self.c.value = bool(output_index & 0b100)  # MSB

        self.current_output = output_index

    def deselect_output(self) -> None:
        """
        Deselect the current output by disabling the demultiplexer.
        After SPI transaction, this should be called to drive all outputs HIGH (inactive).
        """
        # Disable the demux by pulling G1 LOW
        # This drives all outputs HIGH, effectively deselecting
        self.g1.value = 0  # Disable G1 (active HIGH)
        self.current_output = None

    def enable(self) -> None:
        """Enable the demultiplexer (activate outputs)."""
        self.g1.value = 1  # G1 is active HIGH (G2A and G2B are grounded)

    def disable(self) -> None:
        """Disable the demultiplexer (all outputs HIGH/inactive)."""
        self.g1.value = 0  # Disable G1

    def close(self) -> None:
        """Clean up GPIO resources."""
        if hasattr(self, 'a'):
            self.a.close()
        if hasattr(self, 'b'):
            self.b.close()
        if hasattr(self, 'c'):
            self.c.close()
        if hasattr(self, 'g1'):
            self.g1.close()

    def __str__(self) -> str:
        return f"SN54LS138_Demux (currently selecting output {self.current_output})"
