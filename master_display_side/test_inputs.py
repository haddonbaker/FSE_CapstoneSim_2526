import threading
import time
import queue
import math
import random
from pathlib import Path

# Import necessary classes from the project
from channel_manager import ChannelManager
from socket_controller import SocketController
from ui_app import SimulatorApp
from PacketBuilder import dataEntry

def input_simulator(resp_queue, channel_mgr, stop_event):
    """
    Simulates incoming data from the RPi by injecting dataEntry objects
    into the response queue.
    """
    print("Starting input simulation thread...")
    t0 = time.time()
    
    while not stop_event.is_set():
        current_time = time.time()
        elapsed = current_time - t0
        
        # Iterate through all channels to generate fake data
        for name, ch in channel_mgr.channels.items():
            logical_id = ch.get_logical_id()
            if not logical_id:
                continue

            if ch.sig_type.lower() == "ai":
                # Simulate Analog Input: Sine wave oscillating between 4mA and 20mA
                # Period of ~10 seconds
                val_mA = 12.0 + 8.0 * math.sin(2 * math.pi * elapsed / 10.0)
                
                # Add random noise (+/- 0.05 mA)
                val_mA += random.uniform(-0.05, 0.05)
                
                # Clamp values to valid range
                val_mA = max(4.0, min(20.0, val_mA))
                
                # Create data entry (GUI expects mA for AI)
                entry = dataEntry(
                    logical_id=logical_id,
                    val=val_mA,
                    time=current_time
                )
                resp_queue.put(entry)

            elif ch.sig_type.lower() == "di":
                # Simulate Digital Input: Toggle every 3 seconds
                # Offset phase based on name length to make them blink differently
                offset = len(name)
                is_on = ((elapsed + offset) % 2) < 1 # 1 second on, 1 second off
                
                val = 1 if is_on else 0
                
                entry = dataEntry(
                    logical_id=logical_id,
                    val=val,
                    time=current_time
                )
                resp_queue.put(entry)
        
        # Update rate: 10 Hz (every 0.1 seconds)
        time.sleep(0.1)

if __name__ == "__main__":
    # Determine paths
    current_dir = Path(__file__).resolve().parent
    config_path = current_dir / "default_config.json"
    
    # Initialize Channel Manager and load config
    channel_mgr = ChannelManager()
    if config_path.exists():
        channel_mgr.load_from_config_file(str(config_path))
        print(f"Loaded configuration from {config_path}")
    else:
        print(f"Warning: {config_path} not found. Using empty configuration.")

    # Create the shared queue for responses
    resp_queue = queue.Queue()
    
    # Initialize SocketController
    # We use a dummy IP since we are simulating inputs locally.
    # The socket controller will try to connect and fail, but we ignore that for this test.
    socket_ctrl = SocketController(
        host="127.0.0.1", 
        port=5000, 
        socket_timeout_s=0.1, 
        response_queue=resp_queue,
        enable_logging=False
    )
    
    # Start the simulation thread
    stop_event = threading.Event()
    sim_thread = threading.Thread(
        target=input_simulator, 
        args=(resp_queue, channel_mgr, stop_event),
        daemon=True
    )
    sim_thread.start()
    
    print("Simulation running. Close the GUI window to stop.")

    # Create and run the App
    try:
        app = SimulatorApp(config_path=config_path, channel_mgr=channel_mgr, socket_ctrl=socket_ctrl)
        app.run()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Cleanup
        stop_event.set()
        socket_ctrl.close()