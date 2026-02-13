from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class UserCredential(SQLModel, table=True):
    """User credentials table for storing login details."""
    __tablename__ = "user_credentials"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=255)
    password: str = Field(max_length=255)  # Plain text password as requested
    email: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class LoginTime(SQLModel, table=True):
    """Login tracking table for storing login/logout details."""
    __tablename__ = "login_time"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, max_length=255)
    login_time: datetime = Field(default_factory=datetime.utcnow)
    logout_time: Optional[datetime] = Field(default=None)
    session_duration: Optional[int] = Field(default=None)  # Duration in seconds
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    login_status: str = Field(default="active", max_length=20)  # active, logged_out, expired

