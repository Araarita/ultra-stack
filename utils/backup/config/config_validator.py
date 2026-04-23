from typing import Dict, Optional

class ConfigValidator:
    def validate(self, config: Dict) -> None:
        """
        Valida que la configuración sea correcta.

        Args:
            config (Dict): Configuración a validar.

        Raises:
            ValueError: Si la configuración es inválida.
        """
        if not config.get("backup", {}).get("source_dirs"):
            raise ValueError("La configuración debe incluir 'source_dirs' en 'backup'.")
        if not config.get("backup", {}).get("backup_dir"):
            raise ValueError("La configuración debe incluir 'backup_dir' en 'backup'.")
        if not config.get("backup", {}).get("rotation", {}).get("max_age_days"):
            raise ValueError("La configuración debe incluir 'max_age_days' en 'rotation'.")