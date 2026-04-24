# 10. Deployment en VPS de Producción

Este documento describe el proceso recomendado para desplegar **Ultra Stack** en un VPS de producción con un enfoque de estabilidad, seguridad, observabilidad y capacidad de recuperación.  
El objetivo es entregar una guía operativa reproducible, alineada con prácticas de despliegue tipo Kubernetes/Docker: declarativo cuando sea posible, explícito en dependencias, y con procedimientos de rollback claros.

---

## 1. Objetivo y alcance

Este procedimiento cubre:

- Requisitos mínimos y recomendados del servidor.
- Preparación del sistema base (Ubuntu 22.04+).
- Instalación de dependencias (Python, Docker, systemd units, NGINX).
- Despliegue de Ultra Stack (servicios systemd + contenedores Docker).
- Exposición segura de servicios mediante reverse proxy.
- Certificados TLS con Let’s Encrypt.
- Monitoreo con Prometheus y Grafana.
- Backups automáticos y restauración.
- Estrategia de rollback.
- Hardening de seguridad para producción.

No cubre tuning avanzado de kernel ni despliegue multi-nodo/HA. El modelo operativo es **single VPS production-grade**.

---

## 2. Arquitectura objetivo en producción

Ultra Stack en producción se compone de:

- **16 servicios systemd** para orquestación local, agentes y componentes internos.
- **3 contenedores Docker**:
  - `letta`
  - `prometheus`
  - `grafana`
- Interfaces:
  - PWA Next.js (puerto interno 3100)
  - Telegram bot
  - CLI `ultra`
  - Dashboard Streamlit (según configuración del stack)
  - Grafana (normalmente detrás de NGINX)
- Modo de ejecución LLM configurable (`FREE`, `NORMAL`, `KIMI`, `BOOST`, `TURBO`, `BLACKBOX`, `CODE`).
- Módulos self-healing (`Monitor`, `Healer`, `Learner`, `Improver`) activos como servicios supervisados.

Topología de red recomendada:

- Externo:
  - `22/tcp` (SSH restringido)
  - `443/tcp` (HTTPS público)
  - `3100/tcp` (solo si se decide exponer directamente; recomendado proxy por 443)
- Interno:
  - Puertos de Prometheus/Grafana/Letta no expuestos públicamente, accesibles por loopback o red Docker.

---

## 3. Requisitos del servidor

## 3.1 Requisitos mínimos

- SO: **Ubuntu 22.04 LTS** o superior.
- CPU: 2 vCPU.
- RAM: **4 GB** mínimo.
- Disco: 40 GB SSD (mínimo operativo), recomendado 80+ GB.
- Python: **3.10+**.
- Acceso root o usuario con privilegios sudo.
- DNS apuntando al VPS (A/AAAA) para el dominio productivo.

## 3.2 Requisitos recomendados

- 4 vCPU / 8 GB RAM para carga moderada y mejor estabilidad de modelos/agentes.
- Disco SSD NVMe.
- Swap de 2-4 GB para absorber picos.
- Dominio dedicado (ej. `ultra.midominio.com`).
- Backups de volumen en proveedor cloud (snapshot diario).

---

## 4. Preparación inicial del VPS

## 4.1 Crear usuario operativo y acceso SSH seguro

```bash
adduser ultra
usermod -aG sudo ultra
mkdir -p /home/ultra/.ssh
cp /root/.ssh/authorized_keys /home/ultra/.ssh/authorized_keys
chown -R ultra:ultra /home/ultra/.ssh
chmod 700 /home/ultra/.ssh
chmod 600 /home/ultra/.ssh/authorized_keys
```

Editar SSH daemon:

```bash
sudo nano /etc/ssh/sshd_config
```

Parámetros recomendados:

```conf
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
```

Aplicar:

```bash
sudo systemctl restart ssh
```

## 4.2 Actualizar sistema y paquetes base

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install git curl wget unzip jq ca-certificates gnupg lsb-release \
  software-properties-common build-essential ufw fail2ban
```

## 4.3 Instalar Python 3.10+ y tooling

Ubuntu 22.04 ya incluye Python 3.10. Verificar:

```bash
python3 --version
```

Instalar pip/venv:

```bash
sudo apt -y install python3-pip python3-venv
pip3 --version
```

---

## 5. Instalación de Docker y Docker Compose plugin

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ultra
```

Verificar:

```bash
docker --version
docker compose version
```

---

