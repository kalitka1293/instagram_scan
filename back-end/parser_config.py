"""
Конфигурация парсера Instagram
Динамическое управление cookies и таймингами
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Путь к файлу конфигурации
CONFIG_FILE = Path("parser_config.json")

# Значения по умолчанию
DEFAULT_CONFIG = {
    "cookies": [
        'ps_n=1;datr=sILmaEtuPyV0ic4plsg2JQgm;ds_user_id=68935254447;csrftoken=j7agH9jQhSDGcP3Cu0j_xC;ig_did=482AE651-A5C6-42D8-A879-419307D24C78;ps_l=1;wd=867x738;mid=aOaCsQALAAGlauL-lFyGqZKbbbB3;sessionid=68935254447%3AY3fu3mVkfp0bjW%3A3%3AAYjp7IBiTfBO0jV8Q25CvSDYu0-9MzcoiQhHE6i_NA;dpr=1.25;rur="RVA\05468935254447\0541791473291:01fe9f115bfa9133ace319fee63d1397b332af52e12896a73ef0d736f40605845a309c3e"'
    ],
    "timings": {
        "base_delay": 15.0,
        "timeout": 55,
        "max_retries": 5,
        "page_size": 25,
        "max_followers": 50,
        "max_followings": 50,
        "jitter_min": 0.0,
        "jitter_max": 7.5,
        "additional_delay_min": 1.0,
        "additional_delay_max": 3.0
    }
}

class ParserConfig:
    """Управление конфигурацией парсера"""
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из файла"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info("✅ Parser config loaded from file")
                    return config
            else:
                logger.info("⚠️ Config file not found, using defaults")
                self._save_config(DEFAULT_CONFIG)
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Сохранение конфигурации в файл"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("✅ Parser config saved to file")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False
    
    def get_cookies(self) -> List[str]:
        """Получить список cookies"""
        return self._config.get("cookies", []).copy()

    def get_user_agent(self) -> List[dict]:
        """Получить User-Agent"""
        return self._config.get("User-Agent", []).copy()

    def update_user_agent(self, list_user_agent: list) -> bool:
        """Обновление ds_user_id для User-agent для привязки к куки"""
        self._config["User-Agent"] = list_user_agent
        self._save_config(self._config)
    
    def add_cookie(self, cookie: str) -> bool:
        """Добавить новый cookie"""

        if not cookie or not isinstance(cookie, str):
            return False

        cookies = self._config.get("cookies", [])
        if cookie not in cookies:
            cookies.append(cookie)
            self._config["cookies"] = cookies
            self._save_config(self._config)
            logger.info(f"✅ Added new cookie (total: {len(cookies)})")
            return True
        return False
    
    def remove_cookie(self, index: int) -> bool:
        """Удалить cookie по индексу"""
        cookies = self._config.get("cookies", [])
        if 0 <= index < len(cookies):
            removed = cookies.pop(index)
            self._config["cookies"] = cookies
            self._save_config(self._config)
            logger.info(f"✅ Removed cookie at index {index} (remaining: {len(cookies)})")
            return True
        return False
    
    def update_cookie(self, index: int, cookie: str) -> bool:
        """Обновить cookie по индексу"""
        cookies = self._config.get("cookies", [])
        if 0 <= index < len(cookies) and cookie:
            cookies[index] = cookie
            self._config["cookies"] = cookies
            self._save_config(self._config)
            logger.info(f"✅ Updated cookie at index {index}")
            return True
        return False
    
    def get_timings(self) -> Dict[str, Any]:
        """Получить настройки таймингов"""
        return self._config.get("timings", DEFAULT_CONFIG["timings"]).copy()
    
    def update_timings(self, timings: Dict[str, Any]) -> bool:
        """Обновить настройки таймингов"""
        try:
            current_timings = self._config.get("timings", {})
            current_timings.update(timings)
            self._config["timings"] = current_timings
            self._save_config(self._config)
            logger.info("✅ Timings updated")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating timings: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """Получить всю конфигурацию"""
        return self._config.copy()
    
    def reset_to_defaults(self) -> bool:
        """Сброс на значения по умолчанию"""
        self._config = DEFAULT_CONFIG.copy()
        self._save_config(self._config)
        logger.info("✅ Config reset to defaults")
        return True

# Глобальный экземпляр конфигурации
_parser_config = ParserConfig()

def get_parser_config() -> ParserConfig:
    """Получить глобальный экземпляр конфигурации"""
    return _parser_config

def reload_config():
    """Перезагрузить конфигурацию из файла"""
    global _parser_config
    _parser_config = ParserConfig()
    logger.info("🔄 Parser config reloaded")

