from pathlib import Path
from typing import List

class Config:
    """Configurações globais do Linux-Coop, incluindo diretórios, comandos e caminhos do Steam."""
    SCRIPT_DIR = Path(__file__).parent.parent.parent
    PROFILE_DIR = SCRIPT_DIR / "profiles"
    LOG_DIR = Path.home() / ".local/share/linux-coop/logs"
    PREFIX_BASE_DIR = Path.home() / ".local/share/linux-coop/prefixes"
    
    STEAM_PATHS = [
        Path.home() / ".steam/root",
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".steam/debian-installation",
        Path("/var/mnt/games/messi/Games/Steam")
    ]
    
    REQUIRED_COMMANDS = ["gamescope", "bwrap"]
    
    @classmethod
    def get_profile_path(cls, profile_name: str) -> Path:
        """Retorna o caminho do arquivo de perfil a partir do nome informado."""
        return cls.PROFILE_DIR / f"{profile_name}.profile"