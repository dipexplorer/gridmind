from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate

def get_user(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    # In a real app, hash the password here before saving
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = User(email=user.email, full_name=user.full_name, role=user.role, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()
