# -*- coding: utf-8 -*-
"""
Created on 1/17/25

@author: REYNOLDSPG21
"""

import gpiozero
import spidev
try:
    from .SN54LS138_Demux import SN54LS138_Demux
    from .GPIOEX import GPIOEX
except ImportError:
    # Allow running this module directly as a script.
    from SN54LS138_Demux import SN54LS138_Demux
    from GPIOEX import GPIOEX

from enum import IntEnum

class PinState(IntEnum):
    DISCONNECTED = -1
    OFF = 0
    ON = 1


class Digital_Input_Module:
    def __init__(self, momIn : SN54LS138_Demux, mcp:GPIOEX, card_slot: int,  board_slot: int ):
        self.mcp = mcp
        self.pin = card_slot - 1
        self.momIn = momIn
        self.board_slot = board_slot -  6 #  - subtract 6 because demux 2 is wired to outputs y0,y1,y2
        print("-"*100)
        print(f"made it into init di with board{ board_slot} and card {card_slot}" )
        print("-"*100)
        # self.mcp.set_pin_direction(self.pin, input=True)
        # self.mcp.enable_pullups(1 << self.pin)
        

    def readState(self) -> PinState:
        self.momIn.enable()
        self.momIn.select_output(self.board_slot)

        if not self.mcp.is_connected():
            self.momIn.deselect_output()
            self.momIn.disable()
            return PinState.DISCONNECTED

        raw = self.mcp.read_pin(self.pin)
        self.momIn.deselect_output()
        self.momIn.disable()
        return PinState.ON if not raw else PinState.OFF
    
    def close(self):pass

if __name__ == "__main__":
    import time
    spi = spidev.SpiDev()
    spi.open(1, 0)  # Open SPI bus 0, device 0 (CE0)
    resetPin = gpiozero.DigitalOutputDevice("GPIO26", initial_value =1 )
    resetPin.on()
    time.sleep(1)
    # Set up demux for board selectio
    spi.threewire
    momIn = SN54LS138_Demux(a_pin="GPIO23", b_pin="GPIO24", c_pin="GPIO25",g1_pin= None)
    
    # Set up MCP for relay control
    mcp = GPIOEX(spi, hw_addr=0)
    
    # Create digital input module instance
    dim = Digital_Input_Module(momIn, mcp, 1, 9)
    momIn.enable()  # Enable demux for this transaction
    momIn.select_output(1)
    mcp.set_direction(0xFF) # all outputs
    momIn.deselect_output()  # Disable after transaction
    momIn.disable()  
    import time
    try:
        while True:
            print(f"state is {dim.readState()}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    dim.close()
