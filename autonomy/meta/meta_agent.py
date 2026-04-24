"""
Meta-Agent - El cerebro consciente de Ultra.

Observa el sistema completo, detecta qué le falta, 
genera insights y propone mejoras proactivamente.

Corre cada 10 minutos (o cuando se le invoque).
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")

from openai import OpenAI
from tools.secure_executor import execute_tool_secure


CLIENT = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL = "anthropic/claude-opus-4.6"

INSIGHTS_FILE = Path("/opt/ultra/data/meta_insights.jsonl")
INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)

PROPOSALS_FILE = Path("/opt/ultra/data/meta_proposals.json")


META_PROMPT = """Eres el Meta-Agent de Ultra. Tu trabajo es ser la conciencia del sistema.

CONTEXTO:
Eres parte de Ultra Stack, un sistema multi-agente autonomo con:
- 13 servicios systemd (bot, dashboard, healer, monitor, etc.)
- Letta (memoria), Prometheus/Grafana (metricas)
- Smart Agent con 13 tools (shell, read/write, web_search, etc.)
- Owner: Erik (constructor ambicioso, TDAH, VPS en DigitalOcean)

TU TRABAJO:
Analizar el estado del sistema y:
1. Detectar que esta bien, mal o faltante
2. Identificar oportunidades de mejora
3. Proponer acciones concretas priorizadas
4. Comunicar de forma directa y accionable

FORMATO DE RESPUESTA JSON:
{
  "system_health": "excellent|good|needs_attention|critical",
  "observations": [
    "Observacion concreta #1",
    "Observacion #2"
  ],
  "missing": [
    "Feature o herramienta faltante"
  ],
  "opportunities": [
    {
      "title": "Nombre corto",
      "description": "Que haria y por que",
      "priority": "high|medium|low",
      "effort": "low|medium|high",
      "impact": "low|medium|high",
      "category": "security|features|ux|monitoring|optimization"
    }
  ],
  "next_actions": [
    "Accion concreta que proponen que haga ahora"
  ],
  "summary": "Resumen ejecutivo en 2-3 lineas"
}

