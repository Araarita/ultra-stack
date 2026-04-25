import asyncio
import logging
from typing import Any

from .models import Proposal, ProposalStatus
from .store import ProposalStore


class ProposalExecutor:
    """Ejecutor de propuestas para el sistema de automatización."""

    def __init__(self) -> None:
        """Inicializa el ejecutor con su almacenamiento y logger."""
        self.store: ProposalStore = ProposalStore()
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def execute(self, proposal_id: str) -> dict[str, Any]:
        """Ejecuta una propuesta aprobada por su ID.

        Args:
            proposal_id: Identificador único de la propuesta.

        Returns:
            Resultado de la ejecución con estado, éxito y salida/error.
        """
        self.logger.info("Iniciando ejecución de propuesta: %s", proposal_id)
        proposal: Proposal | None = await self.store.get_by_id(proposal_id)

        if proposal is None:
            self.logger.error("Propuesta no encontrada: %s", proposal_id)
            return {"success": False, "error": "Not found"}

        if proposal.status != ProposalStatus.APPROVED:
            self.logger.error(
                "Propuesta no aprobada. id=%s status=%s",
                proposal_id,
                proposal.status,
            )
            return {"success": False, "error": "Not approved"}

        proposal.status = ProposalStatus.EXECUTING
        await self.store.update_status(proposal.id, ProposalStatus.EXECUTING)
        self.logger.debug("Status actualizado a EXECUTING para id=%s", proposal_id)

        try:
            timeout_seconds: int = int(getattr(proposal, "estimated_time_seconds", 60) or 60)
            self.logger.info(
                "Ejecutando action_code para id=%s con timeout=%s",
                proposal_id,
                timeout_seconds,
            )

            process = await asyncio.create_subprocess_shell(
                proposal.action_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )

            stdout: str = stdout_bytes.decode(errors="replace").strip()
            stderr: str = stderr_bytes.decode(errors="replace").strip()
            returncode: int = int(process.returncode or 0)

            if returncode == 0:
                proposal.status = ProposalStatus.COMPLETED
                await self.store.update_status(proposal.id, ProposalStatus.COMPLETED)
                await self.store.add_execution_log(
                    proposal.id,
                    {
                        "status": "completed",
                        "returncode": returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                    },
                )
                self.logger.info("Ejecución completada id=%s", proposal_id)
                return {"success": True, "output": stdout, "status": "completed"}

            proposal.status = ProposalStatus.FAILED
            await self.store.update_status(proposal.id, ProposalStatus.FAILED)
            await self.store.add_execution_log(
                proposal.id,
                {
                    "status": "failed",
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )
            self.logger.error(
                "Ejecución fallida id=%s returncode=%s stderr=%s",
                proposal_id,
                returncode,
                stderr,
            )
            return {"success": False, "error": stderr, "status": "failed"}

        except Exception as e:
            proposal.status = ProposalStatus.FAILED
            await self.store.update_status(proposal.id, ProposalStatus.FAILED)
            self.logger.error("Excepción ejecutando id=%s error=%s", proposal_id, str(e))
            return {"success": False, "error": str(e)}

    async def execute_pending_safe(self) -> list[dict[str, Any]]:
        """Ejecuta propuestas pendientes de riesgo seguro con autoaprobación activa.

        Returns:
            Lista de resultados de ejecución por propuesta procesada.
        """
        self.logger.info("Buscando propuestas pendientes seguras para ejecutar")
        proposals: list[Proposal] = await self.store.list_pending_safe()
        results: list[dict[str, Any]] = []

        for proposal in proposals:
            self.logger.debug(
                "Evaluando propuesta id=%s risk_level=%s auto_approve_safe=%s status=%s",
                proposal.id,
                getattr(proposal, "risk_level", None),
                getattr(proposal, "auto_approve_safe", False),
                proposal.status,
            )
            if bool(getattr(proposal, "auto_approve_safe", False)):
                result = await self.execute(proposal.id)
                results.append(result)

        self.logger.info("Ejecución de propuestas seguras finalizada. total=%s", len(results))
        return results