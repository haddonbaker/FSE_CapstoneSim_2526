import sys
sys.path.insert(0, "/home/fsesim/fresh") # allow this file to find other project modules

# these lines to free any previous lgpio resources. see https://forums.raspberrypi.com/viewtopic.php?t=362014
import gpiozero

class INDICATOR_LIGHT:
    '''controls a status light on the outside of the simulator box'''
    def __init__(self, led_pin: gpiozero.LED):
        self.led_pin = led_pin
        # self.led_obj = gpiozero.LED(self.gpio_cs_pin, active_high=True, initial_value=False)
    
    def setBlink(self, on_time=1, off_time=1):
        # configure the led to blink forever with for a given on_time and off_time
        self.led_pin.blink(on_time=on_time, off_time=off_time, n=None, background=True)
    
    def turnOn(self):
        self.led_pin.on()

    def turnOff(self):
        self.led_pin.off()
    
    def close(self) -> None:
        self.led_pin.close()
    
    def __str__(self) -> str:
        return f"Indicator Light driver assigned to LED pin: {self.led_pin}"

if __name__ == "__main__":
    import time
    # Create LED objects for pins 5 and 6
    led5 = gpiozero.LED(5)
    led6 = gpiozero.LED(6)
    light5 = INDICATOR_LIGHT(led5)
    light6 = INDICATOR_LIGHT(led6)
    # Turn on pin 5
    print("Turning on GPIO pin 5")
    light5.turnOn()
    time.sleep(2)
    # Turn off pin 5
    print("Turning off GPIO pin 5")
    light5.turnOff()
    time.sleep(1)
    # Turn on pin 6
    print("Turning on GPIO pin 6")
    light6.turnOn()
    time.sleep(2)
    # Turn off pin 6
    print("Turning off GPIO pin 6")
    light6.turnOff()
    # Close
    light5.close()
    light6.close()