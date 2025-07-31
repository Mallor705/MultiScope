import sys
from pathlib import Path

class Config:
    """Global Linux-Coop configurations, including directories, commands, and Steam paths."""

    @staticmethod
    def _get_script_dir():
        """Get the script directory, handling PyInstaller frozen executable."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller bundle
            return Path(sys._MEIPASS)
        else:
            # Normal Python execution
            return Path(__file__).parent.parent.parent

    SCRIPT_DIR = _get_script_dir()
    PROFILE_DIR = Path.home() / ".config/linux-coop/profiles"
    LOG_DIR = Path.home() / ".cache/linux-coop/logs"
    PREFIX_BASE_DIR = Path.home() / "Games/linux-coop/prefixes/"

    STEAM_PATHS = [
        Path.home() / ".steam/root",
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".steam/debian-installation",
        Path.home() / ".steam/steam/root",
        Path.home() / ".steam/steam/steamapps",
        Path.home() / ".local/share/Steam/steamapps",
        Path.home() / ".local/share/Steam/steamapps/common",
    ]

    REQUIRED_COMMANDS = ["gamescope", "bwrap"]

    # Timeout configurations (in seconds)
    PROCESS_START_TIMEOUT = 30
    PROCESS_TERMINATE_TIMEOUT = 10
    SUBPROCESS_TIMEOUT = 15
    FILE_IO_TIMEOUT = 5

    @staticmethod
    def get_prefix_base_dir(game_name: str) -> Path:
        """Returns the base prefix directory for a specific game."""
        return Config.PREFIX_BASE_DIR / game_name
