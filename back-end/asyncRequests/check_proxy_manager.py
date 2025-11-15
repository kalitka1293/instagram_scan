import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Dict, List, Optional, Tuple, Any

Base = declarative_base()


class ProxyResource(Base):
    __tablename__ = "proxy_resources"

    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String, nullable=False)
    cookie_data = Column(Text, nullable=True)
    user_agent_data = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    proxy_url = Column(String, nullable=False)
    usage_count = Column(Integer, default=0)
    reset_time = Column(DateTime, default=datetime.utcnow)


class ProxyManager:
    def __init__(self, db_session):
        self.db = db_session
        self.last_reset_time = datetime.now()
        self._cached_resources = []  # Простой кэш в памяти
        self._load_cache()

    def _load_cache(self) -> None:
        """Загрузка всех активных ресурсов в кэш"""
        resources = self.db.query(ProxyResource).filter(
            ProxyResource.is_active == True
        ).all()
        self._cached_resources = list(resources)

    def _check_and_reset_counters(self) -> None:
        """Проверка времени и сброс счетчиков если прошел час"""
        current_time = datetime.now()
        if current_time - self.last_reset_time >= timedelta(hours=1):
            self._reset_usage_counters()
            self.last_reset_time = current_time

    def _reset_usage_counters(self) -> None:
        """Сброс счетчиков использования и сохранение в лог"""
        try:
            # Находим ресурсы для сброса
            resources_to_reset = [r for r in self._cached_resources if r.usage_count > 0]

            # Сохраняем в лог
            for resource in resources_to_reset:
                usage_log = UsageLog(
                    proxy_url=resource.proxy_url,
                    usage_count=resource.usage_count
                )
                self.db.add(usage_log)

            # Сбрасываем счетчики в БД
            for resource in resources_to_reset:
                resource.usage_count = 0

            self.db.commit()

            # Обновляем кэш
            self._load_cache()

        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при сбросе счетчиков: {e}")

    def get_proxy_resource(self, max_requests: int = 200) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Получение одного комплекта прокси, куки и User-Agent для использования
        Работает полностью с кэшированными данными
        """
        self._check_and_reset_counters()

        # Ищем в кэше доступный ресурс с минимальным использованием
        available_resources = [
            r for r in self._cached_resources
            if r.usage_count < max_requests and r.cookie_data and r.user_agent_data
        ]

        if not available_resources:
            return None, None, None

        # Выбираем ресурс с минимальным использованием
        resource = min(available_resources, key=lambda x: x.usage_count)

        # Обновляем счетчик в кэше
        resource.usage_count += 1
        resource.last_used = datetime.now()

        return (
            resource.proxy_url,
            resource.cookie_data,
            resource.user_agent_data
        )

    def add_resource(self, proxy_url: str, cookie_data: str = None, user_agent_data: str = None) -> None:
        """Добавление нового ресурса"""
        resource = ProxyResource(
            proxy_url=proxy_url,
            cookie_data=cookie_data,
            user_agent_data=user_agent_data
        )
        self.db.add(resource)
        self.db.commit()
        self._load_cache()

    def update_cookie(self, proxy_url: str, cookie_data: str) -> bool:
        """Обновление куки для прокси"""
        try:
            resource = self.db.query(ProxyResource).filter(
                ProxyResource.proxy_url == proxy_url
            ).first()

            if resource:
                resource.cookie_data = cookie_data
                self.db.commit()
                self._load_cache()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при обновлении куки: {e}")
            return False

    def update_user_agent(self, proxy_url: str, user_agent_data: str) -> bool:
        """Обновление User-Agent для прокси"""
        try:
            resource = self.db.query(ProxyResource).filter(
                ProxyResource.proxy_url == proxy_url
            ).first()

            if resource:
                resource.user_agent_data = user_agent_data
                self.db.commit()
                self._load_cache()
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при обновлении User-Agent: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики использования из кэша"""
        resources_with_both = len([r for r in self._cached_resources if r.cookie_data and r.user_agent_data])
        available_resources = len(
            [r for r in self._cached_resources if r.usage_count < 200 and r.cookie_data and r.user_agent_data])

        return {
            "total_resources": len(self._cached_resources),
            "available_resources": available_resources,
            "resources_with_both": resources_with_both,
            "last_reset_time": self.last_reset_time,
        }

    def refresh_cache(self) -> None:
        """Принудительное обновление кэша"""
        self._load_cache()


class TestProxyManager:
    @pytest.fixture
    def db_session(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def proxy_manager(self, db_session):
        return ProxyManager(db_session)

    def test_add_and_get_resource(self, proxy_manager):
        proxy_manager.add_resource(
            proxy_url="http://proxy1:8000",
            cookie_data="test_cookie=123",
            user_agent_data="Test User Agent"
        )

        proxy, cookie, user_agent = proxy_manager.get_proxy_resource()

        assert proxy == "http://proxy1:8000"
        assert cookie == "test_cookie=123"
        assert user_agent == "Test User Agent"

    def test_usage_count_increment(self, proxy_manager):
        proxy_manager.add_resource(
            proxy_url="http://proxy2:8000",
            cookie_data="cookie2",
            user_agent_data="ua2"
        )

        stats_before = proxy_manager.get_stats()

        for i in range(3):
            proxy_manager.get_proxy_resource()

        stats_after = proxy_manager.get_stats()

        assert stats_after['total_resources'] == stats_before['total_resources']

    def test_update_cookie_and_user_agent(self, proxy_manager):
        proxy_manager.add_resource(
            proxy_url="http://proxy3:8000",
            cookie_data="old_cookie",
            user_agent_data="old_ua"
        )

        proxy_manager.update_cookie("http://proxy3:8000", "new_cookie")
        proxy_manager.update_user_agent("http://proxy3:8000", "new_ua")

        proxy, cookie, user_agent = proxy_manager.get_proxy_resource()

        assert cookie == "new_cookie"
        assert user_agent == "new_ua"

    def test_max_requests_limit(self, proxy_manager):
        proxy_manager.add_resource(
            proxy_url="http://proxy5:8000",
            cookie_data="cookie5",
            user_agent_data="ua5"
        )

        available_resources = []

        for i in range(10):
            proxy, cookie, user_agent = proxy_manager.get_proxy_resource(max_requests=3)
            if proxy:
                available_resources.append(proxy)

        assert len(available_resources) == 3

    def test_multiple_resources_selection(self, proxy_manager):
        proxy_manager.add_resource(
            proxy_url="http://proxy6:8000",
            cookie_data="cookie6",
            user_agent_data="ua6"
        )

        proxy_manager.add_resource(
            proxy_url="http://proxy7:8000",
            cookie_data="cookie7",
            user_agent_data="ua7"
        )

        proxy1, cookie1, ua1 = proxy_manager.get_proxy_resource()
        proxy2, cookie2, ua2 = proxy_manager.get_proxy_resource()

        assert proxy1 != proxy2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])