## 6. Obtención del código y estructura de despliegue

Con usuario `ultra`:

```bash
cd /opt
sudo mkdir -p /opt/ultra-stack
sudo chown -R ultra:ultra /opt/ultra-stack
cd /opt/ultra-stack
git clone https://github.com/Araarita/ultra-stack.git .
```

Estructura recomendada adicional:

```bash
mkdir -p /opt/ultra-stack/{releases,shared,backups,logs}
mkdir -p /opt/ultra-stack/shared/{env,data,models,prometheus,grafana,letta}
```

Si el repositorio incluye plantilla de variables:

```bash
cp .env.example .env
nano .env
```

Definir como mínimo:

- claves API de proveedores LLM
- modo por defecto (`LLM_MODE=NORMAL`, por ejemplo)
- dominios y puertos internos
- credenciales de Grafana/servicios internos
- tokens de Telegram bot
- rutas persistentes en `/opt/ultra-stack/shared`

---

## 7. Instalación de dependencias Python del stack

Crear entorno virtual dedicado:

```bash
cd /opt/ultra-stack
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
deactivate
```

Si hay componentes con requirements separados, instalarlos en el mismo venv o venvs aislados por servicio según el diseño del repositorio.

---

## 8. Servicios systemd de Ultra Stack

Ultra Stack utiliza múltiples servicios systemd (16 en total). La práctica recomendada es:

- unit files versionados en el repo (`deploy/systemd/*.service`)
- symlink o copia a `/etc/systemd/system/`
- usuario de ejecución no privilegiado (`ultra`)
- reinicio automático (`Restart=always`)
- logs vía journald + rotación

Ejemplo de instalación masiva:

```bash
sudo cp /opt/ultra-stack/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ultra-*.service
sudo systemctl start ultra-*.service
```

Verificación de estado:

```bash
systemctl list-units --type=service | grep ultra
systemctl status ultra-monitor.service
journalctl -u ultra-monitor.service -n 100 --no-pager
```

Parámetros críticos en unit files:

- `WorkingDirectory=/opt/ultra-stack`
- `EnvironmentFile=/opt/ultra-stack/.env`
- `ExecStart=/opt/ultra-stack/.venv/bin/python ...`
- `User=ultra`
- `Group=ultra`
- `Restart=always`
- `RestartSec=5`

---

## 9. Despliegue de contenedores (Letta, Prometheus, Grafana)

Asumiendo `docker-compose.yml` en el repo:

```bash
cd /opt/ultra-stack
docker compose pull
docker compose up -d letta prometheus grafana
```

Verificar salud:

```bash
docker compose ps
docker logs --tail=100 ultra-stack-prometheus-1
docker logs --tail=100 ultra-stack-grafana-1
```

Buenas prácticas de persistencia:

- Montar volúmenes en `/opt/ultra-stack/shared/prometheus`
- Montar volúmenes en `/opt/ultra-stack/shared/grafana`
- Montar estado de Letta en `/opt/ultra-stack/shared/letta`

Nunca depender de filesystem efímero del contenedor para datos críticos.

---

## 10. Firewall de producción (UFW)

Política solicitada: puertos **22**, **3100**, **443**.

Configurar UFW:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 3100/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Recomendación operativa:

- Mantener `3100` abierto solo temporalmente durante validación.
- Una vez NGINX reverse proxy esté estable, restringir 3100 a localhost o eliminar exposición pública:
  ```bash
  sudo ufw delete allow 3100/tcp
  ```
- Si se requiere acceso administrativo a Grafana, publicarlo por subruta/subdominio detrás de 443, no por puerto directo.

---

## 11. NGINX como reverse proxy

Instalar NGINX:

```bash
sudo apt -y install nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

Config base para Ultra Stack (`/etc/nginx/sites-available/ultra-stack`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name ultra.midominio.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ultra.midominio.com;

    ssl_certificate /etc/letsencrypt/live/ultra.midominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ultra.midominio.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer-when-downgrade always;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }

    location /grafana/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /prometheus/ {
        proxy_pass http://127.0.0.1:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/ultra-stack /etc/nginx/sites-enabled/ultra-stack
sudo nginx -t
sudo systemctl reload nginx
```

---

## 12. SSL con Let’s Encrypt

Instalar Certbot:

```bash
sudo apt -y install certbot python3-certbot-nginx
```

Emitir certificado:

