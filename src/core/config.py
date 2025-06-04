from pathlib import Path


class Config:
    """Configurações globais do Linux-Coop, incluindo diretórios, comandos e caminhos do Steam."""
    SCRIPT_DIR = Path(__file__).parent.parent.parent
    PROFILE_DIR = Path.home() / ".config/linux-coop/profiles"
    LOG_DIR = Path.home() / ".cache/linux-coop/logs"
    PREFIX_BASE_DIR = Path.home() / "Games/linux-coop/prefixes/"

    STEAM_PATHS = [
        Path.home() / ".steam/root",
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".steam/debian-installation",
        Path.home() / ".steam/steam/root",
        Path.home() / ".steam/steam/steamapps",
        Path.home() / ".local/share/Steam/steamapps",
        Path.home() / ".local/share/Steam/steamapps/common",
    ]

    REQUIRED_COMMANDS = ["gamescope", "bwrap"]

    # Timeout configurations (in seconds)
    PROCESS_START_TIMEOUT = 30
    PROCESS_TERMINATE_TIMEOUT = 10
    SUBPROCESS_TIMEOUT = 15
    FILE_IO_TIMEOUT = 5
    SUDO_PROMPT_TIMEOUT = 60

    @staticmethod
    def get_prefix_base_dir(game_name: str) -> Path:
        """Retorna o diretório base de prefixos para um jogo específico."""
        return Config.PREFIX_BASE_DIR / game_name
