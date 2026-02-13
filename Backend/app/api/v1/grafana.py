from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging

from app.core.database import get_session
from app.models.domain import CSVFileMetadata
from app.services.data_processing import create_unified_view

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard-url/{filename}")
def get_grafana_dashboard_url(
    filename: str, 
    db: Session = Depends(get_session)
):
    """Generate Grafana dashboard URL for a specific CSV file."""
    metadata = db.exec(
        select(CSVFileMetadata).where(CSVFileMetadata.filename == filename)
    ).first()
    
    if not metadata:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
    
    # Generate Grafana dashboard URL with table name as variable
    grafana_base_url = "http://localhost:3000"
    dashboard_path = "d/anomaly-detection-enhanced/batchwise-anomaly-detection"
    grafana_url = f"{grafana_base_url}/{dashboard_path}?var-table_name={metadata.table_name}&orgId=1"
    
    return {
        "grafana_url": grafana_url,
        "grafana_embed_url": f"{grafana_url}&kiosk=tv",
        "table_name": metadata.table_name,
        "filename": filename,
        "record_count": metadata.record_count
    }

@router.get("/all-tables")
def get_all_grafana_tables(db: Session = Depends(get_session)):
    """Get list of all CSV tables for Grafana variable selection."""
    metadata_list = db.exec(select(CSVFileMetadata).order_by(CSVFileMetadata.upload_timestamp.desc())).all()
    
    return {
        "tables": [
            {
                "table_name": m.table_name,
                "filename": m.filename,
                "record_count": m.record_count,
                "upload_timestamp": m.upload_timestamp
            }
            for m in metadata_list
        ],
        "total_count": len(metadata_list)
    }

@router.get("/refresh-unified-view")
def refresh_unified_view_endpoint(db: Session = Depends(get_session)):
    """Manually refresh the unified view combining all CSV tables."""
    try:
        create_unified_view(db)
        return {
            "message": "Unified view refreshed successfully",
            "view_name": "csv_data_unified_view",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error refreshing unified view: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing view: {str(e)}")
