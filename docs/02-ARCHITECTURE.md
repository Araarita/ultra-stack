# Arquitectura del Ultra Stack

## Diagrama General

USUARIO
  |
  v
INTERFACES: PWA (3100) | Telegram Bot | CLI | Dashboard (8501) | Grafana (3000)
  |
  v
API GATEWAY: FastAPI (puerto 8200) con WebSocket
  |
  v
SMART AGENT con Function Calling
  |
  +--> Auto-Mode Selector (decide modelo segun mensaje)
  |    - simple -> NORMAL
  |    - code -> CODE (GPT-5.3 Codex)
  |    - complex -> BLACKBOX (Claude Opus 4.7)
  |
  +--> Tool Registry (13 tools disponibles)
  |
  +--> Security Layer (22 patrones blocked)
  |
  v
LLM PROVIDERS: OpenRouter + BlackBox AI (83 modelos)
  |
  v
MEMORY: Letta (Docker 8283) + PostgreSQL + Redis

## Las 8 Capas

### 1. Interfaces
- PWA Next.js 16 en puerto 3100
- Telegram Bot (@Ultra_Erik_Bot)
- CLI 'ultra' comando global
- Dashboard Streamlit puerto 8501
- Grafana puerto 3000

### 2. API Gateway
- FastAPI en puerto 8200
- Endpoints REST completos
- WebSocket para updates en vivo
- CORS abierto para PWA

### 3. Smart Agent
- Function calling con LLMs
- Multi-turn conversations
- Context management
- Tool dispatch

### 4. Auto-Mode Selector
- Analiza mensaje del usuario
- Clasifica en 5 categorias
- Cambia modo LLM automaticamente

### 5. Tool Registry (13 tools)
- read_file, write_file
- list_dir, search_files
- shell_execute
- service_status, service_control
- get_logs
- run_python, pip_install
- web_search
- docker_list, docker_logs

### 6. Security Layer
- Blocklist 22 patrones
- Rate limiter 30/min
- Approval queue con botones
- PANIC mode
- Audit log JSONL

### 7. LLM Router (7 modos)
- FREE (DeepSeek V3.2)
- NORMAL (DeepSeek V3.2)
- KIMI (Moonshot K2)
- BOOST (Claude Sonnet 4.6)
- TURBO (Claude Opus 4.6)
- BLACKBOX (Claude Opus 4.7)
- CODE (GPT-5.3 Codex)

### 8. Memory Layer
- Letta persistente (Docker)
- PostgreSQL relacional
- Redis cache

## Self-Healing System

- Monitor cada 60s (detecta caidas)
- Healer cada 120s (auto-restart)
- Learner cada 1h (aprende patrones)
- Improver cada 24h (sugiere mejoras)
- Meta-Agent cada 10 min (observa sistema)
- Proposer cada 30 min (sugiere acciones)

## Flujo End-to-End

1. Usuario escribe mensaje
2. Auto-Mode Selector analiza
3. Smart Agent decide tools
4. Security Layer valida
5. Tool ejecuta (con approval si high risk)
6. Resultado regresa
7. LLM genera respuesta
8. Usuario recibe output

## Los 16 Servicios systemd

1. ultra-bot - Telegram interface
2. ultra-cc - PWA frontend
3. ultra-cc-api - FastAPI backend
4. ultra-dashboard - Streamlit
5. ultra-backup - Scheduler
6. ultra-monitor - Self-healing check
7. ultra-healer - Auto-restart
8. ultra-learner - Pattern learning
9. ultra-improver - Auto-improve
10. ultra-meta - Consciousness
11. ultra-proposer - Proactive
12. ultra-metrics - Prometheus exporter
13. fail2ban - SSH security
14. redis-server - Cache
15. nexus-cortex - Legacy module

## Containers Docker

- letta - Memoria persistente (puerto 8283)
- ultra-prometheus - Metricas (puerto 9090)
- ultra-grafana - Dashboards (puerto 3000)

## Patrones Arquitectonicos

- Microservices (16+ servicios systemd)
- Event-driven (Redis pubsub)
- Multi-provider (OpenRouter + BlackBox)
- Self-healing (Monitor + Healer)
- Audit trail (JSONL inmutable)
- Approval workflow (botones inline)

## Conectividad

- HTTP interno entre servicios
- WebSocket para live updates
- Database pool connections
- Async operations con asyncio

## Built to scale.
