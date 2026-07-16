from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# Схемы для аутентификации (Токены)
# ==========================================

class Token(BaseModel):
    """Схема ответа при успешном логине"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Схема для извлечения данных из токена"""
    username: str | None = None

# --- СХЕМЫ ПОЛЬЗОВАТЕЛЯ (USER) ---

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, json_schema_extra={"example": "john_doe"})
    email: str = Field(..., json_schema_extra={"example": "john@example.com"})

class UserCreate(UserBase):
    # Пароль нужен только при создании пользователя: в ответ API он не попадает.
    password: str = Field(
        ...,
        min_length=8,
        json_schema_extra={"example": "secure_password_123"},
    )

class UserResponse(UserBase):
    id: int

    # Настройка для работы Pydantic напрямую с объектами SQLAlchemy (ORM)
    model_config = {"from_attributes": True}


# --- СХЕМЫ МУЗЫКАЛЬНОГО ТРЕКА (TRACK) ---

class TrackBase(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Blinding Lights"})
    artist: str = Field(..., json_schema_extra={"example": "The Weeknd"})
    genre: str = Field(..., json_schema_extra={"example": "Synthwave"})
    description: str = Field(
        ...,
        description="Текстовое описание настроения и атмосферы трека для построения эмбеддинга ИИ",
        json_schema_extra={"example": "Энергичный ностальгический синтипоп 80-х с яркими синтезаторами, быстрым ритмом и меланхоличным вокалом."}
    )

class TrackCreate(TrackBase):
    pass

class TrackResponse(TrackBase):
    id: int

    model_config = {"from_attributes": True}


# --- СХЕМЫ ПЛЕЙЛИСТА (PLAYLIST) ---

class PlaylistCreate(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Ночные поездки"})
    user_id: int
    track_ids: List[int] = Field(..., description="Список ID треков для включения в плейлист")

class PlaylistResponse(BaseModel):
    id: int
    title: str
    user_id: int
    ai_summary: Optional[str] = None
    tracks: List[TrackResponse] = []

    model_config = {"from_attributes": True}


# --- СХЕМЫ ДЛЯ ПОИСКА (SEARCH) ---

class SemanticSearchRequest(BaseModel):
    query: str = Field(
        ...,
        description="Текстовый запрос для семантического ИИ-поиска",
        json_schema_extra={"example": "Грустная акустическая гитара для дождливого вечера"}
    )
    limit: int = Field(default=5, ge=1, le=20)