```bash
sudo certbot --nginx -d ultra.midominio.com --redirect --agree-tos -m admin@midominio.com --no-eff-email
```

Verificar renovación automática:

```bash
systemctl status certbot.timer
sudo certbot renew --dry-run
```

Puntos clave:

- DNS debe resolver al VPS antes de emitir.
- Puerto 80 debe estar accesible para challenge HTTP-01.
- Renovación automática requiere `certbot.timer` activo.

---

## 13. Monitoreo con Prometheus y Grafana

## 13.1 Prometheus

Configurar targets en `prometheus.yml` para:

- métricas de servicios Ultra Stack (si exponen `/metrics`)
- node exporter (recomendado instalar)
- endpoints de salud internos

Ejemplo de bloque:

```yaml
scrape_configs:
  - job_name: "ultra-services"
    static_configs:
      - targets:
          - "127.0.0.1:9100"
          - "127.0.0.1:8001"
          - "127.0.0.1:8002"
```

Desplegar/reiniciar:

```bash
docker compose up -d prometheus
docker restart ultra-stack-prometheus-1
```

## 13.2 Grafana

Buenas prácticas:

- contraseña admin robusta vía variable de entorno.
- deshabilitar registro público.
- dashboard de:
  - estado de servicios systemd
  - consumo CPU/RAM por proceso
  - latencia y errores por tool/agente
  - uptime de endpoints clave
- alertas básicas:
  - servicio caído > 1 min
  - memoria libre < 10%
  - reinicios frecuentes en systemd/docker
  - uso de disco > 85%

Si se expone Grafana vía NGINX en `/grafana/`, ajustar `root_url` y `serve_from_sub_path=true`.

---

## 14. Backups automáticos

## 14.1 Qué respaldar

- `/opt/ultra-stack/.env`
- `/opt/ultra-stack/shared/` (datos persistentes)
- configuraciones:
  - `/etc/nginx/sites-available/ultra-stack`
  - `/etc/systemd/system/ultra-*.service`
  - `/etc/letsencrypt/` (certificados y metadata)
- dumps de Grafana/Prometheus si aplica.

## 14.2 Script de backup

Crear `/usr/local/bin/ultra-backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TS=$(date +"%Y%m%d-%H%M%S")
DEST="/opt/ultra-stack/backups/$TS"
mkdir -p "$DEST"

tar -czf "$DEST/app-env.tgz" /opt/ultra-stack/.env
tar -czf "$DEST/shared-data.tgz" /opt/ultra-stack/shared
tar -czf "$DEST/nginx.tgz" /etc/nginx/sites-available/ultra-stack
tar -czf "$DEST/systemd.tgz" /etc/systemd/system/ultra-*.service
tar -czf "$DEST/letsencrypt.tgz" /etc/letsencrypt

find /opt/ultra-stack/backups -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} \;
```

Permisos:

```bash
sudo chmod +x /usr/local/bin/ultra-backup.sh
```

## 14.3 Programar backup diario (cron)

```bash
sudo crontab -e
```

Agregar:

```cron
15 3 * * * /usr/local/bin/ultra-backup.sh >> /var/log/ultra-backup.log 2>&1
```

Recomendación: copiar backups a almacenamiento remoto (S3 compatible, rsync a nodo secundario, o snapshots del proveedor).

---

## 15. Estrategia de rollback

Rollback debe ser rápido, determinista y probado. Se recomienda despliegue por releases versionadas:

- `/opt/ultra-stack/releases/<git-sha>`
- symlink activo `/opt/ultra-stack/current`

Flujo recomendado:

1. Preparar nueva release en carpeta separada.
2. Instalar dependencias/validar health checks.
3. Cambiar symlink `current` de forma atómica.
4. Reiniciar servicios apuntando a `current`.
5. Si falla, revertir symlink a release anterior y reiniciar.

Comandos ejemplo:

```bash
ln -sfn /opt/ultra-stack/releases/NEW_SHA /opt/ultra-stack/current
sudo systemctl restart ultra-*.service
```

Rollback:

```bash
ln -sfn /opt/ultra-stack/releases/PREV_SHA /opt/ultra-stack/current
sudo systemctl restart ultra-*.service
docker compose -f /opt/ultra-stack/current/docker-compose.yml up -d
```

Validar post-rollback:

- `systemctl is-active` en servicios críticos.
- health endpoint de PWA/API.
- integridad de bot Telegram.
- dashboards/alertas operativas.

---

## 16. Hardening de seguridad

