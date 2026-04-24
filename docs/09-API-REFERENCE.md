# 09 - API Reference

## Overview

Ultra Stack expone una API REST y canales WebSocket sobre **FastAPI** para permitir integración con UI web, CLI, bots, y servicios externos. Esta referencia describe los contratos HTTP/WebSocket, convenciones de autenticación, control de errores y límites de uso.

- **Base URL local**: `http://127.0.0.1:8200`
- **Base URL LAN**: `http://<host-ip>:8200`
- **OpenAPI schema**: `GET /openapi.json`
- **Interactive docs (Swagger UI)**: `GET /docs`
- **ReDoc**: `GET /redoc`

La API está diseñada para interoperar con el runtime multi-agente de Ultra Stack, incluyendo control de modos LLM, operación de servicios, flujos de aprobación humana y consumo de logs/reportes operativos.

---

## API Conventions

### Content Types

- Request body: `application/json`
- Response body: `application/json`
- WebSocket messages: JSON text frames

### Character Encoding

- UTF-8 en todas las rutas.

### Time Format

- Timestamps en formato ISO-8601 UTC, por ejemplo:
  - `2026-04-24T20:15:31Z`
  - `2026-04-24T20:15:31.483Z`

### Idempotency and Safety

- `GET` se considera seguro y sin efectos colaterales.
- `POST` puede alterar estado (`/api/chat`, `/api/llm/set-mode`, `/api/service/action`, `/api/approvals`).

### Correlation IDs

Se recomienda incluir `X-Request-ID` en cada request para trazabilidad extremo a extremo.

---

## Authentication and Authorization

Dependiendo de la configuración del despliegue, la API puede operar en:

1. **Modo local trusted** (sin auth estricta, recomendado solo localhost).
2. **Modo protegido** con API key o token proxy (Nginx/Traefik/OAuth2 gateway).

Cabeceras recomendadas:

- `Authorization: Bearer <token>`
- o `X-API-Key: <key>`

Cuando auth está activa y falla:

- `401 Unauthorized`: credencial ausente o inválida.
- `403 Forbidden`: credencial válida, permisos insuficientes.

> Nota: La implementación exacta del middleware de auth puede variar por entorno; esta referencia describe el contrato esperado por clientes de integración.

---

## CORS Policy

La API usa CORS configurable para habilitar UI (PWA Next.js), dashboards y clientes externos.

### Default (desarrollo)

- `Access-Control-Allow-Origin: *`
- Métodos permitidos: `GET, POST, OPTIONS`
- Headers permitidos: `Authorization, Content-Type, X-Request-ID, X-API-Key`

### Recommended (producción)

Restringir `allow_origins` a dominios explícitos, por ejemplo:

- `https://ultra.example.com`
- `https://dashboard.example.com`

Evitar `*` cuando se utilicen credenciales (`allow_credentials=true`).

---

## Rate Limiting

El rate limiting protege CPU/GPU, proveedores LLM y estabilidad del sistema. Puede aplicarse vía middleware FastAPI o reverse proxy.

### Suggested Limits

- `/api/chat`: 30 req/min por IP o token
- `/api/llm/set-mode`: 10 req/min
- `/api/service/action`: 20 req/min
- Endpoints de lectura (`status`, `logs`, `reports`): 60 req/min
- WebSockets: límite de conexiones concurrentes por cliente (p. ej. 3)

### Response When Limited

`429 Too Many Requests`

Ejemplo:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after_seconds": 25
  }
}
```

---

## Error Model

Formato estándar de error:

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "req_8f24b9d7"
  }
}
```

### Common Error Codes

- `BAD_REQUEST` → `400`
- `UNAUTHORIZED` → `401`
- `FORBIDDEN` → `403`
- `NOT_FOUND` → `404`
- `CONFLICT` → `409`
- `UNPROCESSABLE_ENTITY` → `422`
- `RATE_LIMIT_EXCEEDED` → `429`
- `INTERNAL_ERROR` → `500`
- `UPSTREAM_TIMEOUT` → `504`

---

## REST Endpoints

## `POST /api/chat`

Envía un mensaje al Smart Agent y retorna respuesta del pipeline LLM activo, incluyendo metadatos útiles para debugging y observabilidad.

### Request Body

```json
{
  "message": "Resume el estado actual del sistema",
  "session_id": "cli-local-001",
  "mode": "NORMAL",
  "context": {
    "source": "cli",
    "user_id": "erik"
  },
  "stream": false
}
```

### Fields

