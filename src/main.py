from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from src.database import get_db, init_db
from src.models import User, Track, Playlist
from src.schemas import (
    UserCreate, UserResponse,
    TrackCreate, TrackResponse,
    PlaylistCreate, PlaylistResponse,
    SemanticSearchRequest
)
from src.services.ai_service import ai_service
from src.tasks import generate_playlist_ai_summary_task

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models import User
from src.schemas import UserCreate, UserResponse, Token  # Не забудьте обновить Pydantic схемы!
from src.security import get_password_hash, verify_password, create_access_token
from src.dependencies import get_current_user

# Инициализируем FastAPI приложение
app = FastAPI(
    title="TuneWise AI API",
    description="Умный музыкальный бэкенд с семантическим поиском и генерацией AI-обзоров плейлистов",
    version="1.0.0"
)


# Событие старта приложения
@app.on_event("startup")
async def on_startup():
    # Автоматически создаем таблицы и подключаем расширение pgvector в БД при запуске
    await init_db()


# --- ЭНДПОИНТЫ ПОЛЬЗОВАТЕЛЕЙ (CRUD) ---

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем уникальность username и email
    existing_user = await db.execute(
        select(User).filter((User.username == user_data.username) | (User.email == user_data.email))
    )
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = User(**user_data.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, есть ли уже такой юзер
    query = select(User).where((User.username == user_data.username) | (User.email == user_data.email))
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Имя пользователя или email уже заняты")

    # Создаем нового с захэшированным паролем
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # OAuth2PasswordRequestForm ожидает поля username и password
    query = select(User).where(User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Генерируем токен
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- ЭНДПОИНТЫ ТРЕКОВ & ИИ-ВЕКТОРИЗАЦИЯ ---

@app.post("/tracks", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def create_track(track_data: TrackCreate, db: AsyncSession = Depends(get_db)):
    # 1. Обращаемся к AI-сервису, чтобы преобразовать текстовое описание в вектор (embedding)
    embedding_vector = await ai_service.get_embedding(track_data.description)

    # 2. Сохраняем трек вместе с его векторным представлением
    new_track = Track(
        title=track_data.title,
        artist=track_data.artist,
        genre=track_data.genre,
        description=track_data.description,
        embedding=embedding_vector
    )
    db.add(new_track)
    await db.commit()
    await db.refresh(new_track)
    return new_track


# --- СЕМАНТИЧЕСКИЙ ПОИСК (PGVECTOR) ---

@app.post("/tracks/search", response_model=List[TrackResponse])
async def semantic_search(search_data: SemanticSearchRequest, db: AsyncSession = Depends(get_db)):
    # 1. Векторизуем поисковый запрос пользователя (например, "грустный рок для поездки")
    query_vector = await ai_service.get_embedding(search_data.query)

    # 2. Выполняем поиск по косинусному расстоянию (метод cosine_distance в pgvector)
    # Оператор <=> на уровне БД найдет наиболее похожие по смыслу векторы треков.
    query = (
        select(Track)
        .order_by(Track.embedding.cosine_distance(query_vector))
        .limit(search_data.limit)
    )

    result = await db.execute(query)
    tracks = result.scalars().all()
    return tracks


# --- ЭНДПОИНТЫ ПЛЕЙЛИСТОВ & CELERY ---

@app.post("/playlists", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(playlist_data: PlaylistCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Проверяем существование пользователя
    print(f"Плейлист создает пользователь: {current_user.username}")

    user = await db.get(User, playlist_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Выгружаем треки по переданному списку ID
    result = await db.execute(select(Track).filter(Track.id.in_(playlist_data.track_ids)))
    tracks = result.scalars().all()
    if len(tracks) != len(playlist_data.track_ids):
        raise HTTPException(status_code=400, detail="Some track IDs are invalid")

    # 3. Создаем плейлист (поле ai_summary пока остается пустым/None)
    new_playlist = Playlist(
        title=playlist_data.title,
        user_id=playlist_data.user_id,
        tracks=tracks
    )

    db.add(new_playlist)
    await db.commit()
    # Загружаем связь до сериализации ответа, чтобы избежать ленивого
    # обращения к БД вне асинхронного контекста (MissingGreenlet).
    await db.refresh(new_playlist, ["tracks"])

    # 4. Отправляем тяжелую задачу генерации обзора в очередь RabbitMQ -> Celery.
    # FastAPI моментально вернет ответ клиенту, не дожидаясь ответа от OpenAI!
    generate_playlist_ai_summary_task.delay(new_playlist.id)

    return new_playlist


@app.get("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    # Получаем плейлист по ID
    result = await db.execute(
        select(Playlist).filter(Playlist.id == playlist_id)
    )
    playlist = result.scalars().first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Асинхронно подгружаем связанные треки для корректного маппинга в схему Pydantic
    await db.refresh(playlist, ["tracks"])
    return playlist
