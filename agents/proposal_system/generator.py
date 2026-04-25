"""Proposal Generator - Usa BlackBox AI para generar propuestas reales."""
import os
import json
import asyncio
import logging
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("/opt/ultra/.env")

from .models import Proposal, Category, Impact, RiskLevel
from .store import ProposalStore

logger = logging.getLogger(__name__)


class ProposalGenerator:
    """Genera propuestas proactivas usando BlackBox AI."""
    
    VALID_CATEGORIES = ["capability", "improvement", "maintenance", "insight", "security", "experience", "performance", "observability"]
    VALID_IMPACTS = ["critical", "high", "medium", "low"]
    VALID_RISKS = ["safe", "low", "medium", "high"]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BLACKBOX_API_KEY")
        if not self.api_key:
            raise ValueError("BLACKBOX_API_KEY is required")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.blackbox.ai/v1"
        )
        self.model = "blackboxai/anthropic/claude-opus-4.7"
        self.store = ProposalStore()
    
    def _build_prompt(self, count: int = 3) -> str:
        return f"""Genera exactamente {count} propuestas de mejora para Ultra Stack.

IMPORTANTE: Responde SOLO un JSON valido con esta estructura exacta:

{{
  "proposals": [
    {{
      "title": "titulo corto max 80 chars",
      "description": "descripcion clara del cambio",
      "benefit": "beneficio concreto",
      "category": "capability",
      "impact": "high",
      "effort": "medium",
      "risk_level": "safe",
      "action_type": "install",
      "action_code": "codigo Python para ejecutar",
      "estimated_time_seconds": 60
    }}
  ]
}}

REGLAS ESTRICTAS:
- category DEBE ser UNO de: capability, improvement, maintenance, insight, security, experience
- impact DEBE ser UNO de: critical, high, medium, low
- risk_level DEBE ser UNO de: safe, low, medium, high
- effort DEBE ser UNO de: low, medium, high

Solo responde el JSON, sin markdown, sin explicaciones."""
    
    def _extract_json(self, text: str) -> dict:
        """Extrae JSON de respuesta LLM (maneja markdown wrappers)."""
        text = text.strip()
        
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1])
            else:
                text = "\n".join(lines[1:])
        
        if text.startswith("json"):
            text = text[4:].strip()
        
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= 0:
            text = text[start:end+1]
        
        return json.loads(text)
    
    def _normalize_category(self, cat: str) -> str:
        """Normaliza category a uno valido."""
        cat_lower = cat.lower().strip()
        if cat_lower in self.VALID_CATEGORIES:
            return cat_lower
        
        # Mapeo de sinonimos
        synonyms = {
            "performance": "improvement",
            "observability": "insight",
            "logging": "insight",
            "monitoring": "insight",
            "feature": "capability",
            "bugfix": "maintenance",
            "refactor": "improvement",
        }
        
        return synonyms.get(cat_lower, "improvement")
    
    async def generate(self, count: int = 3, save: bool = True) -> List[Proposal]:
        """Genera propuestas y las guarda."""
        try:
            print(f"[Generator] Llamando a {self.model}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un asistente que genera propuestas en JSON valido."},
                    {"role": "user", "content": self._build_prompt(count)}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            
            text = response.choices[0].message.content
            print(f"[Generator] Respuesta recibida: {len(text)} chars")
            
            data = self._extract_json(text)
            raw_proposals = data.get("proposals", [])
            print(f"[Generator] Propuestas en JSON: {len(raw_proposals)}")
            
            proposals = []
            for idx, raw in enumerate(raw_proposals):
                try:
                    # Normalizar category
                    if "category" in raw:
                        raw["category"] = self._normalize_category(raw["category"])
                    
                    proposal = Proposal(**raw)
                    
                    if save:
                        self.store.save(proposal)
                    
                    proposals.append(proposal)
                    print(f"[Generator] Propuesta {idx+1} creada: {proposal.title[:50]}")
                
                except Exception as e:
                    print(f"[Generator] Error propuesta {idx+1}: {e}")
                    print(f"[Generator] Raw data: {raw}")
                    continue
            
            return proposals
        
        except Exception as e:
            print(f"[Generator] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return []
