# Los 16 Servicios del Stack

## Servicios Ultra (systemd)

### ultra-bot
Bot de Telegram Ultra_Erik_Bot. Archivo en interfaces/telegram/ultra_bot.py.

### ultra-cc
PWA Command Center Next.js 16 en puerto 3100.

### ultra-cc-api
Backend FastAPI puerto 8200. Docs en http://IP:8200/docs.

### ultra-dashboard
Dashboard Streamlit puerto 8501.

### ultra-backup
Scheduler de backups automatico.

### ultra-monitor
Monitor de servicios cada 60s. Archivo autonomy/monitor/monitor_agent.py.

### ultra-healer
Auto-restart de servicios caidos cada 120s.

### ultra-learner
Analisis de patrones cada 1 hora.

### ultra-improver
Sugerencias de mejora cada 24h.

### ultra-meta
Meta-Agent consciente del sistema cada 10 min.

### ultra-proposer
Propuestas proactivas cada 30 min via Telegram con botones.

### ultra-metrics
Exporter Prometheus puerto 9100.

## Servicios de infraestructura

### redis-server
Cache y pubsub puerto 6379.

### fail2ban
Protector SSH con config en /etc/fail2ban/jail.local. Bantime 3600s, MaxRetry 3.

### postgresql externo
Base de datos principal en DigitalOcean managed.

## Docker Containers

### letta
Memoria persistente IA puerto 8283. API http://localhost:8283/v1.

### ultra-prometheus
Metricas puerto 9090.

### ultra-grafana
Dashboards puerto 3000. Default user admin/admin.
