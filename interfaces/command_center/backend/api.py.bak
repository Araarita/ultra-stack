"""Ultra Command Center - Backend API."""
import os
import subprocess
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
import httpx
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")

from shared.llm_router.router import get_mode_status, list_all_modes, set_mode

API_SECRET = os.getenv("ULTRA_API_SECRET", "ultra-cc-2025")

app = FastAPI(title="Ultra Command Center API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
active_connections: Set[WebSocket] = set()


# ================== STATUS ==================

@app.get("/api/status")
async def get_status():
    services = []
    systemd_list = [
        "ultra-bot", "ultra-dashboard", "ultra-backup",
        "ultra-monitor", "ultra-healer", "ultra-learner",
        "ultra-improver", "ultra-metrics", "redis-server", "nexus-cortex"
    ]
    
    for svc in systemd_list:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=3
            )
            active = r.stdout.strip() == "active"
            
            uptime_sec = 0
            if active:
                try:
                    r2 = subprocess.run(
                        ["systemctl", "show", svc, "--property=ActiveEnterTimestamp"],
                        capture_output=True, text=True, timeout=3
                    )
                    # Parse timestamp
                except:
                    pass
            
            services.append({
                "name": svc,
                "type": "systemd",
                "active": active,
                "uptime_sec": uptime_sec,
            })
        except:
            services.append({"name": svc, "type": "systemd", "active": False})
    
    # Docker containers
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.strip().split("\n"):
            if line and "|" in line:
                name, status = line.split("|", 1)
                services.append({
                    "name": name,
                    "type": "docker",
                    "active": "Up" in status,
                    "status_text": status,
                })
    except:
        pass
    
    # Recursos
    try:
        mem = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
        mem_line = [l for l in mem.split("\n") if l.startswith("Mem:")][0].split()
        total_mb = int(mem_line[1])
        used_mb = int(mem_line[2])
        ram_pct = round((used_mb / total_mb) * 100, 1)
    except:
        total_mb = used_mb = 0
        ram_pct = 0
    
    try:
        disk = subprocess.run(["df", "-P", "/"], capture_output=True, text=True).stdout
        disk_pct = int(disk.split("\n")[1].split()[4].rstrip("%"))
    except:
        disk_pct = 0
    
    try:
        with open("/proc/loadavg") as f:
            load = float(f.read().split()[0])
    except:
        load = 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services": services,
        "total_active": sum(1 for s in services if s["active"]),
        "total_services": len(services),
        "resources": {
            "ram_used_mb": used_mb,
            "ram_total_mb": total_mb,
            "ram_pct": ram_pct,
            "disk_pct": disk_pct,
            "load_avg": load,
        }
    }


# ================== LLM MODE ==================

@app.get("/api/llm/status")
async def llm_status():
    return get_mode_status()


@app.get("/api/llm/modes")
async def llm_modes():
    return list_all_modes()


class ModeChange(BaseModel):
    mode: str
    password: str = ""


@app.post("/api/llm/set_mode")
async def change_mode(data: ModeChange):
    return set_mode(data.mode, data.password)


# ================== CHAT ULTRA ==================

