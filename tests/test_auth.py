# tests/test_auth.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    """Успешная регистрация нового пользователя"""
    payload = {
        "username": "testtester",
        "email": "tester@example.com",
        "password": "supersecurepassword123"
    }
    response = await client.post("/register", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testtester"
    assert data["email"] == "tester@example.com"
    assert "id" in data
    assert "password" not in data  # Проверяем, что пароль не утек в ответе!


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    """Попытка регистрации с уже занятым именем пользователя"""
    payload = {
        "username": "duplicate_user",
        "email": "first@example.com",
        "password": "password123"
    }
    # Первый раз — ок
    await client.post("/register", json=payload)

    # Второй раз с тем же юзернеймом, но другим email
    payload["email"] = "second@example.com"
    response = await client.post("/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Имя пользователя или email уже заняты"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Успешный логин и получение JWT-токена"""
    # 1. Регистрируем пользователя
    register_payload = {
        "username": "login_user",
        "email": "login@example.com",
        "password": "correct_password"
    }
    await client.post("/register", json=register_payload)

    # 2. Пытаемся войти (OAuth2PasswordRequestForm ожидает x-www-form-urlencoded данные)
    login_payload = {
        "username": "login_user",
        "password": "correct_password"
    }
    response = await client.post("/login", data=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Попытка логина с неверным паролем"""
    register_payload = {
        "username": "wrong_pass_user",
        "email": "wrong_pass@example.com",
        "password": "correct_password"
    }
    await client.post("/register", json=register_payload)

    login_payload = {
        "username": "wrong_pass_user",
        "password": "incorrect_password"
    }
    response = await client.post("/login", data=login_payload)

    assert response.status_code == 401
    assert "Неверное имя пользователя или пароль" in response.json()["detail"]