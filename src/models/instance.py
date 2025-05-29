from pathlib import Path
from pydantic import BaseModel
from typing import Optional

class GameInstance(BaseModel):
    """Modelo que representa uma instância individual do jogo."""
    instance_num: int
    profile_name: str
    prefix_dir: Path
    log_file: Path
    pid: Optional[int] = None
    
    def __init__(self, **data):
        """Inicializa a instância do jogo com os dados fornecidos."""
        super().__init__(**data)