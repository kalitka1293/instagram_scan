@echo off
echo =====================================
echo Установка зависимостей для Python 3.13
echo =====================================

echo.
echo 1. Удаляем старую виртуальную среду...
if exist venv rmdir /s /q venv

echo.
echo 2. Создаем новую виртуальную среду...
python -m venv venv

echo.
echo 3. Активируем виртуальную среду...
call venv\Scripts\activate.bat

echo.
echo 4. Обновляем pip...
python -m pip install --upgrade pip

echo.
echo 5. Устанавливаем wheel для ускорения установки...
pip install wheel

echo.
echo 6. Устанавливаем зависимости...
pip install --only-binary=all -r requirements.txt

echo.
echo 7. Проверяем установку...
python -c "import fastapi, uvicorn, pydantic, sqlalchemy, httpx; print('✅ Все зависимости установлены успешно!')"

echo.
echo =====================================
echo Установка завершена!
echo Для запуска: python main.py
echo =====================================
pause