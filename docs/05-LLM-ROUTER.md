# LLM Router - 7 Modos con Auto-Selector

## Los 7 Modos

### FREE
Modelo DeepSeek V3.2 tier gratuito. Costo 0 USD. Uso pruebas y desarrollo. Speed rapido.

### NORMAL (default)
Modelo DeepSeek V3.2. Costo 0.14 por millon de tokens. Uso conversacion general. Speed rapido.

### KIMI
Modelo Moonshot K2. Costo medio. Uso chino y contexto largo. Speed medio.

### BOOST
Modelo Claude Sonnet 4.6. Costo 3 USD por millon. Uso tareas complejas balanceadas. Speed medio.

### TURBO
Modelo Claude Opus 4.6. Costo 15 USD por millon. Uso razonamiento profundo. Speed lento. Requiere password.

### BLACKBOX
Modelo Claude Opus 4.7 via BlackBox AI. Costo incluido en suscripcion. Uso maxima inteligencia. Speed medio.

### CODE
Modelo GPT-5.3 Codex via BlackBox AI. Costo incluido. Uso generacion de codigo. Speed rapido.

## Auto-Mode Selector

Analiza el mensaje y clasifica. Simple va a NORMAL. Code va a CODE. Complex va a BLACKBOX. Web search va a NORMAL con tool. Visual va a BLACKBOX.

Algoritmo usa keywords, largo del mensaje y complejidad estimada.

Override manual con set_mode.

## Cambiar modos desde Telegram

Comandos disponibles: /mode FREE, /mode NORMAL, /mode BOOST password, /mode TURBO password, /mode BLACKBOX, /mode CODE.

## Proveedores

### OpenRouter
5 modos FREE NORMAL KIMI BOOST TURBO. API https://openrouter.ai. Key OPENROUTER_API_KEY.

### BlackBox AI
2 modos BLACKBOX y CODE. 83 modelos disponibles. API https://api.blackbox.ai. Key BLACKBOX_API_KEY.

## Modelos disponibles

83 modelos totales via BlackBox incluyendo Claude 4.7, GPT-5.3, Llama, Mistral, Gemini, Qwen. Ver funcion get_available_models en router.py.

## Fallback

Si un modo falla: 3 reintentos, luego fallback a FREE, luego notificacion al owner.

## Cost tracking

Audit log guarda modelo usado, tokens in/out y costo estimado. Ver en /opt/ultra/data/llm_usage.jsonl.
