from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core.database import create_db_and_tables
from app.api.v1 import upload, anomaly, grafana, users, new_auth
from app.models.user_credentials import UserCredential # Register new models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting application...")
    create_db_and_tables()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title="CSV Upload API",
    description="Enterprise-grade CSV upload system with PostgreSQL storage",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload.router, tags=["CSV Data"], prefix="")
app.include_router(anomaly.router, prefix="/api/anomaly", tags=["Anomaly Detection"])
app.include_router(grafana.router, prefix="/grafana", tags=["Grafana Integration"])
app.include_router(new_auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["User Management"])

@app.get("/")
def root():
    """API health check and information."""
    return {
        "message": "CSV Upload API - Enterprise Edition",
        "description": "Upload CSV files without authentication",
        "version": "2.0.0",
        "swaggger_docs": "/docs",
        "grafana": {
            "dashboard_url": os.getenv("GRAFANA_DASHBOARD_URL", "http://localhost:3001/d/anomaly-detection-dashboard"),
            "setup_guide": "See ANOMALY_DETECTION_SETUP.md for configuration"
        }
    }
