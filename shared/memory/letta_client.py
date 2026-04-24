"""
Simple Memory Client - Memoria persistente en JSON (alternativa a Letta)

Guarda conversaciones en /opt/ultra/data/memory/{user_id}.json
100% confiable, sin dependencias externas.
"""
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path("/opt/ultra/data/memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_agent(user_id="erik"):
    """Crea archivo de memoria si no existe."""
    user_file = MEMORY_DIR / f"{user_id}.json"
    if not user_file.exists():
        user_file.write_text("[]")
    return user_id


def save_to_memory(user_id, role, content):
    """Guardar mensaje en JSON."""
    user_file = MEMORY_DIR / f"{user_id}.json"
    
    try:
        if user_file.exists():
            history = json.loads(user_file.read_text())
        else:
            history = []
        
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(history) > 100:
            history = history[-100:]
        
        user_file.write_text(json.dumps(history, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"[MEMORY] Save error: {e}")
        return False


def get_memory(user_id, limit=20):
    """Recuperar historial."""
    user_file = MEMORY_DIR / f"{user_id}.json"
    
    if not user_file.exists():
        return []
    
    try:
        history = json.loads(user_file.read_text())
        recent = history[-limit:]
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recent
        ]
    except Exception as e:
        print(f"[MEMORY] Get error: {e}")
        return []


def clear_memory(user_id):
    """Borrar memoria."""
    user_file = MEMORY_DIR / f"{user_id}.json"
    if user_file.exists():
        user_file.write_text("[]")
        return True
    return False


def get_memory_stats(user_id="erik"):
    """Stats."""
    user_file = MEMORY_DIR / f"{user_id}.json"
    if not user_file.exists():
        return {"messages": 0, "size_bytes": 0}
    
    history = json.loads(user_file.read_text())
    return {
        "messages": len(history),
        "size_bytes": user_file.stat().st_size,
        "user_id": user_id,
        "first_message": history[0]["timestamp"] if history else None,
        "last_message": history[-1]["timestamp"] if history else None
    }
