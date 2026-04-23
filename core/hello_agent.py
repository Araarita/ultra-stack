"""
Primer agente con LangGraph - usa el LLM Router con modos.
Demuestra: razonamiento + tool use + cambio dinámico de modelo.
"""
import sys
sys.path.insert(0, '/opt/ultra')

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from shared.llm_router.router import get_llm_for_task, get_current_mode, MODE_INFO


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


# =======================
# Tools
# =======================
@tool
def calculate(expression: str) -> str:
    """Evalúa una expresión matemática. Ejemplo: '235 * 47'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Resultado: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool
def get_current_time() -> str:
    """Obtiene la fecha y hora actual."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def get_system_info() -> str:
    """Obtiene información del sistema Ultra."""
    mode = get_current_mode()
    info = MODE_INFO[mode]
    return f"Modo: {mode} {info['emoji']} | Inteligencia: {info['intelligence']} | Costo: {info['cost_level']}"


TOOLS = [calculate, get_current_time, get_system_info]


# =======================
# Nodos
# =======================
def agent_node(state: AgentState) -> dict:
    llm = get_llm_for_task("tool_use")
    llm_with_tools = llm.bind_tools(TOOLS)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(TOOLS)


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    return workflow.compile()


def run_agent(user_message: str) -> str:
    graph = build_graph()
    mode = get_current_mode()
    info = MODE_INFO[mode]
    
    system = f"""Eres Ultra, un asistente IA extremadamente capaz.
Modo actual: {mode} {info['emoji']} ({info['description']})
Tienes acceso a tools: calculate, get_current_time, get_system_info.
Usa los tools cuando sea necesario. Sé conciso y eficiente."""
    
    state = {
        "messages": [
            SystemMessage(content=system),
            HumanMessage(content=user_message)
        ]
    }
    
    result = graph.invoke(state)
    return result["messages"][-1].content


if __name__ == "__main__":
    mode = get_current_mode()
    info = MODE_INFO[mode]
    
    print("=" * 60)
    print(f"🤖 ULTRA AGENT - Hello World")
    print(f"   Modo actual: {info['emoji']} {mode} {info['intelligence']}")
    print("=" * 60)
    
    tests = [
        ("Matemáticas simples", "Cuánto es 235 * 47 + 1234?"),
        ("Fecha/hora", "¿Qué día es hoy?"),
        ("Sistema", "¿En qué modo estoy corriendo?"),
        ("Razonamiento", "Si compré 15 manzanas a $3.50 cada una y pagué con $100, cuánto cambio me dieron?"),
        ("Combinado", "Calcula el área de un círculo de radio 7 y dime qué hora es"),
    ]
    
    for i, (titulo, pregunta) in enumerate(tests, 1):
        print(f"\n[Test {i}: {titulo}]")
        print(f"Q: {pregunta}")
        try:
            r = run_agent(pregunta)
            print(f"A: {r}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Agente Ultra funcionando")
    print("=" * 60)
