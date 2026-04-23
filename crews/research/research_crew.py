"""
Research Crew - CrewAI v1.x usando OpenRouter via LiteLLM.
"""
import sys, os
sys.path.insert(0, '/opt/ultra')

from dotenv import load_dotenv
load_dotenv('/opt/ultra/.env')

# Configurar OpenRouter para LiteLLM (CrewAI lo usa internamente)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from shared.llm_router.router import get_current_mode, MODELS_BY_MODE


def make_llm(task="reasoning"):
    """Crea LLM de CrewAI usando el modo actual del router."""
    mode = get_current_mode()
    model_id = MODELS_BY_MODE[mode][task]
    
    return LLM(
        model=f"openrouter/{model_id}",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )


@tool("web_search")
def web_search(query: str) -> str:
    """Busca información actualizada en la web usando Perplexity."""
    import httpx
    try:
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"},
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 2000,
            },
            timeout=60
        )
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"


def build_research_crew(topic: str):
    llm = make_llm("reasoning")
    
    scout = Agent(
        role="Scout - Buscador de fuentes",
        goal=f"Encontrar las mejores fuentes sobre: {topic}",
        backstory="Eres un investigador OSINT experto. Localizas información de alta calidad rapidísimo.",
        tools=[web_search],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
    
    curator = Agent(
        role="Curator - Selector de información",
        goal="Evaluar cuáles fuentes son más relevantes y confiables",
        backstory="Eres un analista crítico. Filtras ruido y seleccionas lo más valioso.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
    
    synthesizer = Agent(
        role="Synthesizer - Redactor del reporte final",
        goal="Crear un reporte ejecutivo claro y accionable",
        backstory="Escribes reportes profesionales. Estructuras bien y destacas insights clave.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
    
    search_task = Task(
        description=f"Busca las mejores fuentes sobre: {topic}. Retorna 5-10 fuentes relevantes.",
        expected_output="Lista numerada de 5-10 fuentes con resumen de 2-3 líneas cada una",
        agent=scout,
    )
    
    curate_task = Task(
        description="De las fuentes encontradas, selecciona las 3-5 mejores. Justifica cada una.",
        expected_output="Lista de 3-5 fuentes prioritarias con justificación",
        agent=curator,
    )
    
    synthesize_task = Task(
        description=f"Crea un reporte ejecutivo sobre: {topic}. Incluye contexto, hallazgos, implicaciones, recomendaciones.",
        expected_output="Reporte en Markdown con secciones claras",
        agent=synthesizer,
    )
    
    return Crew(
        agents=[scout, curator, synthesizer],
        tasks=[search_task, curate_task, synthesize_task],
        process=Process.sequential,
        verbose=True,
    )


def run_research(topic: str) -> str:
    crew = build_research_crew(topic)
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Agentes IA autónomos 2026"
    print(f"🔍 Research Crew investigando: {topic}\n")
    result = run_research(topic)
    print("\n" + "="*60)
    print("📄 REPORTE FINAL:")
    print("="*60)
    print(result)
