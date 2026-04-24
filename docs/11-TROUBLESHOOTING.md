# 11 - Troubleshooting

Este documento reúne problemas operativos comunes en Ultra Stack y sus procedimientos de diagnóstico y recuperación. Está orientado a operación en producción (Linux + systemd + Docker), con énfasis en pasos reproducibles y verificables.

> Alcance: ultra-bot (Telegram), PWA Next.js, API backend, contenedor Letta, modos LLM con créditos, flujo de approvals, Smart Agent/contexto, capacidad de disco/RAM y servicios en bucle de reinicio.

## Filosofía de diagnóstico

Antes de intervenir, aplicar una secuencia corta y consistente:

1. **Confirmar síntoma exacto** (qué no funciona, desde cuándo, para quién).
2. **Acotar capa afectada**:
   - Red / DNS / TLS
   - Proceso systemd
   - Contenedor Docker
   - Dependencias externas (LLM provider, Telegram, etc.)
   - Estado de recursos del host
3. **Verificar logs recientes** con timestamps.
4. **Aplicar cambio mínimo reversible**.
5. **Validar recuperación** con checks funcionales.
6. **Registrar causa raíz y acción correctiva** para evitar recurrencia.

Comandos base recomendados:

```bash
# Estado de servicios
sudo systemctl --type=service --state=running | grep -E "ultra|agent|api|bot|monitor|healer"

# Logs por servicio
sudo journalctl -u <service-name> -n 200 --no-pager
sudo journalctl -u <service-name> -f

# Estado Docker
docker ps -a
docker logs --tail 200 <container-name>
docker inspect <container-name>

# Recursos host
df -h
free -h
top
htop
```

---

## 1) ultra-bot no responde (Telegram)

### Síntomas
- El bot no responde a `/start`, `/status` u otros comandos.
- Responde con latencia extrema o intermitente.
- Mensajes entran, pero no hay salida en Telegram.

### Checks
1. Verificar proceso del bot:
   ```bash
   sudo systemctl status ultra-bot.service
   ```
2. Revisar logs recientes:
   ```bash
   sudo journalctl -u ultra-bot.service -n 200 --no-pager
   ```
3. Validar conectividad saliente a Telegram API:
   ```bash
   curl -I https://api.telegram.org
   ```
4. Confirmar token cargado en entorno:
   ```bash
   sudo systemctl show ultra-bot.service -p Environment
   ```
5. Si usa webhook, validar endpoint público/TLS:
   ```bash
   curl -vk https://<tu-dominio>/telegram/webhook
   ```

### Causas probables
- Token inválido/rotado (`TELEGRAM_BOT_TOKEN` incorrecto).
- Bot en crash por excepción no manejada.
- Falta de conectividad saliente (firewall, DNS).
- Webhook mal configurado o certificado TLS inválido.
- Rate-limit de Telegram por bursts sin backoff.

### Solución
1. **Corregir credenciales** y recargar servicio:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ultra-bot.service
   ```
2. **Si hay webhook**, re-registrarlo:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<tu-dominio>/telegram/webhook"
   ```
3. **Si hay polling**, asegurar instancia única (evitar doble consumidor).
4. Implementar o validar retry con backoff exponencial en llamadas Telegram.
5. Validar post-fix:
   - `/start` responde < 3s
   - logs sin excepciones repetitivas durante 5 minutos.

---

## 2) PWA no carga (Next.js 16)

### Síntomas
- Pantalla en blanco.
- Error 500/502/504 en frontend.
- Assets estáticos no cargan (JS/CSS 404).
- Service worker con estado inconsistente.

### Checks
1. Estado del servicio frontend:
   ```bash
   sudo systemctl status ultra-pwa.service
   sudo journalctl -u ultra-pwa.service -n 200 --no-pager
   ```
2. Probar endpoint local:
   ```bash
   curl -I http://127.0.0.1:<PORT>
   ```
3. Revisar reverse proxy (Nginx/Caddy/Traefik):
   ```bash
   sudo nginx -t
   sudo journalctl -u nginx -n 100 --no-pager
   ```
4. Confirmar build artefacts:
   - `.next/` presente y consistente con versión desplegada.
5. Verificar cache del navegador/service worker:
   - Hard reload, limpiar cache del sitio, probar incógnito.

### Causas probables
- Build incompleto o artefactos corruptos tras deploy.
- Variables de entorno faltantes en runtime (API base URL, auth keys).
- Reverse proxy apuntando a puerto incorrecto.
- Service worker cacheando assets de versión previa.
- Error SSR por dependencia no disponible.

### Solución
1. Rebuild limpio:
   ```bash
   rm -rf .next
   npm ci
   npm run build
   sudo systemctl restart ultra-pwa.service
   ```
