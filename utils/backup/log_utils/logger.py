import logging
from typing import Optional

class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def info(self, message: str) -> None:
        """
        Registra un mensaje de información.

        Args:
            message (str): Mensaje a registrar.
        """
        self.logger.info(message)

    def error(self, message: str) -> None:
        """
        Registra un mensaje de error.

        Args:
            message (str): Mensaje a registrar.
        """
        self.logger.error(message)