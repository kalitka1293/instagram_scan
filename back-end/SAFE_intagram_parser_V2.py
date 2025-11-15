"""
Новая система парсинга Instagram на основе test.py
С асинхронной обработкой, очередью и кэшированием
"""

import json
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import requests
from sqlalchemy.orm import Session
from threading import Thread, Lock
from image_storage import (
    save_profile_avatar,
    save_post_image,
    save_follower_avatar,
    batch_save_images
)
from queue import Queue, Empty
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
IG_APP_ID = "936619743392459"
QUERY_HASH_FOLLOWERS = "c76146de99bb02f6415203be841dd25a"
QUERY_HASH_FOLLOWINGS = "d04b0a864b4b54837c0d870b0e77e076"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Настройки парсинга - увеличенные лимиты для стабильности
BASE_DELAY = 15.0  # Увеличена задержка между запросами
TIMEOUT = 55  # Увеличен таймаут
MAX_RETRIES = 5  # Больше попыток при ошибках
PAGE_SIZE = 25  # Уменьшен размер страницы для меньшей нагрузки
MAX_FOLLOWERS = 50  # Уменьшено количество подписчиков
MAX_FOLLOWINGS = 50  # Уменьшено количество подписок

# Глобальная очередь задач
task_queue = Queue()
task_results = {}  # {task_id: result}
task_lock = Lock()
worker_thread = None


class RateLimiter:
    """Управление задержками между запросами"""

    def __init__(self, base_delay: float):
        self.base_delay = max(0.0, base_delay)

    def sleep(self):
        # Увеличенная задержка с большим jitter для стабильности
        jitter = random.uniform(0, self.base_delay * 0.5)  # Увеличен jitter
        additional_delay = random.uniform(1.0, 3.0)  # Дополнительная случайная задержка
        total_delay = self.base_delay + jitter + additional_delay
        logger.info(f"Rate limiting: sleeping for {total_delay:.1f}s")
        time.sleep(total_delay)


