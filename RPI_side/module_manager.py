from typing import Union, Tuple
import warnings
import gpiozero
import time
import spidev
import SN54LS138_Demux
import sys
sys.path.append("..") # include parent directory in path

from PacketBuilder import dataEntry, errorEntry
from PacketBuilder_utils import card_pos_from_logical_id, chType_from_logical_id, slot_from_logical_id, spi_from_logical_id
from gpio_manager import GPIO_Manager
from module_drivers.T_Click_1 import T_CLICK_1
from module_drivers.Digital_Input_Module import Digital_Input_Module
from module_drivers.R_Click import R_CLICK
from module_drivers.Relay_Channel import RELAY_CHANNEL
from module_drivers.Indicator_Light import INDICATOR_LIGHT


# initialize Demuxes for controlling the chip select lines
# motherboard out demux - analog and digital output modules - T_CLICK_1 and RELAY_CHANNEL
momOut = SN54LS138_Demux("GPIO17","GPIO27","GPIO22","GPIO7") # (demux1, output select)
# currently going to g1, should be going to g2

# motherboard in demux - analog and digital input modules - R_CLICK and Digital_Input_Module 
momIn = SN54LS138_Demux("GPIO23","GPIO24","GPIO25","GPIO18") # (demux2, input select)

# carrier board demux for selecting between the 8 possible modules on the carrier board. 
car = SN54LS138_Demux("GPIO2","GPIO3","GPIO4") # (demux3, carrier board select) - this is only needed if we have more than 8 modules, which we don't yet. We can hardcode the carrier board selection for now and add this later if we need it.
# no g1 because it comes from motherboard

