import os
import sys
import asyncio
import subprocess
import logging
import re
import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, "/opt/ultra")
load_dotenv("/opt/ultra/.env")

from agents.proposal_system.models import Proposal, Category, Impact, RiskLevel, ProposalStatus
from agents.proposal_system.store import ProposalStore

logger = logging.getLogger(__name__)


class SelfImprovementAgent:
    """Agente que mejora el sistema automaticamente."""

    DEDUP_WINDOW_HOURS = 24

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("BLACKBOX_API_KEY"),
            base_url="https://api.blackbox.ai/v1"
        )
        self.store = ProposalStore()
        self.services_to_monitor = [
            "ultra-bot",
            "ultra-cc",
            "ultra-cc-api",
            "ultra-proposer-api",
            "ultra-monitor",
            "ultra-healer"
        ]
        self.safe_auto_apply = os.getenv("SELF_IMPROVEMENT_AUTO_APPLY_SAFE", "false").lower() in ("1", "true", "yes", "on")

    async def collect_errors(self, since_minutes: int = 10) -> list:
        """Recopila errores y warnings de los servicios en los ultimos N minutos."""
        findings = []

        for service in self.services_to_monitor:
            try:
                cmd = (
                    f"journalctl -u {service} --since '{since_minutes} minutes ago' "
                    f"-p warning --no-pager 2>/dev/null | tail -60"
                )
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=10
                )
                output = (result.stdout or "").strip()

                if output and len(output) > 10:
                    findings.append({
                        "service": service,
                        "errors": output,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error checking {service}: {e}")

        return findings

    async def analyze_errors(self, errors: list) -> list:
        """Analiza errores y genera propuestas de fix."""
        if not errors:
            return []

        errors_summary = "\n\n".join([
            f"### {e['service']}\n{e['errors'][:1500]}"
            for e in errors
        ])

        prompt = f"""Analiza estos errores/warnings del sistema Ultra Stack y genera hasta 3 propuestas de fix.

ERRORES DETECTADOS:
{errors_summary}

Responde SOLO JSON con esta estructura:
{{
  "proposals": [
    {{
      "title": "titulo corto del fix",
      "description": "que problema resuelve y como",
      "benefit": "beneficio concreto",
      "category": "improvement",
      "impact": "high",
      "effort": "low",
      "risk_level": "safe",
      "action_type": "modify",
      "action_code": "comando shell para arreglar el problema",
      "estimated_time_seconds": 30
    }}
  ]
}}

REGLAS:
- category: solo improvement, maintenance, security
- impact: critical, high, medium, low
- risk_level: solo safe o low
- action_code: comandos seguros (systemctl restart, ls, cat, echo, journalctl, grep)
- NO generes codigo destructivo (rm -rf, dd, mkfs, shutdown, reboot, kill -9 masivo, chmod/chown recursivo amplio)
- Solo incluye propuestas que realmente arreglen el problema"""

        try:
            response = self.client.chat.completions.create(
                model="blackboxai/anthropic/claude-opus-4.7",
                messages=[
                    {"role": "system", "content": "Eres un experto en DevOps y Linux. Solo respondes JSON valido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )

            text = (response.choices[0].message.content or "").strip()

            if text.startswith("```"):
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1]
                    if text.startswith("json"):
                        text = text[4:].strip()

            data = json.loads(text)
            proposals = data.get("proposals", [])
            if not isinstance(proposals, list):
                return []
            return proposals

        except Exception as e:
            logger.error(f"Error analyzing: {e}")
            return []

    def _is_safe_command(self, cmd: str) -> bool:
        if not cmd or not isinstance(cmd, str):
            return False
        lowered = cmd.lower().strip()

        banned_patterns = [
            r"\brm\s+-rf\b",
            r"\bdd\b",
            r"\bmkfs\b",
            r"\bshutdown\b",
            r"\breboot\b",
            r":\(\)\s*\{\s*:\|\:&\s*\}\s*;",
            r"\bchmod\s+-r\b",
            r"\bchown\s+-r\b",
            r">\s*/dev/sd[a-z]",
            r"\bkillall\b",
            r"\bpkill\b"
        ]
        for pat in banned_patterns:
            if re.search(pat, lowered):
                return False

        allowed_starts = (
            "systemctl ",
            "journalctl ",
            "grep ",
            "cat ",
            "echo ",
            "ls ",
            "sed ",
            "awk ",
            "tail ",
            "head ",
            "python ",
            "/usr/bin/systemctl ",
            "/bin/systemctl "
        )
        return lowered.startswith(allowed_starts)

    @staticmethod
    def _compute_proposal_hash(title: str, description: str) -> str:
        """Genera un hash estable a partir de title + description normalizados."""
        normalized_title = (title or "").strip().lower()
        normalized_desc = (description or "").strip().lower()
        payload = f"{normalized_title}|{normalized_desc}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _get_recent_hashes(self, hours: int = DEDUP_WINDOW_HOURS) -> set:
        """Devuelve el set de hashes de propuestas creadas en las ultimas N horas."""
        recent_hashes: set = set()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        try:
            data = self.store._read_data()
        except Exception as e:
            logger.error(f"Could not read existing proposals for dedup: {e}")
            return recent_hashes

        for item in data:
            try:
                created_raw = item.get("created_at")
                created_dt = self.store._parse_datetime(created_raw) if created_raw else None

                if created_dt is not None:
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    if created_dt < cutoff:
                        continue

                title = item.get("title", "") or ""
                description = item.get("description", "") or ""
                recent_hashes.add(self._compute_proposal_hash(title, description))
            except Exception as e:
                logger.debug(f"Skipping proposal during dedup scan: {e}")
                continue

        logger.info(f"Loaded {len(recent_hashes)} recent proposal hashes (window={hours}h)")
        return recent_hashes

    async def create_proposals(self, raw_proposals: list) -> int:
        """Convierte propuestas raw a objetos Proposal y guarda, evitando duplicados."""
        count = 0
        skipped_duplicates = 0
        recent_hashes = self._get_recent_hashes(self.DEDUP_WINDOW_HOURS)

        for raw in raw_proposals:
            try:
                if "category" in raw and raw["category"] not in ["capability", "improvement", "maintenance", "insight", "security", "experience"]:
                    raw["category"] = "improvement"

                if "risk_level" in raw and raw["risk_level"] not in ["safe", "low", "medium", "high"]:
                    raw["risk_level"] = "low"

                if "action_code" in raw and not self._is_safe_command(raw["action_code"]):
                    logger.warning(f"Rejected unsafe proposal action_code: {raw.get('title', 'untitled')}")
                    continue

                title = raw.get("title", "") or ""
                description = raw.get("description", "") or ""
                proposal_hash = self._compute_proposal_hash(title, description)

                if proposal_hash in recent_hashes:
                    skipped_duplicates += 1
                    logger.info(
                        f"Skipping duplicate proposal (hash={proposal_hash[:12]}): {title!r}"
                    )
                    continue

                proposal = Proposal(**raw)
                self.store.save(proposal)
                recent_hashes.add(proposal_hash)
                count += 1
                logger.info(f"Created proposal: {proposal.title} (hash={proposal_hash[:12]})")
            except Exception as e:
                logger.error(f"Error creating proposal: {e}")
                continue

        if skipped_duplicates:
            logger.info(f"Anti-duplicate: skipped {skipped_duplicates} proposal(s) already seen in last {self.DEDUP_WINDOW_HOURS}h")

        return count

    async def auto_execute_safe_fixes(self, raw_proposals: list) -> int:
        """Opcionalmente ejecuta fixes safe."""
        if not self.safe_auto_apply:
            return 0

        executed = 0
        for raw in raw_proposals:
            try:
                risk = str(raw.get("risk_level", "")).lower()
                cmd = raw.get("action_code", "")
                if risk != "safe":
                    continue
                if not self._is_safe_command(cmd):
                    continue

                logger.info(f"Auto-executing safe fix: {raw.get('title', 'untitled')} -> {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    executed += 1
                    logger.info(f"Safe fix executed OK: {raw.get('title', 'untitled')}")
                else:
                    logger.warning(f"Safe fix failed: {raw.get('title', 'untitled')} rc={result.returncode} stderr={result.stderr[:300]}")
            except Exception as e:
                logger.error(f"Error auto-executing fix: {e}")

        return executed

    async def run_improvement_cycle(self) -> dict:
        """Ejecuta un ciclo completo de mejora."""
        logger.info("Starting improvement cycle")

        errors = await self.collect_errors(since_minutes=10)
        logger.info(f"Collected findings from {len(errors)} services")

        if not errors:
            return {"status": "no_errors", "proposals_created": 0, "auto_executed": 0}

        raw_proposals = await self.analyze_errors(errors)
        logger.info(f"Generated {len(raw_proposals)} proposal candidates")

        count = await self.create_proposals(raw_proposals)
        auto_executed = await self.auto_execute_safe_fixes(raw_proposals)

        return {
            "status": "completed",
            "errors_found": len(errors),
            "proposals_created": count,
            "auto_executed": auto_executed,
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Loop principal del agente."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    agent = SelfImprovementAgent()

    while True:
        try:
            result = await agent.run_improvement_cycle()
            logger.info(f"Cycle result: {result}")
        except Exception as e:
            logger.error(f"Cycle error: {e}")

        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())
