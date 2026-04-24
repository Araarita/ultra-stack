# 12-ROADMAP.md

## Ultra Stack Roadmap

Este documento define el roadmap técnico y de producto para la evolución de Ultra Stack en las próximas fases. El objetivo es transformar una plataforma ya funcional y altamente integrada en una arquitectura madura, escalable, extensible y operable en entornos empresariales, sin perder la velocidad de iteración que permitió su construcción inicial.

Ultra Stack ya integra múltiples canales (PWA, Telegram, CLI, Dashboard), múltiples modos de inferencia (FREE, NORMAL, KIMI, BOOST, TURBO, BLACKBOX, CODE), un Smart Agent con herramientas, y un sistema de auto-recuperación compuesto por Monitor/Healer/Learner/Improver. El roadmap se enfoca en reducir deuda técnica clave, aumentar confiabilidad operacional, ampliar capacidades multimodales, habilitar operación multi-proveedor y preparar el stack para crecimiento de comunidad y monetización.

---

## 1. Principios de evolución

### 1.1 Diseño orientado a resiliencia
La prioridad es garantizar continuidad operativa ante fallos parciales de proveedores, componentes internos o infraestructura. Se seguirá un enfoque de “graceful degradation”: ante degradación de un servicio, el sistema conserva capacidades mínimas y comunica estado al usuario.

### 1.2 Portabilidad y neutralidad de proveedor
Todas las funcionalidades críticas deben operar con múltiples proveedores de inferencia y servicios cloud. Ningún módulo central debe depender de una API única sin fallback.

### 1.3 Observabilidad primero
Toda nueva capacidad deberá exponer métricas, logs estructurados y trazas. La pregunta “¿qué pasó?” debe responderse en minutos, no horas.

### 1.4 Seguridad por defecto
Se aplicará el principio de mínimo privilegio, gestión centralizada de secretos, trazabilidad de acciones de agentes y controles explícitos para ejecución autónoma.

### 1.5 API estable y extensibilidad
La expansión de herramientas y modos de agente se soportará con contratos versionados (OpenAPI/JSON Schema), semántica clara de errores y compatibilidad hacia atrás.

---

## 2. Smart Agent: memoria conversacional persistente

### 2.1 Objetivo
Agregar memoria conversacional en `smart_agent` para que el sistema mantenga contexto útil entre sesiones, reduzca repetición y mejore continuidad de tareas largas.

### 2.2 Alcance funcional
- Memoria de corto plazo por sesión (buffer contextual, resumible).
- Memoria de largo plazo por usuario/proyecto (hechos persistentes, preferencias, decisiones históricas).
- Recuperación semántica mediante embeddings.
- Compresión automática de historial para optimizar costo/tokens.
- Controles de privacidad: borrado selectivo, TTL configurable, exportación de datos.

### 2.3 Arquitectura propuesta
1. **Memory Service** desacoplado del agente:
   - API `store_event`, `store_fact`, `query_context`, `summarize_thread`, `forget`.
   - Backend inicial: PostgreSQL + pgvector o Qdrant.
2. **Policy Engine de memoria**:
   - Clasifica información como efímera, útil, sensible o persistente.
   - Regla configurable por canal (CLI/Telegram/PWA).
3. **Retriever híbrido**:
   - Búsqueda semántica + filtros por metadatos (usuario, workspace, fecha, tool).
4. **Summarizer asíncrono**:
   - Job background para consolidar conversaciones extensas.
5. **Auditoría**:
   - Registro de cuándo el agente usa memoria en una respuesta.

### 2.4 Riesgos y mitigaciones
- **Contaminación de contexto**: usar score mínimo de relevancia y verificación de contradicciones.
- **Costo elevado**: lotes de summarization, caching y umbrales de embedding.
- **Privacidad**: cifrado en reposo, scopes por tenant, redacción de PII antes de persistir.

