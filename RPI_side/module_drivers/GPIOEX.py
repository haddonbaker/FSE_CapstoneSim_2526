import spidev
import time
import gpiozero # because RPi.GPIO is unsupported on RPi5

class GPIOEX:
    # Register addresses
    IODIR = 0x00
    IPOL = 0x01
    GPINTEN = 0x02
    DEFVAL = 0x03
    INTCON = 0x04
    IOCON = 0x05
    GPPU = 0x06
    INTF = 0x07
    INTCAP = 0x08
    GPIO = 0x09
    OLAT = 0x0A

    def __init__(self, spidev, hw_addr=0):
        max_speed=1000000
        self.resetPin = gpiozero.DigitalOutputDevice("GPIO26", initial_value =1 )
        self.spi = spidev
        self.spi.max_speed_hz = max_speed
        

        self.hw_addr = hw_addr & 0x03

        self.opcode_write = 0x40 | (self.hw_addr << 1)
        self.opcode_read = 0x41 | (self.hw_addr << 1)
        

    def reset(self):
        self.resetPin.off()
        time.sleep(0.1)
        self.resetPin.on()
        time.sleep(0.1)
        self.resetPin.close()

    def _write_reg(self, reg, value):
        self.spi.xfer2([self.opcode_write, reg, value])

    def _read_reg(self, reg):
        resp = self.spi.xfer2([self.opcode_read, reg, 0x00])
        return resp[2]

    def set_direction(self, mask):
        """1=input, 0=output"""
        self._write_reg(self.IODIR, mask)

    def enable_pullups(self, mask):
        self._write_reg(self.GPPU, mask)

    def write_gpio(self, value):
        self._write_reg(self.GPIO, value)

    def read_gpio(self):
        return self._read_reg(self.GPIO)

    def set_pin(self, pin, value):
        current = self._read_reg(self.OLAT)

        if value:
            current |= (1 << pin)
        else:
            current &= ~(1 << pin)

        self._write_reg(self.GPIO, current)

    def read_pin(self, pin):
        value = self._read_reg(self.GPIO)
        return (value >> pin) & 1

    def set_pin_direction(self, pin, input=True):
        """Set a single pin direction: True=input, False=output."""
        direction = self._read_reg(self.IODIR)
        if input:
            direction |= (1 << pin)
        else:
            direction &= ~(1 << pin)
        self._write_reg(self.IODIR, direction)

    def test_input_pin0_read(self):
        """Test helper: configure GPIO0 as input with pull-up and read value."""
        self.set_pin_direction(0, input=True)
        self.enable_pullups(1 << 0)
        value = self.read_pin(0)
        print(f"MCP23S08 GPIO0 input read = {value}")
        return value

    def close(self):
        self.spi.close()


# ------------------------
# Test code
# ------------------------
if __name__ == "__main__":
    spi = spidev.SpiDev()
    spi.open(0, 0)  # Open SPI bus 0, device 0 (CE0)    
    mcp = GPIOEX(spidev=spi, hw_addr=0)

    # Set all pins as outputs
    mcp.set_direction(0x00)

    # Blink all pins
    try:
        while True:
            mcp.write_gpio(0xFF)  # All HIGH
            time.sleep(1)
            mcp.write_gpio(0x00)  # All LOW
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    mcp.close()