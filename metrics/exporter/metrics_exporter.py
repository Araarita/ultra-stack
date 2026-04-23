"""
Ultra Metrics Exporter - Expone metricas Prometheus.
Corre en puerto 9100 y recolecta datos del sistema.
"""
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info


# =============================================
# METRICAS DEFINIDAS
# =============================================

# Estado de servicios (gauge: 1=up, 0=down)
service_up = Gauge("ultra_service_up", "Servicio activo (1=up, 0=down)", ["service", "type"])

# Recursos del sistema
ram_used = Gauge("ultra_ram_used_mb", "RAM usada en MB")
ram_total = Gauge("ultra_ram_total_mb", "RAM total en MB")
ram_pct = Gauge("ultra_ram_percent", "% RAM usada")
disk_pct = Gauge("ultra_disk_percent", "% disco usado")
load_avg = Gauge("ultra_load_avg", "Load average")

# LLM Router
llm_mode_current = Info("ultra_llm_mode", "Modo LLM actual")
llm_requests_total = Counter("ultra_llm_requests_total", "Total requests LLM", ["mode", "task"])
llm_tokens_total = Counter("ultra_llm_tokens_total", "Tokens consumidos", ["mode", "type"])
llm_cost_total = Counter("ultra_llm_cost_usd", "Costo estimado USD", ["mode"])

# Crews ejecutados
crew_executions = Counter("ultra_crew_executions_total", "Crews ejecutados", ["crew_type", "status"])
crew_duration = Histogram("ultra_crew_duration_seconds", "Duracion crews", ["crew_type"])

# Healer events
heal_attempts = Counter("ultra_heal_attempts_total", "Intentos de auto-healing", ["service", "result"])
heal_events_24h = Gauge("ultra_heal_events_last_24h", "Eventos de healing ultimas 24h")

# Letta memory
letta_requests = Counter("ultra_letta_requests_total", "Requests a Letta")
letta_agents_count = Gauge("ultra_letta_agents_count", "Agentes en Letta")


# =============================================
# COLLECTORS
# =============================================

def collect_services():
    """Recolecta estado de servicios."""
    systemd_services = [
        "ultra-bot", "ultra-dashboard", "ultra-backup",
        "ultra-monitor", "ultra-healer", "ultra-learner", "ultra-improver",
        "redis-server", "nexus-cortex"
    ]
    
    for svc in systemd_services:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5
            )
            service_up.labels(service=svc, type="systemd").set(
                1 if r.stdout.strip() == "active" else 0
            )
        except:
            service_up.labels(service=svc, type="systemd").set(0)
    
    # Docker containers
    docker_containers = ["letta"]
    for container in docker_containers:
        try:
            r = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container],
                capture_output=True, text=True, timeout=5
            )
            service_up.labels(service=container, type="docker").set(
                1 if r.stdout.strip() == "running" else 0
            )
        except:
            service_up.labels(service=container, type="docker").set(0)


def collect_resources():
    """Recolecta recursos del sistema."""
    try:
        mem = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
        mem_line = [l for l in mem.split("\n") if l.startswith("Mem:")][0].split()
        ram_used.set(int(mem_line[2]))
        ram_total.set(int(mem_line[1]))
        ram_pct.set((int(mem_line[2]) / int(mem_line[1])) * 100)
    except:
        pass
    
    try:
        # Leer solo la partición raíz con --output específico
        disk = subprocess.run(
            ["df", "-P", "/"],
            capture_output=True, text=True
        ).stdout
        lines = disk.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[-1].split()
            # Última columna antes del mount point es el %
            for p in parts:
                if p.endswith("%"):
                    disk_pct.set(int(p.rstrip("%")))
                    break
    except Exception as e:
        print(f"Error leyendo disco: {e}")
    
    try:
        with open("/proc/loadavg") as f:
            load_avg.set(float(f.read().split()[0]))
    except:
        pass


def collect_llm_mode():
    """Lee el modo actual del router."""
    try:
        mode_file = Path("/opt/ultra/data/current_mode.txt")
        if mode_file.exists():
            mode = mode_file.read_text().strip()
            llm_mode_current.info({"mode": mode})
    except:
        pass


def collect_heal_history():
    """Cuenta eventos de healing en las ultimas 24h."""
    try:
        heal_log = Path("/opt/ultra/data/heal_history.json")
        if heal_log.exists():
            history = json.loads(heal_log.read_text())
            cutoff = datetime.now() - timedelta(hours=24)
            recent = [
                h for h in history
                if datetime.fromisoformat(h.get("timestamp", "2000-01-01")) > cutoff
            ]
            heal_events_24h.set(len(recent))
    except:
        heal_events_24h.set(0)


def collect_letta():
    """Cuenta agentes en Letta."""
    try:
        import httpx
        r = httpx.get("http://localhost:8283/v1/agents/", timeout=5)
        if r.status_code == 200:
            agents = r.json()
            letta_agents_count.set(len(agents))
    except:
        letta_agents_count.set(0)


def collect_all():
    """Ejecuta todos los collectors."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecting metrics...")
    collect_services()
    collect_resources()
    collect_llm_mode()
    collect_heal_history()
    collect_letta()


def main():
    """Inicia el exporter en puerto 9100."""
    PORT = 9100
    print(f"Ultra Metrics Exporter iniciado en puerto {PORT}")
    start_http_server(PORT)
    
    while True:
        try:
            collect_all()
            time.sleep(15)  # Refresca cada 15s
        except KeyboardInterrupt:
            print("Exporter detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(15)


if __name__ == "__main__":
    main()