class InstagramParserV2:
    """Новый парсер Instagram на основе test.py"""

    def __init__(self, cookies: str = ""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": IG_APP_ID,
        })

        # Устанавливаем куки если есть
        if cookies:
            self._set_cookies(cookies)

        self.timeout = TIMEOUT
        self.max_retries = MAX_RETRIES
        self.rate_limiter = RateLimiter(BASE_DELAY)

    def _set_cookies(self, cookie_str: str):
        """Установка куки из строки"""
        for part in cookie_str.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            self.session.cookies.set(key.strip(), value.strip(), domain=".instagram.com")

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Выполнение запроса с retry логикой"""
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                print('\n\n>>>>>', url, '<<<<<<<<<<\n\n')

                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)

                if resp.status_code in (200, 201):
                    return resp

                if resp.status_code in (429, 500, 502, 503, 504):
                    # Увеличенный экспоненциальный backoff для стабильности
                    if resp.status_code == 429:  # Rate limiting
                        wait = min(120, 3 ** attempt) + random.uniform(0, 5.0)  # Увеличено для 429
                    else:
                        wait = min(90, 2.5 ** attempt) + random.uniform(0, 3.0)  # Увеличено для других ошибок
                    logger.warning(
                        f"Status {resp.status_code} on {url}. Waiting {wait:.1f}s (attempt {attempt}/{self.max_retries})")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp

            except requests.RequestException as e:
                last_exc = e
                wait = min(30, 1.5 * attempt) + random.uniform(0, 1.0)
                logger.warning(f"Request exception: {e}. Retry in {wait:.1f}s (attempt {attempt}/{self.max_retries})")
                time.sleep(wait)

        if last_exc:
            raise last_exc
        raise RuntimeError("Failed request with unknown error")

    def get_profile(self, username: str) -> Dict[str, Any]:
        """Получение базовой информации профиля"""
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {"Referer": f"https://www.instagram.com/{username}/"}

        resp = self._request("GET", url, headers=headers)
        data = resp.json().get("data", {}).get("user", {})

        if not data:
            raise ValueError(f"Profile not found: {username}")

        # ДОБАВИТЬ: recent_media с шорткодами из web_profile_info
        media_edges = (data.get("edge_owner_to_timeline_media") or {}).get("edges") or []
        recent_media = []
        for e in media_edges:
            n = e.get("node", {}) or {}
            recent_media.append({
                "id": n.get("id"),
                "shortcode": n.get("shortcode"),
                "is_video": n.get("is_video"),
                "taken_at_timestamp": n.get("taken_at_timestamp"),
                "comments_disabled": bool(n.get("comments_disabled")),
                "comment_count": int(n.get("edge_media_to_comment", {}).get("count", 0)),
            })

        # Безопасное получение count с защитой от None
        followers_count = (data.get("edge_followed_by") or {}).get("count") or 0
        following_count = (data.get("edge_follow") or {}).get("count") or 0
        posts_count = (data.get("edge_owner_to_timeline_media") or {}).get("count") or 0

        print(f"🔍 DEBUG get_profile:")
        print(f"  followers_count: {followers_count} (type: {type(followers_count)})")
        print(f"  following_count: {following_count} (type: {type(following_count)})")
        print(f"  posts_count: {posts_count} (type: {type(posts_count)})")

        # Получаем URL аватара
        profile_pic_url = data.get("profile_pic_url_hd") or data.get("profile_pic_url")
        username = data.get("username")

        # Сохраняем аватар локально
        local_avatar_path = None
        if username and profile_pic_url:
            local_avatar_path = save_profile_avatar(username, profile_pic_url)
            print(f"💾 Аватар профиля сохранён: {local_avatar_path}")

        return {
            "id": data.get("id"),
            "username": username,
            "full_name": data.get("full_name", ""),
            "biography": data.get("biography", ""),
            "external_url": data.get("external_url"),
            "followers_count": followers_count,
            "following_count": following_count,
            "posts_count": posts_count,
            "is_private": data.get("is_private", False),
            "is_verified": data.get("is_verified", False),
            "is_business": data.get("is_business_account", False),
            "profile_pic_url": local_avatar_path or profile_pic_url,  # ✅ Используем локальный путь
            "profile_pic_url_original": profile_pic_url,  # Сохраняем оригинальный URL
            "recent_media": recent_media,
        }

    def _get_user_list(self, user_id: str, query_hash: str, max_count: int = 0) -> List[Dict]:
        """Получение списка подписчиков или подписок через GraphQL"""
        collected = []
        after = None
        has_next_page = True
        fetched = 0

        csrf_token = self.session.cookies.get("csrftoken", "missing")
        headers = {
            "Referer": "https://www.instagram.com/",
            "X-CSRFToken": csrf_token
        }

        while has_next_page and (not max_count or fetched < max_count):
            variables = {
                "id": str(user_id),
                "include_reel": True,
                "fetch_mutual": False,
                "first": PAGE_SIZE
            }

            if after:
                variables["after"] = after

            params = {
                "query_hash": query_hash,
                "variables": json.dumps(variables, separators=(",", ":"))
            }

            url = f"https://www.instagram.com/graphql/query/?{urlencode(params)}"
            resp = self._request("GET", url, headers=headers)

            data = resp.json()
            edge_key = "edge_followed_by" if query_hash == QUERY_HASH_FOLLOWERS else "edge_follow"

            try:
                edges = data["data"]["user"][edge_key]["edges"]
                page_info = data["data"]["user"][edge_key]["page_info"]
            except (KeyError, TypeError):
                logger.error(f"Unexpected response structure: {data}")
                break

            for edge in edges:
                node = edge.get("node", {})
                user_data = {
                    "follower_pk": node.get("id"),
                    "username": node.get("username"),
                    "full_name": node.get("full_name", ""),
                    "profile_pic_url": node.get("profile_pic_url"),
                    "is_verified": node.get("is_verified", False),
                    "is_private": node.get("is_private", False),
                    "has_anonymous_profile_picture": node.get("has_anonymous_profile_picture", False),
                    "fbid_v2": node.get("fbid_v2"),
                    "third_party_downloads_enabled": node.get("third_party_downloads_enabled", False),
                    "latest_reel_media": node.get("latest_reel_media")
                }
                collected.append(user_data)
                fetched += 1

                if max_count and (fetched or 1) >= (max_count or 1):
                    has_next_page = False
                    break

            has_next_page = has_next_page and page_info.get("has_next_page", False)
            after = page_info.get("end_cursor")

            if has_next_page:
                self.rate_limiter.sleep()

        return collected

    def get_followers(self, user_id: str, max_count: int = MAX_FOLLOWERS) -> List[Dict]:
        """Получение подписчиков"""
        return self._get_user_list(user_id, QUERY_HASH_FOLLOWERS, max_count)

    def get_followings(self, user_id: str, max_count: int = MAX_FOLLOWINGS) -> List[Dict]:
        """Получение подписок"""
        return self._get_user_list(user_id, QUERY_HASH_FOLLOWINGS, max_count)

    def find_mutual_followers(self, followers: List[Dict], followings: List[Dict]) -> List[Dict]:
        """Поиск взаимных подписок"""
        followers_by_id = {f["follower_pk"]: f for f in followers if f.get("follower_pk")}
        mutuals = []

        for following in followings:
            following_id = following.get("follower_pk")
            if following_id and following_id in followers_by_id:
                # Объединяем данные из обоих списков
                mutual = followers_by_id[following_id].copy()
                mutuals.append(mutual)

        return mutuals

    def _mobile_headers(self):
        """Заголовки для мобильного API"""
        csrf = self.session.cookies.get("csrftoken") or "missing"
        return {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.instagram.com/",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrf,
            "X-IG-WWW-Claim": "0",
        }

    def get_queue_status() -> Dict[str, Any]:
        """Получить статус всей очереди и активных задач"""
        with task_lock:
            # Задачи в очереди (еще не обрабатываются)
            pending_tasks = []
            # Создаем временную очередь для просмотра
            temp_queue = Queue()

            # Считаем задачи в основной очереди
            queue_count = task_queue.qsize()

            # Извлекаем все задачи для просмотра (и сразу возвращаем обратно)
            for _ in range(queue_count):
                try:
                    task = task_queue.get_nowait()
                    pending_tasks.append({
                        "task_id": task.task_id,
                        "username": task.username,
                        "user_id": task.user_id,
                        "created_at": task.created_at.isoformat()
                    })
                    temp_queue.put(task)
                except Empty:
                    break

            # Возвращаем задачи обратно в основную очередь
            while not temp_queue.empty():
                task_queue.put(temp_queue.get())

            # Активные задачи (в обработке или завершенные)
            active_tasks = {}
            processing_tasks = []
            completed_tasks = []
            failed_tasks = []

            for task_id, result in task_results.items():
                task_info = {
                    "task_id": task_id,
                    "status": result.get("status"),
                    "created_at": result.get("created_at").isoformat() if result.get("created_at") else None,
                    "completed_at": result.get("completed_at").isoformat() if result.get("completed_at") else None
                }

                if result.get("status") == "processing":
                    processing_tasks.append(task_info)
                elif result.get("status") == "completed":
                    completed_tasks.append(task_info)
                elif result.get("status") == "failed":
                    failed_tasks.append(task_info)
                elif result.get("status") == "pending":
                    # pending задачи уже в очереди, не дублируем
                    pass

            return {
                "queue_summary": {
                    "pending_in_queue": queue_count,
                    "processing": len(processing_tasks),
                    "completed": len(completed_tasks),
                    "failed": len(failed_tasks),
                    "total_tasks": len(task_results)
                },
                "pending_tasks": pending_tasks,
                "processing_tasks": processing_tasks,
                "recent_completed": completed_tasks[-10:],  # последние 10 завершенных
                "recent_failed": failed_tasks[-5:],  # последние 5 неудачных
                "worker_status": {
                    "is_alive": worker_thread.is_alive() if worker_thread else False,
                    "queue_size": task_queue.qsize()
                }
            }

    def get_recent_media_mobile(self, user_id: str, count: int = 12) -> List[Dict]:
        """Получение недавних медиа через мобильный API"""
        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/?count={max(1, min(50, count))}"
        headers = self._mobile_headers()

        try:
            response = self._request("GET", url, headers=headers)
            j = response.json()
            items = j.get("items") or []

            out = []
            for it in items:
                pk = str(it.get("pk") or "")
                code = it.get("code") or it.get("shortcode") or ""
                disabled = bool(it.get("comments_disabled") or it.get("commenting_disabled"))
                comment_count = int(it.get("comment_count") or 0)

                # Получаем URL изображения
                image_url = None
                if it.get("image_versions2", {}).get("candidates"):
                    image_url = it["image_versions2"]["candidates"][0].get("url")
                elif it.get("carousel_media"):
                    # Для карусели берем первое изображение
                    first_item = it["carousel_media"][0]
                    if first_item.get("image_versions2", {}).get("candidates"):
                        image_url = first_item["image_versions2"]["candidates"][0].get("url")

                out.append({
                    "pk": pk,
                    "shortcode": code,
                    "comments_disabled": disabled,
                    "comment_count": comment_count,
                    "image_url": image_url
                })
            return out
        except Exception as e:
            print(f"⚠️ Mobile feed failed: {e}")
            return []

    def get_comments_for_media(self, media_ref: str, limit: int = 2, post_shortcode: Optional[str] = None) -> List[
        Dict]:
        """Получение комментариев для медиа"""
        media_pk = None
        if str(media_ref).isdigit():
            media_pk = str(media_ref)
        else:
            try:
                url_sc = f"https://i.instagram.com/api/v1/media/shortcode/{media_ref}/"
                resp_sc = self._request("GET", url_sc, headers=self._mobile_headers())
                j_sc = resp_sc.json()
                media_pk = str(j_sc.get("items", [{}])[0].get("pk") or j_sc.get("media", {}).get("pk") or "")
            except Exception as e:
                print(f"⚠️ Shortcode resolve failed for {media_ref}: {e}")
                return []

        if not media_pk:
            return []

        def _norm(j, post_url=None):
            items = j.get("comments") or j.get("items") or []
            out = []
            for c in items:
                user = c.get("user") or {}
                out.append({
                    "id": str(c.get("pk") or c.get("id") or ""),
                    "text": c.get("text") or "",
                    "username": user.get("username"),
                    "full_name": user.get("full_name"),
                    "profile_pic_url": user.get("profile_pic_url") or user.get("profile_pic_url_hd"),
                    "post_url": post_url,
                })
                if (len(out) or 1) >= (limit or 1):
                    break
            return out

        count = max(1, min(50, limit))
        post_url = f"https://www.instagram.com/p/{post_shortcode}/" if post_shortcode else None

        # Пробуем мобильный API
        try:
            url_i = f"https://i.instagram.com/api/v1/media/{media_pk}/comments/?can_support_threading=true&permalink_enabled=true&count={count}"
            resp = self._request("GET", url_i, headers=self._mobile_headers())
            j = resp.json()
            out = _norm(j, post_url)
            if out:
                return out
        except Exception as e:
            print(f"⚠️ Mobile comments failed: {e}")

        # Fallback к веб API
        try:
            url_w = f"https://www.instagram.com/api/v1/media/{media_pk}/comments/?can_support_threading=true&permalink_enabled=true&count={count}"
            headers_w = self._mobile_headers()
            headers_w["Referer"] = f"https://www.instagram.com/p/{media_ref}/" if not str(
                media_ref).isdigit() else "https://www.instagram.com/"
            resp2 = self._request("GET", url_w, headers=headers_w)
            j2 = resp2.json()
            return _norm(j2, post_url)
        except Exception as e:
            print(f"⚠️ Web comments failed: {e}")
            return []

    def get_comments_fallback_instagrapi(self, shortcode: str, limit: int = 2) -> List[Dict]:
        """Fallback с использованием instagrapi как в test.py"""
        try:
            # Извлекаем sessionid из куков текущей сессии парсера
            sessionid = None
            cookies_str = ""

            # Собираем куки из текущей сессии парсера
            for cookie in self.session.cookies:
                cookies_str += f"{cookie.name}={cookie.value};"

            for part in cookies_str.split(';'):
                part = part.strip()
                x = '1232r'
                if part.startswith('sessionid='):
                    sessionid = part.split('=', 1)[1]
                    break

            if not sessionid:
                print("⚠️ sessionid not found in cookies")
                return []

            from instagrapi import Client
            cl = Client()
            cl.login_by_sessionid(sessionid)
            pk = cl.media_pk_from_code(shortcode)
            comments = cl.media_comments(pk, amount=max(1, min(50, limit)))

            out = []
            for c in comments:
                u = c.user
                out.append({
                    "id": str(getattr(c, 'pk', '')),
                    "text": getattr(c, 'text', '') or '',
                    "username": getattr(u, 'username', None),
                    "full_name": getattr(u, 'full_name', None),
                    "profile_pic_url": getattr(u, 'profile_pic_url', None) or getattr(u, 'profile_pic_url_hd', None),
                    "post_url": f"https://www.instagram.com/p/{shortcode}/",
                })
                if (len(out) or 1) >= (limit or 1):
                    break
            return out
        except Exception as e:
            print(f"⚠️ instagrapi fallback failed: {e}")
            return []

    def collect_comments(self, username: str) -> List[Dict]:
        """Сбор комментариев из недавних постов (до 5 шт)"""
        comments: List[Dict] = []
        try:
            # 1) Брали несуществующий метод + неправильный ключ. Исправляем:
            profile = self.get_profile(username)
            user_id = profile.get("id")  # было "user_id"
            if not user_id:
                print(f"⚠️ User ID not found for {username}")
                return []

            print(f"🔍 Collecting comments for @{username} (ID: {user_id})")

            # 2) Берем недавние медиа через мобильный feed
            try:
                media_list = self.get_recent_media_mobile(user_id, count=12)
                print(f"📱 Found {len(media_list)} media items via mobile feed")
            except Exception as e:
                print(f"⚠️ Mobile feed failed, fallback to web media list: {e}")
                # fallback к web_profile_info
                web_profile = self.get_profile(username)
                recent_media = web_profile.get("recent_media", [])
                media_list = [{
                    "pk": None,
                    "shortcode": m.get("shortcode"),
                    "comments_disabled": False,
                    "comment_count": None,
                    "image_url": None
                } for m in recent_media]

            # 3) Собираем до 5 комментариев суммарно
            for m in media_list:
                if (len(comments) or 1) >= 5:
                    break
                if m.get("comments_disabled"):
                    print(f"⚠️ Comments disabled for {m.get('shortcode')}")
                    continue

                ref = m.get("pk") or m.get("shortcode")
                shortcode = m.get("shortcode")
                if not ref:
                    continue

                print(f"🔍 Getting comments for {shortcode or ref}")

                # метод 1: web/mobile API
                cmts = self.get_comments_for_media(
                    ref,
                    limit=5 - len(comments),
                    post_shortcode=shortcode
                )

                # метод 2: instagrapi fallback (если включен и есть shortcode)
                if not cmts and shortcode and USE_INSTAGRAPI_FALLBACK:
                    print(f"🔄 Trying instagrapi fallback for {shortcode}")
                    cmts = self.get_comments_fallback_instagrapi(
                        shortcode,
                        limit=5 - len(comments)
                    )

                if cmts:
                    for cmt in cmts:
                        cmt["post_image_url"] = m.get("image_url")
                        if not cmt.get("post_url") and shortcode:
                            cmt["post_url"] = f"https://www.instagram.com/p/{shortcode}/"
                    comments.extend(cmts)
                    print(f"✅ Got {len(cmts)} comments from {shortcode or ref}")
                else:
                    print(f"⚠️ No comments found for {shortcode or ref}")

                if len(comments) < 5:
                    self.rate_limiter.sleep()

            print(f"✅ Collected {len(comments)} total comments for @{username}")
            return comments

        except Exception as e:
            print(f"❌ Comments collection failed: {e}")
            return []


# Импортируем систему динамической конфигурации
from parser_config import get_parser_config

USE_INSTAGRAPI_FALLBACK = True


class CookieRotator:
    """Ротация cookies для балансировки нагрузки с динамической конфигурацией"""

    def __init__(self):
        self.current_index = 0
        self.lock = Lock()

    def get_next_cookie(self) -> str:
        """Получить следующий cookie из пула (round-robin)"""
        with self.lock:
            # Получаем актуальный список cookies из конфигурации
            config = get_parser_config()
            cookies_pool = config.get_cookies()

            if not cookies_pool:
                raise ValueError("Cookie pool is empty! Add cookies in admin panel.")

            cookie = cookies_pool[self.current_index]
            self.current_index = (self.current_index + 1) % len(cookies_pool)

            logger.info(f"🔄 Using cookie #{self.current_index + 1}/{len(cookies_pool)}")
            return cookie


# Глобальный ротатор куков
cookie_rotator = CookieRotator()


def get_parser() -> InstagramParserV2:
    """Получить новый парсер с следующим cookie из пула"""
    cookie = cookie_rotator.get_next_cookie()
    return InstagramParserV2(cookie)


def get_parser_timings() -> dict:
    """Получить актуальные тайминги из конфигурации"""
    config = get_parser_config()
    return config.get_timings()


class ParseTask:
    """Задача парсинга"""

    def __init__(self, task_id: str, username: str, user_id: str = None):
        self.task_id = task_id
        self.username = username
        self.user_id = user_id
        self.created_at = datetime.now()


def worker():
    """Воркер для обработки очереди парсинга"""
    from database import SessionLocal
    import crud

    while True:
        try:
            task = task_queue.get(timeout=5)
            if task is None:  # Сигнал остановки
                break

            logger.info(f"Processing task {task.task_id} for {task.username}")

            # Парсим подписчиков и подписки
            db = SessionLocal()
            try:
                # Обновляем статус в БД
                crud.update_profile_parsing_status(db, task.username, "processing", task.task_id)

                # Получаем новый парсер с ротацией cookie для снижения нагрузки
                task_parser = get_parser()

                followers = task_parser.get_followers(task.user_id)
                followings = task_parser.get_followings(task.user_id)
                mutuals = task_parser.find_mutual_followers(followers, followings)

                # Собираем комментарии
                comments = task_parser.collect_comments(task.username)

                # Если нет взаимных, берем случайных из подписок
                if not mutuals and followings:
                    sample_size = min(20, len(followings))
                    mutuals = random.sample(followings, sample_size) if (sample_size or 1) > 0 else []
                elif not mutuals and followers:
                    # Если нет подписок, берем случайных подписчиков
                    sample_size = min(20, len(followers))
                    mutuals = random.sample(followers, sample_size) if (sample_size or 1) > 0 else []

                # Сохраняем аватары подписчиков
                if mutuals:
                    print(f"💾 Сохранение аватаров {len(mutuals)} подписчиков...")
                    saved_avatars = batch_save_images(mutuals, image_type="follower")
                    print(f"✅ Сохранено {len([v for v in saved_avatars.values() if v])} аватаров")

                    # Обновляем пути к аватарам в данных подписчиков
                    for follower in mutuals:
                        username = follower.get("username")
                        if username and username in saved_avatars and saved_avatars[username]:
                            follower["profile_pic_url_local"] = saved_avatars[username]

                # Сохраняем только взаимных подписчиков в БД
                profile = crud.get_instagram_profile_by_username(db, task.username)
                if profile and mutuals:
                    crud.save_instagram_followers(db, profile.id, mutuals)

                # Сохраняем комментарии в профиль
                if profile and comments:
                    profile.comments_data = comments
                    db.commit()

                # Обновляем статус парсинга
                crud.update_profile_parsing_status(db, task.username, "completed")

                with task_lock:
                    task_results[task.task_id] = {
                        "status": "completed",
                        "followers": followers,
                        "followings": followings,
                        "mutuals": mutuals,
                        "comments": comments,
                        "completed_at": datetime.now()
                    }

                logger.info(
                    f"Task {task.task_id} completed. Followers: {len(followers)}, Followings: {len(followings)}, Mutuals: {len(mutuals)}")

            except Exception as e:
                logger.error(f"Task {task.task_id} failed: {e}")
                crud.update_profile_parsing_status(db, task.username, "failed")

                with task_lock:
                    task_results[task.task_id] = {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now()
                    }
            finally:
                db.close()

            task_queue.task_done()

        except Empty:
            continue
        except Exception as e:
            logger.error(f"Worker error: {e}")


def start_worker():
    """Запуск воркера в отдельном потоке"""
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = Thread(target=worker, daemon=True)
        worker_thread.start()
        logger.info("Parser worker started")


def stop_worker():
    """Остановка воркера"""
    task_queue.put(None)
    if worker_thread:
        worker_thread.join(timeout=5)


def generate_task_id(username: str) -> str:
    """Генерация уникального ID задачи"""
    return f"{username}_{int(time.time() * 1000)}"


def add_parse_task(username: str, user_id: str) -> str:
    """Добавление задачи в очередь"""
    task_id = generate_task_id(username)
    task = ParseTask(task_id, username, user_id)

    # Инициализируем статус
    with task_lock:
        task_results[task_id] = {
            "status": "pending",
            "created_at": datetime.now()
        }

    task_queue.put(task)
    logger.info(f"Added parse task {task_id} for {username}")
    return task_id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Получение статуса задачи"""
    with task_lock:
        return task_results.get(task_id, {"status": "not_found"})


