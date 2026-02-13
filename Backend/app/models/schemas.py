from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============================================================================
# Auth Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Request model for user registration."""
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    """Request model for user login."""
    username: str
    password: str

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: Optional[str] = None
    user_id: Optional[int] = None

# ============================================================================
# CSV Schemas
# ============================================================================

class CSVUploadResponse(BaseModel):
    """Response after successful CSV upload."""
    message: str
    records_count: int
    filename: str
    table_name: str
    upload_timestamp: datetime

class UploadListItem(BaseModel):
    """Single upload item in list response."""
    upload_id: str
    filename: str
    record_count: int
    upload_timestamp: str
    columns_schema: Dict[str, str]

class UploadListResponse(BaseModel):
    """Response for listing uploads."""
    total_uploads: int
    uploads: list[UploadListItem]

class CSVDataResponse(BaseModel):
    """Response for CSV data query."""
    upload_id: str
    filename: str
    total_rows: int
    data: list[Dict[str, Any]]

# ============================================================================
# Anomaly Schemas
# ============================================================================

class AnomalyResultItem(BaseModel):
    id: int
    timestamp: str
    batch_id: Optional[str]
    anomaly_score: float
    is_anomaly: bool
    severity: str
    energy_kwh: float
    energy_per_kg: float
    yield_loss_pct: float
    co2_per_kg: float
    room_temp_c: float

class AnomalyResultsResponse(BaseModel):
    """Response model for anomaly results."""
    table_name: str
    total_anomalies: int
    results: List[AnomalyResultItem]

class AnomalyDetectionResponse(BaseModel):
    """Response model for detection triggers."""
    message: str
    table_name: str
    total_records: int
    anomalies_detected: int
    severity_breakdown: Dict[str, int]
    timestamp: str

class ModelMetricsResponse(BaseModel):
    """Response model for model metrics."""
    version: str
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    roc_auc: Optional[float]
    training_samples: Optional[int]
    test_samples: Optional[int]
    timestamp: str