### 2.5 Entregables
- Esquema de datos versionado.
- API de memoria documentada.
- Integración con Smart Agent y pruebas end-to-end.
- Dashboard de métricas (hit-rate, latencia, costo por consulta).

---

## 3. Capacidades multimedia con modo BLACKBOX

### 3.1 Objetivo
Convertir `BLACKBOX` en modo multimodal integral: generación y edición de imagen/audio/video bajo políticas de calidad, costo y seguridad.

### 3.2 Casos de uso prioritarios
- Generación de assets de marketing (imágenes, variantes de estilo).
- Prototipos rápidos de UI (mockups visuales).
- Clips cortos para canales sociales.
- Transformaciones: texto→imagen, imagen→imagen, texto→video corto, audio enhancement.

### 3.3 Diseño técnico
- **Media Orchestrator**:
  - Pipeline declarativo por tipo de media.
  - Enrutamiento por proveedor según SLA/costo.
- **Asset Store**:
  - Bucket S3-compatible con versionado y metadata.
  - URL firmadas de corta duración.
- **Moderación y compliance**:
  - Filtro de prompt y resultado antes de entrega.
- **Post-procesamiento**:
  - Upscaling, normalización de audio, transcodificación de video.
- **Cache de derivados**:
  - Evitar recomputación de prompts repetidos.

### 3.4 Integración con canales
- PWA: editor básico con historial de versiones.
- Telegram: respuestas multimedia con enlace a asset persistido.
- CLI: comandos para batch generation.
- Streamlit/Grafana: métricas de throughput, éxito y costo por tipo de media.

### 3.5 Dependencias
- Cola de trabajos (Redis/RabbitMQ).
- Workers dedicados por media type.
- Límites de concurrencia para evitar saturación.

---

## 4. Voz: pipeline Whisper + TTS

### 4.1 Objetivo
Incorporar entrada y salida de voz para habilitar experiencias hands-free y soporte multicanal natural.

### 4.2 Componentes
1. **ASR (Whisper o equivalente)**
   - Batch y near-real-time.
   - Detección de idioma y diarización opcional.
2. **NLP Core**
   - Reutiliza Smart Agent con memoria.
3. **TTS**
   - Voces configurables por usuario/proyecto.
   - Control de prosodia básica y velocidad.
4. **Voice Gateway**
   - Manejo de audio chunks, silencios, interrupciones.
   - Adaptadores para Telegram Voice, WebRTC en PWA y CLI.

### 4.3 Requisitos no funcionales
- Latencia objetivo para interacción fluida: <2.5s turn-end-to-audio-start en modo estándar.
- Degradación a texto cuando TTS/ASR no estén disponibles.
- Registro de transcripciones para auditoría (con consentimiento).

### 4.4 Seguridad y privacidad
- Consentimiento explícito para almacenamiento de audio.
- Retención configurable y borrado automático.
- Redacción opcional de datos sensibles en transcripciones.

---

## 5. Browser Use: navegación autónoma segura

### 5.1 Objetivo
Permitir que el agente use navegador para investigar, extraer datos, completar formularios y ejecutar workflows web controlados.

### 5.2 Arquitectura
- **Browser Worker aislado**:
  - Playwright en contenedor sandbox.
  - Perfil efímero por tarea.
- **Task DSL**:
  - Declaración de objetivos y límites (dominios permitidos, tiempo máximo, acciones prohibidas).
- **Observation Layer**:
  - Capturas, logs de pasos y trazas de decisión.
- **Result Validator**:
  - Verifica consistencia antes de devolver salida al usuario.

### 5.3 Controles operativos
- Allowlist/denylist de dominios.
- Bloqueo de descargas ejecutables.
- Detección de captchas y fallback manual.
- Rate limit por usuario/tenant.

### 5.4 Casos de uso
- Investigación de precios y benchmarking.
- Recolección de documentación técnica.
- Automatización de tareas administrativas repetitivas.

---

## 6. Auto-approve inteligente para flujos autónomos

