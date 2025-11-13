import json
from pathlib import Path
from typing import Optional, List, Dict

from pydantic import BaseModel, ConfigDict, Field, validator

from ..core.exceptions import ExecutableNotFoundError


class Game(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='ignore')
    """
    Represents a game in the user's library.

    This model stores high-level information about a game, such as its name
    and the path to its executable. This data is shared across all profiles
    associated with this game.

    Attributes:
        game_name (str): The name of the game.
        exe_path (str): The relative path to the game's primary executable from the game_cwd.
        game_cwd (Path): The root path of the game directory.
        app_id (Optional[str]): The Steam AppID of the game.
        game_args (Optional[str]): Command-line arguments to pass to the game.
        is_native (bool): Flag indicating if the game is a native Linux title.
        proton_version (Optional[str]): The Proton version to use for this game.
        apply_dxvk_vkd3d (bool): Whether to apply DXVK/VKD3D to prefixes for this game.
        winetricks_verbs (Optional[List[str]]): Winetricks verbs to run for this game.
        env_vars (Optional[Dict[str, str]]): Environment variables to set for this game.
    """
    guid: Optional[str] = Field(default=None, alias="GUID")
    game_name: str = Field(..., alias="GAME_NAME")
    game_cwd: Path = Field(..., alias="GAME_CWD")
    exe_path: str = Field(..., alias="EXE_PATH")
    app_id: Optional[str] = Field(default=None, alias="APP_ID")
    game_args: Optional[str] = Field(default=None, alias="GAME_ARGS")
    is_native: bool = Field(default=False, alias="IS_NATIVE")
    proton_version: Optional[str] = Field(default=None, alias="PROTON_VERSION")
    apply_dxvk_vkd3d: bool = Field(default=False, alias="APPLY_DXVK_VKD3D")
    winetricks_verbs: Optional[List[str]] = Field(default=None, alias="WINETRICKS_VERBS")
    env_vars: Optional[Dict[str, str]] = Field(default_factory=dict, alias="ENV_VARS")
    use_mangohud: bool = Field(default=False, alias="USE_MANGOHUD")
    executable_to_launch: Optional[str] = Field(default=None, alias="EXECUTABLE_TO_LAUNCH")
    launcher_exe: Optional[str] = Field(default=None, alias="LAUNCHER_EXE")
    symlink_game: bool = Field(default=True, alias="SYMLINK_GAME")
    symlink_exe: bool = Field(default=False, alias="SYMLINK_EXE")
    symlink_folders: bool = Field(default=False, alias="SYMLINK_FOLDERS")
    keep_symlinks_on_exit: bool = Field(default=False, alias="KEEP_SYMLINKS_ON_EXIT")
    symlink_files: Optional[List[str]] = Field(default=None, alias="SYMLINK_FILES")
    copy_files: Optional[List[str]] = Field(default=None, alias="COPY_FILES")
    hardcopy_game: bool = Field(default=False, alias="HARDCOPY_GAME")
    hardlink_game: bool = Field(default=False, alias="HARDLINK_GAME")
    force_symlink: bool = Field(default=False, alias="FORCE_SYMLINK")
    dir_symlink_exclusions: Optional[List[str]] = Field(default=None, alias="DIR_SYMLINK_EXCLUSIONS")
    file_symlink_exclusions: Optional[List[str]] = Field(default=None, alias="FILE_SYMLINK_EXCLUSIONS")
    file_symlink_copy_instead: Optional[List[str]] = Field(default=None, alias="FILE_SYMLINK_COPY_INSTEAD")
    dir_symlink_copy_instead: Optional[List[str]] = Field(default=None, alias="DIR_SYMLINK_COPY_INSTEAD")
    dir_symlink_copy_instead_include_sub_folders: bool = Field(default=False, alias="DIR_SYMLINK_COPY_INSTEAD_INCLUDE_SUB_FOLDERS")
    symlink_folders_to: Optional[List[str]] = Field(default=None, alias="SYMLINK_FOLDERS_TO")
    hardlink_folders_to: Optional[List[str]] = Field(default=None, alias="HARDLINK_FOLDERS_TO")
    change_exe: bool = Field(default=False, alias="CHANGE_EXE")
    copy_custom_utils: Optional[List[str]] = Field(default=None, alias="COPY_CUSTOM_UTILS")


    @property
    def absolute_exe_path(self) -> Path:
        """Returns the absolute path to the game executable."""
        return self.game_cwd / self.exe_path

    @validator('game_name')
    def sanitize_game_name(cls, v):
        """Sanitizes the game name."""
        return v.strip()

    @classmethod
    def load_from_file(cls, file_path: Path) -> "Game":
        """Loads a game from a JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Game file not found: {file_path}")
        with file_path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        # Infer is_native if not present
        if 'IS_NATIVE' not in data:
            exe_path_str = data.get('EXE_PATH')
            data['IS_NATIVE'] = bool(exe_path_str and not exe_path_str.lower().endswith('.exe'))

        return cls.model_validate(data)

    def save_to_file(self, file_path: Path):
        """Saves the game to a JSON file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        json_data = self.model_dump_json(by_alias=True, indent=4)
        file_path.write_text(json_data, encoding='utf-8')