2. Validar env del servicio (`EnvironmentFile`) y secretos.
3. Corregir upstream en proxy y recargar:
   ```bash
   sudo systemctl reload nginx
   ```
4. Invalidar cache PWA (versionado de assets y update de SW).
5. Verificar respuesta:
   ```bash
   curl -I https://<dominio-pwa>
   ```
   Debe devolver 200/304 para HTML y assets estáticos accesibles.

---

## 3) API no responde

### Síntomas
- Timeout desde PWA/CLI/Telegram.
- HTTP 5xx persistente.
- Healthcheck en estado `unhealthy`.

### Checks
1. Estado servicio API:
   ```bash
   sudo systemctl status ultra-api.service
   sudo journalctl -u ultra-api.service -n 300 --no-pager
   ```
2. Health endpoint:
   ```bash
   curl -sS -m 5 http://127.0.0.1:<API_PORT>/health
   ```
3. Puertos en escucha:
   ```bash
   ss -ltnp | grep <API_PORT>
   ```
4. Dependencias API (DB/Redis/queue/LLM gateway) disponibles.
5. Verificar saturación del host (CPU/RAM/FD limits).

### Causas probables
- API arrancó con configuración inválida.
- Bloqueo por dependencia externa caída.
- Pool de conexiones agotado.
- Excepción no capturada en request path crítico.
- Límite de file descriptors o sockets.

### Solución
1. Corregir configuración y reiniciar controlado:
   ```bash
   sudo systemctl restart ultra-api.service
   ```
2. Ajustar timeout/retry hacia dependencias externas.
3. Incrementar límites del servicio (`LimitNOFILE`, pool sizes) si aplica.
4. Habilitar circuit breaker para proveedores externos inestables.
5. Validar:
   - `/health` OK
   - endpoint funcional clave responde en SLA esperado.

---

## 4) Contenedor Letta caído

### Síntomas
- `docker ps` no muestra contenedor Letta en estado `Up`.
- Estado `Exited` o `Restarting`.
- Funciones de memoria/contexto asociadas a Letta fallan.

### Checks
1. Estado contenedor:
   ```bash
   docker ps -a | grep letta
   ```
2. Logs:
   ```bash
   docker logs --tail 300 letta
   ```
3. Motivo de salida:
   ```bash
   docker inspect letta --format='{{.State.Status}} {{.State.ExitCode}} {{.State.Error}}'
   ```
4. Recursos y puertos:
   ```bash
   docker stats --no-stream
   ss -ltnp | grep <LETTA_PORT>
   ```
5. Volúmenes/mounts correctos y permisos.

### Causas probables
- Imagen desactualizada o incompatible con config actual.
- Variables de entorno obligatorias ausentes.
- Puerto en conflicto.
- OOMKill por límite de memoria insuficiente.
- Corrupción en volumen de datos o permisos incorrectos.

### Solución
1. Re-crear contenedor con configuración declarativa (compose).
   ```bash
   docker compose pull letta
   docker compose up -d letta
   ```
2. Corregir variables de entorno y secretos.
3. Resolver conflictos de puertos.
4. Ajustar límites de memoria/reserva en Docker.
5. Si hay volumen corrupto, respaldar y reconstruir con procedimiento controlado.
6. Validar:
   - Contenedor `Up` > 5 min sin restart
   - endpoint de Letta responde correctamente.

---

## 5) LLM sin créditos / cuota agotada

### Síntomas
- Respuestas vacías o fallback continuo.
- Errores tipo `quota exceeded`, `insufficient credits`, `429/402`.
- Cambios automáticos de modo no deseados (FREE/NORMAL/KIMI/etc.).

### Checks
1. Revisar logs de capa LLM router/gateway:
   ```bash
   sudo journalctl -u ultra-api.service -n 300 | grep -Ei "quota|credit|429|402|provider"
   ```
2. Confirmar proveedor activo por modo.
3. Validar claves/API keys vigentes.
4. Revisar panel del proveedor (saldo, límites por minuto/día).
5. Comprobar fallback chain configurado.

### Causas probables
- Saldo agotado en proveedor principal.
- Límite de rate alcanzado por picos.
- Clave revocada o vencida.
- Política de gasto sin alertas preventivas.
- Router LLM mal configurado (sin fallback real).

### Solución
1. Recargar saldo o ampliar cuota.
2. Rotar API key comprometida/caducada.
3. Configurar límites de consumo por servicio/usuario.
4. Definir fallback ordenado entre modos (ej. BOOST -> NORMAL -> FREE).
5. Añadir alertas de saldo bajo (Prometheus + Alertmanager/webhook).
6. Validar con request de prueba en cada modo crítico.

---

## 6) Approvals no llegan

### Síntomas
- Solicitudes de aprobación no aparecen en PWA/Telegram/CLI.
- Flujo queda en estado `pending` indefinidamente.
- Eventos emitidos pero no consumidos.

