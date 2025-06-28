import json
from pathlib import Path
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Tuple

from ..core.exceptions import ProfileNotFoundError, ExecutableNotFoundError
from ..core.cache import get_cache

class PlayerInstanceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    """Configurações específicas para uma instância de jogador."""
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
    """Configuração do modo splitscreen."""
    orientation: str = Field(alias="ORIENTATION")

    @validator('orientation')
    def validate_orientation(cls, v):
        if v not in ["horizontal", "vertical"]:
            raise ValueError("Orientation must be 'horizontal' or 'vertical'.")
        return v

class GameProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    """Modelo de perfil de jogo, contendo configurações e validações para execução multi-instância."""
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

    # Novo campo para configurações por jogador, usando alias "PLAYERS" para o JSON
    player_configs: Optional[List[PlayerInstanceConfig]] = Field(default=None, alias="PLAYERS")
    use_goldberg_emu: bool = Field(default=True, alias="USE_GOLDBERG_EMU")

    @validator('num_players')
    def validate_num_players(cls, v):
        """Valida se o número de jogadores é suportado (mínimo 1, máximo 4)."""
        if not (1 <= v <= 4):
            raise ValueError("O número de jogadores deve ser entre 1 e 4.")
        return v

    @validator('exe_path')
    def validate_exe_path(cls, v, values):
        """Valida se o caminho do executável existe, se fornecido."""
        if v is None: # Allow None for optional exe_path
            return v
        
        path_v = Path(v)
        cache = get_cache()
        if not cache.check_path_exists(path_v):
            # Only raise error if path is not empty and not found
            if str(path_v) != "":
                raise ExecutableNotFoundError(f"Game executable not found: {path_v}")
        return path_v # Retorna o objeto Path

    @property
    def is_splitscreen_mode(self) -> bool:
        """Verifica se está no modo splitscreen."""
        return self.mode == "splitscreen"

    @property
    def effective_instance_width(self) -> int:
        """Retorna a largura efetiva da instância, dividida se for splitscreen horizontal."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "horizontal":
            return self.instance_width // self.effective_num_players
        return self.instance_width

    @property
    def effective_instance_height(self) -> int:
        """Retorna a altura efetiva da instância, dividida se for splitscreen vertical."""
        if self.is_splitscreen_mode and self.splitscreen and self.splitscreen.orientation == "vertical":
            return self.instance_height // self.effective_num_players
        return self.instance_height

    @classmethod
    def load_from_file(cls, profile_path: Path) -> "GameProfile":
        """Carrega um perfil de jogo a partir de um arquivo JSON."""
        # Check cache first
        cache = get_cache()
        profile_key = str(profile_path)
        cached_profile = cache.get_profile(profile_key)
        if cached_profile is not None:
            return cached_profile

        # Validações em lote
        if not profile_path.exists():
            raise ProfileNotFoundError(f"Profile not found: {profile_path}")

        if profile_path.suffix != '.json':
            raise ValueError(f"Unsupported profile file extension: {profile_path.suffix}. Only JSON profiles are supported.")

        # Leitura otimizada do arquivo
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise ValueError(f"Error reading profile file {profile_path}: {e}")

        # Processamento em lote das configurações
        cls._process_profile_data(data)

        profile = cls(**data)
        # Cache the loaded profile
        cache.set_profile(profile_key, profile)
        return profile

    @classmethod
    def _process_profile_data(cls, data: Dict) -> None:
        """Processa dados do perfil de forma otimizada."""
        # Detecta se o jogo é nativo com base na extensão do executável
        exe_path_str = data.get('EXE_PATH')
        if exe_path_str:
            data['is_native'] = not exe_path_str.lower().endswith('.exe')
        else:
            data['is_native'] = False

        # Se 'NUM_PLAYERS' não estiver no JSON mas 'PLAYERS' estiver, infere NUM_PLAYERS
        if 'NUM_PLAYERS' not in data and 'PLAYERS' in data and isinstance(data['PLAYERS'], list):
            data['NUM_PLAYERS'] = len(data['PLAYERS'])

    # Adicionar getter para num_players para garantir consistência caso player_configs seja a fonte da verdade
    @property
    def effective_num_players(self) -> int:
        return self.num_players

    def get_instance_dimensions(self, instance_num: int) -> Tuple[int, int]:
        """Retorna as dimensões (largura, altura) para uma instância específica."""
        # Se não estiver no modo splitscreen, retorna as dimensões completas da instância
        if not self.is_splitscreen_mode or not self.splitscreen:
            return self.instance_width, self.instance_height

        orientation = self.splitscreen.orientation
        num_players = self.effective_num_players

        if num_players == 1:
            # Caso para 1 jogador (tela cheia) ou qualquer outro caso não mapeado explicitamente
            return self.instance_width, self.instance_height
        elif num_players == 2:
            if orientation == "horizontal":
                return self.instance_width // 2, self.instance_height
            else:  # vertical
                return self.instance_width, self.instance_height // 2
        elif num_players == 3:
            if orientation == "horizontal":
                if instance_num == 1:
                    # Instância 1 ocupa largura total, metade da altura
                    return self.instance_width, self.instance_height // 2
                else:  # Instância 2 ou 3
                    # As outras duas dividem a largura total e a outra metade da altura
                    return self.instance_width // 2, self.instance_height // 2
            else:  # vertical
                if instance_num == 1:
                    # Instância 1 ocupa metade da largura, altura total
                    return self.instance_width // 2, self.instance_height
                else:  # Instância 2 ou 3
                    # As outras duas dividem a outra metade da largura e a altura total
                    return self.instance_width // 2, self.instance_height // 2
        elif num_players == 4:
            # Para 4 jogadores, cada um ocupa um quarto da tela
            # Independentemente da orientação, divide-se por 2 em largura e altura
            return self.instance_width // 2, self.instance_height // 2
        else:
            # Comportamento padrão para outros números de jogadores (ex: 5 ou mais)
            # Divide igualmente na orientação especificada
            if orientation == "horizontal":
                return self.instance_width, self.instance_height // num_players
            else:  # vertical
                return self.instance_width // num_players, self.instance_height
