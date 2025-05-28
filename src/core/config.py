from pathlib import Path
from typing import List

class Config:
    SCRIPT_DIR = Path(__file__).parent.parent.parent
    PROFILE_DIR = SCRIPT_DIR / "profiles"
    LOG_DIR = Path.home() / ".local/share/linux-coop/logs"
    PREFIX_BASE_DIR = Path.home() / ".local/share/linux-coop/prefixes"
    
    STEAM_PATHS = [
        Path.home() / ".steam/root",
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".steam/debian-installation",
        Path("/var/mnt/games/messi/Games/Steam")
    ]
    
    REQUIRED_COMMANDS = ["gamescope", "bwrap"]
    
    @classmethod
    def get_profile_path(cls, profile_name: str) -> Path:
        return cls.PROFILE_DIR / f"{profile_name}.profile"