def scrape_profile_basic(username: str) -> Dict[str, Any]:
    """Получение базовой информации профиля (синхронно)"""
    try:
        # Используем ротацию cookies для снижения нагрузки
        profile_parser = get_parser()
        profile_data = profile_parser.get_profile(username)

        print(f"🔍 DEBUG scrape_profile_basic - profile_data type: {type(profile_data)}")
        print(
            f"🔍 DEBUG scrape_profile_basic - profile_data keys: {list(profile_data.keys()) if isinstance(profile_data, dict) else 'NOT A DICT'}")

        # Генерируем фиктивную аналитику
        analytics_data = generate_analytics(profile_data)
        posts_data = generate_posts_data(profile_data, profile_parser)

        return {
            "success": True,
            "profile": profile_data,
            "analytics_data": analytics_data,
            "posts_data": posts_data
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ОШИБКА В scrape_profile_basic:\n{error_trace}")
        logger.error(f"Profile scraping failed for {username}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def generate_analytics(profile_data: Dict) -> Dict[str, Any]:
    """Генерация аналитических данных на основе профиля"""
    # Безопасное получение значений с логированием
    followers_raw = profile_data.get("followers_count")
    following_raw = profile_data.get("following_count")
    posts_raw = profile_data.get("posts_count")

    print(f"🔍 DEBUG generate_analytics:")
    print(f"  followers_count: {followers_raw} (type: {type(followers_raw)})")
    print(f"  following_count: {following_raw} (type: {type(following_raw)})")
    print(f"  posts_count: {posts_raw} (type: {type(posts_raw)})")

    followers = followers_raw if followers_raw is not None else 0
    following = following_raw if following_raw is not None else 0
    posts = posts_raw if posts_raw is not None else 0

    # Вычисляем метрики
    engagement_rate = min(random.uniform(2.5, 8.5), 15.0)
    reach_percent = random.uniform(15, 45)

    return {
        "overview": {
            "total_followers": followers,
            "total_following": following,
            "total_posts": posts,
            "engagement_rate": round(engagement_rate, 1),
            "account_type": "Business" if profile_data.get("is_business") else "Personal"
        },
        "engagement": {
            "likes_per_post": max(int(followers * engagement_rate / 100), 10),
            "comments_per_post": max(int(followers * engagement_rate / 500), 2),
            "reach_percentage": round(reach_percent, 1),
            "story_views": max(int(followers * reach_percent / 100), 50)
        },
        "growth": {
            "weekly_growth": round(random.uniform(-2.5, 5.2), 1),
            "monthly_growth": round(random.uniform(-5.0, 15.8), 1),
            "best_posting_time": random.choice(["9:00", "12:00", "15:00", "18:00", "21:00"]),
            "active_days": random.sample(
                ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"], 3)
        }
    }


def generate_posts_data(profile_data: Dict, profile_parser: InstagramParserV2 = None) -> List[Dict[str, Any]]:
    """Генерация данных о постах на основе реальных данных из профиля"""
    posts = []

    # Логирование входных данных
    posts_count_raw = profile_data.get("posts_count")
    print(f"🔍 DEBUG generate_posts_data:")
    print(f"  posts_count: {posts_count_raw} (type: {type(posts_count_raw)})")
    print(f"  profile_data keys: {list(profile_data.keys())}")

    # Пытаемся получить реальные посты через мобильный API
    user_id = profile_data.get("id")
    if user_id:
        try:
            # Если парсер не передан, создаем новый (для обратной совместимости)
            if profile_parser is None:
                profile_parser = get_parser()

            # Получаем реальные медиа с изображениями через мобильный API
            media_list = profile_parser.get_recent_media_mobile(user_id, count=12)
            for i, media in enumerate(media_list):
                post_id = media.get("pk", f"post_{i}")
                shortcode = media.get("shortcode")
                image_url = media.get("image_url")

                # Сохраняем изображение локально
                local_image_path = None
                if image_url and shortcode:
                    local_image_path = save_post_image(shortcode, image_url)
                    if local_image_path:
                        print(f"💾 Изображение поста сохранено: {local_image_path}")

                post = {
                    "id": post_id,
                    "shortcode": shortcode,
                    "type": "video" if media.get("is_video") else "photo",
                    "likes": random.randint(0, max(1, profile_data.get("posts_count") or 10)),
                    "comments": media.get("comment_count", random.randint(5, 100)),
                    "date": datetime.fromtimestamp(
                        media.get("taken_at_timestamp", time.time())).isoformat() if media.get(
                        "taken_at_timestamp") else (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                    "caption_length": random.randint(50, 300),
                    "thumbnail_url": local_image_path or image_url or f"https://picsum.photos/400/400?random={i}",
                    "thumbnail_url_original": image_url,  # Сохраняем оригинальный URL
                    "is_video": media.get("is_video", False),
                    "caption": f"Реальный пост {shortcode or i + 1}"
                }
                posts.append(post)

            if posts:  # Если получили реальные посты, возвращаем их
                return posts

        except Exception as e:
            print(f"⚠️ Failed to get real posts via mobile API: {e}")

    # Fallback: используем recent_media из web_profile_info
    recent_media = profile_data.get("recent_media", [])
    if recent_media:
        for i, media in enumerate(recent_media[:12]):
            post = {
                "id": media.get("id", f"post_{i}"),
                "shortcode": media.get("shortcode"),
                "type": "video" if media.get("is_video") else "photo",
                "likes": random.randint(0, max(1, profile_data.get("posts_count") or 10)),
                "comments": media.get("comment_count", random.randint(5, 100)),
                "date": datetime.fromtimestamp(media.get("taken_at_timestamp", time.time())).isoformat() if media.get(
                    "taken_at_timestamp") else (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "caption_length": random.randint(50, 300),
                "thumbnail_url": f"https://picsum.photos/400/400?random={media.get('id', i)}",
                # Используем ID для уникальности
                "is_video": media.get("is_video", False),
                "caption": f"Реальный пост {media.get('shortcode', i + 1)}"
            }
            posts.append(post)
    else:
        # Последний fallback к моковым данным
        posts_count = min(profile_data.get("posts_count") or 0, 12)
        for i in range(posts_count):
            is_video = random.choice([True, False])
            post = {
                "id": f"post_{i}",
                "type": random.choice(["photo", "video", "carousel"]),
                "likes": random.randint(0, max(1, profile_data.get("posts_count") or 10)),
                "comments": random.randint(5, 100),
                "date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "caption_length": random.randint(50, 300),
                "thumbnail_url": f"https://picsum.photos/400/400?random={i}",
                "is_video": is_video,
                "caption": f"Пост #{i + 1} - интересное содержание поста..."
            }
            posts.append(post)

    return posts


def generate_user_activities(followers_data: List[Dict], mutual_pks: List[str] = None) -> Dict[str, List[Dict]]:
    """Генерация активностей пользователей с уникальным контентом для каждой вкладки"""
    if not followers_data:
        return {
            "recent_likes": [],
            "recent_follows": [],
            "recent_comments": [],
            "recent_messages": [],
            "recent_sent_comments": []
        }

    # Используем взаимных подписчиков или случайных
    active_users = []
    if mutual_pks:
        # Фильтруем только взаимных
        active_users = [f for f in followers_data if f.get("follower_pk") in mutual_pks]

    if not active_users and followers_data:
        # Если нет взаимных, берем случайных
        sample_size = min(20, len(followers_data))
        if (sample_size or 1) > 0:
            active_users = random.sample(followers_data, sample_size)

    # Создаем копии массива пользователей для каждой вкладки с разным seed
    def get_shuffled_users(seed: int, count: int) -> List[Dict]:
        """Возвращает перемешанный список пользователей с заданным seed"""
        if not active_users:
            return []

        # Используем seed для стабильного, но разного порядка в каждой вкладке
        random_state = random.Random(seed)
        shuffled = active_users.copy()
        random_state.shuffle(shuffled)

        sample_size = min(count, len(shuffled))
        return shuffled[:sample_size]

    def create_activity(user: Dict, action: str, include_likes_count: bool = False) -> Dict:
        statuses = ["Новый!", "Сейчас", "2 мин назад", "5 мин назад", "10 мин назад", "30 мин назад"]
        activity = {
            "username": user.get("username", "unknown"),
            "full_name": user.get("full_name", ""),
            "profile_pic_url": user.get("profile_pic_url"),
            "action": action,
            "status": random.choice(statuses),
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 60))).isoformat()
        }

        # Добавляем количество лайков для активных профилей
        if include_likes_count and ("лайкает" in action or "лайкнул" in action):
            # Генерируем стабильное количество лайков на основе username
            username_hash = hash(user.get("username", "")) % 1000
            posts_count = 10  # По умолчанию
            likes_count = username_hash % (posts_count + 1)
            activity["likes_count"] = likes_count

        return activity

    # Разные действия для каждой вкладки
    likes_actions = [
        "лайкнул(-а) ваш пост",
        "лайкнул(-а) историю",
        "лайкнул(-а) комментарий",
        "лайкнул(-а) фото",
        "активность в сторис"
    ]

    follows_actions = [
        "подписался(-лась) на вас",
        "добавил(-а) в закрытые друзья",
        "просматривает профиль",
        "отметил(-а) вас в сторис",
        "сохранил(-а) в закладки"
    ]

    comments_actions = [
        "написал(-а) в переписке",
        "переписка удалена",
        "скрытая переписка",
        "архивная переписка",
        "групповая переписка"
    ]

    messages_actions = [
        "подозрительная активность",
        "скрытый просмотр",
        "анонимный просмотр",
        "множественные просмотры",
        "необычная активность"
    ]

    # Генерируем активности с уникальными пользователями для каждой вкладки
    # Используем разные seed для каждой вкладки
    likes_users = get_shuffled_users(seed=1, count=8)
    follows_users = get_shuffled_users(seed=2, count=6)
    comments_users = get_shuffled_users(seed=3, count=7)
    messages_users = get_shuffled_users(seed=4, count=5)

    # Создаем активности с разными действиями
    recent_likes = []
    for i, user in enumerate(likes_users):
        action = likes_actions[i % len(likes_actions)]
        recent_likes.append(create_activity(user, action, True))

    recent_follows = []
    for i, user in enumerate(follows_users):
        action = follows_actions[i % len(follows_actions)]
        recent_follows.append(create_activity(user, action))

    recent_comments = []
    for i, user in enumerate(comments_users):
        action = comments_actions[i % len(comments_actions)]
        recent_comments.append(create_activity(user, action))

    recent_messages = []
    for i, user in enumerate(messages_users):
        action = messages_actions[i % len(messages_actions)]
        recent_messages.append(create_activity(user, action))

    # Генерируем данные для отправленных комментариев
    sent_comments_actions = [
        "комментировал(-а) пост",
        "ответил(-а) на комментарий",
        "оставил(-а) отзыв",
        "прокомментировал(-а) историю",
        "написал(-а) под фото"
    ]

    sent_comments_users = get_shuffled_users(seed=5, count=6)
    recent_sent_comments = []
    for i, user in enumerate(sent_comments_users):
        action = sent_comments_actions[i % len(sent_comments_actions)]
        recent_sent_comments.append(create_activity(user, action))

    return {
        "recent_likes": recent_likes,
        "recent_follows": recent_follows,
        "recent_comments": recent_comments,
        "recent_messages": recent_messages,
        "recent_sent_comments": recent_sent_comments
    }


def cleanup_old_results():
    """Очистка старых результатов (старше 1 часа)"""
    cutoff = datetime.now() - timedelta(hours=1)

    with task_lock:
        to_remove = []
        for task_id, result in task_results.items():
            if result.get("created_at", datetime.now()) < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            del task_results[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old task results")


# Запускаем воркер при импорте модуля
start_worker()


# Периодическая очистка старых результатов
def periodic_cleanup():
    while True:
        time.sleep(3600)  # Каждый час
        cleanup_old_results()


cleanup_thread = Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()