## 16.1 Sistema operativo

- Activar actualizaciones de seguridad automáticas:
  ```bash
  sudo apt -y install unattended-upgrades
  sudo dpkg-reconfigure unattended-upgrades
  ```
- Minimizar paquetes instalados.
- Deshabilitar servicios no utilizados:
  ```bash
  systemctl list-unit-files --type=service | grep enabled
  ```

## 16.2 SSH y acceso

- Solo autenticación por llave.
- Cambiar puerto SSH opcionalmente si política lo exige.
- Lista de IPs permitidas por firewall (whitelist administrativa).
- Fail2ban activo para mitigar brute force:
  ```bash
  sudo systemctl enable fail2ban
  sudo systemctl start fail2ban
  ```

## 16.3 Docker

- No exponer daemon Docker por TCP.
- Limitar capacidades de contenedores cuando sea posible.
- Ejecutar imágenes oficiales y fijar tags/versiones.
- Escaneo regular de vulnerabilidades de imágenes.

## 16.4 Secrets management

- No commitear `.env` ni credenciales.
- Permisos estrictos:
  ```bash
  chmod 600 /opt/ultra-stack/.env
  chown ultra:ultra /opt/ultra-stack/.env
  ```
- Rotación periódica de API keys y tokens.

## 16.5 NGINX/TLS

- Solo TLS 1.2/1.3.
- HSTS habilitado.
- Security headers activos.
- Rate limiting opcional para rutas sensibles (`/api`, webhooks, auth).

## 16.6 Auditoría y logs

- Journald persistente.
- Rotación de logs (`logrotate`) para evitar llenar disco.
- Alertas por eventos de seguridad (fail2ban, reinicios anómalos, cambios de configuración).

---

## 17. Checklist de validación post-deploy

- [ ] DNS resuelve correctamente al VPS.
- [ ] UFW activo con reglas esperadas.
- [ ] SSH sin password y root login deshabilitado.
- [ ] Servicios systemd `ultra-*` en estado `active`.
- [ ] Contenedores `letta`, `prometheus`, `grafana` en estado `Up`.
- [ ] NGINX responde en 80->443 y certificado válido.
- [ ] PWA accesible por HTTPS.
- [ ] Métricas visibles en Prometheus.
- [ ] Dashboards y alertas operativas en Grafana.
- [ ] Backup automático ejecuta sin errores.
- [ ] Procedimiento de rollback probado al menos una vez.
- [ ] Hardening mínimo aplicado (fail2ban, unattended upgrades, permisos de secretos).

---

## 18. Operación continua

Frecuencias recomendadas:

- Diario:
  - revisión de alertas críticas.
  - verificación de backups.
- Semanal:
  - revisión de uso de disco/memoria.
  - inspección de logs de errores repetitivos.
- Mensual:
  - rotación de credenciales sensibles.
  - pruebas de restauración desde backup.
  - actualización controlada de dependencias e imágenes.
- Trimestral:
  - simulacro de incidente + rollback.
  - revisión integral de seguridad y puertos expuestos.

---

## 19. Troubleshooting rápido

### 19.1 NGINX no levanta

```bash
sudo nginx -t
journalctl -u nginx -n 200 --no-pager
```

Causas típicas: sintaxis inválida, puerto ocupado, rutas de certificado incorrectas.

### 19.2 Certbot falla emisión/renovación

- verificar DNS (`dig ultra.midominio.com`)
- comprobar puerto 80 accesible
- revisar logs:
  ```bash
  sudo journalctl -u certbot -n 200 --no-pager
  ```

### 19.3 Servicios systemd reiniciando en bucle

```bash
systemctl status ultra-xxx.service
journalctl -u ultra-xxx.service -f
```

Causas típicas: variables faltantes en `.env`, ruta de venv incorrecta, dependencia externa caída.

### 19.4 Grafana/Prometheus sin datos

- validar red Docker
- revisar `prometheus.yml`
- comprobar targets en estado `UP`
- inspeccionar logs de contenedores

---

## 20. Conclusión

Con este procedimiento, Ultra Stack queda desplegado en un VPS de producción con controles esenciales de seguridad, observabilidad y recuperación operativa.  
El enfoque recomendado es iterativo: primero estabilidad y visibilidad, luego optimización de rendimiento.  
En producción, la confiabilidad depende más de procesos operativos (backups, alertas, rollback probado, hardening continuo) que del despliegue inicial.