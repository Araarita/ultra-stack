"""
Router LLM con modelos REALES de OpenRouter (Abril 2026).
5 modos: FREE → NORMAL → KIMI → BOOST → TURBO
"""
import os
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv('/opt/ultra/.env')

BOOST_PASSWORD = os.getenv("ULTRA_BOOST_PASSWORD", "boost2025")
TURBO_PASSWORD = os.getenv("ULTRA_TURBO_PASSWORD", "turbo2025")
MODE_FILE = "/opt/ultra/data/current_mode.txt"

TaskType = Literal[
    "reasoning", "coding", "creative", "fast",
    "vision", "long_context", "cheap", "tool_use",
    "agentic"  # nuevo: tareas multi-agente
]


# ============================================
# 5 MODOS con modelos REALES verificados
# ============================================

MODELS_BY_MODE = {
    # 🆓 FREE - 100% gratis verificado en OpenRouter
    "FREE": {
        "reasoning": "deepseek/deepseek-v3.2-exp",  # $0.27 (casi gratis + fiable)
        "coding": "qwen/qwen-turbo",  # $0.033 (el más barato)
        "creative": "google/gemini-2.5-flash-lite",  # $0.10
        "fast": "google/gemini-2.5-flash-lite",  # $0.10
        "vision": "google/gemini-2.5-flash-lite",  # $0.10
        "long_context": "meta-llama/llama-4-maverick",  # $0.15 con 1M ctx
        "cheap": "qwen/qwen-turbo",  # $0.033
        "tool_use": "deepseek/deepseek-v3.2-exp",  # $0.27 bueno en tools
        "agentic": "x-ai/grok-4-fast",  # $0.20 con 2M ctx
    },
    # 🟢 NORMAL - Ultra barato + bueno (ganga absoluta)
    "NORMAL": {
        "reasoning": "deepseek/deepseek-v3.2-exp",      # $0.27/$0.41
        "coding": "qwen/qwen-turbo",                    # $0.033/$0.13
        "creative": "openai/gpt-5-nano",                # $0.05/$0.40
        "fast": "google/gemini-2.5-flash-lite",         # $0.10/$0.40
        "vision": "google/gemini-2.5-flash-lite",       # $0.10/$0.40
        "long_context": "meta-llama/llama-4-maverick",  # 1M ctx $0.15/$0.60
        "cheap": "qwen/qwen-turbo",                     # $0.033/$0.13 (el más barato)
        "tool_use": "deepseek/deepseek-v3.2-exp",
        "agentic": "x-ai/grok-4-fast",                  # 2M ctx $0.20/$0.50
    },
    # 🟣 KIMI - Moonshot K2.6 (última versión)
    "KIMI": {
        "reasoning": "moonshotai/kimi-k2-thinking",     # con razonamiento
        "coding": "moonshotai/kimi-k2.6",
        "creative": "moonshotai/kimi-k2.6",
        "fast": "moonshotai/kimi-k2-0905",              # más barato
        "vision": "moonshotai/kimi-k2.6",
        "long_context": "moonshotai/kimi-k2.6",         # 262K ctx
        "cheap": "moonshotai/kimi-k2-0905",             # $0.40/$2
        "tool_use": "moonshotai/kimi-k2-thinking",
        "agentic": "moonshotai/kimi-k2-thinking",
    },
    # 🟡 BOOST - Premium (Claude 4.6 + Grok multi-agent)
    "BOOST": {
        "reasoning": "anthropic/claude-sonnet-4.6",     # 1M ctx $3/$15
        "coding": "anthropic/claude-sonnet-4.6",
        "creative": "openai/gpt-5.1-codex-mini",        # código top
        "fast": "anthropic/claude-haiku-4.5",           # $1/$5 rápido
        "vision": "google/gemini-3.1-flash-lite-preview",  # 1M ctx
        "long_context": "anthropic/claude-sonnet-4.6",  # 1M ctx
        "cheap": "anthropic/claude-haiku-4.5",
        "tool_use": "anthropic/claude-sonnet-4.6",
        "agentic": "x-ai/grok-4.20-multi-agent",        # multi-agente nativo!
    },
    # 🔴 TURBO - TOP ABSOLUTO 2026
    "TURBO": {
        "reasoning": "anthropic/claude-sonnet-4.6",     # El rey del razonamiento
        "coding": "openai/gpt-5.1-codex-mini",          # Best code 400K ctx
        "creative": "anthropic/claude-sonnet-4.6",
        "fast": "moonshotai/kimi-k2-thinking",          # Razonamiento rápido
        "vision": "google/gemini-3.1-flash-lite-preview",  # Multimodal 1M
        "long_context": "x-ai/grok-4-fast",             # 2M context!
        "cheap": "deepseek/deepseek-v3.2-exp",          # Razonamiento barato top
        "tool_use": "anthropic/claude-sonnet-4.6",
        "agentic": "x-ai/grok-4.20-multi-agent",        # Multi-agente nativo
    },
}


