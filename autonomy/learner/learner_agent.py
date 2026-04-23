"""
Learner Agent - Aprende de errores pasados y previene repeticiones.
Guarda patterns en Letta para reconocimiento futuro.
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")

from letta_client import Letta, MessageCreate

LEARNER_AGENT_NAME = "ultra-learner"
AGENT_ERIK_ID = "agent-ea61e976-a19f-49d4-b4f3-1e66214b1258"


class Learner:
    def __init__(self):
        self.letta = Letta(base_url="http://localhost:8283")
        self.patterns_file = Path("/opt/ultra/data/learned_patterns.json")
        self.patterns_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_patterns(self):
        if self.patterns_file.exists():
            try:
                return json.loads(self.patterns_file.read_text())
            except:
                return {}
        return {}
    
    def save_patterns(self, patterns):
        self.patterns_file.write_text(json.dumps(patterns, indent=2, default=str))
    
    def analyze_heal_history(self):
        """Analiza el historial del healer y extrae patrones."""
        heal_log = Path("/opt/ultra/data/heal_history.json")
        if not heal_log.exists():
            return {"status": "no_history"}
        
        try:
            history = json.loads(heal_log.read_text())
        except:
            return {"status": "invalid_history"}
        
        if not history:
            return {"status": "empty"}
        
        # Contar fallos por servicio
        failures_by_service = Counter()
        success_by_service = Counter()
        failures_by_hour = Counter()
        
        for event in history:
            service = event.get("service", "unknown")
            status = event.get("status", "")
            
            if status == "healed" or event.get("success"):
                success_by_service[service] += 1
            else:
                failures_by_service[service] += 1
            
            ts = event.get("timestamp", "")
            if ts:
                try:
                    hour = datetime.fromisoformat(ts).hour
                    failures_by_hour[hour] += 1
                except:
                    pass
        
        # Detectar patrones
        patterns = {
            "analyzed_at": datetime.now().isoformat(),
            "total_events": len(history),
            "last_24h_events": sum(
                1 for e in history 
                if datetime.fromisoformat(e.get("timestamp", "2000-01-01")) > datetime.now() - timedelta(hours=24)
            ),
            "top_failing_services": failures_by_service.most_common(5),
            "top_recovering_services": success_by_service.most_common(5),
            "failure_distribution_by_hour": dict(failures_by_hour.most_common(5)),
            "insights": [],
        }
        
        # Generar insights
        if failures_by_service:
            top_fail, fail_count = failures_by_service.most_common(1)[0]
            if fail_count >= 3:
                patterns["insights"].append({
                    "type": "repeat_failure",
                    "severity": "high",
                    "message": f"Servicio {top_fail} fallo {fail_count} veces. Investigar causa raiz.",
                    "service": top_fail,
                })
        
        if failures_by_hour:
            peak_hour, peak_count = failures_by_hour.most_common(1)[0]
            if peak_count >= 3:
                patterns["insights"].append({
                    "type": "time_pattern",
                    "severity": "medium",
                    "message": f"Mayoria de fallos ocurren a las {peak_hour}:00 (total {peak_count}). Posible cron conflictivo.",
                    "hour": peak_hour,
                })
        
        # Si un servicio tiene muchos restarts exitosos, es inestable
        for service, count in success_by_service.items():
            if count >= 5:
                patterns["insights"].append({
                    "type": "instability",
                    "severity": "medium",
                    "message": f"{service} fue restaurado {count} veces. Posible bug cronico, revisar logs.",
                    "service": service,
                })
        
        return patterns
    
    def store_in_letta(self, patterns):
        """Guarda los patrones en la memoria persistente de Letta."""
        insights_text = "\n".join(
            f"- [{i['severity']}] {i['message']}"
            for i in patterns.get("insights", [])
        )
        
        message = f"""REPORTE DE APRENDIZAJE DEL SISTEMA (Learner)

Total eventos analizados: {patterns['total_events']}
Eventos ultimas 24h: {patterns['last_24h_events']}

Servicios que mas fallan:
{json.dumps(patterns['top_failing_services'], indent=2)}

Distribucion por hora:
{json.dumps(patterns['failure_distribution_by_hour'], indent=2)}

INSIGHTS DETECTADOS:
{insights_text if insights_text else '(sin patrones significativos aun)'}

Recuerda estos patrones para futuras decisiones."""
        
        try:
            self.letta.agents.messages.create(
                agent_id=AGENT_ERIK_ID,
                messages=[MessageCreate(role="user", content=message)]
            )
            return True
        except Exception as e:
            print(f"Error guardando en Letta: {e}")
            return False
    
    def report_to_telegram(self, patterns):
        """Envia reporte de insights por Telegram."""
        import httpx
        
        token = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
        owner = os.getenv("TELEGRAM_OWNER_CHAT_ID")
        
        if not token or not owner:
            return
        
        if patterns.get("status") in ["no_history", "empty"]:
            return
        
        insights = patterns.get("insights", [])
        
        if not insights:
            text = f"Learner Report\n\nSin patrones criticos detectados.\n\nTotal eventos: {patterns['total_events']}\nUltimas 24h: {patterns['last_24h_events']}\n\nSistema estable."
        else:
            insights_list = "\n".join(
                f"[{i['severity'].upper()}] {i['message']}"
                for i in insights
            )
            text = f"Learner Report\n\nPatrones detectados:\n\n{insights_list}\n\nEventos analizados: {patterns['total_events']}"
        
        try:
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": owner, "text": text},
                timeout=10
            )
        except:
            pass
    
    def run_cycle(self):
        """Ejecuta un ciclo de aprendizaje completo."""
        print(f"\n[LEARNER] Iniciando ciclo de analisis...")
        
        patterns = self.analyze_heal_history()
        
        if patterns.get("status") in ["no_history", "empty"]:
            print(f"[LEARNER] Sin historial aun, nada que aprender")
            return patterns
        
        print(f"[LEARNER] {patterns['total_events']} eventos analizados")
        print(f"[LEARNER] {len(patterns.get('insights', []))} insights detectados")
        
        # Guardar patrones locales
        self.save_patterns(patterns)
        
        # Memoria en Letta (solo si hay insights)
        if patterns.get("insights"):
            if self.store_in_letta(patterns):
                print(f"[LEARNER] Patrones guardados en memoria persistente")
            
            # Reportar insights importantes
            high_severity = [i for i in patterns["insights"] if i["severity"] == "high"]
            if high_severity:
                self.report_to_telegram(patterns)
                print(f"[LEARNER] Notificado al owner: {len(high_severity)} insights criticos")
        
        return patterns


def learn_loop(interval=3600):
    """Loop de aprendizaje - cada hora por defecto."""
    learner = Learner()
    print(f"Learner iniciado - ciclo cada {interval}s ({interval//60} min)")
    
    while True:
        try:
            result = learner.run_cycle()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Learner: {result.get('total_events', 0)} eventos | {len(result.get('insights', []))} insights")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Learner detenido")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    learner = Learner()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "once":
            result = learner.run_cycle()
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "loop":
            learn_loop(int(sys.argv[2]) if len(sys.argv) > 2 else 3600)
    else:
        learn_loop(3600)
