from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},  # Только для SQLite
    echo=False  # Логирование SQL запросов в разработке
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

# Функция инициализации базы данных
def init_db():
    """Создание таблиц в базе данных"""
    import models
    models.Base.metadata.create_all(bind=engine)

    from asyncRequests import proxy_database
    proxy_database.Base.metadata.create_all(bind=engine)

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
