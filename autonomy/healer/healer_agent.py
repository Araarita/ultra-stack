"""Healer Agent - Auto-corrección de problemas detectados."""
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
import httpx
import os
import sys

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")


# Base de conocimiento de fixes conocidos
KNOWN_FIXES = {
    "ultra-bot": {
        "restart": ["systemctl", "restart", "ultra-bot"],
        "check": ["systemctl", "is-active", "ultra-bot"],
        "logs": ["journalctl", "-u", "ultra-bot", "-n", "20", "--no-pager"],
    },
    "ultra-dashboard": {
        "restart": ["systemctl", "restart", "ultra-dashboard"],
        "check": ["systemctl", "is-active", "ultra-dashboard"],
        "logs": ["journalctl", "-u", "ultra-dashboard", "-n", "20", "--no-pager"],
    },
    "ultra-backup": {
        "restart": ["systemctl", "restart", "ultra-backup"],
        "check": ["systemctl", "is-active", "ultra-backup"],
        "logs": ["journalctl", "-u", "ultra-backup", "-n", "20", "--no-pager"],
    },
    "letta": {
        "restart": ["docker", "restart", "letta"],
        "check": ["docker", "inspect", "--format", "{{.State.Status}}", "letta"],
        "logs": ["docker", "logs", "letta", "--tail", "20"],
    },
    "redis-server": {
        "restart": ["systemctl", "restart", "redis-server"],
        "check": ["systemctl", "is-active", "redis-server"],
        "logs": ["journalctl", "-u", "redis-server", "-n", "20", "--no-pager"],
    },
    "nexus-cortex": {
        "restart": ["systemctl", "restart", "nexus-cortex"],
        "check": ["systemctl", "is-active", "nexus-cortex"],
        "logs": ["journalctl", "-u", "nexus-cortex", "-n", "20", "--no-pager"],
    },
}


class Healer:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
        self.owner_id = os.getenv("TELEGRAM_OWNER_CHAT_ID")
        self.heal_log = Path("/opt/ultra/data/heal_history.json")
        self.heal_log.parent.mkdir(parents=True, exist_ok=True)
    
    def notify(self, message):
        if not self.bot_token or not self.owner_id:
            return
        try:
            httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.owner_id, "text": f"Healer\n\n{message}"},
                timeout=10
            )
        except:
            pass
    
    def log_action(self, action):
        history = []
        if self.heal_log.exists():
            try:
                history = json.loads(self.heal_log.read_text())
            except:
                pass
        history.append({**action, "timestamp": datetime.now().isoformat()})
        history = history[-100:]
        self.heal_log.write_text(json.dumps(history, indent=2, default=str))
    
    def is_service_alive(self, service):
        fix_config = KNOWN_FIXES.get(service)
        if not fix_config:
            return None
        try:
            r = subprocess.run(fix_config["check"], capture_output=True, text=True, timeout=10)
            output = r.stdout.strip()
            return output == "active" or output == "running"
        except:
            return False
    
    def get_recent_logs(self, service):
        fix_config = KNOWN_FIXES.get(service)
        if not fix_config:
            return ""
        try:
            r = subprocess.run(fix_config["logs"], capture_output=True, text=True, timeout=10)
            return r.stdout[-2000:]
        except:
            return ""
    
    def attempt_restart(self, service):
        fix_config = KNOWN_FIXES.get(service)
        if not fix_config:
            return {"success": False, "reason": "servicio desconocido"}
        
        print(f"[HEAL] Intentando restart de {service}")
        try:
            r = subprocess.run(fix_config["restart"], capture_output=True, text=True, timeout=30)
            time.sleep(5)
            
            alive = self.is_service_alive(service)
            return {
                "success": bool(alive),
                "action": "restart",
                "service": service,
                "return_code": r.returncode,
                "stderr": r.stderr[:500] if r.stderr else "",
            }
        except Exception as e:
            return {"success": False, "action": "restart", "service": service, "error": str(e)}
    
    def heal(self, service):
        """Intenta sanar un servicio - pipeline completo."""
        print(f"\n[HEALER] Diagnosticando {service}...")
        
        # Paso 1: ¿ya está vivo?
        if self.is_service_alive(service):
            print(f"[HEALER] {service} ya esta vivo, nada que hacer")
            return {"service": service, "status": "already_healthy"}
        
        # Paso 2: intento de restart
        result = self.attempt_restart(service)
        self.log_action(result)
        
        if result["success"]:
            msg = f"{service} RESTAURADO exitosamente (restart)"
            print(f"[HEALER] {msg}")
            self.notify(msg)
            return {"service": service, "status": "healed", "method": "restart"}
        
        # Paso 3: restart falló, obtener logs
        logs = self.get_recent_logs(service)
        print(f"[HEALER] Restart fallo, analizando logs...")
        
        # Paso 4: notificar al owner con info para intervención manual
        error_msg = f"NO PUDE SANAR: {service}\n\nLogs recientes:\n{logs[-800:]}\n\nRevisa manualmente o convoca Code Crew."
        print(f"[HEALER] {service} requiere intervencion manual")
        self.notify(error_msg)
        
        self.log_action({
            "service": service,
            "status": "failed",
            "logs_sample": logs[-500:],
            "severity": "critical",
        })
        
        return {"service": service, "status": "failed", "logs": logs[-500:]}
    
    def heal_all_unhealthy(self):
        """Lee el estado del monitor y sana todo lo caido."""
        state_file = Path("/opt/ultra/data/health_state.json")
        if not state_file.exists():
            print("[HEALER] No hay health_state.json - monitor no ha corrido aun")
            return {"status": "no_state"}
        
        try:
            state = json.loads(state_file.read_text())
        except:
            return {"status": "invalid_state"}
        
        results = []
        for service_name, service_info in state.items():
            # Saltar checks http que no son servicios reales
            if service_info.get("type") == "http":
                continue
            
            if not service_info.get("healthy", True):
                result = self.heal(service_name)
                results.append(result)
                time.sleep(2)
        
        if not results:
            return {"status": "all_healthy"}
        
        healed = sum(1 for r in results if r.get("status") == "healed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        
        summary = f"Healer Cycle\n\nSanados: {healed}\nFallaron: {failed}\nTotal: {len(results)}"
        if results:
            self.notify(summary)
        
        return {"status": "completed", "results": results, "healed": healed, "failed": failed}


def heal_loop(interval=120):
    """Loop infinito de auto-healing."""
    healer = Healer()
    print(f"Healer iniciado - ciclo cada {interval}s")
    
    while True:
        try:
            result = healer.heal_all_unhealthy()
            if result.get("healed", 0) > 0 or result.get("failed", 0) > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Healer: +{result['healed']} sanados, -{result['failed']} fallaron")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Healer detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    healer = Healer()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "heal" and len(sys.argv) > 2:
            result = healer.heal(sys.argv[2])
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "all":
            result = healer.heal_all_unhealthy()
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "loop":
            heal_loop(int(sys.argv[2]) if len(sys.argv) > 2 else 120)
        else:
            print("Uso: healer.py [heal <servicio>|all|loop [seg]]")
    else:
        heal_loop(120)
