from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select, text
from app.core.database import get_session
from app.models.user_credentials import UserCredential, LoginTime
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    username: str
    message: str

class LoginRecord(BaseModel):
    """Login record model."""
    username: str
    login_time: datetime
    logout_time: datetime = None
    session_duration: int = None
    ip_address: str = None
    user_agent: str = None
    login_status: str = "active"

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), 
                                session: Session = Depends(get_session)):
    """Login with plain text password verification."""
    try:
        # Check user credentials in new table
        statement = select(UserCredential).where(UserCredential.username == form_data.username)
        user = session.exec(statement).first()
        
        # Plain text password comparison (as requested)
        if not user or user.password != form_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Record login time
        login_record = LoginTime(
            username=user.username,
            login_time=datetime.utcnow(),
            login_status="active"
        )
        session.add(login_record)
        session.commit()
        
        # Generate token
        from datetime import timedelta
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )

class LoginRequest(BaseModel):
    """JSON-based login request model."""
    username: str
    password: str

class LoginResponseJSON(BaseModel):
    """JSON login response model."""
    success: bool
    username: str
    role: str
    access_token: str = None
    message: str

@router.post("/login", response_model=LoginResponseJSON)
async def login_with_json(login_data: LoginRequest, session: Session = Depends(get_session)):
    """JSON-based login endpoint for frontend."""
    try:
        # Check user credentials - support both username and email
        statement = select(UserCredential).where(
            (UserCredential.username == login_data.username) | 
            (UserCredential.email == login_data.username)
        )
        user = session.exec(statement).first()
        
        # Plain text password comparison
        if not user or user.password != login_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Record login time
        login_record = LoginTime(
            username=user.username,
            login_time=datetime.utcnow(),
            login_status="active"
        )
        session.add(login_record)
        session.commit()
        
        # Generate token
        from datetime import timedelta
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        # Determine user role
        roles = {
            'admin': 'Administrator',
            'manager': 'Manager',
            'supervisor': 'Supervisor',
            'user': 'User',
            'pharma': 'Pharma Staff'
        }
        user_role = roles.get(user.username, 'User')
        
        return {
            "success": True,
            "username": user.username,
            "role": user_role,
            "access_token": access_token,
            "message": "Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/logout")
async def logout_user(username: str, session: Session = Depends(get_session)):
    """Record user logout time."""
    try:
        # Find active login record
        statement = select(LoginTime).where(
            LoginTime.username == username,
            LoginTime.login_status == "active"
        ).order_by(LoginTime.login_time.desc())
        
        active_login = session.exec(statement).first()
        
        if active_login:
            # Calculate session duration
            logout_time = datetime.utcnow()
            session_duration = int((logout_time - active_login.login_time).total_seconds())
            
            # Update login record
            active_login.logout_time = logout_time
            active_login.session_duration = session_duration
            active_login.login_status = "logged_out"
            
            session.commit()
            
            return {
                "message": "Logout recorded successfully",
                "session_duration": session_duration,
                "logout_time": logout_time
            }
        else:
            return {"message": "No active login session found"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout error: {str(e)}"
        )

class RegisterRequest(BaseModel):
    """JSON-based registration request."""
    username: str
    email: str
    password: str

class RegisterResponse(BaseModel):
    """Registration response model."""
    access_token: str
    username: str
    message: str

@router.post("/register", response_model=RegisterResponse)
async def register_user_json(register_data: RegisterRequest, session: Session = Depends(get_session)):
    """JSON-based user registration endpoint."""
    try:
        # Check if username exists
        statement = select(UserCredential).where(UserCredential.username == register_data.username)
        existing_user = session.exec(statement).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email exists
        if register_data.email:
            email_statement = select(UserCredential).where(UserCredential.email == register_data.email)
            existing_email = session.exec(email_statement).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create new user
        user = UserCredential(
            username=register_data.username,
            password=register_data.password,  # Plain text
            email=register_data.email or None
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Generate token for immediate login
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "username": user.username,
            "message": "Registration successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )

class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: str

class ForgotPasswordResponse(BaseModel):
    """Forgot password response."""
    message: str
    reset_token: str = None

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(forgot_data: ForgotPasswordRequest, session: Session = Depends(get_session)):
    """Send password reset link to user's email."""
    try:
        # Find user by email
        statement = select(UserCredential).where(UserCredential.email == forgot_data.email)
        user = session.exec(statement).first()
        
        if not user:
            # For security, don't reveal if email exists or not
            return {
                "message": "If an account with that email exists, a password reset link has been sent.",
                "reset_token": None
            }
        
        # Generate reset token (valid for 1 hour)
        from datetime import timedelta
        import secrets
        reset_token = secrets.token_urlsafe(32)
        reset_token_jwt = create_access_token(
            data={"sub": user.username, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # In a real application, you would:
        # 1. Store the reset token in database
        # 2. Send an email with the reset link
        # 3. The link would be: https://yourdomain.com/reset-password?token={reset_token_jwt}
        
        # For development/demo purposes, we return the token
        return {
            "message": "Password reset instructions sent to your email. For demo: use the reset_token below.",
            "reset_token": reset_token_jwt
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset error: {str(e)}"
        )

class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(reset_data: ResetPasswordRequest, session: Session = Depends(get_session)):
    """Reset user password with valid token."""
    try:
        # Verify token and extract username
        from app.core.security import verify_access_token
        payload = verify_access_token(reset_data.token)
        
        if not payload or payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        username = payload.get("sub")
        
        # Find user
        statement = select(UserCredential).where(UserCredential.username == username)
        user = session.exec(statement).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.password = reset_data.new_password  # Plain text
        session.commit()
        
        return {
            "message": "Password reset successful. You can now login with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset error: {str(e)}"
        )

@router.get("/login-history/{username}")
async def get_login_history(username: str, session: Session = Depends(get_session)):
    """Get login history for a user."""
    try:
        statement = select(LoginTime).where(LoginTime.username == username).order_by(LoginTime.login_time.desc())
        logins = session.exec(statement).all()
        
        history = []
        for login in logins:
            history.append({
                "login_time": login.login_time,
                "logout_time": login.logout_time,
                "session_duration": login.session_duration,
                "login_status": login.login_status,
                "ip_address": login.ip_address,
                "user_agent": login.user_agent
            })
        
        return {
            "username": username,
            "total_logins": len(history),
            "login_history": history
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving login history: {str(e)}"
        )
