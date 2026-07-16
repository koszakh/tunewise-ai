# generate_key.py
import secrets
from pathlib import Path


def main():
    env_path = Path(".env")
    example_path = Path(".env.example")

    # 1. Если .env нет, но есть .env.example — копируем его
    if not env_path.exists():
        if example_path.exists():
            env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            print("📝 Создан файл .env на основе .env.example")
        else:
            env_path.touch()
            print("📝 Создан новый пустой файл .env")

    # 2. Генерируем безопасный ключ (32 байта / 64 символа hex)
    new_key = secrets.token_hex(32)

    # 3. Читаем текущее содержимое .env
    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    key_exists = False
    new_lines = []

    # 4. Ищем строку SECRET_KEY= и заменяем её значение
    for line in lines:
        if line.strip().startswith("SECRET_KEY="):
            new_lines.append(f"SECRET_KEY={new_key}")
            key_exists = True
        else:
            new_lines.append(line)

    # Если переменной SECRET_KEY вообще не было в файле, добавляем её в конец
    if not key_exists:
        new_lines.append(f"SECRET_KEY={new_key}")

    # 5. Записываем обновленные данные обратно
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"🔑 Секретный ключ успешно сгенерирован и записан в {env_path}!")


if __name__ == "__main__":
    main()