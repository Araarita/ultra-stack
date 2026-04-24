"""
Auto Mode Selector - Decide que modo LLM usar segun el mensaje del usuario.
"""
import re


CODE_KEYWORDS = [
    "escribe funcion", "escribe clase", "codigo", "script",
    "implementa", "debuggea", "fix bug", "refactor",
    "javascript", "python", "typescript", "java", "c++",
    "html", "css", "sql", "api endpoint", "regex",
    "algoritmo", "decorador", "async", "test unitario",
    "pytest", "junit", "eslint", "compile", "npm install",
    "pip install", "git commit", "dockerfile",
]

COMPLEX_REASONING_KEYWORDS = [
    "analiza", "compara", "explica a detalle", "disena arquitectura",
    "propon solucion", "evalua riesgos", "estrategia", "roadmap",
    "porque", "cual es la diferencia", "pros y contras",
    "deep dive", "investigacion profunda", "razonamiento",
    "decide", "recomienda", "opinion profesional",
    "solucion tecnica", "arquitectura de sistema",
]

CREATIVE_KEYWORDS = [
    "genera imagen", "crea imagen", "imagen de", "foto de",
    "genera video", "crea video", "video de",
    "genera audio", "voz de", "tts",
    "midjourney", "flux", "sora", "dall-e",
    "dibuja", "ilustracion", "diseno grafico",
]

WEB_SEARCH_KEYWORDS = [
    "busca", "investigate", "ultimas noticias", "actualidad",
    "que esta pasando", "tendencias 2025", "tendencias 2026",
    "precio actual", "informacion actualizada", "reciente",
    "hoy", "ultima version", "nuevo",
]

SIMPLE_KEYWORDS = [
    "hola", "como estas", "gracias", "buenos dias",
    "ok", "entendido", "si", "no",
]


def analyze_message(message):
    msg_lower = message.lower().strip()
    msg_length = len(msg_lower)
    
    scores = {
        "simple": 0,
        "code": 0,
        "complex": 0,
        "creative": 0,
        "web_search": 0,
    }
    
    for kw in CODE_KEYWORDS:
        if kw in msg_lower:
            scores["code"] += 2
    
    for kw in COMPLEX_REASONING_KEYWORDS:
        if kw in msg_lower:
            scores["complex"] += 2
    
    for kw in CREATIVE_KEYWORDS:
        if kw in msg_lower:
            scores["creative"] += 3
    
    for kw in WEB_SEARCH_KEYWORDS:
        if kw in msg_lower:
            scores["web_search"] += 2
    
    for kw in SIMPLE_KEYWORDS:
        if kw in msg_lower:
            scores["simple"] += 1
    
    # Heuristicas adicionales
    if "```" in message or msg_lower.count("`") >= 2:
        scores["code"] += 3
    
    if re.search(r"\.(py|js|ts|sql|java|cpp|go|rs|yaml|json)\b", msg_lower):
        scores["code"] += 3
    
    if msg_length < 30:
        scores["simple"] += 2
    
    if msg_length > 300:
        scores["complex"] += 2
    
    if "http" in msg_lower or "www." in msg_lower:
        scores["web_search"] += 1
    
    top_category = max(scores, key=scores.get)
    
    mode_map = {
        "simple": "NORMAL",
        "code": "CODE",
        "complex": "BLACKBOX",
        "creative": "BLACKBOX",
        "web_search": "NORMAL",
    }
    
    suggested_mode = mode_map[top_category]
    
    return {
        "scores": scores,
        "top_category": top_category,
        "suggested_mode": suggested_mode,
        "confidence": scores[top_category],
    }


def auto_select_mode(message, current_mode="NORMAL"):
    analysis = analyze_message(message)
    
    should_change = (
        analysis["confidence"] >= 2 and
        analysis["suggested_mode"] != current_mode
    )
    
    return {
        "should_change": should_change,
        "current_mode": current_mode,
        "suggested_mode": analysis["suggested_mode"],
        "category": analysis["top_category"],
        "confidence": analysis["confidence"],
        "analysis": analysis["scores"],
    }


if __name__ == "__main__":
    test_messages = [
        "hola",
        "escribe funcion python que valide emails",
        "analiza el sistema completo y dame un reporte",
        "busca las ultimas noticias de IA",
        "genera imagen cyberpunk de un hacker",
        "como funciona async await en javascript?",
        "disena arquitectura microservicios completa",
    ]
    
    print("=== AUTO-MODE SELECTOR TEST ===")
    print()
    for msg in test_messages:
        result = auto_select_mode(msg)
        cat = result["category"]
        sug = result["suggested_mode"]
        conf = result["confidence"]
        change = result["should_change"]
        print("Msg: " + msg[:60])
        print("  -> Category: " + cat)
        print("  -> Suggested: " + sug + " (confidence: " + str(conf) + ")")
        print("  -> Should change: " + str(change))
        print()
