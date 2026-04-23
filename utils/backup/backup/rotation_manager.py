import os
import time
from typing import Optional
from utils.backup.log_utils.logger import Logger

class RotationManager:
    def __init__(self, logger: Logger):
        self.logger = logger

    def rotate(self, backup_dir: str, max_age_days: int) -> None:
        """
        Elimina backups antiguos según el límite de días.

        Args:
            backup_dir (str): Ruta del directorio de backups.
            max_age_days (int): Número máximo de días para mantener los backups.
        """
        try:
            if not os.path.exists(backup_dir):
                self.logger.info(f"Directorio de backup no encontrado: {backup_dir}")
                return

            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60

            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                if os.path.isdir(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        shutil.rmtree(file_path)
                        self.logger.info(f"Backup eliminado: {file_path}")
        except Exception as e:
            self.logger.error(f"Error al rotar backups: {str(e)}")