from sqlalchemy import String, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from src.database import Base

# Промежуточная таблица для связи Многие-ко-Многим между Playlists и Tracks
playlist_track = Table(
    "playlist_track",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # Связь с плейлистами пользователя
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")




class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artist: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    genre: Mapped[str] = mapped_column(String(50), nullable=False)

    # Текстовое описание трека (настроение, инструменты, атмосфера)
    # Оно нужно, чтобы сгенерировать качественный вектор (эмбеддинг)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Векторное представление описания трека.
    # Используем размерность 1536 (стандарт для OpenAI Embeddings)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    # Обратная связь с плейлистами
    playlists: Mapped[list["Playlist"]] = relationship(
        secondary=playlist_track, back_populates="tracks"
    )


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    # AI-сгенерированное саммари/обзор для этого плейлиста (задача для Celery)
    ai_summary: Mapped[str] = mapped_column(String(2000), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Связи
    user: Mapped["User"] = relationship(back_populates="playlists")
    tracks: Mapped[list["Track"]] = relationship(
        secondary=playlist_track, back_populates="playlists"
    )