import json
from pathlib import Path
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Tuple

from ..core.exceptions import ProfileNotFoundError, ExecutableNotFoundError
from ..core.cache import get_cache

class PlayerInstanceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    """Specific configurations for a player instance."""
    ACCOUNT_NAME: Optional[str] = Field(default=None, alias="ACCOUNT_NAME")
    LANGUAGE: Optional[str] = Field(default=None, alias="LANGUAGE")
    LISTEN_PORT: Optional[str] = Field(default=None, alias="LISTEN_PORT")
    USER_STEAM_ID: Optional[str] = Field(default=None, alias="USER_STEAM_ID")
    PHYSICAL_DEVICE_ID: Optional[str] = Field(default=None, alias="PHYSICAL_DEVICE_ID")
    MOUSE_EVENT_PATH: Optional[str] = Field(default=None, alias="MOUSE_EVENT_PATH")
    KEYBOARD_EVENT_PATH: Optional[str] = Field(default=None, alias="KEYBOARD_EVENT_PATH")
    AUDIO_DEVICE_ID: Optional[str] = Field(default=None, alias="AUDIO_DEVICE_ID")

class SplitscreenConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    """Splitscreen mode configuration."""
    orientation: str = Field(alias="ORIENTATION")

    @validator('orientation')
    def validate_orientation(cls, v):
        if v not in ["horizontal", "vertical"]:
            raise ValueError("Orientation must be 'horizontal' or 'vertical'.")
        return v

class GameProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    """Game profile model, containing configurations and validations for multi-instance execution."""
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

    # New field for player configurations, using "PLAYERS" alias for JSON
    player_configs: Optional[List[PlayerInstanceConfig]] = Field(default=None, alias="PLAYERS")

    @validator('num_players')
    def validate_num_players(cls, v):
        """Validates if the number of players is supported (minimum 1, maximum 4)."""
        if not (1 <= v <= 4):
            raise ValueError("The number of players must be between 1 and 4.")
        return v

    @validator('exe_path')
    def validate_exe_path(cls, v, values):
        """Validates if the executable path exists, if provided."""
        if v is None: # Allow None for optional exe_path
            return v

        path_v = Path(v)
        cache = get_cache()
        if not cache.check_path_exists(path_v):
            # Only raise error if path is not empty and not found
            if str(path_v) != "":
                raise ExecutableNotFoundError(f"Game executable not found: {path_v}")
        return path_v # Returns the Path object

    @property
    def is_splitscreen_mode(self) -> bool:
        """Checks if it is in splitscreen mode."""
        return self.mode == "splitscreen"

    @property
    def effective_instance_width(self) -> int:
        """Returns the effective instance width, divided if it is horizontal splitscreen."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "horizontal":
            return self.instance_width // self.effective_num_players
        return self.instance_width

    @property
    def effective_instance_height(self) -> int:
        """Returns the effective instance height, divided if it is vertical splitscreen."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "vertical":
            return self.instance_height // self.effective_num_players
        return self.instance_height

    @classmethod
    def load_from_file(cls, profile_path: Path) -> "GameProfile":
        """Loads a game profile from a JSON file."""
        # Check cache first
        cache = get_cache()
        profile_key = str(profile_path)
        cached_profile = cache.get_profile(profile_key)
        if cached_profile is not None:
            return cached_profile

        # Batch validations
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_path}")

        if profile_path.suffix != '.json':
            raise ValueError(f"Unsupported profile file extension: {profile_path.suffix}. Only JSON profiles are supported.")

        # Optimized file reading
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ValueError(f"Error reading profile file {profile_path}: {e}")

        # Batch processing of configurations
        cls._process_profile_data(data)

        profile = cls(**data)
        # Cache the loaded profile
        cache.set_profile(profile_key, profile)
        return profile

    @classmethod
    def _process_profile_data(cls, data: Dict) -> None:
        """Optimized processing of profile data."""
        # Detects if the game is native based on the executable extension
        exe_path_str = data.get('EXE_PATH')
        if exe_path_str:
            data['is_native'] = not exe_path_str.lower().endswith('.exe')
        else:
            data['is_native'] = False

        # If 'NUM_PLAYERS' is not in JSON but 'PLAYERS' is, infer NUM_PLAYERS
        if 'NUM_PLAYERS' not in data and 'PLAYERS' in data and isinstance(data['PLAYERS'], list):
            data['NUM_PLAYERS'] = len(data['PLAYERS'])

    selected_players: Optional[List[int]] = Field(default=None, alias="selected_players")

    # Add getter for num_players to ensure consistency in case player_configs is the source of truth
    @property
    def effective_num_players(self) -> int:
        """Returns the number of players that will actually be launched."""
        return len(self.players_to_launch)

    @property
    def players_to_launch(self) -> List[PlayerInstanceConfig]:
        """Returns the players that should be launched based on the selection.
        If no specific players are selected (selected_players is None or empty),
        all available player configurations will be launched.
        """
        if not self.player_configs:
            return []

        if not self.selected_players: # If no specific players are selected, launch all
            return self.player_configs

        # Filters players based on the selected_players list (1-based index)
        return [p for i, p in enumerate(self.player_configs) if (i + 1) in self.selected_players]

    def get_instance_dimensions(self, instance_num: int) -> Tuple[int, int]:
        """Returns the dimensions (width, height) for a specific instance."""
        # If not in splitscreen mode, return full instance dimensions
        if not self.is_splitscreen_mode or not self.splitscreen:
            return self.instance_width, self.instance_height

        orientation = self.splitscreen.orientation
        num_players = self.effective_num_players

        # Ensure num_players is at least 1 to prevent ZeroDivisionError
        if num_players < 1:
            num_players = 1

        if num_players == 1:
            # Case for 1 player (fullscreen) or any other explicitly unmapped case
            return self.instance_width, self.instance_height
        elif num_players == 2:
            if orientation == "horizontal":
                return self.instance_width // 2, self.instance_height
            else:  # vertical
                return self.instance_width, self.instance_height // 2
        elif num_players == 3:
            if orientation == "horizontal":
                if instance_num == 1:
                    # Player 1 (top): Full width, half height
                    return self.instance_width, self.instance_height // 2
                else:  # Player 2 or 3 (bottom, split horizontally)
                    # Each occupies half width, half height
                    return self.instance_width // 2, self.instance_height // 2
            else:  # vertical
                if instance_num == 1:
                    # Player 1 (left): Half width, full height
                    return self.instance_width // 2, self.instance_height
                else:  # Player 2 or 3 (right, split vertically)
                    # Each occupies half of remaining width, half of total height
                    return self.instance_width // 2, self.instance_height // 2
        elif num_players == 4:
            # For 4 players, each occupies a quarter of the screen (2x2 grid)
            return self.instance_width // 2, self.instance_height // 2
        else:
            # Default behavior for other numbers of players (e.g., 5 or more)
            # Divide equally in the specified orientation
            if orientation == "horizontal":
                return self.instance_width, self.instance_height // num_players
            else:  # vertical
                return self.instance_width // num_players, self.instance_height

    def save_to_file(self, profile_path: Path):
        """Saves the current game profile to a JSON file."""
        # Use .model_dump_json() to export the Pydantic model to a JSON string
        # by_alias=True ensures that fields with 'alias' (ex: GAME_NAME) use their aliases
        # indent=4 for formatted and readable JSON output
        json_data = self.model_dump_json(by_alias=True, indent=4)
        profile_path.write_text(json_data, encoding='utf-8')
