from sqlalchemy.orm import Session
from database.database import ChatRoom, User

# Функция для получения пользователя по email
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
