from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from schemas.user import UserCreate, UserResponse
from crud import crud_user

router = APIRouter()

@router.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Naya Engineer (User) system mein add karne ke liye.
    """
    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db=db, user=user)

@router.get("/users/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Saare registered engineers ki list dekhne ke liye.
    """
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users
