"""
Invoice OCR System - FastAPI Main Application Server Entrypoint
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import config
from app.api.upload import router as upload_router
from app.api.invoice import router as health_router

app = FastAPI(
    title="Invoice OCR Processing System",
    description="Production-grade, high-accuracy Invoice OCR processing system with GSTIN priority and multi-engine retry fallback.",
    version="1.0.0"
)

# Enable CORS for local web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(upload_router)
app.include_router(health_router)

# Mount outputs directory for rendered invoice previews
if config.OUTPUT_DIR.exists():
    app.mount("/outputs", StaticFiles(directory=str(config.OUTPUT_DIR)), name="outputs")

# Mount frontend web application static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
