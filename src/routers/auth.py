from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.deps import get_db, get_current_user
from core.security import hash_password, verify_password, create_access_token
from models import User, Practitioner

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    practitioner_id: str | None


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "practitioner"
    practitioner_name: str | None = None
    practitioner_email: str | None = None


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "practitioner_id": str(user.practitioner_id) if user.practitioner_id else None,
    })

    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role,
        practitioner_id=str(user.practitioner_id) if user.practitioner_id else None,
    )


@router.post("/register", response_model=LoginResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Owner only in V1 (admin UI to add staff)."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate role
    valid_roles = ("owner", "admin", "practitioner", "viewer")
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    practitioner_id = None

    # If creating a practitioner, also create the Practitioner record
    if data.role in ("practitioner", "admin"):
        if not data.practitioner_name:
            raise HTTPException(status_code=400, detail="practitioner_name required")
        import uuid
        from datetime import datetime
        practitioner = Practitioner(
            id=str(uuid.uuid4()),
            name=data.practitioner_name,
            email=data.practitioner_email or data.email,
            role=data.role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(practitioner)
        db.flush()
        practitioner_id = practitioner.id

    import uuid
    from datetime import datetime
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        practitioner_id=practitioner_id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "practitioner_id": str(practitioner_id) if practitioner_id else None,
    })

    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role,
        practitioner_id=str(practitioner_id) if practitioner_id else None,
    )


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return current_user
