# main.py
"""
Bootstrap the modular GUI application.
"""
import os
from pathlib import Path
import queue
 
from channel_manager import ChannelManager
from socket_controller import SocketController
from ui_app import SimulatorApp

if __name__ == "__main__":
    # determine paths
    current_dir = Path(__file__).resolve().parent
    config_path = current_dir / "config.json"

    # initialize channel manager and load config
    channel_mgr = ChannelManager()
    channel_mgr.load_from_config_file(config_file_path=str(config_path))

    # create shared response queue for SSM -> UI
    resp_queue = queue.Queue()

    # socket controller configuration
    # these defaults mimic your previous code; consider moving host/port into config.json
    host = "192.168.80.1"
    port = 5000

    # we can use the config manager to get socket timeout if you want; for now, use 3s default
    socket_ctrl = SocketController(host=host, port=port, socket_timeout_s=3, response_queue=resp_queue, enable_logging=True)

    # create and run the app
    app = SimulatorApp(config_path=config_path, channel_mgr=channel_mgr, socket_ctrl=socket_ctrl)
    app.run()
