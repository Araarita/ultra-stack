from letta_client import Letta, MessageCreate

client = Letta(base_url="http://localhost:8283")

# Borrar agente viejo
for a in client.agents.list():
    if a.name == "ultra-erik":
        client.agents.delete(agent_id=a.id)
        print(f"🗑️  Borrado: {a.id[:20]}...")

print("\n📝 Creando agente con Claude Opus 4.6...")
agent = client.agents.create(
    name="ultra-erik",
    memory_blocks=[
        {"label": "human", "value": "Erik - Constructor ambicioso de sistemas multi-agente. TDAH, directo. VPS 32GB en DigitalOcean IP 45.76.28.255. Proyecto /opt/ultra con 5 modos LLM (FREE/NORMAL/KIMI/BOOST/TURBO). Trabaja con OpenRouter, Letta, CrewAI, LangGraph."},
        {"label": "persona", "value": "Soy Ultra, asistente IA de Erik con memoria persistente vía Letta. Uso Claude Opus 4.6 vía OpenRouter. Directo y eficiente. Recuerdo TODO entre sesiones."}
    ],
    model="openai-proxy/anthropic/claude-opus-4.6",
    embedding="openrouter/text-embedding-3-large",
)
print(f"✅ Agente creado: {agent.id}\n")

tests = [
    "Hola, ¿quién soy yo?",
    "¿En qué proyecto estoy trabajando?",
    "¿Qué modelos puedes usar?",
]

for q in tests:
    print(f"👤 Erik: {q}")
    try:
        r = client.agents.messages.create(
            agent_id=agent.id,
            messages=[MessageCreate(role="user", content=q)]
        )
        for msg in r.messages:
            c = getattr(msg, 'content', None)
            if c:
                if isinstance(c, str):
                    print(f"🤖 Ultra: {c}")
                elif isinstance(c, list):
                    for item in c:
                        t = getattr(item, 'text', None)
                        if t:
                            print(f"🤖 Ultra: {t}")
    except Exception as e:
        print(f"❌ {str(e)[:300]}")
    print("-" * 60)

print(f"\n💾 Agent ID guardado: {agent.id}")
print("   Úsalo para futuras conversaciones con este mismo agente")
