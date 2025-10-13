import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import (BaseModel, ConfigDict, Field, ValidationError,
                      validator)

from ..core.config import Config
from ..core.exceptions import ExecutableNotFoundError, ProfileNotFoundError
from ..core.logger import Logger


class PlayerInstanceConfig(BaseModel):
    """
    Defines the specific configuration for a single player's game instance.

    This includes settings like in-game account name, language, and device
    bindings for mouse, keyboard, and audio, allowing for complete isolation
    between instances.

    Attributes:
        ACCOUNT_NAME (Optional[str]): The in-game account or profile name.
        LANGUAGE (Optional[str]): The language setting for the game instance.
        LISTEN_PORT (Optional[str]): Network port for the instance, if applicable.
        USER_STEAM_ID (Optional[str]): A unique Steam ID for the player.
        PHYSICAL_DEVICE_ID (Optional[str]): Identifier for the physical controller.
        MOUSE_EVENT_PATH (Optional[str]): The `/dev/input/event*` path for the mouse.
        KEYBOARD_EVENT_PATH (Optional[str]): The `/dev/input/event*` path for the keyboard.
        AUDIO_DEVICE_ID (Optional[str]): The audio sink device ID.
        monitor_id (Optional[str]): The specific monitor to display this instance on.
    """
    model_config = ConfigDict(populate_by_name=True)

    ACCOUNT_NAME: Optional[str] = Field(default=None, alias="ACCOUNT_NAME")
    LANGUAGE: Optional[str] = Field(default=None, alias="LANGUAGE")
    LISTEN_PORT: Optional[str] = Field(default=None, alias="LISTEN_PORT")
    USER_STEAM_ID: Optional[str] = Field(default=None, alias="USER_STEAM_ID")
    PHYSICAL_DEVICE_ID: Optional[str] = Field(default=None, alias="PHYSICAL_DEVICE_ID")
    MOUSE_EVENT_PATH: Optional[str] = Field(default=None, alias="MOUSE_EVENT_PATH")
    KEYBOARD_EVENT_PATH: Optional[str] = Field(default=None, alias="KEYBOARD_EVENT_PATH")
    AUDIO_DEVICE_ID: Optional[str] = Field(default=None, alias="AUDIO_DEVICE_ID")
    monitor_id: Optional[str] = Field(default=None, alias="MONITOR_ID")


class SplitscreenConfig(BaseModel):
    """
    Configuration for splitscreen mode.

    Attributes:
        orientation (str): The screen split orientation, either "horizontal"
            or "vertical".
    """
    model_config = ConfigDict(populate_by_name=True)
    orientation: str = Field(alias="ORIENTATION")

    @validator('orientation')
    def validate_orientation(cls, v):
        """Ensures orientation is either 'horizontal' or 'vertical'."""
        if v not in ["horizontal", "vertical"]:
            raise ValueError("Orientation must be 'horizontal' or 'vertical'.")
        return v