- `message` (string, requerido): prompt del usuario.
- `session_id` (string, opcional): correlación conversacional.
- `mode` (string, opcional): fuerza modo LLM para esta invocación (`FREE|NORMAL|KIMI|BOOST|TURBO|BLACKBOX|CODE`).
- `context` (object, opcional): metadata libre.
- `stream` (bool, opcional): si `true`, puede delegar streaming por WebSocket según implementación.

### Success Response `200`

```json
{
  "reply": "Sistema operativo. 16 servicios activos, 3 contenedores saludables, sin alertas críticas.",
  "mode_used": "NORMAL",
  "session_id": "cli-local-001",
  "latency_ms": 842,
  "tokens": {
    "prompt": 54,
    "completion": 31,
    "total": 85
  },
  "tools_invoked": ["health_check", "service_status"],
  "timestamp": "2026-04-24T20:20:01Z"
}
```

### Validation Errors `422`

Campos inválidos, JSON malformado o modo no soportado.

---

## `GET /api/status`

Retorna estado agregado de Ultra Stack: salud general, runtime, servicios y componentes críticos.

### Query Params

- `verbose` (bool, opcional, default `false`): incluye detalle de servicios y recursos.
- `include_metrics` (bool, opcional): incluye snapshot de CPU/RAM/disco.

### Example Request

`GET /api/status?verbose=true&include_metrics=true`

### Success Response `200`

```json
{
  "overall_status": "healthy",
  "uptime_seconds": 182340,
  "timestamp": "2026-04-24T20:22:17Z",
  "services": {
    "systemd_total": 16,
    "systemd_active": 16,
    "docker_total": 3,
    "docker_healthy": 3
  },
  "llm": {
    "current_mode": "NORMAL",
    "fallback_chain": ["FREE", "NORMAL", "KIMI", "BOOST"]
  },
  "self_healing": {
    "monitor": "running",
    "healer": "running",
    "learner": "running",
    "improver": "running"
  },
  "metrics": {
    "cpu_percent": 23.4,
    "memory_percent": 61.2,
    "disk_percent": 44.9
  }
}
```

---

## `GET /api/llm/status`

Devuelve estado del subsistema LLM: proveedor activo, disponibilidad, modo actual y últimos eventos relevantes.

### Success Response `200`

```json
{
  "current_mode": "KIMI",
  "provider": "moonshot",
  "available_modes": ["FREE", "NORMAL", "KIMI", "BOOST", "TURBO", "BLACKBOX", "CODE"],
  "last_switch": {
    "from": "NORMAL",
    "to": "KIMI",
    "reason": "manual_api_request",
    "at": "2026-04-24T20:05:12Z"
  },
  "health": {
    "provider_reachable": true,
    "avg_latency_ms_5m": 1102,
    "error_rate_5m": 0.01
  }
}
```

---

## `GET /api/llm/modes`

Lista los modos disponibles y sus capacidades declaradas.

### Success Response `200`

```json
{
  "modes": [
    {
      "name": "FREE",
      "description": "Modo económico con prioridad a costo cero",
      "intended_use": ["fallback", "low-priority"],
      "supports_code": false
    },
    {
      "name": "NORMAL",
      "description": "Balance general costo/rendimiento",
      "intended_use": ["default", "chat"],
      "supports_code": true
    },
    {
      "name": "KIMI",
      "description": "Modelo de alta ventana de contexto",
      "intended_use": ["long-context", "analysis"],
      "supports_code": true
    },
    {
      "name": "BOOST",
      "description": "Calidad reforzada",
      "intended_use": ["critical tasks"],
      "supports_code": true
    },
    {
      "name": "TURBO",
      "description": "Baja latencia",
      "intended_use": ["real-time", "fast iterations"],
      "supports_code": true
    },
    {
      "name": "BLACKBOX",
      "description": "Modo experimental",
      "intended_use": ["research"],
      "supports_code": true
    },
    {
      "name": "CODE",
      "description": "Optimizado para generación de código",
      "intended_use": ["coding", "refactor", "debugging"],
      "supports_code": true
    }
  ]
}
```

---

## `POST /api/llm/set-mode`

Cambia el modo LLM global activo del sistema.

### Request Body

```json
{
  "mode": "CODE",
  "reason": "maintenance_codegen_batch",
  "requested_by": "api-client"
}
```

### Fields

- `mode` (string, requerido): uno de los 7 modos soportados.
- `reason` (string, opcional): auditoría de cambio.
- `requested_by` (string, opcional): actor lógico.

### Success Response `200`

```json
{
  "ok": true,
  "previous_mode": "NORMAL",
  "new_mode": "CODE",
  "applied_at": "2026-04-24T20:26:48Z"
}
```

### Conflict Response `409`

Cuando un lock operativo impide el cambio (p. ej. tarea crítica en progreso):