### Checks
1. Revisar servicio responsable de approvals/notificaciones:
   ```bash
   sudo systemctl status ultra-approvals.service
   sudo journalctl -u ultra-approvals.service -n 300 --no-pager
   ```
2. Verificar broker/cola (si aplica) y consumers activos.
3. Confirmar conectividad con canal de salida (Telegram/websocket/push).
4. Revisar timestamps y timezone (expiraciones prematuras).
5. Auditar DB de approvals: estados, retries, dead-letter.

### Causas probables
- Worker de approvals detenido o con lag.
- Error de serialización en payload.
- Falla en canal de notificación.
- TTL demasiado corto o clock skew entre servicios.
- Mensajes atascados en DLQ sin reproceso.

### Solución
1. Reiniciar worker afectado y drenar cola de forma segura.
2. Corregir esquema/payload y versionado de eventos.
3. Sincronizar hora del host (NTP) en todos los nodos.
4. Ajustar TTL y política de retry.
5. Implementar replay de mensajes pendientes.
6. Validar extremo a extremo:
   - generar approval de prueba
   - recepción en canal esperado
   - transición `pending -> approved/rejected`.

---

## 7) Smart Agent pierde contexto (bug conocido)

### Síntomas
- El agente “olvida” instrucciones previas dentro de la misma sesión.
- Respuestas inconsistentes con memoria reciente.
- Herramientas invocadas sin continuidad lógica.

### Checks
1. Confirmar versión actual y changelog del bug.
2. Revisar logs del Smart Agent y memory backend.
3. Verificar límites de contexto por modo/modelo.
4. Confirmar persistencia de sesión (session_id estable).
5. Validar estado de Letta/memoria intermedia.

### Causas probables
- Bug conocido en gestión de contexto (race condition/snapshot overwrite).
- Truncamiento agresivo de historial por token budget.
- Session ID regenerado entre requests (frontend o API).
- Escritura asíncrona de memoria que no confirma antes de leer.
- Degradación por fallback de modelo con menor ventana de contexto.

### Solución (workaround operativo)
1. **Fijar session_id** en cliente durante toda la conversación.
2. Reducir concurrencia de writes de memoria por sesión.
3. Ajustar política de resumen incremental en lugar de truncado abrupto.
4. Forzar modo/modelo con ventana de contexto mayor para tareas largas.
5. Reiniciar solo componente de memoria si hay corrupción temporal.
6. Informar limitación conocida al usuario y recomendar checkpoints manuales.

### Solución estructural (recomendada)
- Implementar control de versión de estado conversacional (optimistic locking).
- Añadir pruebas de regresión multi-turn con concurrencia.
- Registrar huellas de contexto (hash de historial) para detectar pérdida.
- Publicar fix versionado y plan de migración.

---

## 8) Disco lleno

### Síntomas
- Errores `No space left on device`.
- Servicios fallan al iniciar o escribir logs.
- Docker no puede crear capas/volúmenes.

### Checks
1. Uso global:
   ```bash
   df -h
   ```
2. Inodos:
   ```bash
   df -i
   ```
3. Directorios pesados:
   ```bash
   sudo du -xh /var --max-depth=2 | sort -h | tail -n 30
   sudo du -xh / --max-depth=2 2>/dev/null | sort -h | tail -n 30
   ```
4. Espacio Docker:
   ```bash
   docker system df
   ```
5. Logs systemd/journald:
   ```bash
   journalctl --disk-usage
   ```

### Causas probables
- Rotación de logs ausente o mal configurada.
- Acumulación de imágenes/containers huérfanos.
- Volúmenes Docker crecientes sin retención.
- Dumps/backups temporales no purgados.
- Crecimiento anómalo de métricas/trazas.

### Solución
1. Liberar espacio inmediato:
   ```bash
   docker system prune -af
   docker volume prune -f
   ```
   (usar con criterio; validar impacto antes en producción)
2. Limitar journald en `/etc/systemd/journald.conf`:
   - `SystemMaxUse=1G` (ajustar a capacidad real)
3. Configurar logrotate para servicios Ultra.
4. Definir políticas de retención (logs, backups, artefactos).
5. Mover datos voluminosos a disco dedicado.
6. Validar recuperación:
   - >15% libre en particiones críticas (`/`, `/var`, `/var/lib/docker`).

---

## 9) RAM alta / presión de memoria

### Síntomas
- Latencia elevada general.
- OOMKills en servicios o contenedores.
- Swap excesivo y degradación sostenida.

### Checks
1. Memoria global:
   ```bash
   free -h
   vmstat 1 5
   ```
2. Top procesos:
   ```bash
   ps aux --sort=-%mem | head -n 20
   ```
