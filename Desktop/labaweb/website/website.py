from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, status, Form, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict
import crud
from database.database import User, Token, ChatRoom, get_db, Base, engine
from auth import create_access_token, get_current_user
from schemas import UserCreate, TokenResponse
import logging
import jwt
from jwt import InvalidTokenError


# Инициализация FastAPI
app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 схема для получения токенов
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_email = payload.get("sub")
            if user_email and db.query(User).filter(User.email == user_email).first():
                return RedirectResponse(url="/chat_rooms")
        except jwt.PyJWTError:
            pass  # Игнорируем ошибку и продолжаем
    return templates.TemplateResponse("home.html", {"request": request, "user": None})

# Страница регистрации
@app.get("/register")
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Регистрация нового пользователя
@app.post("/register")
async def register(request: Request, user: UserCreate = Depends(UserCreate.as_form), db: Session = Depends(get_db)):
    rows_user = db.query(User).count()
    if rows_user != 0:
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            return templates.TemplateResponse("register.html", {"request": request, "error": "User already registered"})
    new_user = User(id = rows_user + 1, email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": new_user.email})
    rows_token = db.query(Token).count()
    new_token  = Token(id = rows_token + 1, token = access_token, user_id = rows_user + 1)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    response = RedirectResponse(url="/chat_rooms", status_code=303)
    response.set_cookie(key="access_token", value=access_token)  # Сохраняем токен в cookies
    return response

# Страница входа
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Вход в систему
@app.post("/login")
async def login(data: UserCreate = Depends(UserCreate.as_form), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not (data.password == user.password):
        raise HTTPException(
            status_code=422,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        return templates.TemplateResponse("register.html", {"request": request, "error": "Incorrect email or password"})
    
    # Generate JWT token for authentication
    access_token = create_access_token(data={"sub": user.email})
    rows_token = db.query(Token).count()
    new_token  = Token(id = rows_token + 1, token = access_token, user_id = user.id)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    response = RedirectResponse(url="/chat_rooms", status_code=303)
    response.set_cookie(key="access_token", value=access_token)  # Сохраняем токен в cookies
    return response

@app.get("/chat_rooms")
async def chat_rooms(request: Request, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    if not user:
        response = RedirectResponse(url="/chat_rooms", status_code=303)
        return response 
    
    # Получаем все комнаты пользователя из базы данных
    rooms = crud.get_user_chat_rooms(db, user.id)
    
    return templates.TemplateResponse("chat_rooms.html", {"request": request, "rooms": rooms, "user": user})

@app.post("/create_chat_room")
async def create_chat_room_action(room_name: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return {"error": "You need to log in first"}
    
    # Создаем новую комнату
    new_room = crud.create_chat_room(db, room_name, user.id)
    
    # После создания комнаты перенаправляем на страницу с чатами
    return RedirectResponse(url="/chat_rooms", status_code=303)

@app.get("/search_chat_rooms")
async def search_chat_rooms_action(request: Request, query: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user:
        return {"error": "You need to log in first"}

    # Ищем комнаты по имени
    search_results = crud.search_chat_rooms(db, query)
    rooms = crud.get_user_chat_rooms(db, user.id)

    return templates.TemplateResponse("chat_rooms.html", {"request": request, "rooms": rooms, "search_results": search_results, "user": user})

@app.post("/delete_chat_room/{chat_room_id}")
async def delete_chat_room_endpoint(chat_room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Получаем комнату и проверяем, является ли пользователь владельцем комнаты
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id, ChatRoom.user_id == user.id).first()
    
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found or you are not the owner of this room"
        )
    
    # Используем функцию удаления
    deleted_room = crud.delete_chat_room(db, chat_room_id)
    
    if not deleted_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete chat room"
        )
    
    return RedirectResponse(url="/chat_rooms", status_code=303)

# Страница чата
@app.get("/chat/{chat_room_id}")
async def get_chat(request: Request, chat_room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room_name = crud.get_room_by_id(db, chat_room_id)
    return templates.TemplateResponse("chat.html", {"request": request, "chat_room_id": chat_room_id, "room_name": room_name, "user": user})
