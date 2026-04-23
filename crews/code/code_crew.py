"""Code Crew - Desarrollo autonomo multi-agente."""
import sys, os
sys.path.insert(0, "/opt/ultra")

from dotenv import load_dotenv
load_dotenv("/opt/ultra/.env")

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from shared.llm_router.router import get_current_mode, MODELS_BY_MODE


def make_llm(task_type="coding"):
    mode = get_current_mode()
    model_id = MODELS_BY_MODE[mode][task_type]
    return LLM(
        model=f"openrouter/{model_id}",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )


@tool("best_practices_search")
def best_practices_search(query: str) -> str:
    """Busca mejores practicas y librerias actuales."""
    import httpx
    try:
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"},
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": f"Best practices Python 2026: {query}. Librerias, patrones, ejemplos."}],
                "max_tokens": 2000,
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"


def build_code_crew(task_description: str):
    llm = make_llm("coding")
    
    architect = Agent(
        role="Principal Software Architect",
        goal=f"Disenar arquitectura optima para: {task_description}",
        backstory="Arquitecto senior con 20 anos. Experto en clean architecture, SOLID, DDD y Python moderno.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=3,
    )
    
    researcher = Agent(
        role="Tech Research Engineer",
        goal="Identificar mejores librerias y patrones actuales",
        backstory="Ingeniero al dia con ecosistema Python 2025-2026.",
        tools=[best_practices_search],
        llm=llm, verbose=True, allow_delegation=False, max_iter=3,
    )
    
    developer = Agent(
        role="Senior Python Developer",
        goal="Implementar codigo production-ready",
        backstory="Senior Python developer. Type hints, docstrings Google, async, logging estructurado. Codigo que pasa ruff y mypy strict.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=3,
    )
    
    tester = Agent(
        role="QA Test Engineer",
        goal="Suite completa de tests con alta cobertura",
        backstory="QA experto en pytest y TDD. Cubres happy path, edge cases, errores. Target: 90%+ cobertura.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=3,
    )
    
    reviewer = Agent(
        role="Principal Code Reviewer",
        goal="Review exhaustivo final",
        backstory="Reviewer senior. Detectas bugs, vulnerabilidades, race conditions. Evaluas seguridad, performance, legibilidad. Entregas version FINAL.",
        llm=llm, verbose=True, allow_delegation=False, max_iter=3,
    )
    
    design_task = Task(
        description=f"Disenar arquitectura para: {task_description}. Entrega: componentes, estructura archivos, interfaces, dependencias, escalabilidad.",
        expected_output="Documento de arquitectura en Markdown",
        agent=architect,
    )
    
    research_task = Task(
        description="Investigar librerias Python 2025-2026, patrones, ejemplos en produccion. Usa best_practices_search.",
        expected_output="Reporte de investigacion con recomendaciones",
        agent=researcher,
        context=[design_task],
    )
    
    implement_task = Task(
        description="Implementar codigo siguiendo arquitectura y research. Python 3.11+, type hints, docstrings Google, error handling, logging. Codigo COMPLETO y ejecutable.",
        expected_output="Codigo Python completo en bloques markdown",
        agent=developer,
        context=[design_task, research_task],
    )
    
    test_task = Task(
        description="Tests pytest: happy path, edge cases, pytest.raises, mocks, fixtures, parametrize. 15-20 tests minimo.",
        expected_output="Archivos test_*.py completos",
        agent=tester,
        context=[implement_task],
    )
    
    review_task = Task(
        description="Review final. Entrega VERSION FINAL con: codigo mejorado, tests actualizados, README.md, requirements.txt, checklist de mejoras.",
        expected_output="Paquete completo production-ready",
        agent=reviewer,
        context=[design_task, research_task, implement_task, test_task],
    )
    
    return Crew(
        agents=[architect, researcher, developer, tester, reviewer],
        tasks=[design_task, research_task, implement_task, test_task, review_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )


def run_code_task(task_description: str) -> str:
    crew = build_code_crew(task_description)
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "Cache LRU thread-safe con TTL"
    print(f"Code Crew: {task}\n")
    result = run_code_task(task)
    print("\n" + "="*60)
    print("FINAL:")
    print("="*60)
    print(result)
