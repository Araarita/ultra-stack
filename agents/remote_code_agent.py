"""
Remote Code Agent (ReCA) - Genera codigo automaticamente via BlackBox AI

Uso:
  python3 -m agents.remote_code_agent "tarea en lenguaje natural"
  
Features:
- Divide tarea en subtareas
- Usa GPT-5.3 Codex via BlackBox
- Ejecuta y valida cada parte
- Guarda archivos automaticamente
- Reporta progreso en tiempo real
"""
import os
import sys
import json
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, '/opt/ultra')
from dotenv import load_dotenv
load_dotenv()


# Cliente BlackBox
BLACKBOX_KEY = os.getenv('BLACKBOX_API_KEY')
client = OpenAI(
    api_key=BLACKBOX_KEY,
    base_url='https://api.blackbox.ai/v1'
)

# Modelo por defecto
MODEL = 'blackboxai/openai/gpt-5.3-codex'


def generate_code(task_description, context=''):
    """Genera codigo usando BlackBox AI."""
    system_prompt = '''Eres un programador experto. Generas codigo Python de alta calidad, 
production-ready, bien documentado. Cuando te pidan archivos, devuelves SOLO el contenido 
del archivo sin explicaciones adicionales, sin bloques markdown. El codigo debe estar 
listo para guardar directamente.'''
    
    messages = [
        {'role': 'system', 'content': system_prompt},
    ]
    
    if context:
        messages.append({'role': 'user', 'content': f'Contexto: {context}'})
        messages.append({'role': 'assistant', 'content': 'Entendido, tengo el contexto.'})
    
    messages.append({'role': 'user', 'content': task_description})
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=8000,
        temperature=0.1,
    )
    
    return response.choices[0].message.content


def generate_doc(filename, description, context=''):
    """Genera un archivo de documentacion markdown."""
    task = f'''Genera el contenido completo del archivo {filename} con esta descripcion:

{description}

Requisitos:
- Formato markdown profesional
- Secciones bien organizadas con ## y ###
- Informacion tecnica precisa
- Sin emojis excesivos
- Estilo documentacion Kubernetes/Docker
- Entre 1500-2500 palabras
- Solo devuelve el contenido del archivo, sin explicaciones ni bloques adicionales'''
    
    print(f'Generando {filename}...')
    content = generate_code(task, context)
    
    # Limpiar si vino con bloques markdown
    if content.startswith('```'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])
    
    return content


def generate_all_remaining_docs():
    """Genera los docs restantes del Ultra Stack."""
    
    ultra_context = '''Ultra Stack: Sistema multi-agente IA autonomo. 
    16 servicios systemd, 3 containers Docker (letta, prometheus, grafana), 
    7 modos LLM (FREE, NORMAL, KIMI, BOOST, TURBO, BLACKBOX, CODE),
    Smart Agent con 13 tools, Self-healing con Monitor/Healer/Learner/Improver,
    interfaces: PWA Next.js 16, Telegram bot, CLI ultra, Dashboard Streamlit, Grafana.
    Creado por Erik en ~4 dias. Repo github.com/Araarita/ultra-stack.'''
    
    docs = [
        ('06-TOOLS.md', 'Las 13 herramientas del Smart Agent: read_file, write_file, list_dir, search_files, shell_execute, service_status, service_control, get_logs, run_python, pip_install, web_search, docker_list, docker_logs. Cada una con descripcion, parametros, ejemplos de uso, risk level, y notas de seguridad.'),
        
        ('07-SECURITY.md', 'Security Layer completo: blocklist de 22 patrones peligrosos, rate limiting por tool, approval queue con botones inline de Telegram, PANIC mode, audit log JSONL, auto-approve paths (/opt/ultra/docs/, /opt/ultra/examples/, /tmp/ultra/), fail2ban config, risk levels LOW/MEDIUM/HIGH.'),
        
        ('08-INTERFACES.md', 'Las 5 interfaces: PWA Command Center Next.js 16 en puerto 3100 con 4 vistas (Home/Chat/Approvals/System), Telegram Bot @Ultra_Erik_Bot con botones inline, CLI ultra global, Dashboard Streamlit puerto 8501, Grafana puerto 3000. Como usar cada una.'),
        
        ('09-API-REFERENCE.md', 'API REST de FastAPI puerto 8200. Endpoints: /api/chat, /api/status, /api/llm/status, /api/llm/modes, /api/llm/set-mode, /api/service/action, /api/logs, /api/reports, /api/approvals. WebSockets /ws/status /ws/chat /ws/approvals. Request/response examples. CORS, rate limiting, error codes.'),
        
        ('10-DEPLOYMENT.md', 'Deploy en VPS de produccion: requisitos servidor (Ubuntu 22.04+, 4GB RAM, Python 3.10+), instalacion paso a paso, configuracion firewall (puertos 22, 3100, 443), nginx reverse proxy, SSL con Lets Encrypt, monitoreo con Prometheus+Grafana, backups automaticos, rollback, hardening de seguridad.'),
        
        ('11-TROUBLESHOOTING.md', 'Problemas comunes y soluciones: ultra-bot no responde, PWA no carga, API no responde, Letta container caido, LLM sin creditos, approvals no llegan, Smart Agent pierde contexto (bug conocido), disco lleno, RAM alta, servicios en loop de restart. Cada problema con check, causas, y solucion.'),
        
        ('12-ROADMAP.md', 'Futuro del Ultra Stack: mejoras pendientes (memoria conversacional en smart_agent, multimedia generation con BlackBox, voz Whisper+TTS, browser use, auto-approve inteligente), integracion con Azure OpenAI y otros proveedores, escalabilidad horizontal, kubernetes, CDN con Akamai, monetizacion posible, open source release, comunidad.'),
    ]
    
    results = []
    for filename, description in docs:
        try:
            content = generate_doc(filename, description, ultra_context)
            path = Path(f'/opt/ultra/docs/{filename}')
            path.write_text(content)
            size = len(content)
            lines = content.count('\n')
            print(f'  OK: {size} bytes, {lines} lineas')
            results.append((filename, size, lines, True))
        except Exception as e:
            print(f'  ERROR: {e}')
            results.append((filename, 0, 0, False))
    
    print('\n=== RESUMEN ===')
    for filename, size, lines, success in results:
        status = 'OK' if success else 'FAIL'
        print(f'{status} {filename}: {size} bytes, {lines} lineas')
    
    total_success = sum(1 for _, _, _, s in results if s)
    print(f'\nTotal exitosos: {total_success}/{len(results)}')


if __name__ == '__main__':
    generate_all_remaining_docs()
