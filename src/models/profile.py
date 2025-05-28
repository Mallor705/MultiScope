from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import Optional
from ..core.exceptions import ProfileNotFoundError, ExecutableNotFoundError

class GameProfile(BaseModel):
    game_name: str = Field(..., alias="GAME_NAME")
    exe_path: Path = Field(..., alias="EXE_PATH")
    proton_version: str = Field(..., alias="PROTON_VERSION")
    num_players: int = Field(..., alias="NUM_PLAYERS")
    instance_width: int = Field(..., alias="INSTANCE_WIDTH")
    instance_height: int = Field(..., alias="INSTANCE_HEIGHT")
    
    @validator('num_players')
    def validate_num_players(cls, v):
        if v != 2:
            raise ValueError("Currently supports exactly 2 players")
        return v
    
    @validator('exe_path')
    def validate_exe_path(cls, v):
        if not v.exists():
            raise ExecutableNotFoundError(f"Game executable not found: {v}")
        return v
    
    @classmethod
    def load_from_file(cls, profile_path: Path) -> "GameProfile":
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_path}")
        
        profile_vars = {}
        with open(profile_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    if key in ['NUM_PLAYERS', 'INSTANCE_WIDTH', 'INSTANCE_HEIGHT']:
                        value = int(value)
                    elif key == 'EXE_PATH':
                        value = Path(value)
                    
                    profile_vars[key] = value
        
        return cls(**profile_vars)