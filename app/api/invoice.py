"""
Invoice OCR System - Health, Engine Management & Orchestrator API Endpoints
Provides APIs for viewing and toggling OCR engines ON/OFF dynamically,
and adjusting pipeline quality thresholds.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import config
from app.ocr.router import OCRRouter

router = APIRouter(prefix="/api", tags=["System Status & Orchestrator"])

class EngineToggleRequest(BaseModel):
    engine_name: str
    enabled: bool

class SettingsUpdateRequest(BaseModel):
    accept_threshold: Optional[float] = Field(default=None, ge=10.0, le=100.0)
    max_retries: Optional[int] = Field(default=None, ge=1, le=5)

@router.get("/health")
def health_check():
    """Returns backend system status and list of registered OCR engines with operational status."""
    ocr_router = OCRRouter()
    engines_status = {}

    for name, engine in ocr_router.engines.items():
        engine_cfg = config.OCR_ENGINE_CONFIG.get(name, {})
        engines_status[name] = {
            "name": name,
            "enabled": engine_cfg.get("enabled", True),
            "available": engine.available,
            "init_error": engine.init_error,
            "priority": engine_cfg.get("priority", 1),
            "strengths": engine_cfg.get("strengths", []),
            "weight_digital": engine_cfg.get("weight_digital", 0.8),
            "weight_scanned": engine_cfg.get("weight_scanned", 0.8)
        }

    return {
        "status": "healthy",
        "accept_threshold": config.OCR_ACCEPT_THRESHOLD,
        "max_retries": config.MAX_OCR_RETRIES,
        "ocr_engines": engines_status
    }

@router.post("/engines/toggle")
def toggle_engine(req: EngineToggleRequest):
    """Toggles a specific OCR Engine ON or OFF dynamically."""
    name = req.engine_name
    if name not in config.OCR_ENGINE_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{name}' is not registered in OCR router configuration."
        )

    config.OCR_ENGINE_CONFIG[name]["enabled"] = req.enabled

    return {
        "success": True,
        "engine_name": name,
        "enabled": req.enabled,
        "message": f"Engine '{name}' toggled {'ON' if req.enabled else 'OFF'} successfully."
    }

@router.post("/settings/update")
def update_settings(req: SettingsUpdateRequest):
    """Updates OCR Accept Threshold and Max Retries settings dynamically."""
    if req.accept_threshold is not None:
        config.OCR_ACCEPT_THRESHOLD = req.accept_threshold

    if req.max_retries is not None:
        config.MAX_OCR_RETRIES = req.max_retries

    return {
        "success": True,
        "accept_threshold": config.OCR_ACCEPT_THRESHOLD,
        "max_retries": config.MAX_OCR_RETRIES,
        "message": "Orchestrator thresholds updated successfully."
    }

class SimulationRequest(BaseModel):
    document_type: str = "Scanned PDF"
    has_tables: bool = False
    is_noisy: bool = False
    is_low_contrast: bool = False
    skew_angle: float = 0.0

@router.post("/orchestrator/simulate")
def simulate_orchestrator_routing(req: SimulationRequest):
    """Simulates dynamic engine ranking and scoring based on document characteristics."""
    ocr_router = OCRRouter()
    doc_inspection = {"document_type": req.document_type}
    doc_analysis = {
        "has_tables": req.has_tables,
        "is_noisy": req.is_noisy,
        "is_low_contrast": req.is_low_contrast,
        "skew_angle": req.skew_angle
    }

    ranked = ocr_router.get_ranked_engines(doc_inspection, doc_analysis)
    
    ranking_results = []
    for engine, score, rationale in ranked:
        engine_cfg = config.OCR_ENGINE_CONFIG.get(engine.name, {})
        ranking_results.append({
            "name": engine.name,
            "score": round(score, 2),
            "rationale": rationale,
            "available": engine.available,
            "enabled": engine_cfg.get("enabled", True),
            "priority": engine_cfg.get("priority", 99)
        })

    return {
        "document_type": req.document_type,
        "characteristics": {
            "has_tables": req.has_tables,
            "is_noisy": req.is_noisy,
            "is_low_contrast": req.is_low_contrast,
            "skew_angle": req.skew_angle
        },
        "ranked_engines": ranking_results
    }

