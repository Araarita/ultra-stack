"""Proposal System API - Servidor standalone."""
import sys
sys.path.insert(0, '/opt/ultra')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interfaces.command_center.backend.proposals_routes import router as proposals_router

app = FastAPI(
    title="Ultra Proposal System API",
    version="1.0.0",
    description="API for Ultra's proactive proposal system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proposals_router)

@app.get("/")
async def root():
    return {
        "service": "Ultra Proposal System API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "proposals": "/api/proposals/",
            "stats": "/api/proposals/stats/summary",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
