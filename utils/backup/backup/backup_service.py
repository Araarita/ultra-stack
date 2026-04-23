import os
import shutil
import logging
from typing import Optional
from utils.backup.log_utils.logger import Logger

class BackupService:
    def __init__(self, logger: Logger):
        self.logger = logger

    def backup(self, source_dir: str, backup_dir: str) -> bool:
        """
        Realiza el backup de un directorio.

        Args:
            source_dir (str): Ruta del directorio fuente.
            backup_dir (str): Ruta del directorio de backup.

        Returns:
            bool: True si el backup fue exitoso, False en caso contrario.
        """
        try:
            if not os.path.exists(source_dir):
                self.logger.error(f"Directorio fuente no encontrado: {source_dir}")
                return False

            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                self.logger.info(f"Directorio de backup creado: {backup_dir}")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
            shutil.copytree(source_dir, backup_path)
            self.logger.info(f"Backup completado: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error al realizar el backup: {str(e)}")
            return False