class Module_Manager:
    # maintain a list of modules (e.g. R_CLICK, COMPARATOR_CLICK)
    #  initiated by the master, over the socket 
    # has an instance of GPIO_manager to allocate GPIOs to serve as 
    #  chip selects and digital inputs for the modules

    # also responsible for creating a module if not exist yet
    # or to write a value to a module at the specified gpio pin

    def __init__(self, spi : spidev.SpiDev):
        self.spi = spi
        self.module_dict = dict() # checks if logic string is already in the dict, like "SPIx_CARDx_SLOTx"
        self.gpio_manager = GPIO_Manager() # initialize to empty at first
    
    def execute_command(self, logical_id: str, chType: str, val: float | int) -> Tuple[dataEntry, list[errorEntry]]:
        '''
        Executes a command from the socket, given the module's gpio string, channel type, and value.  This class
        is responsible for choosing the appropriate driver instance for the requested channel and for allocating
        a gpio reservation with self.gpio_manager.
        If `chType` is "ai", then the `val` (int) will be interpreted as the number of measurements to average 
        (LPF) before returning a value
        This method can also return multiple error entries. See the implementation for details.

        :param str gpio_str: the gpio string of the module (e.g. "GPIO13")
        :param str chType: one of ["ao", "ai", "di", "do"]
        :param float|int val: the value to write to the module
        '''
        if logical_id not in self.module_dict:
            print(f"[Module_Manager] making a module entry for {logical_id} as a {chType}")
            self.make_module_entry(gpio_str = logical_id, chType = chType)
            print(f"[module_manager] made a new module entry. module_dict is now {self.module_dict}")

        driverObj = self.module_dict.get(logical_id)[1] # second element in value list is the driver object
        print(f"[module_manager] driverObj is {driverObj}")
        
        valueResponse = None # we will update these later
        errorResponse_list = []

        # first element is the channel type
        if chType.lower() == "ao": # then it's a T_CLICK_1 instance
            try:
                driverObj.write_mA(val)
            except Exception as e:
                errorResponse_list.append(errorEntry(source = "ao", criticalityLevel = "High", description = f"{e}. Encountered unexpected exception:{gpio_str}"))
                        
            # don't update the valueResponse with anything. This is no ao signal, so don't return anything
        elif chType.lower() == "ai": # then it's an R_CLICK instance
            # the ai adc readings can be noisy, so do a simple average to attenuate noise
            numMeasurements = max(int(val), 1) # at least one measurement
            sum = 0
            for _ in range(numMeasurements):
                sum += driverObj.read_mA()
                
            ma_reading = sum / numMeasurements
            valueResponse = dataEntry( logical_id = logical_id, val = ma_reading, time = time.time())

            if ma_reading == 0: # there is always a small amount of random noise that can be read on the adc chip to indicate a valid SPI connection
                errorResponse_list.append(errorEntry(source = "ai", criticalityLevel = "High", description = f"SPI communication error detected:{gpio_str}"))

        elif chType.lower() == "do": # then it's a relay channel instance
            print("[module_manager] entered do branch to write val: {bool(val)}")
            driverObj.writeState(state = bool(val))
            # don't update either the value response or the error response list
        elif chType.lower() == "di": # then it's a comparator channel instance
            di_value = int(driverObj.readState())
            valueResponse = dataEntry(logical_id = logical_id, val = di_value, time = time.time())

        # the "in" chtype is not controlled by packet data. The RPi locally controls the indicator lights, but
        # we still need the GUI to tell the RPi which GPIO pin the lights are using
        elif chType.lower() == "in": # indicator light
            # different indication modes: 2:blink rapidly, 1:solid on, 0:off
            if val==2:
                driverObj.setBlink(on_time=0.3, off_time=0.3)
            elif val==1:
                driverObj.turnOn()
            elif val==0:
                driverObj.turnOff()
            valueResponse = None
            errorResponse_list.append(errorEntry(source = "Module Manager", criticalityLevel = "Medium", description = "The indicator light channel is reserved. Any commands from master will be ignored."))
        else:
            valueResponse = None
            errorResponse_list.append(errorEntry(source = "Module Manager", criticalityLevel = "Medium", description = f"Invalid channel type given {chType} for module at {gpio_str}."))

        return (valueResponse, errorResponse_list)


    def make_module_entry(self, logical_id: str, chType: str):
        # add an entry to the dictionary because it doesn't exist yet.
        # Also need to request the gpio_manager to add a GPIO object to itself
        self.gpio_manager.put_gpio(logical_id, chType = chType)
        print(f"[module_manager.make_module_entry] after put_gpio, list is {self.gpio_manager.gpio_dict}")

        # now create a driver object for the module of the correct type
        if chType.lower() == "ai":
            driverObj = R_CLICK(gpio_cs_pin = self.gpio_manager.get_gpio(logical_id),
                                spi = self.spi)
        elif chType.lower() == "ao":
            driverObj = T_CLICK_1(demux_controller = momOut, card_controller=car, card_pos = card_pos_from_logical_id(logical_id),demux_output = slot_from_logical_id(logical_id), spi = spi_from_logical_id(logical_id))
        
        elif chType.lower() == "di":
            driverObj = Digital_Input_Module(gpio_in_pin = self.gpio_manager.get_gpio(logical_id))
        elif chType.lower() == "do":
            driverObj = RELAY_CHANNEL(gpio_out_pin = self.gpio_manager.get_gpio(logical_id))
        elif chType.lower() == "in": # this channel is not writable by the master. We include it here so that the 
            # Pi can initialize it at its own startup
            driverObj = INDICATOR_LIGHT(led_pin = self.gpio_manager.get_gpio(logical_id))
        else:
            driverObj = None
            warnings.warn(f"[module_manager] Invalid channel type {chType}")
        print(f"[Module_Manager make_module_entry] will insert key {logical_id} with values {chType} and {driverObj}")
        self.module_dict[logical_id] = [chType, driverObj]
        print(f"[module_manager.make_module_entry] new module_dict is {self.module_dict}")
    
    def release_all_modules(self):
        for chType, driver_obj in self.module_dict.values():
            driver_obj.close()

        self.gpio_manager.release_all_gpios()
        self.module_dict.clear()

