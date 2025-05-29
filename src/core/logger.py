import logging
import sys
from datetime import datetime
from pathlib import Path

class Logger:
    """Logger customizado para o Linux-Coop, com saída para console e arquivo."""
    def __init__(self, name: str, log_dir: Path):
        """Inicializa o logger, criando diretório de logs e configurando handlers."""
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers do logger, evitando duplicidade."""
        if self.logger.hasHandlers():
            return
        formatter = logging.Formatter('%(asctime)s - %(message)s', 
                                    datefmt='%Y-%m-%d %H:%M:%S')
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """Loga uma mensagem de informação."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Loga uma mensagem de erro."""
        self.logger.error(message)