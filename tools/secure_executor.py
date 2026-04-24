"""Secure Tool Executor - Wrapper con seguridad completa."""
import sys
sys.path.insert(0, "/opt/ultra")

from tools.registry import TOOLS_REGISTRY, ToolResult
from security.guard import safe_execute


def execute_tool_secure(tool_name, params):
    if tool_name not in TOOLS_REGISTRY:
        return {"success": False, "error": "Tool desconocida: " + tool_name}
    
    tool = TOOLS_REGISTRY[tool_name]
    executor = tool["fn"]
    risk = tool.get("risk", "medium")
    
    return safe_execute(
        tool_name=tool_name,
        executor_fn=executor,
        params=params,
        risk=risk,
    )


def list_available_tools():
    tools = []
    for name, tool in TOOLS_REGISTRY.items():
        tools.append({
            "name": name,
            "description": tool["description"],
            "parameters": tool["parameters"],
            "risk": tool.get("risk", "medium"),
        })
    return tools


if __name__ == "__main__":
    print("=== Tools disponibles ===")
    for t in list_available_tools():
        risk_map = {"safe": "SAFE", "medium": "MED ", "high": "HIGH"}
        risk_label = risk_map.get(t["risk"], "?")
        name = t["name"]
        desc = t["description"]
        print("[" + risk_label + "] " + name + ": " + desc)
    
    print()
    print("=== Test SAFE: read_file ===")
    r = execute_tool_secure("read_file", {"path": "/opt/ultra/README.md", "max_bytes": 200})
    if r["success"]:
        output = r["result"].get("output", "")
        print("OK: " + output[:100] + "...")
    else:
        print("FAIL: " + str(r.get("error")))
    
    print()
    print("=== Test BLOCKED: rm -rf / ===")
    r = execute_tool_secure("shell_execute", {"command": "rm -rf /"})
    blocked = not r.get("success")
    print("Blocked: " + str(blocked))
    print("Reason: " + str(r.get("error") or r.get("blocked_by")))
    
    print()
    print("=== Test SAFE: ls ===")
    r = execute_tool_secure("shell_execute", {"command": "ls /opt/ultra | head -5"})
    if r["success"]:
        output = r["result"].get("output", "")
        print("Output:")
        print(output[:300])
