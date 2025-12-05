import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from pydantic import (BaseModel, ConfigDict, Field, ValidationError,
                      validator)

from ..core.config import Config
from ..core.exceptions import ProfileNotFoundError
from ..core.logger import Logger


class PlayerInstanceConfig(BaseModel):
    """
    Defines the specific configuration for a single player's game instance.
    """
    model_config = ConfigDict(populate_by_name=True)

    ACCOUNT_NAME: Optional[str] = Field(default=None, alias="ACCOUNT_NAME")
    LANGUAGE: Optional[str] = Field(default=None, alias="LANGUAGE")
    LISTEN_PORT: Optional[str] = Field(default=None, alias="LISTEN_PORT")
    USER_STEAM_ID: Optional[str] = Field(default=None, alias="USER_STEAM_ID")
    PHYSICAL_DEVICE_ID: Optional[str] = Field(default=None, alias="PHYSICAL_DEVICE_ID")
    grab_input_devices: bool = Field(default=False, alias="GRAB_INPUT_DEVICES")
    # MOUSE_EVENT_PATH: Optional[str] = Field(default=None, alias="MOUSE_EVENT_PATH")
    # KEYBOARD_EVENT_PATH: Optional[str] = Field(default=None, alias="KEYBOARD_EVENT_PATH")
    AUDIO_DEVICE_ID: Optional[str] = Field(default=None, alias="AUDIO_DEVICE_ID")
    monitor_id: Optional[str] = Field(default=None, alias="MONITOR_ID")
    env: Optional[Dict[str, str]] = Field(default=None, alias="ENV")


class SplitscreenConfig(BaseModel):
    """
    Configuration for splitscreen mode.
    """
    model_config = ConfigDict(populate_by_name=True)
    orientation: str = Field(alias="ORIENTATION")

    @validator('orientation')
    def validate_orientation(cls, v):
        if v not in ["horizontal", "vertical"]:
            raise ValueError("Orientation must be 'horizontal' or 'vertical'.")
        return v


class Profile(BaseModel):
    """
    A profile for launching a set of Steam instances with a specific configuration.
    """
    model_config = ConfigDict(populate_by_name=True, extra='ignore')

    profile_name: str = Field(default="Default", alias="PROFILE_NAME")
    num_players: int = Field(default=2, alias="NUM_PLAYERS")
    instance_width: Optional[int] = Field(default=1280, alias="INSTANCE_WIDTH")
    instance_height: Optional[int] = Field(default=720, alias="INSTANCE_HEIGHT")
    mode: Optional[str] = Field(default="fullscreen", alias="MODE")
    use_gamescope: bool = Field(default=True, alias="USE_GAMESCOPE")
    splitscreen: Optional[SplitscreenConfig] = Field(default=None, alias="SPLITSCREEN")
    env: Optional[Dict[str, str]] = Field(default=None, alias="ENV")
    player_configs: List[PlayerInstanceConfig] = Field(default_factory=lambda: [PlayerInstanceConfig(), PlayerInstanceConfig()], alias="PLAYERS")
    selected_players: Optional[List[int]] = Field(default=None, alias="selected_players")

    @classmethod
    def load(cls) -> "Profile":
        """Loads the profile from the default JSON file."""
        profile_path = Config.get_profile_path()
        if not profile_path.exists():
            # If no profile exists, create a default one and save it
            default_profile = cls()
            default_profile.save()
            return default_profile

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ValueError(f"Error reading profile file {profile_path}: {e}")

        try:
            profile = cls(**data)
        except ValidationError as e:
            # Consider logging this instead of printing
            print(f"Pydantic Validation Error for {profile_path}: {e.errors()}")
            raise ValueError(f"Profile data validation failed: {e}")
        return profile

    def save(self):
        """
        Saves the profile to the default JSON file.
        """
        profile_path = Config.get_profile_path()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        data_to_save = self.model_dump(by_alias=True, exclude_none=True)
        json_data = json.dumps(data_to_save, indent=4)
        profile_path.write_text(json_data, encoding='utf-8')

    @property
    def is_splitscreen_mode(self) -> bool:
        """Checks if the profile is configured for splitscreen mode."""
        return self.mode == "splitscreen"

    def effective_num_players(self) -> int:
        if self.selected_players:
            return len(self.selected_players)
        return len(self.player_configs) if self.player_configs else 0

    def get_env_for_instance(self, instance_idx: int) -> Dict[str, str]:
        """Returns the merged environment variables for a given instance index (0-based).
        Per-player ENV overrides values from the global ENV."""
        base_env: Dict[str, str] = dict(self.env or {})
        if 0 <= instance_idx < len(self.player_configs):
            player_env = self.player_configs[instance_idx].env or {}
            player_env = {str(k): str(v) for k, v in player_env.items()}
            base_env.update(player_env)
        base_env = {str(k): str(v) for k, v in base_env.items()}
        return base_env

    def get_instance_dimensions(self, instance_num: int) -> Tuple[Optional[int], Optional[int]]:
        """Calculates instance dimensions, accounting for splitscreen."""
        if not self.instance_width or not self.instance_height:
            return None, None

        if not self.is_splitscreen_mode or not self.splitscreen:
            return self.instance_width, self.instance_height

        orientation = self.splitscreen.orientation
        num_players = self.effective_num_players()

        if num_players < 1:
            return self.instance_width, self.instance_height

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
        else:
            # Fallback for > 4 players, might not be visually ideal
            if orientation == "horizontal":
                return self.instance_width, self.instance_height // num_players
            else:
                return self.instance_width // num_players, self.instance_height
