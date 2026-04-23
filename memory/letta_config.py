"""
Configuración de Letta usando PostgreSQL compartido con Nexus.
Memoria jerárquica: core_memory + archival_memory + recall_memory.
"""
import os
from dotenv import load_dotenv

load_dotenv('/opt/ultra/.env')

# Config para Letta
LETTA_CONFIG = {
    "database_url": f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?sslmode=require",
    "openai_api_key": os.getenv("OPENROUTER_API_KEY"),
    "openai_api_base": "https://openrouter.ai/api/v1",
    "default_model": "anthropic/claude-sonnet-4.6",
    "default_embedding_model": "openai/text-embedding-3-small",
}

print("✅ Letta config cargado")
print(f"   DB: {os.getenv('DB_HOST')}")
print(f"   Model: {LETTA_CONFIG['default_model']}")
