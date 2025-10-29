import logging
import os
from datetime import datetime
from config_manager import config_manager


class Logger:
    """
    Handles logging for the Obsidian Vault Merger tool.
    Tracks file operations, errors, and other important events.
    """

    def __init__(self):
        self.logger = logging.getLogger("obsidian_vault_merger")
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent adding multiple handlers if logger is already configured
        if not self.logger.handlers:
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Create file handler
            log_dir = os.path.join(config_manager.destination_path, ".merge_logs")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"merge_{timestamp}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            # Add handlers to logger
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)


# Global logger instance
logger = Logger()