MODE_INFO = {
    "FREE": {
        "emoji": "🆓",
        "rank": 0,
        "description": "Ultra barato (~$0.03-0.27/1M) - modelos fiables sin rate limit",
        "avg_cost": "$0.03-0.27/1M",
        "speed": "Rápido",
        "password_required": False,
        "intelligence": "⭐⭐⭐",
        "cost_level": "💚",
        "key_models": "DeepSeek V3.2, Qwen Turbo, Gemini 2.5, Llama 4",
    },
    "NORMAL": {
        "emoji": "🟢",
        "rank": 1,
        "description": "Ultra barato con modelos modernos (DeepSeek V3.2, Gemini 2.5, Llama 4)",
        "avg_cost": "$0.05-0.30/1M",
        "speed": "Muy rápido",
        "password_required": False,
        "intelligence": "⭐⭐⭐⭐",
        "cost_level": "💰",
        "key_models": "DeepSeek V3.2, GPT-5-nano, Llama 4, Grok-4-fast",
    },
    "KIMI": {
        "emoji": "🟣",
        "rank": 2,
        "description": "Kimi K2.6 + thinking mode (Moonshot AI 2026)",
        "avg_cost": "$0.40-0.75/1M",
        "speed": "Rápido con reasoning",
        "password_required": False,
        "intelligence": "⭐⭐⭐⭐",
        "cost_level": "💰",
        "key_models": "Kimi-K2.6, K2-thinking, K2-0905",
    },
    "BOOST": {
        "emoji": "🟡",
        "rank": 3,
        "description": "Premium: Claude Sonnet 4.6 (1M ctx) + Grok multi-agent",
        "avg_cost": "$1-3/1M",
        "speed": "Medio-Rápido",
        "password_required": True,
        "intelligence": "⭐⭐⭐⭐⭐",
        "cost_level": "💰💰",
        "key_models": "Claude-Sonnet-4.6, Haiku-4.5, Grok-4.20-multi-agent",
    },
    "TURBO": {
        "emoji": "🔴",
        "rank": 4,
        "description": "TOP 2026: Claude 4.6 + GPT-5 + Grok 2M + Gemini 3",
        "avg_cost": "$3-15/1M",
        "speed": "Variable",
        "password_required": True,
        "intelligence": "⭐⭐⭐⭐⭐⭐",
        "cost_level": "💰💰💰",
        "key_models": "Claude-Sonnet-4.6, GPT-5.1-codex, Grok-4-fast (2M), Gemini-3.1",
    },
}


def get_current_mode() -> str:
    try:
        if os.path.exists(MODE_FILE):
            with open(MODE_FILE) as f:
                mode = f.read().strip().upper()
                if mode in MODELS_BY_MODE:
                    return mode
    except Exception:
        pass
    return "NORMAL"


