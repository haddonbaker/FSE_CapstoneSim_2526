# socket_controller.py
"""
SocketController: wraps SocketSenderManager and exposes only the methods
used by the GUI. Keeps the GUI code independent of the SocketSenderManager API.
"""
import queue
import time
from typing import Tuple
from SocketSenderManager import SocketSenderManager  # existing module
# keep imports of dataEntry/errorEntry out of this module to avoid tight coupling with GUI;
# we only pass through whatever the SSM expects/returns.

class SocketController:
    def __init__(self, host: str, port: int, socket_timeout_s: float = 3.0, response_queue: queue.Queue | None = None, enable_logging: bool = True):
        self.q = response_queue if response_queue is not None else queue.Queue()
        self.ssm = SocketSenderManager(host=host, port=port, q=self.q,
                                       socketTimeout=socket_timeout_s,
                                       testSocketOnInit=False,
                                       loopDelay=1,
                                       log=enable_logging)
    # Expose the needed SSM API used by the GUI
    def place_single_mA(self, ch2send, mA_val: float, time: float | None = None) -> Tuple[bool, str|None]:
        t = time if time is not None else time
        return self.ssm.place_single_mA(ch2send=ch2send, mA_val=mA_val, time=time)

    def place_single_EngineeringUnits(self, ch2send, val_in_eng_units, time: float | None = None) -> Tuple[bool, str|None]:
        return self.ssm.place_single_EngineeringUnits(ch2send=ch2send, val_in_eng_units=val_in_eng_units, time=time)

    def place_ramp(self, ch2send, start_mA: float, stop_mA: float, stepPerSecond_mA: float) -> bool:
        return self.ssm.place_ramp(ch2send=ch2send, start_mA=start_mA, stop_mA=stop_mA, stepPerSecond_mA=stepPerSecond_mA)

    def clear_all_entries_with_gpio_str(self, gpio_str: str) -> int:
        return self.ssm.clearAllEntriesWithGPIOStr(gpio_str)

    def close(self):
        # terminate the ssm thread and clear queue
        try:
            self.ssm.close()
        except Exception:
            pass

    @property
    def response_queue(self):
        return self.q

    # The original code adjusts ssm.loopDelay after creating SSM instance. Provide proxy.
    @property
    def loop_delay(self):
        return getattr(self.ssm, "loopDelay", None)

    @loop_delay.setter
    def loop_delay(self, v):
        if hasattr(self.ssm, "loopDelay"):
            setattr(self.ssm, "loopDelay", v)