class GameProfile(BaseModel):
    """
    A comprehensive profile for launching a game with specific configurations.

    This model holds all the necessary settings to define how a game is launched,
    including the number of players, display settings, executable paths, and
    dependencies like Proton and Winetricks. It uses Pydantic for data
    validation and serialization.

    Attributes:
        game_name (str): The name of the game.
        exe_path (Optional[Path]): The path to the game's primary executable.
        proton_version (Optional[str]): The name of the Proton version to use.
        num_players (int): The total number of players for this session.
        instance_width (int): The base width of a single game instance window.
        instance_height (int): The base height of a single game instance window.
        app_id (Optional[str]): The Steam AppID of the game.
        game_args (Optional[str]): Command-line arguments to pass to the game.
        is_native (bool): Flag indicating if the game is a native Linux title.
        mode (Optional[str]): The launch mode (e.g., "splitscreen").
        splitscreen (Optional[SplitscreenConfig]): Splitscreen configuration.
        env_vars (Optional[Dict[str, str]]): Custom environment variables to set.
        player_configs (Optional[List[PlayerInstanceConfig]]): A list of configs
            for each player instance.
        selected_players (Optional[List[int]]): Indices of players to launch.
        apply_dxvk_vkd3d (bool): Whether to apply DXVK/VKD3D to the prefix.
        winetricks_verbs (Optional[List[str]]): A list of Winetricks verbs to run.
    """
    model_config = ConfigDict(populate_by_name=True)

    game_name: str = Field(..., alias="GAME_NAME")
    exe_path: Optional[Path] = Field(default=None, alias="EXE_PATH")
    proton_version: Optional[str] = Field(default=None, alias="PROTON_VERSION")
    num_players: int = Field(..., alias="NUM_PLAYERS")
    instance_width: int = Field(..., alias="INSTANCE_WIDTH")
    instance_height: int = Field(..., alias="INSTANCE_HEIGHT")
    app_id: Optional[str] = Field(default=None, alias="APP_ID")
    game_args: Optional[str] = Field(default=None, alias="GAME_ARGS")
    is_native: bool = Field(default=False, alias="IS_NATIVE")
    mode: Optional[str] = Field(default=None, alias="MODE")
    splitscreen: Optional[SplitscreenConfig] = Field(default=None, alias="SPLITSCREEN")
    env_vars: Optional[Dict[str, str]] = Field(default=None, alias="ENV_VARS")
    player_configs: Optional[List[PlayerInstanceConfig]] = Field(default=None, alias="PLAYERS")
    selected_players: Optional[List[int]] = Field(default=None, alias="selected_players")
    apply_dxvk_vkd3d: bool = Field(default=True, alias="APPLY_DXVK_VKD3D")
    winetricks_verbs: Optional[List[str]] = Field(default=None, alias="WINETRICKS_VERBS")

    @validator('game_name')
    def sanitize_game_name_for_paths(cls, v):
        """Replaces spaces with underscores to ensure it's a valid path component."""
        return v.replace(' ', '_')

    @validator('num_players')
    def validate_num_players(cls, v):
        """Validates that the number of players is between 1 and 4."""
        if not (1 <= v <= 4):
            raise ValueError("The number of players must be between 1 and 4.")
        return v

    @validator('exe_path')
    def validate_exe_path(cls, v, values):
        """Validates that the executable path exists, if provided."""
        if v is None:
            return v

        path_v = Path(v)
        if not path_v.exists() and str(path_v) != "":
            raise ExecutableNotFoundError(f"Game executable not found: {path_v}")
        return path_v

    @property
    def is_splitscreen_mode(self) -> bool:
        """Checks if the profile is configured for splitscreen mode."""
        return self.mode == "splitscreen"

    @property
    def effective_instance_width(self) -> int:
        """Calculates the effective width for an instance in splitscreen."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "horizontal":
            return self.instance_width // self.effective_num_players()
        return self.instance_width

    @property
    def effective_instance_height(self) -> int:
        """Calculates the effective height for an instance in splitscreen."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "vertical":
            return self.instance_height // self.effective_num_players()
        return self.instance_height

    @classmethod
    def load_from_file(cls, profile_path: Path) -> "GameProfile":
        """
        Loads and validates a game profile from a JSON file.

        Args:
            profile_path (Path): The path to the `.json` profile file.

        Returns:
            GameProfile: An instance of the GameProfile.

        Raises:
            ProfileNotFoundError: If the profile file does not exist.
            ValueError: If the file is not a valid JSON or fails validation.
        """
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_path}")

        if profile_path.suffix != '.json':
            raise ValueError(f"Unsupported profile file extension: {profile_path.suffix}.")

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ValueError(f"Error reading profile file {profile_path}: {e}")

        cls._process_profile_data(data)

        try:
            profile = cls(**data)
        except ValidationError as e:
            Logger("LinuxCoop", Config.LOG_DIR).error(f"Pydantic Validation Error for {profile_path}: {e.errors()}")
            raise ValueError(f"Profile data validation failed: {e}")
        except Exception as e:
            Logger("LinuxCoop", Config.LOG_DIR).error(f"Unexpected error creating profile from {profile_path}: {e}")
            raise

        return profile

    @classmethod
    def _process_profile_data(cls, data: Dict) -> None:
        """
        Pre-processes raw profile data before Pydantic validation.

        This method infers `is_native` from the executable path and sets
        `NUM_PLAYERS` based on the length of the `PLAYERS` list if it's not
        explicitly defined.

        Args:
            data (Dict): The raw dictionary data loaded from JSON.
        """
        exe_path_str = data.get('EXE_PATH')
        data['is_native'] = bool(exe_path_str and not exe_path_str.lower().endswith('.exe'))

        if 'NUM_PLAYERS' not in data and 'PLAYERS' in data and isinstance(data['PLAYERS'], list):
            data['NUM_PLAYERS'] = len(data['PLAYERS'])

    def effective_num_players(self) -> int:
        """Returns the number of players that will actually be launched."""
        return len(self.player_configs) if self.player_configs else 0

    @property
    def players_to_launch(self) -> List[PlayerInstanceConfig]:
        """Returns the list of player configurations to be launched."""
        return self.player_configs if self.player_configs else []

    def get_instance_dimensions(self, instance_num: int) -> Tuple[int, int]:
        """
        Calculates the dimensions (width, height) for a specific game instance.

        This method accounts for splitscreen configurations, dividing the
        total resolution among the players based on the orientation and player count.

        Args:
            instance_num (int): The 1-based index of the instance.

        Returns:
            Tuple[int, int]: A tuple containing the (width, height) for the instance.
        """
        if not self.is_splitscreen_mode or not self.splitscreen:
            return self.instance_width, self.instance_height

        orientation = self.splitscreen.orientation
        num_players = self.effective_num_players()

        if num_players < 1:
            return self.instance_width, self.instance_height # Fallback

        if num_players == 1:
            return self.instance_width, self.instance_height
        elif num_players == 2:
            if orientation == "horizontal":
                return self.instance_width // 2, self.instance_height
            else:
                return self.instance_width, self.instance_height // 2
        elif num_players == 3:
            if orientation == "horizontal":
                if instance_num == 1:
                    return self.instance_width, self.instance_height // 2
                else:
                    return self.instance_width // 2, self.instance_height // 2
            else:
                if instance_num == 1:
                    return self.instance_width // 2, self.instance_height
                else:
                    return self.instance_width // 2, self.instance_height // 2
        elif num_players == 4:
            return self.instance_width // 2, self.instance_height // 2
        else: # Fallback for 5+ players
            if orientation == "horizontal":
                return self.instance_width, self.instance_height // num_players
            else:
                return self.instance_width // num_players, self.instance_height

    def save_to_file(self, profile_path: Path):
        """
        Saves the current profile state to a JSON file.

        The output is a well-formatted JSON, using aliases for field names
        as defined in the model.

        Args:
            profile_path (Path): The path where the JSON file will be saved.
        """
        json_data = self.model_dump_json(by_alias=True, indent=4)
        profile_path.write_text(json_data, encoding='utf-8')
