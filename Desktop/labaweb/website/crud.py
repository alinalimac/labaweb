from sqlalchemy.orm import Session
import schemas
from auth import get_password_hash
from database.database import ChatRoom, User


# Функция для создания нового пользователя
def create_user(db: Session, user: schemas.UserCreate):
    db_user = User(email=user.email, password=get_password_hash(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Функция для получения пользователя по email
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

# Функция для создания новой чат-комнаты
def create_chat_room(db: Session, room_name: str, user_id: int):
    new_room = ChatRoom(name=room_name, user_id=user_id)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

# Функция для получения всех чат-комнат
def get_chat_rooms(db: Session, skip: int = 0, limit: int = 100):
    return db.query(ChatRoom).offset(skip).limit(limit).all()

# Функция для удаления чат-комнаты
def delete_chat_room(db: Session, room_id: int):
    db_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if db_room:
        db.delete(db_room)
        db.commit()
    return db_room

def get_user_chat_rooms(db: Session, user_id: int):
    return db.query(ChatRoom).filter(ChatRoom.user_id == user_id).all()

def search_chat_rooms(db: Session, query: str):
    return db.query(ChatRoom).filter(ChatRoom.name.contains(query)).all()

def get_room_by_id(db: Session, chat_room_id: int):
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
    if chat_room:
        return chat_room.name
    else:
        return None
