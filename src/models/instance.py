from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from ..models.profile import PlayerInstanceConfig


class GameInstance(BaseModel):
    """
    Represents a single, running instance of a game.

    This Pydantic model holds all the runtime information associated with one
    player's game process, including its process ID, Wine prefix path, and
    the specific player configuration it's using.

    Attributes:
        instance_num (int): A unique identifier for this instance within a
            single launch session (e.g., 1, 2, 3).
        profile_name (str): The name of the game profile being used.
        prefix_dir (Path): The absolute path to the Wine prefix directory for
            this instance.
        log_file (Path): The path to the log file for this instance's output.
        pid (Optional[int]): The process ID of the main game process. This is
            set once the game is launched.
        gamescope_pid (Optional[int]): The process ID of the Gamescope process,
            if used.
        player_config (Optional[PlayerInstanceConfig]): The specific player
            configuration (e.g., input devices, screen position) for this
            instance.
        is_native (bool): A flag indicating whether this is a native Linux
            game, which affects cleanup procedures (e.g., skipping `wineserver -k`).
    """
    instance_num: int
    profile_name: str
    prefix_dir: Path
    log_file: Path
    pid: Optional[int] = None
    gamescope_pid: Optional[int] = None
    player_config: Optional[PlayerInstanceConfig] = None
    is_native: bool = False

    def __init__(self, **data):
        """
        Initializes the GameInstance.

        Args:
            **data: Keyword arguments corresponding to the model's attributes.
        """
        super().__init__(**data)