### 6.1 Objetivo
Reducir fricción operativa en tareas recurrentes manteniendo seguridad y control humano.

### 6.2 Modelo de aprobación
- **Nivel 0**: siempre pedir aprobación humana.
- **Nivel 1**: auto-approve en acciones de bajo riesgo y bajo costo.
- **Nivel 2**: auto-approve condicionado por historial de éxito.
- **Nivel 3**: ejecución autónoma con auditoría posterior para pipelines definidos.

### 6.3 Motor de riesgo
Variables:
- Tipo de herramienta invocada.
- Impacto externo (escritura, publicación, gasto).
- Costo estimado.
- Confianza del modelo y coherencia con intent.
- Historial del usuario y del agente en tareas similares.

Resultado:
- Score de riesgo y recomendación: aprobar / pedir confirmación / bloquear.

### 6.4 Trazabilidad
- Registro firmado de decisiones de aprobación.
- Replay de contexto de decisión.
- Alertas automáticas cuando sube la tasa de fallos por tool.

---

## 7. Integración multi-proveedor: Azure OpenAI y ecosistema

### 7.1 Objetivo
Incorporar Azure OpenAI como proveedor de primera clase y ampliar soporte para otros endpoints LLM/embedding/speech de forma uniforme.

### 7.2 Abstracción de proveedores
Crear una capa `Provider Adapter` con:
- Contrato común para chat/completions/embeddings/audio/image.
- Mapeo de capacidades y límites por modelo.
- Manejo uniforme de errores, timeouts y retries.
- Contabilidad de costos por proveedor.

### 7.3 Azure OpenAI: requisitos específicos
- Soporte de `deployment names` por región.
- Autenticación con API key y Managed Identity donde aplique.
- Rotación de claves vía secreto centralizado.
- Configuración de content filters y políticas enterprise.
- Telemetría de consumo por subscription/resource group.

### 7.4 Estrategia de routing
- Policy-based routing:
  - Prioridad por costo, latencia o cumplimiento.
  - Fallback automático entre proveedores compatibles.
- Circuit breakers por proveedor.
- Shadow traffic opcional para evaluar nuevos modelos sin impacto usuario.

### 7.5 Proveedores adicionales candidatos
- Anthropic, Google, Groq, Together, OpenRouter, local inference (vLLM/Ollama).
- Cada integración debe pasar suite de compatibilidad funcional y de seguridad.

---

## 8. Escalabilidad horizontal

### 8.1 Objetivo
Pasar de operación centrada en host único a arquitectura distribuida con autoescalado de componentes críticos.

### 8.2 Servicios a escalar primero
- API Gateway / backend principal.
- Worker pool de tools.
- Media workers (imagen/audio/video).
- Memory retriever.
- Cola de eventos y scheduling.

### 8.3 Estrategia
- Stateless en servicios front y API.
- Estado persistente en sistemas administrados (DB, cache, object store).
- Particionado por tenant/proyecto cuando el volumen lo requiera.
- Gestión de backpressure en colas.

### 8.4 Capacidad y performance
- Definir SLO por servicio (latencia, disponibilidad, error rate).
- Pruebas de carga periódicas con escenarios realistas.
- Capacity planning mensual con márgenes de crecimiento.

---

## 9. Migración y operación en Kubernetes

### 9.1 Objetivo
Estandarizar despliegue, escalado y operación mediante Kubernetes, manteniendo compatibilidad con entornos simples durante transición.

### 9.2 Blueprint inicial
- Namespace por ambiente: dev/staging/prod.
- Deployments para servicios stateless.
- StatefulSets para componentes stateful cuando no se use servicio administrado.
- HPA por CPU/memoria y métricas custom.
- Ingress controller con TLS automatizado.
- Jobs/CronJobs para tareas de mantenimiento y summarization.

### 9.3 Plataforma y tooling
- Helm charts versionados.
- GitOps (Argo CD o Flux).
- Secret management (External Secrets + Vault/Azure Key Vault).
- Service mesh opcional para mTLS y observabilidad avanzada.

