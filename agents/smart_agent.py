"""
Smart Agent - Chat con function calling.
Recibe tu mensaje, decide que tools usar, las ejecuta, te responde.
"""
import os
import sys
import json
from typing import Dict, List

sys.path.insert(0, "/opt/ultra")
from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")

from openai import OpenAI
from tools.registry import TOOLS_REGISTRY
from tools.secure_executor import execute_tool_secure
from shared.llm_router.router import get_current_mode, MODELS_BY_MODE


def get_tools_schema():
    """Convierte TOOLS_REGISTRY a formato OpenAI function calling."""
    schema = []
    for name, tool in TOOLS_REGISTRY.items():
        properties = {}
        for param_name, param_type in tool["parameters"].items():
            properties[param_name] = {"type": "string", "description": param_type}
        
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": [],
                },
            }
        })
    return schema


def get_client():
    return OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )


def get_model():
    # Claude Opus 4.6 es el mejor para function calling multi-turn
    return "anthropic/claude-opus-4.6"


SYSTEM_PROMPT = """Eres Ultra, un asistente IA ejecutor.

Tienes acceso a herramientas para:
- Leer y escribir archivos
- Ejecutar comandos shell
- Controlar servicios systemd
- Buscar informacion web (Perplexity)
- Ejecutar codigo Python
- Instalar paquetes pip
- Gestionar Docker

REGLAS:
1. Usa herramientas cuando sea necesario para cumplir la tarea
2. Se conciso y eficiente
3. Si una accion es peligrosa (write_file, service_control, pip_install) te pedira approval automaticamente
4. Siempre explica brevemente que hiciste
5. Si hay error, sugiere como arreglarlo
6. Responde en espanol"""


def chat_with_tools(user_message: str, conversation_history: List = None) -> Dict:
    """Chat con Ultra usando function calling."""
    if conversation_history is None:
        conversation_history = []
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    
    client = get_client()
    model = get_model()
    tools_schema = get_tools_schema()
    
    # Max 10 iteraciones
    tool_calls_log = []
    
    for iteration in range(10):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            max_tokens=2000,
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        # Si no pide tools, terminar
        if not message.tool_calls:
            return {
                "reply": message.content or "",
                "tool_calls": tool_calls_log,
                "iterations": iteration + 1,
                "model": model,
            }
        
        # Ejecutar cada tool call
        for tc in message.tool_calls:
            tool_name = tc.function.name
            try:
                tool_args = json.loads(tc.function.arguments)
            except:
                tool_args = {}
            
            print(f"[TOOL] {tool_name}({tool_args})")
            result = execute_tool_secure(tool_name, tool_args)
            
            tool_calls_log.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })
            
            # Agregar resultado al contexto
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)[:3000],
            })
    
    # Si llegamos aqui es porque termino el loop sin respuesta final
    # Generar resumen basado en las tools ejecutadas
    if tool_calls_log:
        summary_parts = ["Ejecute las siguientes acciones:"]
        for tc in tool_calls_log:
            tool = tc["tool"]
            success = tc["result"].get("success", False)
            status = "OK" if success else "FAIL"
            summary_parts.append(f"- {tool}: {status}")
        
        # Intentar una respuesta final simple
        try:
            final_response = client.chat.completions.create(
                model=model,
                messages=messages + [{
                    "role": "user",
                    "content": "Resume brevemente lo que hiciste en 2-3 lineas. NO uses mas tools."
                }],
                max_tokens=500,
            )
            final_reply = final_response.choices[0].message.content or "\n".join(summary_parts)
        except:
            final_reply = "\n".join(summary_parts)
    else:
        final_reply = "No pude completar la tarea"
    
    return {
        "reply": final_reply,
        "tool_calls": tool_calls_log,
        "iterations": 10,
        "model": model,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "Dime que archivos hay en /opt/ultra/tools"
    
    print(f"Usuario: {msg}")
    print("=" * 60)
    result = chat_with_tools(msg)
    print()
    print("=" * 60)
    print("Ultra: " + result["reply"])
    print()
    print("Tool calls: " + str(len(result["tool_calls"])))
    for tc in result["tool_calls"]:
        tool = tc["tool"]
        success = tc["result"].get("success")
        print("  - " + tool + ": " + ("OK" if success else "FAIL"))
