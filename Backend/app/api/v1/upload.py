from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select, text
from typing import List, Optional
import json

from app.core.database import get_session, engine
from app.models.schemas import CSVUploadResponse
from app.models.domain import CSVFileMetadata
from app.services.data_processing import process_csv_upload
from app.services.anomaly import get_anomaly_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def run_anomaly_detection(table_name: str):
    """Background task wrapper for anomaly detection."""
    try:
        logger.info(f"Starting background anomaly detection for {table_name}")
        # Create a new session for the background task
        with Session(engine) as db:
            service = get_anomaly_service()
            detect_result = service.detect_and_update(table_name, db)
            logger.info(f"Anomaly detection result: {detect_result}")
    except Exception as e:
        logger.error(f"Background anomaly detection failed: {e}")

@router.post("/upload-csv/", response_model=CSVUploadResponse)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_session)
):
    """Upload a CSV file and store in database."""
    logger.info(f"Upload request received for file: {file.filename}")
    
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Process upload using service
        metadata, records_created = await process_csv_upload(file, db)
        
        # Trigger Anomaly Detection in Background
        # Do not pass 'db' session as it closes after request.
        background_tasks.add_task(run_anomaly_detection, metadata.table_name)
        
        return CSVUploadResponse(
            message="CSV file uploaded successfully. Anomaly detection running in background.",
            records_count=records_created,
            filename=file.filename,
            table_name=metadata.table_name,
            upload_timestamp=metadata.upload_timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing CSV file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.get("/csv-data/")
def get_csv_data(
    filename: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Get CSV data from database."""
    try:
        query = select(CSVFileMetadata)
        if filename:
            query = query.where(CSVFileMetadata.filename == filename)
        
        files_metadata = db.exec(query).all()
        
        result = []
        for metadata in files_metadata:
            try:
                data_query = f"SELECT * FROM {metadata.table_name} ORDER BY id"
                data_rows = db.exec(text(data_query)).fetchall()
                
                columns = data_rows[0]._fields if data_rows else []
                table_data = []
                for row in data_rows:
                    row_dict = dict(zip(columns, row))
                    table_data.append(row_dict)
                
                result.append({
                    "filename": metadata.filename,
                    "table_name": metadata.table_name,
                    "upload_timestamp": metadata.upload_timestamp,
                    "record_count": metadata.record_count,
                    "columns_info": json.loads(metadata.columns_info) if metadata.columns_info else {},
                    "data": table_data
                })
                
            except Exception as e:
                logger.error(f"Error retrieving data for {metadata.filename}: {str(e)}")
                result.append({
                    "filename": metadata.filename,
                    "table_name": metadata.table_name,
                    "error": f"Could not retrieve data: {str(e)}"
                })
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")

@router.delete("/csv-data/{filename}")
def delete_csv_data(
    filename: str, 
    db: Session = Depends(get_session)
):
    """Delete CSV data and table."""
    try:
        metadata = db.exec(
            select(CSVFileMetadata).where(CSVFileMetadata.filename == filename)
        ).first()
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        
        # Drop table with CASCADE to handle view dependency
        drop_table_sql = f"DROP TABLE IF EXISTS {metadata.table_name} CASCADE"
        db.exec(text(drop_table_sql))
        
        deleted_count = metadata.record_count
        db.delete(metadata)
        db.commit()
        
        # Refresh unified view
        from app.services.data_processing import create_unified_view
        create_unified_view(db)
        
        logger.info(f"Deleted table {metadata.table_name} and metadata for file {filename}")
        return {"message": f"Deleted {deleted_count} records and table for file {filename}"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting data for {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting data: {str(e)}")
