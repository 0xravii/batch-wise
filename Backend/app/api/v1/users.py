from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.database import get_session
from app.models.user_credentials import UserCredential
from app.core.security import get_password_hash
from pydantic import BaseModel

router = APIRouter()

class UserResponse(BaseModel):
    """Safe user response model (without password hash)."""
    id: int
    username: str

class UserCreate(BaseModel):
    """User creation model."""
    username: str
    password: str
    email: str = ""

@router.get("/users", response_model=List[UserResponse])
async def list_users(session: Session = Depends(get_session)):
    """Get all users (safe - no passwords)."""
    try:
        statement = select(UserCredential)
        users = session.exec(statement).all()
        return [{"id": user.id, "username": user.username} for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/create")
async def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    """Create a new user."""
    try:
        # Check if user exists
        statement = select(UserCredential).where(UserCredential.username == user_data.username)
        existing_user = session.exec(statement).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail=f"User '{user_data.username}' already exists"
            )
        
        # Create new user
        # pass plain password as per UserCredential model
        user = UserCredential(username=user_data.username, password=user_data.password, email=user_data.email)
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {
            "message": f"User '{user_data.username}' created successfully",
            "user_id": user.id,
            "username": user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/table")
async def get_users_table(session: Session = Depends(get_session)):
    """Get users in table format for display."""
    try:
        statement = select(UserCredential).order_by(UserCredential.id)
        users = session.exec(statement).all()
        
        table_data = []
        for user in users:
            table_data.append({
                "id": user.id,
                "username": user.username,
                "password_status": "Plain Text (Dev Mode)", # Updated to reflect current status
                "created_date": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "Unknown"
            })
        
        return {
            "users": table_data,
            "total_count": len(table_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
