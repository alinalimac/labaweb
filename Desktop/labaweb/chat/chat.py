from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session
from typing import List, Dict
from database.database import get_db
from database.database import User
import crud

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# WebSocket эндпоинт для чатов
connected_clients: Dict[int, List[WebSocket]] = {}


# WebSocket эндпоинт
@app.websocket("/ws/{chat_room_id}")
async def websocket_endpoint(websocket: WebSocket, chat_room_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Аутентификация и получение email пользователя
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise credentials_exception
        user = crud.get_user_by_email(db, user_email)
        if not user:
            raise credentials_exception
    except InvalidTokenError:
        await websocket.close(code=1008)
        return

    # Подключение пользователя
    await websocket.accept()
    if chat_room_id not in connected_clients:
        connected_clients[chat_room_id] = []
    connected_clients[chat_room_id].append(websocket)

    # Уведомление о присоединении
    for client in connected_clients[chat_room_id]:
        if client != websocket:
            await client.send_text(f"{user_email} подключился к комнате.")

    try:
        while True:
            data = await websocket.receive_text()

            # Отправка сообщения всем пользователям комнаты
            for client in connected_clients[chat_room_id]:
                await client.send_text(f"{user_email}: {data}")

    except WebSocketDisconnect:
        # Удаление пользователя из подключений при отключении
        connected_clients[chat_room_id].remove(websocket)
        for client in connected_clients[chat_room_id]:
            await client.send_text(f"{user_email} отключился от комнаты.")
        if not connected_clients[chat_room_id]:
            del connected_clients[chat_room_id]