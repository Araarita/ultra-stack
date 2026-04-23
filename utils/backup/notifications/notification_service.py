from typing import Optional

class NotificationService:
    def send(self, message: str, level: str = "info") -> None:
        """
        Envía una notificación.

        Args:
            message (str): Mensaje a enviar.
            level (str, optional): Nivel de la notificación (info, error, warning). Defaults to "info".
        """
        # Implementación de notificación (ej. correo, SMS, webhook)
        # Para este ejemplo, solo se imprime en consola
        print(f"[{level.upper()}] {message}")