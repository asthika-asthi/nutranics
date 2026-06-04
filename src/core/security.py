from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt

# Import settings lazily to avoid circular imports at module level
_pwd_context = None
_settings = None


def get_pwd_context():
    global _pwd_context
    if _pwd_context is None:
        _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return _pwd_context


def get_settings():
    global _settings
    if _settings is None:
        from config import settings as s
        _settings = s
    return _settings


def hash_password(password: str) -> str:
    return get_pwd_context().hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return get_pwd_context().verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    s = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=s.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, s.secret_key, algorithm=s.algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.secret_key, algorithms=[s.algorithm])
