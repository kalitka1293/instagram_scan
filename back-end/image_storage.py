"""
Модуль для скачивания и хранения изображений из Instagram
"""
import os
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict
import logging
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

# Базовая директория для хранения изображений
BASE_STORAGE_DIR = Path("storage/images")

# Поддиректории для разных типов изображений
PROFILE_AVATARS_DIR = BASE_STORAGE_DIR / "profiles"
POSTS_DIR = BASE_STORAGE_DIR / "posts"
FOLLOWERS_DIR = BASE_STORAGE_DIR / "followers"

# Максимальный размер изображения (для оптимизации)
MAX_IMAGE_SIZE = (1200, 1200)

# Создаём директории при импорте
for directory in [PROFILE_AVATARS_DIR, POSTS_DIR, FOLLOWERS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def get_image_hash(url: str) -> str:
    """Получить хеш URL для использования в качестве имени файла"""
    return hashlib.md5(url.encode()).hexdigest()


def download_image(url: str, save_path: Path, optimize: bool = True) -> bool:
    """
    Скачать изображение по URL и сохранить локально
    
    Args:
        url: URL изображения
        save_path: Путь для сохранения
        optimize: Оптимизировать размер изображения
    
    Returns:
        True если успешно, False если ошибка
    """
    try:
        # Скачиваем изображение
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # Открываем изображение
        img = Image.open(BytesIO(response.content))
        
        # Оптимизируем размер если нужно
        if optimize and (img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]):
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # Конвертируем в RGB если необходимо (для JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Сохраняем
        img.save(save_path, 'JPEG', quality=85, optimize=True)
        
        logger.info(f"✅ Изображение сохранено: {save_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при скачивании изображения {url}: {e}")
        return False


def save_profile_avatar(username: str, avatar_url: Optional[str]) -> Optional[str]:
    """
    Сохранить аватар профиля
    
    Args:
        username: Имя пользователя Instagram
        avatar_url: URL аватара
    
    Returns:
        Относительный путь к сохранённому изображению или None
    """
    if not avatar_url:
        return None
    
    try:
        # Создаём имя файла на основе username и хеша URL
        image_hash = get_image_hash(avatar_url)
        filename = f"{username}_{image_hash}.jpg"
        save_path = PROFILE_AVATARS_DIR / filename
        
        # Если файл уже существует, возвращаем путь
        if save_path.exists():
            return f"/storage/images/profiles/{filename}"
        
        # Скачиваем и сохраняем
        if download_image(avatar_url, save_path, optimize=True):
            return f"/storage/images/profiles/{filename}"
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении аватара {username}: {e}")
        return None


def save_post_image(post_id: str, image_url: Optional[str]) -> Optional[str]:
    """
    Сохранить изображение поста
    
    Args:
        post_id: ID поста
        image_url: URL изображения
    
    Returns:
        Относительный путь к сохранённому изображению или None
    """
    if not image_url:
        return None
    
    try:
        # Создаём имя файла на основе post_id и хеша URL
        image_hash = get_image_hash(image_url)
        filename = f"post_{post_id}_{image_hash}.jpg"
        save_path = POSTS_DIR / filename
        
        # Если файл уже существует, возвращаем путь
        if save_path.exists():
            return f"/storage/images/posts/{filename}"
        
        # Скачиваем и сохраняем
        if download_image(image_url, save_path, optimize=True):
            return f"/storage/images/posts/{filename}"
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении изображения поста {post_id}: {e}")
        return None


def save_follower_avatar(username: str, avatar_url: Optional[str]) -> Optional[str]:
    """
    Сохранить аватар подписчика
    
    Args:
        username: Имя пользователя
        avatar_url: URL аватара
    
    Returns:
        Относительный путь к сохранённому изображению или None
    """
    if not avatar_url:
        return None
    
    try:
        # Создаём имя файла на основе username и хеша URL
        image_hash = get_image_hash(avatar_url)
        filename = f"{username}_{image_hash}.jpg"
        save_path = FOLLOWERS_DIR / filename
        
        # Если файл уже существует, возвращаем путь
        if save_path.exists():
            return f"/storage/images/followers/{filename}"
        
        # Скачиваем и сохраняем
        if download_image(avatar_url, save_path, optimize=False):  # Не оптимизируем аватарки
            return f"/storage/images/followers/{filename}"
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении аватара подписчика {username}: {e}")
        return None


def batch_save_images(items: list, image_type: str = "follower") -> Dict[str, Optional[str]]:
    """
    Массовое сохранение изображений
    
    Args:
        items: Список элементов с полями username/id и profile_pic_url/image_url
        image_type: Тип изображения ("profile", "post", "follower")
    
    Returns:
        Словарь {username/id: local_path}
    """
    results = {}
    
    for item in items:
        try:
            if image_type == "profile":
                username = item.get("username")
                url = item.get("profile_pic_url")
                if username and url:
                    results[username] = save_profile_avatar(username, url)
                    
            elif image_type == "post":
                post_id = item.get("id") or item.get("shortcode")
                url = item.get("thumbnail_url") or item.get("image_url")
                if post_id and url:
                    results[post_id] = save_post_image(post_id, url)
                    
            elif image_type == "follower":
                username = item.get("username")
                url = item.get("profile_pic_url")
                if username and url:
                    results[username] = save_follower_avatar(username, url)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке элемента: {e}")
            continue
    
    return results


def cleanup_old_images(days: int = 30):
    """
    Удалить старые изображения (старше N дней)
    
    Args:
        days: Количество дней
    """
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    for directory in [PROFILE_AVATARS_DIR, POSTS_DIR, FOLLOWERS_DIR]:
        for file_path in directory.glob("*.jpg"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка при удалении {file_path}: {e}")
    
    logger.info(f"🗑️ Удалено {deleted_count} старых изображений")
    return deleted_count


def get_storage_stats() -> Dict[str, any]:
    """Получить статистику хранилища"""
    stats = {
        "profiles": 0,
        "posts": 0,
        "followers": 0,
        "total_size_mb": 0
    }
    
    for directory, key in [
        (PROFILE_AVATARS_DIR, "profiles"),
        (POSTS_DIR, "posts"),
        (FOLLOWERS_DIR, "followers")
    ]:
        count = 0
        size = 0
        for file_path in directory.glob("*.jpg"):
            count += 1
            size += file_path.stat().st_size
        
        stats[key] = count
        stats["total_size_mb"] += size / (1024 * 1024)
    
    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    return stats