```json
{
  "error": {
    "code": "MODE_SWITCH_LOCKED",
    "message": "Mode cannot be changed during protected execution window"
  }
}
```

---

## `POST /api/service/action`

Ejecuta acciones operativas sobre servicios gestionados (systemd y/o contenedores).

### Request Body

```json
{
  "target": "ultra-monitor.service",
  "kind": "systemd",
  "action": "restart",
  "dry_run": false
}
```

### Fields

- `target` (string, requerido): nombre del servicio/unidad.
- `kind` (string, requerido): `systemd` o `docker`.
- `action` (string, requerido): `start|stop|restart|status`.
- `dry_run` (bool, opcional): si `true`, no ejecuta cambios reales.

### Success Response `200`

```json
{
  "ok": true,
  "target": "ultra-monitor.service",
  "kind": "systemd",
  "action": "restart",
  "result": "active",
  "executed_at": "2026-04-24T20:28:03Z",
  "duration_ms": 412
}
```

### Not Found `404`

Servicio inexistente o no administrable.

---

## `GET /api/logs`

Consulta logs recientes del sistema para troubleshooting.

### Query Params

- `source` (string, opcional): `systemd|docker|app|all` (default `all`)
- `service` (string, opcional): nombre específico de servicio.
- `level` (string, opcional): `DEBUG|INFO|WARNING|ERROR|CRITICAL`
- `limit` (int, opcional, default `100`, max recomendado `1000`)
- `since` (ISO-8601, opcional): filtra desde timestamp.
- `contains` (string, opcional): búsqueda textual.

### Example Request

`GET /api/logs?source=systemd&service=ultra-healer.service&level=ERROR&limit=50`

### Success Response `200`

```json
{
  "count": 2,
  "items": [
    {
      "timestamp": "2026-04-24T20:01:07Z",
      "source": "systemd",
      "service": "ultra-healer.service",
      "level": "ERROR",
      "message": "Provider timeout; retry scheduled",
      "meta": {
        "retry_in_seconds": 10
      }
    },
    {
      "timestamp": "2026-04-24T20:01:17Z",
      "source": "systemd",
      "service": "ultra-healer.service",
      "level": "INFO",
      "message": "Recovery attempt succeeded",
      "meta": {}
    }
  ]
}
```

---

## `GET /api/reports`

Lista o recupera reportes operativos generados por los módulos autónomos (monitoring, healing, learning, improvement).

### Query Params

- `type` (string, opcional): `health|incident|learning|improvement|all`
- `limit` (int, opcional, default `20`)
- `offset` (int, opcional, default `0`)
- `from` / `to` (ISO-8601, opcional): ventana temporal

### Success Response `200`

```json
{
  "total": 134,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "rep_20260424_0012",
      "type": "incident",
      "created_at": "2026-04-24T19:40:00Z",
      "summary": "Transient LLM provider latency spike",
      "severity": "medium",
      "status": "resolved",
      "links": {
        "details": "/api/reports/rep_20260424_0012"
      }
    }
  ]
}
```

> Si la implementación incluye endpoint de detalle (`/api/reports/{id}`), seguir el mismo esquema de error/serialización documentado aquí.

---

## `GET /api/approvals`
## `POST /api/approvals`

Gestiona solicitudes de aprobación humana para acciones sensibles (reinicios críticos, cambios de modo protegidos, operaciones destructivas).

### `GET /api/approvals` Query Params

- `status` (string, opcional): `pending|approved|rejected|expired`
- `limit` (int, opcional, default `50`)

### `GET` Success Response `200`

```json
{
  "count": 1,
  "items": [
    {
      "id": "apr_8d31",
      "created_at": "2026-04-24T20:10:00Z",
      "requested_by": "ultra-healer",
      "action": "restart",
      "target": "postgres.service",
      "reason": "healthcheck failed 5 times",
      "status": "pending",
      "expires_at": "2026-04-24T20:20:00Z"
    }
  ]
}
```

### `POST /api/approvals` Request Body

```json
{
  "approval_id": "apr_8d31",
  "decision": "approved",
  "decided_by": "erik",
  "comment": "Proceder con reinicio controlado"
}
```

### `POST` Success Response `200`

```json
{
  "ok": true,
  "approval_id": "apr_8d31",
  "new_status": "approved",
  "applied_at": "2026-04-24T20:12:11Z"
}
```

### Invalid State `409`

Decisión sobre solicitud expirada o ya resuelta.

---

## WebSocket Endpoints

Los WebSockets proporcionan eventos en tiempo real para dashboards, PWA y CLI interactiva.

### Connection Notes

