# channel_manager.py
# created by Haddon Baker 10/7/25 with assistance from ChatGPT. Refactored from original simulator_gui.py for modularity
"""
ChannelManager: thin wrapper around the Channel_Entries class.
This keeps the rest of the app decoupled from direct imports of the
channel_definitions module and gives us a place to add helpers later.
"""
from pathlib import Path
from typing import Optional
from channel_definitions import Channel_Entries  # existing module in parent project


class ChannelManager:
    def __init__(self):
        self._channels = Channel_Entries()

    def load_from_config_file(self, config_file_path: str | Path) -> None:
        self._channels.load_from_config_file(config_file_path=str(config_file_path))

    @property
    def channels(self):
        return self._channels.channels

    def get_channel_entry(self, sigName: str):
        # wrapper for existing method naming
        return self._channels.getChannelEntry(sigName)

    def get_channel_from_gpio(self, gpio_str: str):
        return self._channels.get_channelEntry_from_GPIOstr(gpio_str)
