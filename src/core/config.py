import sys
from pathlib import Path

class Config:
    """
    Global Proton-Coop configurations.

    This class centralizes all static configuration values for the application,
    including paths to critical directories, lists of required external commands,
    and timeout settings. It also provides utility methods for path management
    and data migration.

    Attributes:
        SCRIPT_DIR (Path): The root directory of the script, correctly identified
            whether running from source or a PyInstaller frozen executable.
        PROFILE_DIR (Path): The directory where game profile `.json` files are stored.
        LOG_DIR (Path): The directory for storing application logs.
        PREFIX_BASE_DIR (Path): The base directory under which all Wine prefixes
            for different games are created.
        STEAM_PATHS (list[Path]): A list of common paths where Steam libraries
            may be installed. Used to locate Proton versions.
        REQUIRED_COMMANDS (list[str]): A list of essential command-line tools
            that must be present on the system for the application to function.
        OPTIONAL_COMMANDS (list[str]): A list of optional command-line tools.
        PROCESS_START_TIMEOUT (int): Timeout in seconds for waiting for a
            game process to start.
        PROCESS_TERMINATE_TIMEOUT (int): Timeout in seconds for waiting for a
            process to terminate gracefully.
        SUBPROCESS_TIMEOUT (int): General timeout in seconds for running
            various subprocesses (e.g., `wineboot`, `winetricks`).
        FILE_IO_TIMEOUT (int): Timeout in seconds for file operations.
    """

    @staticmethod
    def _get_script_dir() -> Path:
        """
        Determines the script's root directory.

        This method correctly identifies the application's root directory regardless
        of whether it's being run from source or as a frozen executable packaged
        by PyInstaller. This is crucial for locating bundled resources.

        Returns:
            Path: The absolute path to the application's root directory.
        """
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running as a PyInstaller bundle
            return Path(sys._MEIPASS)
        else:
            # Running as a normal Python script
            return Path(__file__).parent.parent.parent

    SCRIPT_DIR: Path = _get_script_dir()
    PROFILE_DIR: Path = Path.home() / ".config/proton-coop/profiles"
    LOG_DIR: Path = Path.home() / ".cache/proton-coop/logs"
    PREFIX_BASE_DIR: Path = Path.home() / "Games/proton-coop/prefixes/"

    STEAM_PATHS: list[Path] = [
        Path.home() / ".steam/root",
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".steam/debian-installation",
    ]

    REQUIRED_COMMANDS: list[str] = ["bwrap", "gamescope"]
    OPTIONAL_COMMANDS: list[str] = []

    # Timeout configurations (in seconds)
    PROCESS_START_TIMEOUT: int = 30
    PROCESS_TERMINATE_TIMEOUT: int = 10
    SUBPROCESS_TIMEOUT: int = 15
    FILE_IO_TIMEOUT: int = 5

    @staticmethod
    def migrate_legacy_paths() -> None:
        """
        Migrates legacy storage paths to the current underscore-based naming convention.

        This definitive migration function scans both the prefix and profile
        directories for any names containing spaces or hyphens and renames them
        to use underscores. This ensures path safety and consistency. It prints
        warnings if a target path already exists and errors if a rename fails.
        """
        def _migrate_and_rename(path: Path):
            """Helper to rename a single path if needed."""
            original_name = path.name
            # Standardize to underscores, cleaning up spaces and hyphens
            new_name = original_name.replace(" ", "_").replace("-", "_")

            if original_name == new_name:
                return  # No migration needed

            new_path = path.parent / new_name
            if new_path.exists():
                print(
                    f"Warning: Cannot migrate '{original_name}' because target "
                    f"'{new_name}' already exists. Skipping.",
                    file=sys.stderr
                )
                return

            try:
                path.rename(new_path)
                print(f"Info: Migrated '{original_name}' to '{new_name}'.")
            except OSError as e:
                print(
                    f"Error: Could not migrate '{original_name}'. Error: {e}",
                    file=sys.stderr
                )

        # 1. Migrate Prefix Directories
        if Config.PREFIX_BASE_DIR.exists() and Config.PREFIX_BASE_DIR.is_dir():
            # Create a snapshot list, as we modify the directory while iterating
            for path in list(Config.PREFIX_BASE_DIR.iterdir()):
                if path.is_dir():
                    _migrate_and_rename(path)

        # 2. Migrate Profile Filenames
        if Config.PROFILE_DIR.exists() and Config.PROFILE_DIR.is_dir():
            for path in list(Config.PROFILE_DIR.glob('*.json')):
                _migrate_and_rename(path)

    @staticmethod
    def get_prefix_base_dir(game_name: str) -> Path:
        """
        Constructs the base prefix directory path for a specific game.

        This method ensures that the directory name for a game's prefixes is
        path-safe by replacing any spaces in the game name with underscores.

        Args:
            game_name (str): The name of the game.

        Returns:
            Path: The full, path-safe directory for the game's Wine prefixes.
        """
        safe_game_name = game_name.replace(" ", "_")
        return Config.PREFIX_BASE_DIR / safe_game_name
