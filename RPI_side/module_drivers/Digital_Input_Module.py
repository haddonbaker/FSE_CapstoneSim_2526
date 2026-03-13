# -*- coding: utf-8 -*-
"""
Created on 1/17/25

@author: REYNOLDSPG21
"""

import gpiozero

class Digital_Input_Module:
    def __init__(self, mcp=None, pin: int | None = None):
        self.mcp = mcp
        self.pin = pin

    def readState(self) -> int:
        if self.mcp is not None and self.pin is not None:
            return int(self.mcp.read_pin(self.pin))
        else:
            raise RuntimeError("Digital_Input_Module has no input interface configured")

    def close(self):pass

if __name__ == "__main__":
    my_pin = gpiozero.DigitalInputDevice("GPIO19", pull_up=True)
    dim = Digital_Input_Module(gpio_in_pin=my_pin)

    import time
    try:
        while True:
            print(f"state is {dim.readState()}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    dim.close()
    my_pin.close()
