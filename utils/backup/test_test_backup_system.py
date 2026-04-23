import os
import shutil
import yaml
import pytest
from unittest.mock import patch, MagicMock
from utils.backup.main import BackupSystem, main
from utils.backup.backup.backup_service import BackupService
from utils.backup.config.config_loader import ConfigLoader
from utils.backup.config.config_validator import ConfigValidator
from utils.backup.log_utils.logger import Logger
from utils.backup.notifications.notification_service import NotificationService
from utils.backup.scheduler.scheduler import Scheduler
from utils.backup.backup.rotation_manager import RotationManager

# Fixtures
@pytest.fixture
def mock_config_loader():
    with patch('backup_system.config.config_loader.ConfigLoader.load') as mock_load:
        config = {
            "backup": {
                "source_dirs": ["/test/source1", "/test/source2"],
                "backup_dir": "/test/backup",
                "rotation": {
                    "max_age_days": 7
                }
            }
        }
        mock_load.return_value = config
        yield mock_load

@pytest.fixture
def mock_config_validator():
    with patch('backup_system.config.config_validator.ConfigValidator.validate') as mock_validate:
        yield mock_validate

@pytest.fixture
def mock_backup_service():
    with patch('backup_system.backup.backup_service.BackupService.backup') as mock_backup:
        mock_backup.return_value = True
        yield mock_backup

@pytest.fixture
def mock_rotation_manager():
    with patch('backup_system.backup.rotation_manager.RotationManager.rotate') as mock_rotate:
        yield mock_rotate

@pytest.fixture
def mock_notification_service():
    with patch('backup_system.notifications.notification_service.NotificationService.send') as mock_send:
        yield mock_send

@pytest.fixture
def mock_logger():
    with patch('backup_system.logging.logger.Logger.info') as mock_info, \
         patch('backup_system.logging.logger.Logger.error') as mock_error:
        yield mock_info, mock_error

@pytest.fixture
def backup_system_instance(mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config_loader = ConfigLoader()
    config_validator = ConfigValidator()
    backup_service = BackupService(Logger())
    rotation_manager = RotationManager(Logger())
    logger = Logger()
    notification_service = NotificationService()
    return BackupSystem(config_loader, config_validator, backup_service, rotation_manager, logger, notification_service)

# Tests
def test_run_success(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_not_called()

def test_run_backup_failure(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_backup_service.return_value = False
    backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Backup fallido para /test/source1", level="error")

def test_run_config_validation_error(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_config_validator.side_effect = ValueError("Config error")
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: Config error", level="error")

def test_run_config_load_error(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_config_loader.side_effect = RuntimeError("Load error")
    with pytest.raises(RuntimeError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_not_called()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: Load error", level="error")

def test_run_backup_service_error(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_backup_service.side_effect = Exception("Backup error")
    with pytest.raises(Exception):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: Backup error", level="error")

def test_run_rotation_error(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_rotation_manager.side_effect = Exception("Rotation error")
    backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: Rotation error", level="error")

def test_run_source_dir_not_found(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_backup_service.side_effect = [False, True]
    backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Backup fallido para /test/source1", level="error")

def test_run_backup_dir_not_found(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_backup_service.side_effect = [True, False]
    backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Backup fallido para /test/source2", level="error")

def test_run_backup_service_exception(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_backup_service.side_effect = Exception("Backup error")
    with pytest.raises(Exception):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    assert mock_backup_service.call_count == 2
    mock_rotation_manager.assert_called_once()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: Backup error", level="error")

def test_run_backup_service_no_source_dirs(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": [],
            "backup_dir": "/test/backup",
            "rotation": {
                "max_age_days": 7
            }
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'source_dirs' en 'backup'.", level="error")

def test_run_backup_service_no_backup_dir(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "",
            "rotation": {
                "max_age_days": 7
            }
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'backup_dir' en 'backup'.", level="error")

def test_run_backup_service_no_max_age_days(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "/test/backup",
            "rotation": {}
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'max_age_days' en 'rotation'.", level="error")

def test_run_backup_service_invalid_config(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "/test/backup",
            "rotation": {
                "max_age_days": "invalid"
            }
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'max_age_days' en 'rotation'.", level="error")

def test_run_backup_service_missing_config(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    mock_config_loader.return_value = {}
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'source_dirs' en 'backup'.", level="error")

def test_run_backup_service_missing_backup_dir(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "rotation": {
                "max_age_days": 7
            }
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'backup_dir' en 'backup'.", level="error")

def test_run_backup_service_missing_rotation(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "/test/backup"
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'max_age_days' en 'rotation'.", level="error")

def test_run_backup_service_missing_rotation_max_age_days(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "/test/backup",
            "rotation": {}
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'max_age_days' en 'rotation'.", level="error")

def test_run_backup_service_missing_rotation_max_age_days_invalid_type(backup_system_instance, mock_config_loader, mock_config_validator, mock_backup_service, mock_rotation_manager, mock_notification_service, mock_logger):
    config = {
        "backup": {
            "source_dirs": ["/test/source1"],
            "backup_dir": "/test/backup",
            "rotation": {
                "max_age_days": "invalid"
            }
        }
    }
    mock_config_loader.return_value = config
    with pytest.raises(ValueError):
        backup_system_instance.run("config.yaml")
    mock_config_loader.assert_called_once_with("config.yaml")
    mock_config_validator.assert_called_once()
    mock_backup_service.assert_not_called()
    mock_rotation_manager.assert_not_called()
    mock_notification_service.assert_called_once_with("Error en el proceso de backup: La configuración debe incluir 'max_age_days' en 'rotation'.", level="error")