"""
Improver Agent - Auto-mejora del sistema basado en patrones aprendidos.
Analiza el Learner, convoca al Code Crew, propone fixes, pide aprobacion humana.
"""
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
import httpx

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")


class Improver:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
        self.owner_id = os.getenv("TELEGRAM_OWNER_CHAT_ID")
        self.improvements_file = Path("/opt/ultra/data/improvements.json")
        self.improvements_file.parent.mkdir(parents=True, exist_ok=True)
        self.patterns_file = Path("/opt/ultra/data/learned_patterns.json")
    
    def load_improvements(self):
        if self.improvements_file.exists():
            try:
                return json.loads(self.improvements_file.read_text())
            except:
                return []
        return []
    
    def save_improvements(self, improvements):
        self.improvements_file.write_text(json.dumps(improvements, indent=2, default=str))
    
    def notify(self, message):
        if not self.bot_token or not self.owner_id:
            return
        try:
            httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.owner_id, "text": f"Improver\n\n{message}"},
                timeout=10
            )
        except:
            pass
    
    def get_critical_patterns(self):
        """Obtiene patrones criticos del Learner."""
        if not self.patterns_file.exists():
            return []
        try:
            data = json.loads(self.patterns_file.read_text())
            insights = data.get("insights", [])
            # Filtrar solo los criticos y altos
            return [i for i in insights if i.get("severity") in ["high", "medium"]]
        except:
            return []
    
    def generate_improvement_task(self, pattern):
        """Convierte un pattern en una tarea para el Code Crew."""
        severity = pattern.get("severity")
        msg = pattern.get("message", "")
        service = pattern.get("service", "")
        
        if pattern.get("type") == "repeat_failure":
            return f"El servicio {service} esta fallando repetidamente. Analiza los logs en journalctl -u {service}, identifica la causa raiz y genera un fix permanente que prevenga el problema. Genera codigo Python mejorado si es necesario."
        
        elif pattern.get("type") == "time_pattern":
            hour = pattern.get("hour")
            return f"Se detectaron fallos repetidos a las {hour}:00. Revisa si hay cron jobs, scheduled tasks o procesos que podrian estar chocando. Propone una solucion: mover horarios, aumentar timeouts, o agregar retry logic."
        
        elif pattern.get("type") == "instability":
            return f"El servicio {service} se reinicia constantemente. Analiza los logs, detecta si hay memory leaks, deadlocks, o bugs recurrentes. Genera un fix permanente."
        
        return f"Analiza este patron del sistema: {msg}. Propone una mejora de codigo que lo resuelva permanentemente."
    
    def call_code_crew(self, task_description):
        """Convoca al Code Crew para generar un fix."""
        try:
            from crews.code.code_crew import run_code_task
            print(f"[IMPROVER] Convocando Code Crew: {task_description[:80]}")
            result = run_code_task(task_description)
            return result
        except Exception as e:
            return f"Error convocando Code Crew: {e}"
    
    def propose_improvement(self, pattern):
        """Propone una mejora al owner via Telegram."""
        task = self.generate_improvement_task(pattern)
        
        # Notificar inicio
        self.notify(f"Detecte un patron que requiere mejora:\n\n{pattern.get('message')}\n\nConvocando Code Crew para analisis...")
        
        # Generar fix con Code Crew
        fix = self.call_code_crew(task)
        
        # Guardar propuesta
        proposal = {
            "id": f"improvement_{int(time.time())}",
            "pattern": pattern,
            "task": task,
            "fix_proposal": fix[:3000],  # Primeras 3000 chars
            "status": "pending_approval",
            "created_at": datetime.now().isoformat(),
        }
        
        improvements = self.load_improvements()
        improvements.append(proposal)
        self.save_improvements(improvements)
        
        # Notificar resultado
        summary = f"Propuesta de mejora lista\n\nPatron: {pattern.get('message')}\n\nID: {proposal['id']}\n\nRevisa /opt/ultra/data/improvements.json\n\nResponde con: /approve {proposal['id']} o /reject {proposal['id']}"
        self.notify(summary)
        
        return proposal
    
    def run_cycle(self):
        """Ejecuta un ciclo de mejora completo."""
        print(f"\n[IMPROVER] Iniciando ciclo...")
        
        patterns = self.get_critical_patterns()
        
        if not patterns:
            print("[IMPROVER] Sin patrones criticos, nada que mejorar")
            return {"status": "no_patterns"}
        
        # Verificar si ya se propuso algo para este pattern en las ultimas 24h
        improvements = self.load_improvements()
        recent_proposals = [
            i for i in improvements
            if datetime.fromisoformat(i["created_at"]) > datetime.now().replace(hour=0, minute=0)
        ]
        recent_messages = {i["pattern"].get("message") for i in recent_proposals}
        
        # Filtrar patterns ya propuestos hoy
        new_patterns = [p for p in patterns if p.get("message") not in recent_messages]
        
        if not new_patterns:
            print("[IMPROVER] Todos los patrones ya tienen propuestas recientes")
            return {"status": "already_proposed"}
        
        # Procesar solo el mas critico (1 por ciclo para no abrumar)
        most_critical = sorted(
            new_patterns,
            key=lambda p: {"high": 3, "medium": 2, "low": 1}.get(p.get("severity"), 0),
            reverse=True
        )[0]
        
        proposal = self.propose_improvement(most_critical)
        
        return {
            "status": "proposed",
            "proposal_id": proposal["id"],
            "pattern": most_critical.get("message"),
        }


def improve_loop(interval=86400):
    """Loop de mejora - cada 24h por defecto."""
    improver = Improver()
    print(f"Improver iniciado - ciclo cada {interval}s ({interval//3600}h)")
    
    while True:
        try:
            result = improver.run_cycle()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Improver: {result.get('status')}")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Improver detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    improver = Improver()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "once":
            result = improver.run_cycle()
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "loop":
            improve_loop(int(sys.argv[2]) if len(sys.argv) > 2 else 86400)
        elif cmd == "list":
            improvements = improver.load_improvements()
            print(f"Total propuestas: {len(improvements)}\n")
            for imp in improvements[-10:]:
                print(f"  [{imp['status']}] {imp['id']}")
                print(f"    Pattern: {imp['pattern'].get('message', '')[:100]}")
                print(f"    Creado: {imp['created_at']}\n")
    else:
        improve_loop(86400)
