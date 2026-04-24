# Getting Started

Guia de instalacion del Ultra Stack.

## Requisitos

Ubuntu 22.04 o Debian 12, Python 3.10+, Node.js 20+, Docker, PostgreSQL, 4GB RAM minimo.

## Pasos

1. Clonar repo desde github.com/Araarita/ultra-stack
2. Crear venv Python e instalar requirements.txt
3. Instalar dependencias frontend con pnpm
4. Configurar .env con keys necesarias
5. Copiar archivos systemd y habilitar servicios
6. Levantar Letta en Docker
7. Probar con comando ultra hola

## Variables .env necesarias

- TELEGRAM_ULTRA_BOT_TOKEN
- OPENROUTER_API_KEY
- BLACKBOX_API_KEY
- PERPLEXITY_API_KEY
- DATABASE_URL

## Verificar instalacion

Comprobar systemctl status de ultra-bot, ultra-cc, ultra-cc-api. Verificar que Letta responde en puerto 8283.

## Troubleshooting inicial

Si ultra-bot falla revisar el TELEGRAM_ULTRA_BOT_TOKEN. Si LLMs fallan revisar OPENROUTER_API_KEY. Ver docs de troubleshooting para mas detalle.
