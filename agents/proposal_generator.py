"""
Proposal Generator - Genera propuestas proactivas estilo Jules

Cada cierto tiempo analiza el sistema y propone mejoras concretas.
Usuario solo dice SI o NO con botones.

Tipos de propuestas:
- capability: activar feature que no tiene
- improvement: mejorar algo existente  
- maintenance: limpieza/actualizacion
- insight: informacion interesante
"""
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")


PROPOSALS_FILE = Path("/opt/ultra/data/proposals/queue.json")
PROPOSALS_FILE.parent.mkdir(parents=True, exist_ok=True)
if not PROPOSALS_FILE.exists():
    PROPOSALS_FILE.write_text("[]")


client = OpenAI(
    api_key=os.getenv("BLACKBOX_API_KEY"),
    base_url="https://api.blackbox.ai/v1"
)


SYSTEM_PROMPT = """Eres el Meta-Agent de Ultra Stack. Tu trabajo es analizar el sistema actual y proponer mejoras concretas que mejoren la experiencia del usuario.

Contexto del sistema:
- Ultra Stack: sistema multi-agente IA autonomo
- 16 servicios systemd, 3 containers Docker
- 7 modos LLM (FREE, NORMAL, KIMI, BOOST, TURBO, BLACKBOX, CODE)
- Interfaces: CLI, Telegram bot, PWA, Dashboard, Grafana
- Memoria persistente en JSON
- Owner: Erik, le gusta Python

Genera 3 propuestas CONCRETAS para mejorar el sistema. Cada una debe:
1. Resolver un problema real o desbloquear capacidad nueva
2. Ser ejecutable automaticamente (sin intervencion manual compleja)
3. Tener titulo claro + 1-2 lineas de descripcion + beneficio

Formato JSON estricto:
{
  "proposals": [
    {
      "title": "titulo corto",
      "description": "que hace en 1-2 lineas", 
      "benefit": "beneficio concreto",
      "category": "capability|improvement|maintenance|insight",
      "impact": "high|medium|low",
      "action_type": "install|modify|create|scan|report",
      "estimated_time_seconds": 60,
      "risk_level": "safe|medium|high"
    }
  ]
}

Sin emojis excesivos. Estilo Google Jules: directo y accionable."""


def generate_proposals(n_proposals=3):
    """Genera propuestas proactivas usando BlackBox AI."""
    try:
        response = client.chat.completions.create(
            model="blackboxai/anthropic/claude-opus-4.7",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Genera {n_proposals} propuestas para mejorar el Ultra Stack ahora mismo."}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        text = response.choices[0].message.content
        
        # Extraer JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_text = text[start:end]
            data = json.loads(json_text)
            return data.get("proposals", [])
    except Exception as e:
        print(f"[ERROR] Generando propuestas: {e}")
        return []
    
    return []


def save_proposal(proposal):
    """Guarda propuesta en la queue."""
    proposals = []
    if PROPOSALS_FILE.exists():
        proposals = json.loads(PROPOSALS_FILE.read_text())
    
    proposal_entry = {
        "id": str(uuid.uuid4())[:8],
        "title": proposal.get("title"),
        "description": proposal.get("description"),
        "benefit": proposal.get("benefit"),
        "category": proposal.get("category"),
        "impact": proposal.get("impact"),
        "action_type": proposal.get("action_type"),
        "estimated_time_seconds": proposal.get("estimated_time_seconds", 60),
        "risk_level": proposal.get("risk_level", "medium"),
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    proposals.append(proposal_entry)
    
    # Mantener solo ultimas 50
    if len(proposals) > 50:
        proposals = proposals[-50:]
    
    PROPOSALS_FILE.write_text(json.dumps(proposals, indent=2, ensure_ascii=False))
    return proposal_entry


def get_pending_proposals():
    """Obtiene propuestas pendientes."""
    if not PROPOSALS_FILE.exists():
        return []
    proposals = json.loads(PROPOSALS_FILE.read_text())
    return [p for p in proposals if p.get("status") == "pending"]


def respond_proposal(proposal_id, response):
    """Responde a propuesta: approved|rejected|snoozed."""
    if not PROPOSALS_FILE.exists():
        return False
    
    proposals = json.loads(PROPOSALS_FILE.read_text())
    for p in proposals:
        if p.get("id") == proposal_id:
            p["status"] = response
            p["responded_at"] = datetime.now().isoformat()
            PROPOSALS_FILE.write_text(json.dumps(proposals, indent=2, ensure_ascii=False))
            return True
    return False


if __name__ == "__main__":
    print("Generando propuestas proactivas...")
    proposals = generate_proposals(3)
    
    for p in proposals:
        saved = save_proposal(p)
        print(f"
[{saved['id']}] {saved['title']}")
        print(f"  {saved['description']}")
        print(f"  Benefit: {saved['benefit']}")
        print(f"  Impact: {saved['impact']} | Risk: {saved['risk_level']}")
