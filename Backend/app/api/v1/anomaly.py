from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Dict, Any
import logging
import json
from pathlib import Path

from app.core.database import get_session
from app.services.anomaly import get_anomaly_service
from app.models.schemas import AnomalyDetectionResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/detect", response_model=AnomalyDetectionResponse)
def detect_anomalies(
    table_name: str,
    db: Session = Depends(get_session)
):
    """
    Run anomaly detection on a CSV table.
    """
    try:
        logger.info(f"Anomaly detection requested for table: {table_name}")
        
        service = get_anomaly_service()
        results = service.detect_anomalies(table_name, db)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")

@router.get("/results/{table_name}")
def get_anomaly_results(
    table_name: str,
    db: Session = Depends(get_session)
):
    """Get stored anomaly results."""
    try:
        service = get_anomaly_service()
        return service.get_anomaly_results(table_name, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-metrics")
def get_model_metrics():
    """
    Get current model performance metrics.
    Useful for dashboard visualizations.
    """
    try:
        # Load metrics from AI directory
        base_dir = Path(__file__).parent.parent.parent.parent
        metrics_path = base_dir / 'AI' / 'model_metrics.json'
        
        if not metrics_path.exists():
            raise HTTPException(status_code=404, detail="Model metrics not found")
        
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        return metrics
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model metrics not found")
    except Exception as e:
        logger.error(f"Error fetching model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/feature-importance/{batch_id}")
def get_feature_importance(
    batch_id: str,
    db: Session = Depends(get_session)
):
    """
    Get feature importance/contribution for a specific batch.
    Shows which features flagged this batch as anomalous.
    
    NOTE: Full implementation requires storing feature contributions
    during anomaly detection. Currently returns placeholder.
    """
    try:
        # Placeholder response - full implementation would query
        # feature contributions stored during detection
        return {
            "batch_id": batch_id,
            "top_features": [
                {"feature": "Energy_kWh", "contribution": 0.45, "value": 2100, "percentile": 95},
                {"feature": "Yield_loss_pct", "contribution": 0.30, "value": 12.5, "percentile": 88},
                {"feature": "Energy_per_kg", "contribution": 0.25, "value": 16.2, "percentile": 82}
            ],
            "note": "Full feature importance requires model updates (Phase 3)"
        }
    
    except Exception as e:
        logger.error(f"Error getting feature importance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-check")
def run_health_check(
    table_name: str = None
):
    """
    Trigger manual model health check.
    Returns alerts and performance status.
    """
    try:
        from app.ml.monitoring import ModelMonitor
        
        monitor = ModelMonitor()
        checks = monitor.daily_health_check(table_name=table_name)
        report = monitor.generate_report(checks)
        
        return {
            "status": "complete",
            "alert_count": checks.get('alert_count', 0),
            "checks": checks,
            "report": report
        }
    
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Monitoring module not available. Install dependencies: pip install apscheduler"
        )
    except Exception as e:
        logger.error(f"Error running health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