class ChatMessage(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_ultra(data: ChatMessage):
    """Chat inteligente con function calling - Ultra ejecuta tools reales."""
    try:
        from agents.smart_agent import chat_with_tools
        
        result = chat_with_tools(data.message)
        
        return {
            "reply": result["reply"],
            "tool_calls": [
                {
                    "tool": tc["tool"],
                    "args": tc["args"],
                    "success": tc["result"].get("success", False)
                }
                for tc in result.get("tool_calls", [])
            ],
            "iterations": result.get("iterations", 0),
            "model": result.get("model", ""),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Chat error: {str(e)}")


@app.get("/api/graph")
async def get_graph():
    status_data = await get_status()
    services_by_name = {s["name"]: s["active"] for s in status_data["services"]}
    mode = get_mode_status()
    
    nodes = [
        {"id": "user", "type": "user", "data": {"label": "Erik", "emoji": "👤"},
         "position": {"x": 50, "y": 300}, "active": True},
        
        {"id": "telegram", "type": "interface", "data": {"label": "Telegram Bot", "emoji": "📱", "port": None},
         "position": {"x": 300, "y": 150}, "active": services_by_name.get("ultra-bot", False)},
        
        {"id": "cc", "type": "interface", "data": {"label": "Command Center", "emoji": "🎛️", "port": 8200},
         "position": {"x": 300, "y": 300}, "active": True},
        
        {"id": "dashboard", "type": "interface", "data": {"label": "Dashboard", "emoji": "📊", "port": 8501},
         "position": {"x": 300, "y": 450}, "active": services_by_name.get("ultra-dashboard", False)},
        
        {"id": "letta", "type": "memory", "data": {"label": "Letta Memory", "emoji": "🧠", "port": 8283},
         "position": {"x": 600, "y": 300}, "active": services_by_name.get("letta", False)},
        
        {"id": "router", "type": "router", "data": {"label": f"LLM Router", "emoji": mode["emoji"], "mode": mode["mode"]},
         "position": {"x": 900, "y": 300}, "active": True},
        
        {"id": "research", "type": "crew", "data": {"label": "Research Crew", "emoji": "🔍", "agents": 3},
         "position": {"x": 1200, "y": 80}, "active": True},
        
        {"id": "code", "type": "crew", "data": {"label": "Code Crew", "emoji": "💻", "agents": 5},
         "position": {"x": 1200, "y": 180}, "active": True},
        
        {"id": "monitor", "type": "agent", "data": {"label": "Monitor", "emoji": "🔍", "interval": "60s"},
         "position": {"x": 1200, "y": 280}, "active": services_by_name.get("ultra-monitor", False)},
        
        {"id": "healer", "type": "agent", "data": {"label": "Healer", "emoji": "🩺", "interval": "120s"},
         "position": {"x": 1200, "y": 380}, "active": services_by_name.get("ultra-healer", False)},
        
        {"id": "learner", "type": "agent", "data": {"label": "Learner", "emoji": "📚", "interval": "1h"},
         "position": {"x": 1200, "y": 480}, "active": services_by_name.get("ultra-learner", False)},
        
        {"id": "improver", "type": "agent", "data": {"label": "Improver", "emoji": "⚡", "interval": "24h"},
         "position": {"x": 1200, "y": 580}, "active": services_by_name.get("ultra-improver", False)},
        
        {"id": "openrouter", "type": "provider", "data": {"label": "OpenRouter", "emoji": "🌐"},
         "position": {"x": 1500, "y": 300}, "active": True},
        
        {"id": "grafana", "type": "metrics", "data": {"label": "Grafana", "emoji": "📈", "port": 3000},
         "position": {"x": 600, "y": 550}, "active": True},
        
        {"id": "prometheus", "type": "metrics", "data": {"label": "Prometheus", "emoji": "📊", "port": 9090},
         "position": {"x": 900, "y": 550}, "active": True},
    ]
    
    edges = [
        {"id": "e1", "source": "user", "target": "telegram", "animated": True, "label": "chat"},
        {"id": "e2", "source": "user", "target": "cc", "animated": True, "label": "UI"},
        {"id": "e3", "source": "user", "target": "dashboard"},
        {"id": "e4", "source": "telegram", "target": "letta"},
        {"id": "e5", "source": "cc", "target": "letta", "animated": True},
        {"id": "e6", "source": "dashboard", "target": "letta"},
        {"id": "e7", "source": "letta", "target": "router", "animated": True},
        {"id": "e8", "source": "router", "target": "research"},
        {"id": "e9", "source": "router", "target": "code"},
        {"id": "e10", "source": "router", "target": "monitor"},
        {"id": "e11", "source": "router", "target": "healer"},
        {"id": "e12", "source": "router", "target": "learner"},
        {"id": "e13", "source": "router", "target": "improver"},
        {"id": "e14", "source": "router", "target": "openrouter", "animated": True},
        {"id": "e15", "source": "monitor", "target": "prometheus"},
        {"id": "e16", "source": "prometheus", "target": "grafana"},
    ]
    
    return {"nodes": nodes, "edges": edges}


# ================== ACCIONES ==================

class ServiceAction(BaseModel):
    service: str
    action: str


@app.post("/api/service/action")
async def service_action(data: ServiceAction):
    if data.action not in ["start", "stop", "restart"]:
        raise HTTPException(400, "action invalido")
    
    try:
        r = subprocess.run(
            ["systemctl", data.action, data.service],
            capture_output=True, text=True, timeout=30
        )
        return {
            "ok": r.returncode == 0,
            "service": data.service,
            "action": data.action,
            "stdout": r.stdout,
            "stderr": r.stderr
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ================== LOGS ==================

@app.get("/api/logs/{service}")
async def get_logs(service: str, lines: int = 100):
    try:
        r = subprocess.run(
            ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
            capture_output=True, text=True, timeout=5
        )
        return {"service": service, "logs": r.stdout.split("\n")}
    except Exception as e:
        raise HTTPException(500, str(e))


# ================== REPORTS ==================

@app.get("/api/reports/research")
async def list_research():
    d = Path("/opt/ultra/data/reportes")
    if not d.exists():
        return []
    return [
        {
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        }
        for f in sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    ]


@app.get("/api/reports/research/{name}")
async def get_research(name: str):
    f = Path("/opt/ultra/data/reportes") / name
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"name": name, "content": f.read_text()}


@app.get("/api/reports/code")
async def list_code():
    d = Path("/opt/ultra/data/codigo")
    if not d.exists():
        return []
    return [
        {
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        }
        for f in sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    ]


@app.get("/api/reports/code/{name}")
async def get_code(name: str):
    f = Path("/opt/ultra/data/codigo") / name
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"name": name, "content": f.read_text()}


# ================== WEBSOCKET LIVE UPDATES ==================

@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            status = await get_status()
            await websocket.send_json(status)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        active_connections.discard(websocket)


@app.get("/")
async def root():
    return {
        "service": "Ultra Command Center API",
        "version": "1.0",
        "status": "running"
    }
