import yaml
from typing import Dict, Optional

class ConfigLoader:
    def load(self, config_path: str) -> Dict:
        """
        Carga la configuración desde un archivo YAML.

        Args:
            config_path (str): Ruta al archivo de configuración.

        Returns:
            Dict: Diccionario con la configuración cargada.
        """
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            return config
        except Exception as e:
            raise RuntimeError(f"Error al cargar la configuración: {str(e)}")