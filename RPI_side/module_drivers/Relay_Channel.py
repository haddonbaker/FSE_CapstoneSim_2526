import gpiozero
import spidev
from .SN54LS138_Demux import SN54LS138_Demux
from .GPIOEX import GPIOEX

from enum import IntEnum

class PinState(IntEnum):
    DISCONNECTED = -1
    OFF = 0
    ON = 1

class RELAY_CHANNEL:
    def __init__(self, momOut: SN54LS138_Demux, mcp: GPIOEX, card_slot: int, board_slot: int):
        self.mcp = mcp
        self.pin = card_slot - 1
        self.momOut = momOut
        self.board_slot = board_slot

    def writeState(self, state: bool) -> None:
        self.momOut.enable()
        self.momOut.select_output(self.board_slot)

        if not self.mcp.is_connected():
            self.momOut.deselect_output()
            self.momOut.disable()
            return

        # Re-assert direction every time, just as Digital_Input_Module does in
        # its __main__ block before each use. This ensures the chip is always
        # configured as outputs even after a power-cycle/reconnect.
        self.mcp.set_direction(0x00)  # all outputs
        self.mcp.set_pin(self.pin, bool(state))

        self.momOut.deselect_output()
        self.momOut.disable()

    def close(self) -> None:
        pass


if __name__ == "__main__":
    import time
    spi = spidev.SpiDev()
    spi.open(0, 0)
    resetPin = gpiozero.DigitalOutputDevice("GPIO26", initial_value=1)
    time.sleep(1)
    demux = SN54LS138_Demux(a_pin="GPIO17", b_pin="GPIO27", c_pin="GPIO22", g1_pin=None)
    mcp = GPIOEX(spi, hw_addr=0)
    rc = RELAY_CHANNEL(momOut=demux, mcp=mcp, card_slot=0, board_slot=5)

    time.sleep(3)
    print("Turning relay on")
    rc.writeState(True)
    time.sleep(3)
    print("Turning relay off")
    rc.writeState(False)
    time.sleep(3)

    rc.close()
    demux.close()
    spi.close()