3. Eventos OOM:
   ```bash
   dmesg -T | grep -Ei "killed process|out of memory|oom"
   ```
4. Docker consumo por contenedor:
   ```bash
   docker stats --no-stream
   ```
5. Revisar fugas en servicios con crecimiento monotónico RSS.

### Causas probables
- Memory leak en API/agent worker.
- Límite de memoria no definido en contenedores.
- Concurrencia excesiva para capacidad del host.
- Cachés sin límites.
- Demasiados modelos/procesos pesados simultáneos.

### Solución
1. Reinicio controlado del proceso con mayor consumo (mitigación inmediata).
2. Establecer límites por servicio (systemd `MemoryMax`, Docker `mem_limit`).
3. Reducir workers/concurrencia y batch size.
4. Activar profiling de memoria en componente sospechoso.
5. Dimensionar swap de contingencia (sin usarlo como solución permanente).
6. Escalar vertical/horizontal según carga real.
7. Validar:
   - sin OOM en 24h
   - latencia y error rate dentro de umbral.

---

## 10) Servicios en loop de restart (systemd)

### Síntomas
- `Active: activating (auto-restart)` o `failed` recurrente.
- Alta frecuencia de reinicios y downtime intermitente.
- Cascada de fallas entre dependencias.

### Checks
1. Estado detallado:
   ```bash
   sudo systemctl status <service>
   sudo systemctl show <service> -p Restart -p RestartSec -p StartLimitBurst -p StartLimitIntervalSec
   ```
2. Logs de arranque:
   ```bash
   sudo journalctl -u <service> -b -n 300 --no-pager
   ```
3. Ejecutar binario manualmente con la misma configuración para aislar error.
4. Confirmar dependencias (`After=`, `Requires=`) disponibles al arranque.
5. Validar rutas, permisos, usuario de ejecución y archivos de entorno.

### Causas probables
- Error fatal al iniciar (config/env faltante).
- Dependencia no lista cuando arranca el servicio.
- Healthcheck interno falla y fuerza exit.
- Políticas de restart demasiado agresivas.
- Cambios recientes no aplicados con `daemon-reload`.

### Solución
1. Corregir error raíz mostrado en logs.
2. Ajustar unit file:
   - `Restart=on-failure`
   - `RestartSec=5s` o más
   - `StartLimit*` razonables para evitar thrash
3. Asegurar orden de arranque correcto con dependencias.
4. Ejecutar:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl reset-failed <service>
   sudo systemctl restart <service>
   ```
5. Validar estabilidad 10-15 minutos sin reinicios.

---

## Runbook rápido de recuperación (severidad alta)

Cuando múltiples componentes fallan al mismo tiempo:

1. **Congelar cambios** (no desplegar nuevas versiones).
2. **Recuperar recursos base**:
   - liberar disco
   - estabilizar RAM
3. **Levantar plano de control**:
   - API
   - servicios de coordinación/cola
4. **Levantar interfaces**:
   - PWA
   - bot Telegram
5. **Levantar componentes avanzados**:
   - Letta / Smart Agent / self-healing loops
6. **Validación funcional mínima**:
   - health API
   - comando Telegram
   - carga inicial PWA
   - ejecución de 1 tool del Smart Agent
7. **Postmortem corto**:
   - causa raíz
   - impacto
   - acciones preventivas

---

## Señales de observabilidad recomendadas

Para prevenir recurrencia, monitorizar al menos:

- `service_up` por cada servicio systemd crítico.
- Tasa de reinicios por unidad y contenedor.
- Latencia p95/p99 de API y bot.
- Errores HTTP 5xx por ruta.
- Uso de RAM por proceso + OOM events.
- Uso de disco por partición + crecimiento diario.
- Estado de créditos/cuota por proveedor LLM.
- Lag de colas y tamaño de DLQ (approvals/eventos).
- Tasa de “context reset” del Smart Agent (métrica específica).

Alertas mínimas:
- Disco > 85%
- RAM > 90% sostenido 10 min
- API health failing > 2 min
- Restart loop > 5 reinicios/10 min
- Créditos LLM por debajo de umbral operativo.

---

## Checklist final de cierre de incidente

Antes de declarar incidente resuelto:

- [ ] Síntoma original reproducido y ahora corregido.
- [ ] Causa raíz identificada (o hipótesis explícita si no concluyente).
- [ ] Evidencia en logs/metrics archivada.
- [ ] Mitigación temporal aplicada (si no hay fix definitivo).
- [ ] Ticket de hardening creado (automatización/alerta/test).
- [ ] Documentación actualizada (este archivo u runbooks relacionados).

Si el problema reaparece en menos de 24-48h, tratarlo como **no resuelto** y escalar a análisis profundo (profiling, trazas detalladas, pruebas de carga y revisión de arquitectura de dependencia).