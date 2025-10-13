import logging
import sys
from functools import lru_cache
from pathlib import Path


class Logger:
    """
    A custom logger for Proton-Coop providing console and file output.

    This class configures a logger that writes to both stderr and a log file
    in the specified directory. It's designed to be efficient by avoiding
    handler duplication and using an LRU cache for log level checks.

    Attributes:
        log_dir (Path): The directory where log files are stored.
        logger (logging.Logger): The underlying standard Python logger instance.
    """

    def __init__(self, name: str, log_dir: Path):
        """
        Initializes the logger and sets up its handlers.

        This creates the log directory if it doesn't exist and configures
        a logger with a specified name.

        Args:
            name (str): The name of the logger, typically `__name__` of the
                calling module.
            log_dir (Path): The path to the directory for storing log files.
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self._handlers_setup = False
        self._setup_handlers()

    def _setup_handlers(self):
        """
        Configures and adds stream and file handlers to the logger.

        This method ensures that handlers are only configured once. It sets up
        a console handler (stderr) and a file handler, both with a consistent
        format.
        """
        if self.logger.hasHandlers() or self._handlers_setup:
            return

        formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler to stderr
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

        # File handler
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
        """
        Checks if a given log level is enabled for the logger.

        This check is cached to improve performance for frequent logging calls.

        Args:
            level (int): The logging level to check (e.g., `logging.INFO`).

        Returns:
            bool: True if the level is enabled, False otherwise.
        """
        return self.logger.isEnabledFor(level)

    def info(self, message: str):
        """
        Logs an informational message.

        Args:
            message (str): The message to log.
        """
        if self._should_log(logging.INFO):
            self.logger.info(message)

    def error(self, message: str):
        """
        Logs an error message.

        Args:
            message (str): The message to log.
        """
        if self._should_log(logging.ERROR):
            self.logger.error(message)

    def warning(self, message: str):
        """
        Logs a warning message.

        Args:
            message (str): The message to log.
        """
        if self._should_log(logging.WARNING):
            self.logger.warning(message)

    def flush(self):
        """
        Flushes all handlers attached to the logger.

        This is useful to ensure that all buffered log records have been
        written to their destination.
        """
        for handler in self.logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
