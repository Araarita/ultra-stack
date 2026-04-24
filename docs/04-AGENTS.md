# Agentes IA del Sistema

## Smart Agent

Core agent con function calling. Archivo agents/smart_agent.py. Usa Claude Opus 4.7 por defecto con maximo 5 iteraciones. 13 tools disponibles y context management.

## Meta-Agent

El cerebro supervisor del sistema. Corre cada 10 minutos. Observa estado del sistema, detecta problemas, sugiere mejoras. Outputs en /data/meta/reports/ e insights en Letta. Envia alertas por Telegram.

## Proposer

Proactivo que sugiere acciones. Cada 30 minutos propone instalar paquetes faltantes, configurar servicios, optimizar parametros. Interaccion via Telegram con botones Aprobar y Rechazar.

## Monitor

Vigilancia de servicios cada 60 segundos. Chequea systemctl is-active para cada servicio, uso de CPU RAM Disco, puertos abiertos. Envia alertas por Telegram cuando algo se cae.

## Healer

Auto-restart de servicios caidos cada 120 segundos. Detecta servicio en failed state, intenta systemctl restart. Si falla 3 veces alerta al humano. Log en audit.

## Learner

Aprende de patrones cada 1 hora. Input: audit log, heal history, user interactions. Output: patterns detectados en /data/patterns/.

## Improver

Sugiere mejoras al codigo cada 24 horas. Analiza Learner patterns, genera propuestas de codigo, envia a Proposer para aprobacion.

## Research Crew (3 agentes CrewAI)

Scout busca informacion web con Perplexity. Curator organiza y prioriza hallazgos. Synthesizer genera reporte final estructurado.

## Code Crew (5 agentes CrewAI)

Architect disena arquitectura. Developer implementa codigo. Tester genera tests pytest. Reviewer hace code review. Refactor optimiza codigo existente.

## Agentes vs Crews

Agentes individuales hacen tareas especializadas corren 24/7. Crews son grupos coordinados que se activan bajo demanda.
