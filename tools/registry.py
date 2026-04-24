"""
Tool Registry - Acciones que Ultra puede ejecutar.
"""
import os
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


RISK_SAFE = "safe"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"


class ToolResult:
    def __init__(self, success, output="", error="", data=None):
        self.success = success
        self.output = output
        self.error = error
        self.data = data
    
    def to_dict(self):
        return {
            "success": self.success,
            "output": self.output[:2000] if self.output else "",
            "error": self.error[:500] if self.error else "",
            "data": self.data,
        }


# ============= FILE TOOLS =============

def read_file(path, max_bytes=50000):
    try:
        p = Path(path)
        if not p.exists():
            return ToolResult(False, error="File not found: " + str(path))
        content = p.read_text()[:max_bytes]
        return ToolResult(True, output=content, data={"size": p.stat().st_size})
    except Exception as e:
        return ToolResult(False, error=str(e))


def write_file(path, content, mode="w"):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        if p.exists() and mode == "w":
            backup = p.with_suffix(p.suffix + ".bak." + str(int(datetime.now().timestamp())))
            shutil.copy(p, backup)
        
        with open(p, mode) as f:
            f.write(content)
        
        return ToolResult(True, output="Wrote " + str(len(content)) + " bytes to " + str(path))
    except Exception as e:
        return ToolResult(False, error=str(e))


def list_dir(path="."):
    try:
        p = Path(path)
        if not p.exists():
            return ToolResult(False, error="Path not found: " + str(path))
        
        items = []
        for item in sorted(p.iterdir()):
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        return ToolResult(True, data=items, output=str(len(items)) + " items")
    except Exception as e:
        return ToolResult(False, error=str(e))


def search_files(pattern, path="/opt/ultra", max_results=20):
    try:
        results = []
        p = Path(path)
        for f in p.rglob(pattern):
            if len(results) >= max_results:
                break
            if "node_modules" in str(f) or "__pycache__" in str(f) or ".next" in str(f):
                continue
            results.append(str(f))
        return ToolResult(True, data=results, output="Found " + str(len(results)) + " files")
    except Exception as e:
        return ToolResult(False, error=str(e))


# ============= SHELL =============

def shell_execute(command, timeout=30):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/opt/ultra"
        )
        return ToolResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            data={"return_code": result.returncode, "command": command}
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, error="Timeout")
    except Exception as e:
        return ToolResult(False, error=str(e))


# ============= SYSTEMD =============

def service_status(service):
    r = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=5)
    return ToolResult(True, output=r.stdout.strip(), data={"active": r.stdout.strip() == "active"})


def service_control(service, action):
    if action not in ["restart", "start", "stop", "reload"]:
        return ToolResult(False, error="Action invalida")
    
    r = subprocess.run(["systemctl", action, service], capture_output=True, text=True, timeout=30)
    return ToolResult(
        success=r.returncode == 0,
        output=action + " " + service + ": " + r.stdout,
        error=r.stderr
    )


def get_logs(service, lines=50):
    r = subprocess.run(
        ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
        capture_output=True, text=True, timeout=10
    )
    return ToolResult(True, output=r.stdout)


# ============= PYTHON =============

def run_python(code):
    try:
        result = subprocess.run(
            ["/opt/ultra/venv/bin/python3", "-c", code],
            capture_output=True, text=True, timeout=30,
            cwd="/opt/ultra",
            env={**os.environ, "PYTHONPATH": "/opt/ultra"}
        )
        return ToolResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr
        )
    except Exception as e:
        return ToolResult(False, error=str(e))


def pip_install(package):
    r = subprocess.run(
        ["/opt/ultra/venv/bin/pip", "install", package],
        capture_output=True, text=True, timeout=120
    )
    return ToolResult(
        success=r.returncode == 0,
        output=r.stdout[-500:],
        error=r.stderr[-500:]
    )


# ============= WEB SEARCH =============

def web_search(query):
    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv("/opt/ultra/.env")
        
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            return ToolResult(False, error="PERPLEXITY_API_KEY no configurada")
        
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": "Bearer " + api_key},
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 2000,
            },
            timeout=60
        )
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        return ToolResult(True, output=content)
    except Exception as e:
        return ToolResult(False, error=str(e))


# ============= DOCKER =============

def docker_list():
    r = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"],
        capture_output=True, text=True, timeout=5
    )
    containers = []
    for line in r.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            containers.append({
                "name": parts[0],
                "status": parts[1] if len(parts) > 1 else "",
                "image": parts[2] if len(parts) > 2 else "",
            })
    return ToolResult(True, data=containers)


def docker_logs(container, lines=50):
    r = subprocess.run(
        ["docker", "logs", container, "--tail", str(lines)],
        capture_output=True, text=True, timeout=10
    )
    return ToolResult(True, output=r.stdout[-3000:] + r.stderr[-500:])


# ============= REGISTRY =============

TOOLS_REGISTRY = {
    "read_file": {
        "fn": read_file,
        "description": "Lee contenido de un archivo",
        "parameters": {"path": "string", "max_bytes": "int"},
        "risk": RISK_SAFE,
    },
    "write_file": {
        "fn": write_file,
        "description": "Escribe archivo (hace backup)",
        "parameters": {"path": "string", "content": "string", "mode": "string"},
        "risk": RISK_HIGH,
    },
    "list_dir": {
        "fn": list_dir,
        "description": "Lista contenido de directorio",
        "parameters": {"path": "string"},
        "risk": RISK_SAFE,
    },
    "search_files": {
        "fn": search_files,
        "description": "Busca archivos por patron",
        "parameters": {"pattern": "string", "path": "string", "max_results": "int"},
        "risk": RISK_SAFE,
    },
    "shell_execute": {
        "fn": shell_execute,
        "description": "Ejecuta comando shell",
        "parameters": {"command": "string", "timeout": "int"},
        "risk": RISK_MEDIUM,
    },
    "service_status": {
        "fn": service_status,
        "description": "Estado de servicio systemd",
        "parameters": {"service": "string"},
        "risk": RISK_SAFE,
    },
    "service_control": {
        "fn": service_control,
        "description": "Controla servicio systemd",
        "parameters": {"service": "string", "action": "string"},
        "risk": RISK_HIGH,
    },
    "get_logs": {
        "fn": get_logs,
        "description": "Logs de servicio",
        "parameters": {"service": "string", "lines": "int"},
        "risk": RISK_SAFE,
    },
    "run_python": {
        "fn": run_python,
        "description": "Ejecuta codigo Python",
        "parameters": {"code": "string"},
        "risk": RISK_HIGH,
    },
    "pip_install": {
        "fn": pip_install,
        "description": "Instala paquete pip",
        "parameters": {"package": "string"},
        "risk": RISK_HIGH,
    },
    "web_search": {
        "fn": web_search,
        "description": "Busqueda web con Perplexity",
        "parameters": {"query": "string"},
        "risk": RISK_SAFE,
    },
    "docker_list": {
        "fn": docker_list,
        "description": "Lista contenedores Docker",
        "parameters": {},
        "risk": RISK_SAFE,
    },
    "docker_logs": {
        "fn": docker_logs,
        "description": "Logs de contenedor Docker",
        "parameters": {"container": "string", "lines": "int"},
        "risk": RISK_SAFE,
    },
}
