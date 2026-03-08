# main.py
# created by Haddon Baker 10/7/25 with assistance from ChatGPT. Refactored from original simulator_gui.py for modularity
"""
Bootstrap the modular GUI application.
"""
import os
from pathlib import Path
import queue
from datetime import datetime, timedelta
 
from channel_manager import ChannelManager
from socket_controller import SocketController
from ui_app import SimulatorApp


def cleanup_old_logs(logs_dir, days_threshold=15):
    """
    Delete log files with 'instance_' prefix older than the specified number of days.
    Parses the date from the filename (instance_yyyy-mm-dd format).
    
    Args:
        logs_dir: Path to the logs directory
        days_threshold: Number of days; files older than this will be deleted
    """
    if not os.path.exists(logs_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_threshold)
    
    try:
        for filename in os.listdir(logs_dir):
            # Only process files starting with 'instance_'
            if not filename.startswith("instance_"):
                continue
            
            file_path = os.path.join(logs_dir, filename)
            
            # Only process files, not directories
            if not os.path.isfile(file_path):
                continue
            
            # Extract date from filename (instance_yyyy-mm-dd_...)
            try:
                date_str = filename.split("_")[1]  # Get 'yyyy-mm-dd' part
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Delete if file is older than threshold
                if file_date < cutoff_date:
                    os.remove(file_path)
                    print(f"Deleted old log file: {filename}")
            except (ValueError, IndexError):
                # Skip files that don't match expected naming convention
                continue
    except Exception as e:
        print(f"Error during log cleanup: {e}")

if __name__ == "__main__":
    # determine paths
    current_dir = Path(__file__).resolve().parent
    config_path = current_dir / "t_config.json"
    logs_dir = current_dir.parent / "logs"

    # cleanup old log files on startup
    cleanup_old_logs(str(logs_dir), days_threshold=15)

    # initialize channel manager and load config
    channel_mgr = ChannelManager() 
    channel_mgr.load_from_config_file(config_file_path=str(config_path))

    # create shared response queue for SSM -> UI
    resp_queue = queue.Queue()

    # socket controller configuration 
    # consider moving host/port into config.json
    host = "192.168.137.10"
    port = 5000

    # use 3s default
    socket_ctrl = SocketController(host=host, port=port, socket_timeout_s=3, response_queue=resp_queue, enable_logging=True)

    # create and run the app
    app = SimulatorApp(config_path=config_path, channel_mgr=channel_mgr, socket_ctrl=socket_ctrl)
    app.run()
