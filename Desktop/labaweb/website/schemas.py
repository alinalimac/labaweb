from pydantic import BaseModel
from fastapi import Form

# Схема для регистрации пользователя
class UserCreate(BaseModel):
    email: str
    password: str

    @classmethod
    def as_form(
        cls,
        email: str = Form(...),
        password: str = Form(...),
    ) -> "UserCreate":
        return cls(email=email, password=password)


# Схема для JWT токена
class Token(BaseModel):
    access_token: str
    token_type: str

# Схема для пользователя
class User(BaseModel):
    email: str


# Схема для создания чата
class ChatRoomCreate(BaseModel):
    name: str

# Схема для отображения чата
class ChatRoomBase(BaseModel):
    id: int
    name: str
    owner_id: int

# responses
class UserResponse(BaseModel):
    username: str
    secret: str

class RegisterResponse(BaseModel):
    message: str

class TokenResponse(BaseModel):
    token: str