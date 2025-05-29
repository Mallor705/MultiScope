from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import Optional
from ..core.exceptions import ProfileNotFoundError, ExecutableNotFoundError

class GameProfile(BaseModel):
    """Modelo de perfil de jogo, contendo configurações e validações para execução multi-instância."""
    game_name: str = Field(..., alias="GAME_NAME")
    exe_path: Path = Field(..., alias="EXE_PATH")
    proton_version: Optional[str] = Field(default=None, alias="PROTON_VERSION")
    num_players: int = Field(..., alias="NUM_PLAYERS")
    instance_width: int = Field(..., alias="INSTANCE_WIDTH")
    instance_height: int = Field(..., alias="INSTANCE_HEIGHT")
    player_physical_device_ids: Optional[list] = Field(default=None, alias="PLAYER_PHYSICAL_DEVICE_IDS")
    is_native: bool = False
    
    @validator('num_players')
    def validate_num_players(cls, v):
        """Valida se o número de jogadores é suportado (mínimo 2)."""
        if v < 2:
            raise ValueError("O número mínimo suportado é 2 jogadores")
        return v
    
    @validator('exe_path')
    def validate_exe_path(cls, v):
        """Valida se o caminho do executável existe."""
        if not v.exists():
            raise ExecutableNotFoundError(f"Game executable not found: {v}")
        return v
    
    @classmethod
    def load_from_file(cls, profile_path: Path) -> "GameProfile":
        """Carrega um perfil de jogo a partir de um arquivo."""
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_path}")
        
        profile_vars = {}
        array_key = None
        array_values = []
        with open(profile_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.endswith('(') and '=' in line:
                    # Início de array bash
                    array_key = line.split('=')[0].strip()
                    array_values = []
                    continue
                if array_key:
                    if line.endswith(')'):
                        # Fim do array
                        array_key = array_key.strip()
                        profile_vars[array_key] = array_values
                        array_key = None
                        array_values = []
                        continue
                    # Adiciona valor ao array
                    value = line.split('#')[0].strip().strip('"\'')
                    if value:
                        array_values.append(value)
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key in ['NUM_PLAYERS', 'INSTANCE_WIDTH', 'INSTANCE_HEIGHT']:
                        value = int(value)
                    elif key == 'EXE_PATH':
                        value = Path(value)
                    profile_vars[key] = value
        # Detecta se é nativo
        exe_path = profile_vars.get('EXE_PATH')
        is_native = False
        if exe_path and isinstance(exe_path, Path) and exe_path.suffix != '.exe':
            is_native = True
        profile_vars['is_native'] = is_native
        return cls(**profile_vars)