def set_mode(mode: str, password: Optional[str] = None) -> dict:
    mode = mode.upper()
    if mode not in MODELS_BY_MODE:
        return {"ok": False, "error": f"Modo inválido. Usa: {', '.join(MODELS_BY_MODE.keys())}"}
    
    info = MODE_INFO[mode]
    if info["password_required"]:
        if mode == "BOOST" and password != BOOST_PASSWORD:
            return {"ok": False, "error": "Contraseña BOOST incorrecta"}
        if mode == "TURBO" and password != TURBO_PASSWORD:
            return {"ok": False, "error": "Contraseña TURBO incorrecta"}
    
    os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
    with open(MODE_FILE, "w") as f:
        f.write(mode)
    
    return {
        "ok": True,
        "mode": mode,
        "emoji": info["emoji"],
        "description": info["description"],
        "cost": info["avg_cost"],
        "intelligence": info["intelligence"],
        "key_models": info["key_models"],
        "message": f"{info['emoji']} {mode} activo: {info['description']}"
    }


def get_mode_status() -> dict:
    mode = get_current_mode()
    info = MODE_INFO[mode]
    return {
        "mode": mode,
        **info,
        "models": MODELS_BY_MODE[mode],
    }


def list_all_modes() -> list:
    modes = []
    for mode, info in sorted(MODE_INFO.items(), key=lambda x: x[1]["rank"]):
        modes.append({"mode": mode, **info})
    return modes


def get_llm_for_task(task: TaskType, override_model=None, force_mode=None):
    mode = force_mode or get_current_mode()
    model_id = override_model or MODELS_BY_MODE[mode].get(task)
    
    if not model_id:
        raise ValueError(f"No hay modelo para task='{task}' en mode='{mode}'")
    
    from langchain_openai import ChatOpenAI
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY no configurada")
    
    return ChatOpenAI(
        model=model_id,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://ultra.local",
            "X-Title": f"Ultra AI [{mode}]",
        },
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1 or sys.argv[1] == "status":
        s = get_mode_status()
        print(f"\n{s['emoji']} Modo: {s['mode']} (rank {s['rank']}/4)")
        print(f"   {s['intelligence']} | {s['cost_level']} | {s['avg_cost']}")
        print(f"   {s['description']}")
        print(f"   Modelos clave: {s['key_models']}")
        print(f"\n📊 Modelos activos en este modo:")
        for task, model in s['models'].items():
            print(f"   {task:14} → {model}")
    
    elif sys.argv[1] == "list":
        print("\n📋 Los 5 modos (ordenados por capacidad/costo):\n")
        for m in list_all_modes():
            pwd = "🔒" if m["password_required"] else "  "
            print(f"{m['emoji']} {pwd} [{m['rank']}] {m['mode']:8} {m['intelligence']:<12} {m['cost_level']:<7}")
            print(f"         {m['description']}")
            print(f"         Key: {m['key_models']}\n")
        print("🔒 = requiere contraseña\n")
    
    elif sys.argv[1] == "set":
        mode = sys.argv[2] if len(sys.argv) > 2 else None
        pwd = sys.argv[3] if len(sys.argv) > 3 else None
        if not mode:
            print("❌ Uso: python router.py set <mode> [password]")
            sys.exit(1)
        r = set_mode(mode, pwd)
        print(r.get("message", r.get("error")))
    
    elif sys.argv[1] == "test":
        print("🤖 Testing TODOS los modos con una llamada real a cada uno...\n")
        for mode_name in ["FREE", "NORMAL", "KIMI", "BOOST", "TURBO"]:
            info = MODE_INFO[mode_name]
            print(f"{info['emoji']} [{info['rank']}] {mode_name} {info['intelligence']} {info['cost_level']}")
            try:
                llm = get_llm_for_task("reasoning", force_mode=mode_name)
                model = MODELS_BY_MODE[mode_name]["reasoning"]
                r = llm.invoke("di 'funciona' y nada mas")
                print(f"   ✅ reasoning → {model}")
                print(f"      Response: {r.content[:60]}")
            except Exception as e:
                print(f"   ❌ {model}: {str(e)[:80]}")
            print()
        print("✅ Test completo")
