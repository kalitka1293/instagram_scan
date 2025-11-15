import sys
import os

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

config_path2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asyncRequests', 'proxy_database')
print(config_path2)
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database.py')
sys.path.append(os.path.dirname(config_path))
sys.path.append(os.path.dirname(config_path2))
from proxy_database import ProxyResource, UsageLog


from database import SessionLocal

class ProxyManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.last_reset_time = datetime.now()
        self._cached_resources = []
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
        if current_time - self.last_reset_time >= timedelta(minutes=5):
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
            self._format_proxy(resource.proxy_url),
            resource.cookie_data,
            resource.user_agent_data
        )

    def _format_proxy(self, proxy_url: str) -> str:
        """форматирование прокси для использования"""

        # proxies = {
        #     "http": "http://46M2W2:0pdJpr@103.78.191.150:8000",
        #     "https": "http://46M2W2:0pdJpr@103.78.191.150:8000"
        # }

        # return {
        #     "http": proxy_formated,
        #     "https": proxy_formated
        # }

        #    0            1      2     3
        # 103.78.191.150:8000:46M2W2:0pdJpr
        split_proxy = proxy_url.split(':')
        proxy_formated = f"http://{split_proxy[2]}:{split_proxy[3]}@{split_proxy[0]}:{split_proxy[1]}"

        return proxy_formated

    def add_resource(self, proxy_url: str, cookie_data: str = None, user_agent_data: str = None) -> None:
        """Добавление нового ресурса"""
        resource = ProxyResource(
            proxy_url=proxy_url,
            cookie_data=cookie_data,
            user_agent_data=user_agent_data
        )
        self.db.add(resource)
        self.db.commit()
        self._load_cache()  # Обновляем кэш

    def update_cookie(self, proxy_url: str, cookie_data: str) -> bool:
        """Обновление куки для прокси"""
        try:
            resource = self.db.query(ProxyResource).filter(
                ProxyResource.proxy_url == proxy_url
            ).first()

            if resource:
                resource.cookie_data = cookie_data
                self.db.commit()
                self._load_cache()  # Обновляем кэш
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
                self._load_cache()  # Обновляем кэш
                return True
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

        total_request = [{str(i.id): str(i.usage_count)} for i in self._cached_resources]

        return {
            "total_resources": len(self._cached_resources),
            "available_resources": available_resources,
            "resources_with_both": resources_with_both,
            "last_reset_time": self.last_reset_time,
            "total_request": total_request
        }

    def refresh_cache(self) -> None:
        """Принудительное обновление кэша"""
        self._load_cache()


db = SessionLocal()
proxy_manager = ProxyManager(db)
