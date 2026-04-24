# Ultra Stack - Documentacion Oficial

Sistema multi-agente IA autonomo con self-healing, self-learning y self-improving.

## Indice

1. Getting Started - Instalacion y primeros pasos
2. Architecture - Arquitectura del sistema
3. Services - Los 16 servicios del stack
4. Agents - Agentes IA y crews
5. LLM Router - 7 modos con auto-selector
6. Tools - 13 herramientas del Smart Agent
7. Security - Security layer + approvals
8. Interfaces - PWA, Telegram, CLI
9. API Reference - Endpoints REST
10. Deployment - Deploy en produccion
11. Troubleshooting - Solucion de problemas
12. Roadmap - Futuro del proyecto

## Que es Ultra?

Ultra es un sistema multi-agente IA autonomo que corre 24/7 en un VPS y:

- Se auto-monitorea y arregla solo (Self-healing)
- Aprende de cada interaccion (Self-learning)
- Se mejora con tu aprobacion (Self-improving)
- Ejecuta codigo real en el servidor (Smart Agent)
- Selecciona automaticamente el mejor LLM por tarea
- Tiene memoria persistente (Letta)
- Funciona por multiples interfaces (PWA, Telegram, CLI)

## Stack Tecnologico

- Python 3.10+ (FastAPI, LangChain, CrewAI)
- Node.js 20+ (Next.js 16 PWA)
- PostgreSQL (DigitalOcean)
- Redis (cache)
- Docker (Letta, Prometheus, Grafana)
- systemd (16+ servicios)

## Features Unicos

### Auto-Mode Selector
Ultra elige el mejor LLM automaticamente segun el mensaje:
- Simple -> NORMAL
- Codigo -> CODE (GPT-5.3 Codex)
- Analisis -> BLACKBOX (Claude Opus 4.7)

### Ciclo TDD Autonomo
1. Genera codigo
2. Ejecuta tests
3. Detecta bugs
4. Auto-corrige
5. Guarda final (con approval)

### Self-Healing
- Monitor detecta caidas (60s)
- Healer restaura automatico (120s)
- Learner analiza patrones (1h)
- Improver sugiere mejoras (24h)

## Metricas de Produccion

- 16 servicios systemd 24/7
- 3 contenedores Docker
- 83+ modelos LLM disponibles
- 13 tools ejecutables
- 6 agentes autonomos
- 2 crews multi-agente
- 5 interfaces

## Autor

Erik - Creador del Ultra Stack
Construido en ~4 dias con disciplina y curiosidad.

## Licencia

MIT License

---

Built with passion by Erik
