import uuid
from passlib.context import CryptContext
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from . import models
from .database import get_db

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_token():
    return str(uuid.uuid4())


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth scheme")
    token = authorization.split(" ", 1)[1]
    user = db.query(models.User).filter(models.User.token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_perm(perm: str):
    def checker(user: models.User = Depends(get_current_user)):
        if user.perms == "all":
            return user
        perms = [p.strip() for p in (user.perms or "").split(",") if p.strip()]
        if perm not in perms:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
