import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Dict

from ..core.config import Config
from ..core.logger import Logger
from ..models.game import Game
from ..models.profile import Profile
from .handler_parser import HandlerParser


class GameManager:
    """
    Manages the game and profile library stored on the file system.

    This service abstracts all file operations related to creating, reading,
    updating, and deleting games and their associated profiles. It enforces
    the new directory structure: `~/.config/proton-coop/games/[game_name]/`.
    """

    def __init__(self, logger: Logger):
        self.logger = logger
        self.games_dir = Config.GAMES_DIR
        self.games_dir.mkdir(parents=True, exist_ok=True)
        self.handler_parser = HandlerParser(logger)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Creates a safe filename from a game or profile name."""
        return name.strip().replace(" ", "_").lower()

    def get_game_dir(self, game_name: str) -> Path:
        """Returns the specific directory for a given game."""
        return self.games_dir / self._sanitize_filename(game_name)

    def get_profiles_dir(self, game_name: str) -> Path:
        """Returns the profiles directory for a given game."""
        return self.get_game_dir(game_name) / "profiles"

    def get_games(self) -> List[Game]:
        """Scans the games directory and loads all found games."""
        games = []
        for game_dir in self.games_dir.iterdir():
            if game_dir.is_dir():
                game_file = game_dir / "game.json"
                if game_file.exists():
                    try:
                        game = Game.load_from_file(game_file)
                        games.append(game)
                    except Exception as e:
                        self.logger.error(f"Failed to load game from {game_file}: {e}")
        return sorted(games, key=lambda g: g.game_name)

    def get_game_by_name(self, game_name: str) -> Optional[Game]:
        """Finds and loads a single game by its name."""
        safe_name = self._sanitize_filename(game_name)
        game_dir = self.games_dir / safe_name
        game_file = game_dir / "game.json"
        if game_file.exists():
            try:
                return Game.load_from_file(game_file)
            except Exception as e:
                self.logger.error(f"Failed to load game '{game_name}' from {game_file}: {e}")
        return None

    def get_profiles(self, game: Game) -> List[Profile]:
        """Loads all profiles for a specific game, excluding the default."""
        profiles_dir = self.get_profiles_dir(game.game_name)
        if not profiles_dir.exists():
            return []

        profiles = []
        for profile_file in profiles_dir.glob("*.json"):
            if profile_file.stem.lower() != 'default':
                try:
                    profile = Profile.load_from_file(profile_file)
                    profiles.append(profile)
                except Exception as e:
                    self.logger.error(f"Failed to load profile from {profile_file}: {e}")
        return sorted(profiles, key=lambda p: p.profile_name)

    def get_profile(self, game: Game, profile_name: str) -> Optional[Profile]:
        """Loads a single profile by name for a specific game."""
        profiles_dir = self.get_profiles_dir(game.game_name)
        profile_filename = f"{self._sanitize_filename(profile_name)}.json"
        profile_path = profiles_dir / profile_filename
        if profile_path.exists():
            try:
                return Profile.load_from_file(profile_path)
            except Exception as e:
                self.logger.error(f"Failed to load profile '{profile_name}' from {profile_path}: {e}")
        return None

    def save_game(self, game: Game):
        """Saves a game's data to its game.json file."""
        game_dir = self.get_game_dir(game.game_name)
        game_file = game_dir / "game.json"
        game.save_to_file(game_file)
        self.logger.info(f"Game '{game.game_name}' saved to {game_file}.")

    def save_profile(self, game: Game, profile: Profile):
        """Saves a profile to a JSON file within its game's directory."""
        profiles_dir = self.get_profiles_dir(game.game_name)
        profile_filename = f"{self._sanitize_filename(profile.profile_name)}.json"
        profile_path = profiles_dir / profile_filename
        profile.save_to_file(profile_path)
        self.logger.info(f"Profile '{profile.profile_name}' for game '{game.game_name}' saved to {profile_path}.")

    def _extract_and_parse_handler(self, archive_path: Path) -> (Dict, str):
        """Extracts and parses the handler.js file from a game archive."""
        temp_dir = tempfile.mkdtemp(prefix="proton-coop-")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        handler_js_path = Path(temp_dir) / "handler.js"
        if not handler_js_path.exists():
            raise FileNotFoundError("handler.js not found in the archive.")

        handler_data = self.handler_parser.parse_handler(handler_js_path)
        if not handler_data:
            raise ValueError("Failed to parse handler.js.")

        return handler_data, temp_dir


    def add_game_from_archive(self, archive_path: Path, exe_path: Path, game_cwd: Path) -> Game:
        """Adds a new game from a .nc or .zip archive."""
        handler_data, temp_dir = self._extract_and_parse_handler(archive_path)

        # Calculate the relative path for exe_path
        relative_exe_path = str(exe_path.relative_to(game_cwd))

        new_game = Game(
            game_name=handler_data.get("GameName"),
            exe_path=relative_exe_path,
            game_cwd=game_cwd,
            guid=handler_data.get("GUID"),
            app_id=handler_data.get("SteamID"),
            executable_to_launch=handler_data.get("ExecutableToLaunch"),
            launcher_exe=handler_data.get("LauncherExe"),
            symlink_game=handler_data.get("SymlinkGame", True),
            symlink_exe=handler_data.get("SymlinkExe", False),
            symlink_folders=handler_data.get("SymlinkFolders", False),
            keep_symlink_on_exit=handler_data.get("KeepSymLinkOnExit", True),
            symlink_files=handler_data.get("SymlinkFiles", []),
            copy_files=handler_data.get("CopyFiles", []),
            hardcopy_game=handler_data.get("HardcopyGame", False),
            hardlink_game=handler_data.get("HardlinkGame", False),
            force_symlink=handler_data.get("ForceSymlink", False),
            dir_symlink_exclusions=handler_data.get("DirSymlinkExclusions", []),
            file_symlink_exclusions=handler_data.get("FileSymlinkExclusions", []),
            file_symlink_copy_instead=handler_data.get("FileSymlinkCopyInstead", []),
            dir_symlink_copy_instead=handler_data.get("DirSymlinkCopyInstead", []),
            dir_symlink_copy_instead_include_sub_folders=handler_data.get("DirSymlinkCopyInsteadIncludeSubFolders", False),
        )
        self.add_game(new_game)
        self._move_handler_files(new_game, temp_dir)

        return new_game

    def add_game(self, game: Game) -> None:
        """Adds a new game to the library and creates a default profile."""
        game_dir = self.get_game_dir(game.game_name)
        if game_dir.exists():
            raise FileExistsError(f"A game with the name '{game.game_name}' already exists.")

        # Create directories and save the game file
        profiles_dir = self.get_profiles_dir(game.game_name)
        profiles_dir.mkdir(parents=True, exist_ok=True)
        self.save_game(game)

        # Create a default profile
        default_profile = Profile(profile_name="Default")
        self.save_profile(game, default_profile)

        self.logger.info(f"Added new game '{game.game_name}' at {game_dir} with a default profile.")

    def _move_handler_files(self, game: Game, temp_dir: str):
        """Moves the handler files to the game directory."""
        handler_dir = self.get_game_dir(game.game_name) / "handler"
        shutil.move(temp_dir, handler_dir)
        self.logger.info(f"Moved handler files to {handler_dir}")

    def add_profile(self, game: Game, profile: Profile) -> None:
        """Adds a new profile to a game."""
        profiles_dir = self.get_profiles_dir(game.game_name)
        profile_filename = f"{self._sanitize_filename(profile.profile_name)}.json"
        profile_path = profiles_dir / profile_filename

        if profile_path.exists():
            raise FileExistsError(f"A profile with the name '{profile.profile_name}' already exists for this game.")

        self.save_profile(game, profile)
        self.logger.info(f"Added new profile '{profile.profile_name}' to game '{game.game_name}'.")

    def delete_game(self, game: Game):
        """Deletes a game and all its associated profiles."""
        game_dir = self.get_game_dir(game.game_name)
        if game_dir.exists():
            shutil.rmtree(game_dir)
            self.logger.info(f"Deleted game '{game.game_name}' and all its data from {game_dir}.")
        else:
            self.logger.warning(f"Attempted to delete non-existent game directory: {game_dir}")

    def delete_profile(self, game: Game, profile: Profile):
        """Deletes a specific profile from a game."""
        profiles_dir = self.get_profiles_dir(game.game_name)
        profile_filename = f"{self._sanitize_filename(profile.profile_name)}.json"
        profile_path = profiles_dir / profile_filename

        if profile_path.exists():
            profile_path.unlink()
            self.logger.info(f"Deleted profile '{profile.profile_name}' from game '{game.game_name}'.")
        else:
            self.logger.warning(f"Attempted to delete non-existent profile file: {profile_path}")
