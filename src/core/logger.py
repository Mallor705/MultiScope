import logging
import sys
from pathlib import Path
from functools import lru_cache

class Logger:
    """Logger customizado para o Linux-Coop, com saída para console e arquivo otimizada."""
    def __init__(self, name: str, log_dir: Path):
        """Inicializa o logger, criando diretório de logs e configurando handlers."""
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self._handlers_setup = False
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers do logger de forma otimizada, evitando duplicidade."""
        if self.logger.hasHandlers() or self._handlers_setup:
            return
            
        # Formatter otimizado
        formatter = logging.Formatter('%(asctime)s - %(message)s', 
                                    datefmt='%Y-%m-%d %H:%M:%S')
        
        # Console handler com buffer
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
        
        # File handler otimizado
        log_file = self.log_dir / f"{self.logger.name}.log"
        file_handler = logging.FileHandler(
            log_file, 
            mode='a', 
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        self._handlers_setup = True
    
    @lru_cache(maxsize=128)
    def _should_log(self, level: int) -> bool:
        """Cache para verificação de nível de log."""
        return self.logger.isEnabledFor(level)
    
    def info(self, message: str):
        """Loga uma mensagem de informação de forma otimizada."""
        if self._should_log(logging.INFO):
            self.logger.info(message)
    
    def error(self, message: str):
        """Loga uma mensagem de erro de forma otimizada."""
        if self._should_log(logging.ERROR):
            self.logger.error(message)

    def warning(self, message: str):
        """Loga uma mensagem de aviso de forma otimizada."""
        if self._should_log(logging.WARNING):
            self.logger.warning(message)
    
    def flush(self):
        """Força o flush dos handlers para garantir que logs sejam escritos."""
        for handler in self.logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()