- URL base: `ws://<host>:8200`
- Si hay auth, enviar token por:
  - Query param: `?token=<jwt>`
  - o cabecera soportada por proxy/middleware.
- Heartbeat recomendado cliente: ping cada 20-30s.
- Reconexión exponencial recomendada (1s, 2s, 4s, 8s, máx 30s).

---

### `GET ws://<host>:8200/ws/status`

Stream de estado operativo agregado.

#### Server Event Example

```json
{
  "event": "status_update",
  "timestamp": "2026-04-24T20:30:00Z",
  "data": {
    "overall_status": "healthy",
    "systemd_active": 16,
    "docker_healthy": 3,
    "current_mode": "NORMAL"
  }
}
```

Frecuencia típica: 1-5 segundos (configurable).

---

### `GET ws://<host>:8200/ws/chat`

Canal bidireccional para chat en tiempo real con soporte de tokens/parciales.

#### Client Message

```json
{
  "type": "chat_request",
  "message": "Dame un resumen de errores críticos de hoy",
  "session_id": "pwa-42",
  "mode": "TURBO"
}
```

#### Server Partial

```json
{
  "type": "chat_chunk",
  "session_id": "pwa-42",
  "delta": "No se detectaron errores críticos ",
  "index": 1
}
```

#### Server Final

```json
{
  "type": "chat_final",
  "session_id": "pwa-42",
  "reply": "No se detectaron errores críticos en las últimas 24h. Hubo 2 incidentes de latencia media resueltos automáticamente.",
  "latency_ms": 910,
  "mode_used": "TURBO"
}
```

---

### `GET ws://<host>:8200/ws/approvals`

Notificaciones push de nuevas solicitudes y cambios de estado de aprobaciones.

#### Server Event Example

```json
{
  "event": "approval_created",
  "timestamp": "2026-04-24T20:31:10Z",
  "data": {
    "id": "apr_9f22",
    "action": "restart",
    "target": "ultra-learner.service",
    "status": "pending",
    "expires_at": "2026-04-24T20:41:10Z"
  }
}
```

---

## HTTP Status Codes Summary

- `200 OK`: operación completada.
- `201 Created`: opcional para recursos nuevos (si aplica en extensiones).
- `400 Bad Request`: parámetros inválidos.
- `401 Unauthorized`: auth requerida o inválida.
- `403 Forbidden`: sin permisos.
- `404 Not Found`: recurso/servicio inexistente.
- `409 Conflict`: conflicto de estado (lock, expirado, ya resuelto).
- `422 Unprocessable Entity`: validación semántica de payload.
- `429 Too Many Requests`: límite excedido.
- `500 Internal Server Error`: fallo inesperado.
- `502/503/504`: errores/transitorio de upstream.

---

## Compatibility and Versioning

Aunque los endpoints descritos son estables para el stack actual, se recomienda:

- Consumir rutas bajo prefijo versionado si se habilita (`/api/v1/...`).
- Tolerar campos adicionales en respuestas JSON.
- No asumir orden fijo en listas.
- Validar `mode` contra `/api/llm/modes` en runtime.

Para cambios breaking:

1. Introducir nueva versión de endpoint.
2. Mantener compatibilidad temporal.
3. Publicar ventana de deprecación.

---

## Operational Best Practices for Clients

1. **Timeouts**: usar timeout de cliente (3-10s lectura normal, más alto para operaciones pesadas).
2. **Retries**:
   - Reintentar en `429`, `502`, `503`, `504`.
   - Backoff exponencial con jitter.
3. **Circuit Breaking**:
   - Abrir circuito si tasa de error supera umbral.
4. **Observability**:
   - Adjuntar `X-Request-ID`.
   - Registrar latencia y código HTTP.
5. **Safety**:
   - Confirmar acciones sensibles por `/api/approvals`.
   - Usar `dry_run=true` en `/api/service/action` antes de producción.
6. **WebSocket resilience**:
   - Auto-reconectar.
   - Re-sincronizar estado vía REST tras reconexión.

---

## Minimal End-to-End Flow Example

1. Verificar estado:
   - `GET /api/status`
2. Inspeccionar modo actual:
   - `GET /api/llm/status`
3. Cambiar a modo de trabajo:
   - `POST /api/llm/set-mode` (`CODE`)
4. Ejecutar interacción:
   - `POST /api/chat`
5. Si se requiere acción crítica:
   - recibir solicitud en `/ws/approvals`
   - decidir por `POST /api/approvals`
6. Auditar:
   - `GET /api/logs`
   - `GET /api/reports`

Este flujo cubre operación estándar de Ultra Stack para entornos autónomos con supervisión humana opcional.