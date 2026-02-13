from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, JSON

# ============================================================================
# User & Auth Models
# ============================================================================

class User(SQLModel, table=True):
    """User model for authentication."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=255)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# CSV Upload Models
# ============================================================================

class CSVFileMetadata(SQLModel, table=True):
    """Metadata for each uploaded CSV file."""
    __tablename__ = "csv_files_metadata"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    table_name: str = Field(index=True, unique=True)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    record_count: int = Field(default=0)
    columns_info: str = Field(default="{}") # JSON string of column types
    user_id: Optional[int] = Field(default=None, foreign_key="user_credentials.id")

class CSVUpload(SQLModel, table=True):
    """Metadata for each CSV upload (Legacy/Alternative table)."""
    __tablename__ = "csv_uploads"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: UUID = Field(default_factory=uuid4, unique=True, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user_credentials.id", index=True)
    filename: str = Field(max_length=500)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    record_count: int = Field(ge=0)
    columns_schema: Dict[str, Any] = Field(sa_column=Column(JSON))

class CSVDataRow(SQLModel, table=True):
    """Individual CSV data rows stored as JSONB."""
    __tablename__ = "csv_data"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: UUID = Field(foreign_key="csv_uploads.upload_id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user_credentials.id", index=True)
    row_number: int = Field(ge=1)
    data: Dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# Anomaly Detection Models
# ============================================================================

class AnomalyDetection(SQLModel, table=True):
    """Anomaly detection results for each batch."""
    __tablename__ = "anomaly_detections"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    batch_id: Optional[str] = Field(default=None, max_length=100, index=True)
    metric: Optional[str] = Field(default=None, max_length=50)
    value: Optional[float] = None
    anomaly_score: Optional[float] = None
    is_anomaly: bool = Field(default=False, index=True)
    severity: str = Field(max_length=10, index=True)  # GREEN, AMBER, RED
    table_name: str = Field(max_length=500, index=True)
    energy_kwh: Optional[float] = None
    energy_per_kg: Optional[float] = None
    yield_loss_pct: Optional[float] = None
    co2_per_kg: Optional[float] = None
    room_temp_c: Optional[float] = None

class AnomalyAlert(SQLModel, table=True):
    """Accessory table if needed for specific alerts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    # Define structure if used, currently placeholder based on imports in original code

class ModelPerformance(SQLModel, table=True):
    """Model performance metrics tracking."""
    __tablename__ = "model_performance"
    
    run_id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(max_length=50, index=True)
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    training_samples: Optional[int] = None
    test_samples: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
