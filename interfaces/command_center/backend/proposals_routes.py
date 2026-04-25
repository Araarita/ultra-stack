"""Proposal System API Routes."""
import sys
sys.path.insert(0, "/opt/ultra")

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from agents.proposal_system.models import Proposal, ProposalStatus, Category
from agents.proposal_system.store import ProposalStore
from agents.proposal_system.executor import ProposalExecutor
from agents.proposal_system.generator import ProposalGenerator


router = APIRouter(prefix="/api/proposals", tags=["proposals"])


def proposal_to_dict(p: Proposal) -> dict:
    """Convierte Proposal a dict JSON-serializable."""
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "benefit": p.benefit,
        "category": p.category.value if hasattr(p.category, "value") else str(p.category),
        "impact": p.impact.value if hasattr(p.impact, "value") else str(p.impact),
        "effort": p.effort,
        "risk_level": p.risk_level.value if hasattr(p.risk_level, "value") else str(p.risk_level),
        "action_type": p.action_type,
        "action_code": p.action_code,
        "estimated_time_seconds": p.estimated_time_seconds,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "created_at": p.created_at.isoformat() if isinstance(p.created_at, datetime) else str(p.created_at),
        "responded_at": p.responded_at.isoformat() if p.responded_at and isinstance(p.responded_at, datetime) else None,
        "executed_at": p.executed_at.isoformat() if p.executed_at and isinstance(p.executed_at, datetime) else None,
        "execution_log": p.execution_log or "",
    }


class ActionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class FeedbackRequest(BaseModel):
    rating: int
    comment: Optional[str] = None


@router.get("/")
async def list_proposals(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10
):
    """Lista propuestas filtradas."""
    try:
        store = ProposalStore()
        
        if status == "pending" or status is None:
            proposals = store.get_pending()
        else:
            proposals = store.get_all() if hasattr(store, "get_all") else store.get_pending()
        
        if category:
            proposals = [
                p for p in proposals 
                if (p.category.value if hasattr(p.category, "value") else str(p.category)) == category
            ]
        
        # Convertir a dicts serializables
        result = [proposal_to_dict(p) for p in proposals[:limit]]
        return result
    except Exception as e:
        raise HTTPException(500, f"Error listing: {str(e)}")


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Obtiene una propuesta por ID."""
    store = ProposalStore()
    p = store.get_by_id(proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found")
    return proposal_to_dict(p)


@router.post("/{proposal_id}/approve", response_model=ActionResponse)
async def approve_proposal(proposal_id: str, background: BackgroundTasks):
    """Aprueba y ejecuta una propuesta."""
    store = ProposalStore()
    executor = ProposalExecutor()
    
    p = store.get_by_id(proposal_id)
    if not p:
        raise HTTPException(404, "Not found")
    
    store.update_status(proposal_id, ProposalStatus.approved)
    background.add_task(executor.execute, proposal_id)
    
    return ActionResponse(
        success=True,
        message="Approved and executing in background",
        data={"proposal_id": proposal_id}
    )


@router.post("/{proposal_id}/reject", response_model=ActionResponse)
async def reject_proposal(proposal_id: str):
    """Rechaza una propuesta."""
    store = ProposalStore()
    
    if not store.update_status(proposal_id, ProposalStatus.rejected):
        raise HTTPException(404, "Not found")
    
    return ActionResponse(success=True, message="Rejected")


@router.post("/generate")
async def generate_now(count: int = 3):
    """Genera propuestas on-demand."""
    try:
        gen = ProposalGenerator()
        proposals = await gen.generate(count=count)
        return {
            "success": True,
            "count": len(proposals),
            "proposals": [proposal_to_dict(p) for p in proposals]
        }
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {str(e)}")


@router.get("/stats/summary")
async def get_stats():
    """Estadísticas generales."""
    store = ProposalStore()
    
    try:
        # Obtener todas (con fallback a pending si get_all no existe)
        if hasattr(store, "get_all"):
            all_proposals = store.get_all()
        else:
            all_proposals = store.get_pending()
        
        return {
            "total": len(all_proposals),
            "pending": len([p for p in all_proposals if (p.status.value if hasattr(p.status, "value") else str(p.status)) == "pending"]),
            "approved": len([p for p in all_proposals if (p.status.value if hasattr(p.status, "value") else str(p.status)) == "approved"]),
            "completed": len([p for p in all_proposals if (p.status.value if hasattr(p.status, "value") else str(p.status)) == "completed"]),
            "rejected": len([p for p in all_proposals if (p.status.value if hasattr(p.status, "value") else str(p.status)) == "rejected"]),
        }
    except Exception as e:
        return {"error": str(e), "total": 0}
