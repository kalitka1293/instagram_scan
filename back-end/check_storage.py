#!/usr/bin/env python3
"""
Скрипт для проверки путей к storage
"""
import os
from pathlib import Path

print("=" * 60)
print("📂 ПРОВЕРКА STORAGE ДИРЕКТОРИЙ")
print("=" * 60)

# Текущая рабочая директория
cwd = os.getcwd()
print(f"\n1. Текущая директория: {cwd}")

# Путь к скрипту
script_dir = Path(__file__).parent.absolute()
print(f"2. Директория скрипта: {script_dir}")

# Проверяем storage относительно текущей директории
storage_cwd = Path("storage/images")
print(f"\n3. Storage относительно CWD: {storage_cwd.absolute()}")
print(f"   Существует: {storage_cwd.exists()}")

if storage_cwd.exists():
    # Проверяем поддиректории
    for subdir in ["profiles", "posts", "followers"]:
        subdir_path = storage_cwd / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*.jpg"))
            print(f"   - {subdir}/: {len(files)} файлов")
            if files:
                print(f"     Пример: {files[0].name}")

# Проверяем storage относительно директории скрипта
storage_script = script_dir / "storage" / "images"
print(f"\n4. Storage относительно скрипта: {storage_script}")
print(f"   Существует: {storage_script.exists()}")

if storage_script.exists():
    for subdir in ["profiles", "posts", "followers"]:
        subdir_path = storage_script / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*.jpg"))
            print(f"   - {subdir}/: {len(files)} файлов")
            if files:
                print(f"     Пример: {files[0].name}")

# Проверяем, где FastAPI будет искать файлы
print(f"\n5. FastAPI StaticFiles будет искать в:")
print(f"   {Path('storage').absolute()}")
print(f"   Существует: {Path('storage').exists()}")

# Проверяем конкретный файл
test_file = Path("storage/images/posts/post_C87V_ezogza_9884f233f036a22ad167a56e7f2ec84b.jpg")
print(f"\n6. Тестовый файл:")
print(f"   Путь: {test_file.absolute()}")
print(f"   Существует: {test_file.exists()}")
if test_file.exists():
    print(f"   Размер: {test_file.stat().st_size} байт")
    print(f"   Права: {oct(test_file.stat().st_mode)}")

print("\n" + "=" * 60)