Se concreto, accionable, sin relleno. Responde SOLO JSON valido."""


def gather_system_context() -> Dict:
    """Recolecta contexto completo del sistema."""
    context = {"timestamp": datetime.now().isoformat()}
    
    # Servicios
    services = execute_tool_secure("shell_execute", {
        "command": "systemctl list-units --type=service --state=running | grep -E 'ultra|nexus|letta|redis' | head -20"
    })
    context["services"] = services["result"].get("output", "") if services["success"] else ""
    
    # Recursos
    resources = execute_tool_secure("shell_execute", {
        "command": "echo RAM: && free -h | grep Mem && echo DISK: && df -h / | tail -1 && echo LOAD: && uptime"
    })
    context["resources"] = resources["result"].get("output", "") if resources["success"] else ""
    
    # Docker
    docker = execute_tool_secure("docker_list", {})
    context["docker"] = docker.get("result", {}).get("data", [])
    
    # Logs recientes de errores
    errors = execute_tool_secure("shell_execute", {
        "command": "journalctl --since '30 minutes ago' --priority=err --no-pager | tail -20"
    })
    context["recent_errors"] = errors["result"].get("output", "") if errors["success"] else ""
    
    # Heal events 24h
    heal_file = Path("/opt/ultra/data/heal_history.json")
    if heal_file.exists():
        try:
            history = json.loads(heal_file.read_text())
            last_24h = [h for h in history 
                       if datetime.fromisoformat(h.get("timestamp", "2000-01-01")) > datetime.now() - timedelta(hours=24)]
            context["heal_events_24h"] = len(last_24h)
            context["heal_sample"] = last_24h[-3:] if last_24h else []
        except:
            context["heal_events_24h"] = 0
    
    # Estructura del proyecto
    tree = execute_tool_secure("shell_execute", {
        "command": "cd /opt/ultra && ls -la | head -20 && echo --- && find . -type d -name 'agents' -o -name 'crews' -o -name 'autonomy' | head -10"
    })
    context["structure"] = tree["result"].get("output", "") if tree["success"] else ""
    
    # Ultimas ejecuciones de tools
    audit_file = Path("/opt/ultra/data/audit.jsonl")
    if audit_file.exists():
        try:
            lines = audit_file.read_text().strip().split("\n")
            context["recent_tool_executions"] = len([l for l in lines if l])
        except:
            context["recent_tool_executions"] = 0
    
    # Agentes de Letta
    letta = execute_tool_secure("shell_execute", {
        "command": "curl -s http://localhost:8283/v1/agents/ 2>/dev/null | python3 -c 'import sys, json; print(len(json.load(sys.stdin)))' 2>/dev/null || echo '0'"
    })
    context["letta_agents"] = letta["result"].get("output", "0").strip() if letta["success"] else "unknown"
    
    # Reportes generados
    for report_type in ["reportes", "codigo"]:
        report_dir = Path(f"/opt/ultra/data/{report_type}")
        if report_dir.exists():
            context[f"{report_type}_count"] = len(list(report_dir.glob("*.md")))
    
    return context


def analyze_system(context: Dict) -> Dict:
    """Llama al LLM con el contexto y pide analisis."""
    context_str = json.dumps(context, indent=2, default=str)[:10000]
    
    response = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": META_PROMPT},
            {"role": "user", "content": f"Analiza el estado actual del sistema y propone mejoras:\n\n{context_str}"}
        ],
        max_tokens=3000,
        temperature=0.7,
    )
    
    reply = response.choices[0].message.content
    
    # Extraer JSON
    try:
        # Si viene con backticks de markdown
        if "```json" in reply:
            reply = reply.split("```json")[1].split("```")[0]
        elif "```" in reply:
            reply = reply.split("```")[1].split("```")[0]
        
        return json.loads(reply.strip())
    except Exception as e:
        return {
            "system_health": "unknown",
            "summary": "Error parseando respuesta del LLM",
            "raw_response": reply[:500],
            "error": str(e)
        }


def save_insights(analysis: Dict):
    """Guarda el analisis en el journal."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis
    }
    with open(INSIGHTS_FILE, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def save_proposals(analysis: Dict):
    """Actualiza las propuestas activas."""
    proposals = []
    if PROPOSALS_FILE.exists():
        try:
            proposals = json.loads(PROPOSALS_FILE.read_text())
        except:
            proposals = []
    
    new_ops = analysis.get("opportunities", [])
    for op in new_ops:
        op["id"] = f"op_{int(datetime.now().timestamp())}_{hash(op.get('title', '')) % 10000}"
        op["created_at"] = datetime.now().isoformat()
        op["status"] = "pending"
        proposals.append(op)
    
    # Mantener solo las ultimas 50
    proposals = proposals[-50:]
    
    PROPOSALS_FILE.write_text(json.dumps(proposals, indent=2, default=str))


def notify_owner(analysis: Dict):
    """Si hay algo importante, manda notificacion por Telegram."""
    import httpx
    
    health = analysis.get("system_health", "unknown")
    opportunities = analysis.get("opportunities", [])
    
    high_priority = [o for o in opportunities if o.get("priority") == "high"]
    
    if health in ["needs_attention", "critical"] or high_priority:
        token = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
        owner = os.getenv("TELEGRAM_OWNER_CHAT_ID")
        
        if token and owner:
            msg = f"Meta-Agent Insight\n\n"
            msg += f"Health: {health}\n"
            msg += f"Summary: {analysis.get('summary', '')[:300]}\n\n"
            
            if high_priority:
                msg += "Oportunidades HIGH priority:\n"
                for op in high_priority[:3]:
                    msg += f"- {op['title']}: {op['description'][:150]}\n"
            
            try:
                httpx.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": owner, "text": msg[:4000]},
                    timeout=10
                )
            except:
                pass


def run_meta_cycle() -> Dict:
    """Un ciclo completo: recolecta contexto, analiza, guarda, notifica."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Meta-Agent iniciando ciclo...")
    
    # 1. Recolectar contexto
    print("  Recolectando contexto del sistema...")
    context = gather_system_context()
    
    # 2. Analizar con LLM
    print("  Analizando con Claude Opus 4.6...")
    analysis = analyze_system(context)
    
    # 3. Guardar
    save_insights(analysis)
    save_proposals(analysis)
    
    # 4. Notificar si es relevante
    notify_owner(analysis)
    
    # 5. Log resumen
    print(f"  Health: {analysis.get('system_health')}")
    print(f"  Observations: {len(analysis.get('observations', []))}")
    print(f"  Opportunities: {len(analysis.get('opportunities', []))}")
    print(f"  Summary: {analysis.get('summary', '')[:100]}")
    
    return analysis


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        result = run_meta_cycle()
        print()
        print("=" * 60)
        print(json.dumps(result, indent=2, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "loop":
        import time
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 600  # 10 min default
        print(f"Meta-Agent en loop cada {interval}s")
        while True:
            try:
                run_meta_cycle()
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nDetenido")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
    else:
        print("Uso: python meta_agent.py [once|loop [interval]]")