### 9.4 Observabilidad en cluster
- Prometheus Operator + Grafana.
- Loki/ELK para logs.
- OpenTelemetry para trazas distribuidas.
- Alertmanager con rutas por severidad.

### 9.5 Estrategia de migración
1. Containerización homogénea de todos los servicios.
2. Paridad funcional en staging K8s.
3. Canary por servicio crítico.
4. Cutover progresivo por canal (CLI, Telegram, PWA).
5. Plan de rollback por release.

---

## 10. Edge delivery y CDN con Akamai

### 10.1 Objetivo
Mejorar latencia global, disponibilidad de activos estáticos y resiliencia de frontends mediante CDN enterprise.

### 10.2 Alcance
- Distribución de assets PWA y multimedia generada.
- Caching de contenido estático con invalidación controlada.
- Protección DDoS y WAF gestionado.
- Edge rules para compresión, headers de seguridad y georouting.

### 10.3 Integración técnica
- Origin shielding para reducir carga al backend.
- URL signing para assets privados.
- Cache keys con versionado de build.
- Purga por tag para releases rápidas.

### 10.4 Consideraciones
- No cachear respuestas con datos sensibles.
- Reglas separadas para API y static/media.
- Métricas de hit ratio y latencia por región.

---

## 11. Monetización y modelo de negocio

### 11.1 Objetivo
Definir rutas sostenibles de monetización sin comprometer la propuesta open source.

### 11.2 Posibles líneas
- **SaaS gestionado**:
  - Plan Free limitado, Pro, Team, Enterprise.
- **Usage-based billing**:
  - Cobro por tokens, minutos de voz, generación multimedia, browser tasks.
- **Add-ons premium**:
  - Memoria avanzada, compliance pack, SLA dedicado.
- **Servicios profesionales**:
  - Integración, fine-tuning operativo, soporte premium.

### 11.3 Requisitos técnicos para billing
- Metering unificado por evento y recurso.
- Rate limits por plan.
- Cuotas y hard stops configurables.
- Facturación mensual con exportables para auditoría.

### 11.4 Riesgos
- Complejidad de pricing por múltiples proveedores.
- Variabilidad de costos unitarios.
- Mitigación: pricing dinámico por margen mínimo y alertas de costo anómalo.

---

## 12. Open source release strategy

### 12.1 Objetivo
Publicar Ultra Stack como proyecto open source con gobernanza clara, experiencia de contribución sólida y roadmap transparente.

### 12.2 Alcance de liberación
- Core orquestador.
- Smart Agent framework y tools base.
- Integraciones no sensibles por defecto.
- Plantillas de despliegue local (Docker Compose) y cluster (K8s).

### 12.3 Licenciamiento
Evaluar:
- Apache-2.0 para máxima adopción empresarial.
- MIT para simplicidad.
- Modelo open core opcional para features enterprise.

### 12.4 Hygiene de repositorio
- Estructura modular.
- Documentación de arquitectura y ADRs.
- Tests automáticos (unit/integration/e2e).
- Security policy, codeowners, issue templates, PR templates.
- Versionado semántico y changelog automatizado.

### 12.5 Cadena de supply segura
- SBOM por release.
- Escaneo de dependencias e imágenes.
- Firmado de artefactos.
- Política de CVEs y ventanas de parcheo.

---

## 13. Comunidad y ecosistema de contribución

### 13.1 Objetivo
Construir una comunidad técnica activa que acelere innovación, detecte problemas temprano y amplíe casos de uso.

### 13.2 Pilares de comunidad
- Documentación pragmática de onboarding.
- “Good first issues” y mentoring de contribuidores.
- RFC process para cambios mayores.
- Office hours y demos regulares.
- Canal público de soporte y discusión técnica.

