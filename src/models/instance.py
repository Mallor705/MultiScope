from pathlib import Path
from pydantic import BaseModel
from typing import Optional

class GameInstance(BaseModel):
    instance_num: int
    profile_name: str
    prefix_dir: Path
    log_file: Path
    pid: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.prefix_dir.mkdir(parents=True, exist_ok=True)
        (self.prefix_dir / "pfx").mkdir(exist_ok=True)