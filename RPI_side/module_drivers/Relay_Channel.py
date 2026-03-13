import gpiozero
import spidev

class RELAY_CHANNEL:
    def __init__(self, mcp=None, pin: int | None = None):
        # Can operate with an MCP23S08 expander (preferred) or a direct gpiozero output device
        self.mcp = mcp
        self.pin = pin

    def writeState(self, state: bool) -> None:
        if self.mcp is not None and self.pin is not None:
            self.mcp.write_pin(self.pin, bool(state))
        else:
            raise RuntimeError("RELAY_CHANNEL has no output interface configured")

    def close(self) -> None:
        pass

if __name__ == "__main__":
    p = gpiozero.DigitalOutputDevice("GPIO6")
    rc = RELAY_CHANNEL(gpio_out_pin = p)
    
    import time
    rc.writeState(True)
    time.sleep(3)
    rc.writeState(False)
    time.sleep(3)
    p.close()
