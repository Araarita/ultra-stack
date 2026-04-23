import os
import logging
import yaml
import shutil
import datetime
import schedule
import time
from typing import Dict, List, Optional
from utils.backup.backup.backup_service import BackupService
from utils.backup.backup.rotation_manager import RotationManager
from utils.backup.config.config_loader import ConfigLoader
from utils.backup.config.config_validator import ConfigValidator
from utils.backup.log_utils.logger import Logger
from utils.backup.notifications.notification_service import NotificationService
from utils.backup.scheduler.scheduler import Scheduler

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupSystem:
    def __init__(self, config_loader: ConfigLoader, config_validator: ConfigValidator, backup_service: BackupService, 
                 rotation_manager: RotationManager, logger: Logger, notification_service: NotificationService):
        self.config_loader = config_loader
        self.config_validator = config_validator
        self.backup_service = backup_service
        self.rotation_manager = rotation_manager
        self.logger = logger
        self.notification_service = notification_service

    def run(self, config_path: str = "config.yaml") -> None:
        """Ejecuta el proceso de backup."""
        try:
            self.logger.info("Iniciando el sistema de backup...")
            config = self.config_loader.load(config_path)
            self.config_validator.validate(config)

            for source_dir in config["backup"]["source_dirs"]:
                backup_dir = config["backup"]["backup_dir"]
                self.logger.info(f"Realizando backup del directorio: {source_dir}")
                success = self.backup_service.backup(source_dir, backup_dir)
                if not success:
                    self.logger.error(f"Backup fallido para {source_dir}")
                    self.notification_service.send(f"Backup fallido para {source_dir}", level="error")
                else:
                    self.logger.info(f"Backup completado para {source_dir}")

            self.logger.info("Iniciando rotación de backups...")
            self.rotation_manager.rotate(config["backup"]["backup_dir"], config["backup"]["rotation"]["max_age_days"])
            self.logger.info("Rotación de backups completada.")

            self.logger.info("Proceso de backup completado con éxito.")
        except Exception as e:
            self.logger.error(f"Error en el proceso de backup: {str(e)}")
            self.notification_service.send(f"Error en el proceso de backup: {str(e)}", level="error")
            raise

def main():
    config_loader = ConfigLoader()
    config_validator = ConfigValidator()
    backup_service = BackupService(Logger())
    rotation_manager = RotationManager(Logger())
    logger = Logger()
    notification_service = NotificationService()

    backup_system = BackupSystem(config_loader, config_validator, backup_service, rotation_manager, logger, notification_service)
    backup_system.run()

if __name__ == "__main__":
    # Configuración del scheduler
    scheduler = Scheduler()
    scheduler.run(main)