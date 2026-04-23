"""Monitor Agent - Vigilancia 24/7 del sistema Ultra."""
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import httpx
import os
import sys

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")


class HealthCheck:
    def __init__(self):
        self.state_file = Path("/opt/ultra/data/health_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.alert_bot_token = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
        self.owner_id = os.getenv("TELEGRAM_OWNER_CHAT_ID")
        self.last_state = self._load_state()
    
    def _load_state(self):
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except:
                return {}
        return {}
    
    def _save_state(self, state):
        self.state_file.write_text(json.dumps(state, indent=2, default=str))
    
    def check_systemd(self, service):
        try:
            r = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            active = r.stdout.strip() == "active"
            restarts = 0
            if active:
                try:
                    r2 = subprocess.run(
                        ["systemctl", "show", service, "--property=NRestarts"],
                        capture_output=True, text=True, timeout=5
                    )
                    for line in r2.stdout.split("\n"):
                        if "NRestarts=" in line:
                            restarts = int(line.split("=")[1])
                except:
                    pass
            return {
                "service": service,
                "type": "systemd",
                "active": active,
                "restarts": restarts,
                "healthy": active and restarts < 10,
            }
        except Exception as e:
            return {"service": service, "type": "systemd", "active": False, "error": str(e), "healthy": False}
    
    def check_docker(self, container):
        try:
            r = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}|{{.RestartCount}}", container],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return {"service": container, "type": "docker", "active": False, "healthy": False}
            parts = r.stdout.strip().split("|")
            status = parts[0] if parts else "unknown"
            restarts = int(parts[1]) if len(parts) > 1 else 0
            return {
                "service": container,
                "type": "docker",
                "active": status == "running",
                "restarts": restarts,
                "healthy": status == "running" and restarts < 10,
            }
        except Exception as e:
            return {"service": container, "type": "docker", "active": False, "error": str(e), "healthy": False}
    
    def check_http(self, url, name):
        try:
            r = httpx.get(url, timeout=5, follow_redirects=True)
            return {
                "service": name,
                "type": "http",
                "active": r.status_code == 200,
                "status_code": r.status_code,
                "response_ms": r.elapsed.total_seconds() * 1000,
                "healthy": (200 <= r.status_code < 400) and r.elapsed.total_seconds() < 5,
            }
        except Exception as e:
            return {"service": name, "type": "http", "active": False, "error": str(e)[:100], "healthy": False}
    
    def check_resources(self):
        try:
            mem = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
            mem_line = [l for l in mem.split("\n") if l.startswith("Mem:")][0].split()
            total_mem = int(mem_line[1])
            used_mem = int(mem_line[2])
            mem_pct = (used_mem / total_mem) * 100
            
            disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout
            disk_line = disk.split("\n")[1].split()
            disk_pct = int(disk_line[4].rstrip("%"))
            
            with open("/proc/loadavg") as f:
                load = float(f.read().split()[0])
            
            return {
                "ram_used_mb": used_mem,
                "ram_total_mb": total_mem,
                "ram_pct": round(mem_pct, 1),
                "disk_pct": disk_pct,
                "load_avg": load,
                "healthy": mem_pct < 90 and disk_pct < 90 and load < 10,
            }
        except Exception as e:
            return {"error": str(e), "healthy": True}
    
    def send_alert(self, message, severity="warning"):
        if not self.alert_bot_token or not self.owner_id:
            return
        emoji = {"critical": "ALERT", "warning": "WARN", "info": "OK"}.get(severity, "!")
        text = f"Monitor Alert [{emoji}]\n\n{message}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            httpx.post(
                f"https://api.telegram.org/bot{self.alert_bot_token}/sendMessage",
                json={"chat_id": self.owner_id, "text": text},
                timeout=10
            )
        except Exception as e:
            print(f"Alert send failed: {e}")
    
    def run_full_check(self):
        results = {
            "timestamp": datetime.now().isoformat(),
            "services": [],
            "resources": {},
            "alerts": [],
        }
        
        for svc in ["ultra-bot", "ultra-dashboard", "ultra-backup", "redis-server", "nexus-cortex"]:
            results["services"].append(self.check_systemd(svc))
        
        results["services"].append(self.check_docker("letta"))
        results["services"].append(self.check_http("http://localhost:8501", "dashboard-http"))
        results["services"].append(self.check_http("http://localhost:8283/v1/health", "letta-api"))
        
        results["resources"] = self.check_resources()
        
        for svc in results["services"]:
            name = svc["service"]
            was_healthy = self.last_state.get(name, {}).get("healthy", True)
            is_healthy = svc.get("healthy", False)
            
            if was_healthy and not is_healthy:
                results["alerts"].append({
                    "severity": "critical",
                    "message": f"{name} CAIDO ({svc.get('error', 'down')})",
                })
            elif not was_healthy and is_healthy:
                results["alerts"].append({
                    "severity": "info",
                    "message": f"{name} RECUPERADO",
                })
        
        res = results["resources"]
        if res.get("ram_pct", 0) > 90:
            results["alerts"].append({
                "severity": "critical",
                "message": f"RAM al {res['ram_pct']}%"
            })
        if res.get("disk_pct", 0) > 90:
            results["alerts"].append({
                "severity": "critical",
                "message": f"Disco al {res['disk_pct']}%"
            })
        
        for alert in results["alerts"]:
            self.send_alert(alert["message"], alert["severity"])
        
        new_state = {svc["service"]: svc for svc in results["services"]}
        self._save_state(new_state)
        self.last_state = new_state
        
        return results


def monitor_loop(interval=60):
    checker = HealthCheck()
    print(f"Monitor iniciado - check cada {interval}s")
    
    while True:
        try:
            result = checker.run_full_check()
            all_healthy = all(s.get("healthy", False) for s in result["services"])
            total = len(result["services"])
            healthy_count = sum(1 for s in result["services"] if s.get("healthy", False))
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {healthy_count}/{total} services OK | RAM {result['resources'].get('ram_pct', 0)}% | Alerts: {len(result['alerts'])}")
            
            history_dir = Path("/opt/ultra/data/monitor_history")
            history_dir.mkdir(parents=True, exist_ok=True)
            (history_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}.json").write_text(
                json.dumps(result, indent=2, default=str)
            )
            
            cutoff = datetime.now() - timedelta(hours=24)
            for f in history_dir.glob("*.json"):
                try:
                    file_time = datetime.strptime(f.stem, "%Y%m%d_%H%M")
                    if file_time < cutoff:
                        f.unlink()
                except:
                    pass
            
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Monitor detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        checker = HealthCheck()
        result = checker.run_full_check()
        print(json.dumps(result, indent=2, default=str))
    else:
        monitor_loop(60)
