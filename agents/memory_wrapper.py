"""
Memory Wrapper - Agrega memoria persistente al Smart Agent

Uso:
  from agents.memory_wrapper import chat_with_memory
  
  response = chat_with_memory('hola ultra', user_id='erik')

Este wrapper:
1. Recupera historial de Letta
2. Construye contexto con mensajes previos
3. Llama al smart_agent con contexto
4. Guarda nuevo intercambio en Letta
"""
import os
import sys
from typing import Optional

sys.path.insert(0, '/opt/ultra')

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv('/opt/ultra/.env')

from shared.memory.letta_client import get_memory, save_to_memory


def chat_with_memory(user_message: str, user_id: str = 'erik') -> str:
    """Chat con memoria persistente via Letta.
    
    Args:
        user_message: Mensaje del usuario
        user_id: Identificador del usuario (default erik)
    
    Returns:
        Respuesta del asistente
    """
    # 1. Recuperar historial
    history = get_memory(user_id, limit=10)
    
    # 2. Construir mensajes
    messages = [
        {
            'role': 'system',
            'content': '''Eres Ultra, asistente IA con memoria persistente. 
Tienes contexto de conversaciones previas con el usuario. 
Mantienes continuidad y recuerdas preferencias, nombres, y contexto.
Responde de forma directa y util.'''
        }
    ]
    
    # Agregar historial previo
    for msg in history:
        messages.append({
            'role': msg.get('role', 'user'),
            'content': msg.get('content', '')
        })
    
    # Agregar mensaje actual
    messages.append({'role': 'user', 'content': user_message})
    
    # 3. Llamar al LLM (usar Claude Opus 4.7 via BlackBox)
    client = OpenAI(
        api_key=os.getenv('BLACKBOX_API_KEY'),
        base_url='https://api.blackbox.ai/v1'
    )
    
    try:
        response = client.chat.completions.create(
            model='blackboxai/anthropic/claude-opus-4.7',
            messages=messages,
            max_tokens=2000
        )
        
        reply = response.choices[0].message.content
    except Exception as e:
        return f'[Error LLM: {e}]'
    
    # 4. Guardar en memoria
    save_to_memory(user_id, 'user', user_message)
    save_to_memory(user_id, 'assistant', reply)
    
    return reply


if __name__ == '__main__':
    # Test rapido
    import sys
    if len(sys.argv) > 1:
        msg = sys.argv[1]
        user = sys.argv[2] if len(sys.argv) > 2 else 'erik'
        print(chat_with_memory(msg, user))
    else:
        print('Uso: python3 -m agents.memory_wrapper "mensaje"')
