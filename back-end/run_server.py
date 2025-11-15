#!/usr/bin/env python3
"""
Скрипт для запуска FastAPI сервера InstardingBot
"""

import uvicorn
import sys
import os

# Добавляем текущую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.dirname('asyncRequests'))
from asyncRequests.loggingAsync import logger

def main():
    logger.debug("Запуск Теста "*5)
    print("TEST "*10)
    print("🚀 Запуск InstardingBot API v2.0 с асинхронным парсингом...")
    print("📍 URL: http://127.0.0.1:8008")
    print("📖 Документация: http://127.0.0.1:8008/docs")
    print("🔄 ReDoc: http://127.0.0.1:8008/redoc")
    print("✨ Новые возможности:")
    print("   - Мгновенная отдача профилей")
    print("   - Асинхронный парсинг подписчиков")
    print("   - Очередь задач")
    print("   - Только взаимные подписки")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8002,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