### 13.3 Programa de extensiones
- SDK para tools/plugins.
- Marketplace comunitario de integraciones.
- Validación automática de compatibilidad de plugins.
- Ranking por calidad, seguridad y mantenimiento.

### 13.4 Métricas de salud comunitaria
- Tiempo medio de respuesta en issues.
- PR merge lead time.
- Número de contribuidores activos por mes.
- Cobertura documental por módulo.

---

## 14. Seguridad, cumplimiento y gobernanza operacional

### 14.1 Hardening base
- mTLS interno cuando sea viable.
- Rotación automática de secretos.
- Escaneo continuo de imágenes y dependencias.
- Políticas RBAC estrictas por servicio.

### 14.2 Gobierno de agentes
- Lista explícita de acciones permitidas por tool.
- Sandbox para ejecución de código y browser tasks.
- Límites de gasto/acción por tenant.
- Logs inmutables para acciones de alto impacto.

### 14.3 Cumplimiento
- Preparación para requisitos de privacidad (derecho al olvido, exportación).
- Trazabilidad para auditorías internas/externas.
- Separación de datos por tenant.

---

## 15. Fases y milestones propuestos

### 15.1 Fase 1 (0-2 meses): Fundaciones
- Memory Service v1 + integración Smart Agent.
- Provider Adapter unificado con Azure OpenAI.
- Métricas de costo/latencia por modo y proveedor.
- Auto-approve v1 con reglas estáticas y auditoría.

### 15.2 Fase 2 (2-4 meses): Capacidades avanzadas
- Whisper + TTS en PWA/Telegram.
- BLACKBOX multimedia v1 (imagen y audio).
- Browser worker sandbox con dominio allowlist.
- Billing metering interno (sin cobro externo aún).

### 15.3 Fase 3 (4-6 meses): Escala y plataforma
- Despliegue de referencia en Kubernetes.
- HPA y colas con políticas de backpressure.
- CDN Akamai para assets estáticos/media.
- Hardening de seguridad y políticas de cumplimiento.

### 15.4 Fase 4 (6-9 meses): Ecosistema
- Open source release formal.
- SDK de plugins + primeras extensiones comunitarias.
- Planes comerciales iniciales (SaaS/Enterprise piloto).
- Programa de comunidad y gobernanza técnica.

---

## 16. KPIs de éxito del roadmap

### 16.1 Producto
- Incremento de retención por mejora de memoria conversacional.
- Reducción de pasos manuales por auto-approve controlado.
- Adopción de funcionalidades voz y multimedia.

### 16.2 Plataforma
- Disponibilidad > 99.9% en servicios críticos.
- Latencia p95 dentro de SLO definidos por canal.
- Reducción de incidentes de severidad alta.

### 16.3 Costos y eficiencia
- Costo por interacción estable o decreciente.
- Mejor ratio rendimiento/costo por routing multi-proveedor.
- Menor recomputación gracias a cache y summarization.

### 16.4 Comunidad
- Crecimiento sostenido de contribuidores activos.
- Tiempo de resolución de issues en tendencia descendente.
- Publicaciones regulares de roadmap y release notes.

---

## 17. Cierre

Ultra Stack ya demostró velocidad de ejecución y capacidad de integración en un tiempo excepcionalmente corto. El siguiente salto requiere institucionalizar esa velocidad con arquitectura robusta, procesos operables y una estrategia clara de plataforma.

Este roadmap prioriza mejoras de alto impacto: memoria persistente del agente, capacidades multimodales reales, voz end-to-end, navegación autónoma segura, aprobación inteligente, soporte multi-proveedor con Azure OpenAI, escalado horizontal y operación Kubernetes. Sobre esa base se habilitan distribución global con CDN, modelo de monetización sostenible y apertura a comunidad open source.

La meta no es solo agregar funcionalidades, sino convertir Ultra Stack en un sistema confiable, extensible y económicamente viable, preparado para uso intensivo en escenarios reales y para evolucionar con una comunidad técnica alrededor del proyecto.