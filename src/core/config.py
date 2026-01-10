import os
import sys
from pathlib import Path


class Config:
    """
    Global Twinverse configurations.
    """

    APP_NAME = "twinverse"

    @staticmethod
    def _get_script_dir() -> Path:
        # Access attributes on `sys` using getattr to avoid direct attribute
        # access that static checkers may flag.
        frozen = getattr(sys, "frozen", False)
        meipass = getattr(sys, "_MEIPASS", None)
        if frozen and meipass:
            return Path(meipass)
        return Path(__file__).parent.parent.parent

    SCRIPT_DIR: Path = _get_script_dir()
    APP_DIR: Path = Path(__file__).parent.parent.parent

    LOCAL_DIR: Path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / APP_NAME
    CONFIG_DIR: Path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
    LOG_DIR: Path = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_NAME / "logs"

    @staticmethod
    def get_profile_path() -> Path:
        """Returns the path to the default profile JSON file."""
        return Config.CONFIG_DIR / "profile.json"

    @staticmethod
    def get_steam_home_path(instance_num: int) -> Path:
        """Returns the isolated Steam home path for a given instance."""
        return Config.LOCAL_DIR / f"home_{instance_num + 1}"
