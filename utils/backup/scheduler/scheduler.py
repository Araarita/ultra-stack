import schedule
import time
from typing import Callable

class Scheduler:
    def run(self, job: Callable) -> None:
        """
        Ejecuta una tarea programada.

        Args:
            job (Callable): Función a ejecutar.
        """
        def job_wrapper():
            try:
                job()
            except Exception as e:
                print(f"Error en la tarea programada: {str(e)}")

        schedule.every().day.at("02:00").do(job_wrapper)

        while True:
            schedule.run_pending()
            time.sleep(1)