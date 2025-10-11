from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from ..models.profile import PlayerInstanceConfig

class GameInstance(BaseModel):
    """Model representing an individual game instance."""
    instance_num: int
    profile_name: str
    prefix_dir: Path
    log_file: Path
    pid: Optional[int] = None
    gamescope_pid: Optional[int] = None
    player_config: Optional[PlayerInstanceConfig] = None
    is_native: bool = False
    
    def __init__(self, **data):
        """Initializes the game instance with the provided data."""
        super().__init__(**data)