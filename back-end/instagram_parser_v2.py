"""
Новая система парсинга Instagram на основе test.py
С асинхронной обработкой, очередью и кэшированием
"""

import json
import random
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import requests
from sqlalchemy.orm import Session
from image_storage import (
    save_profile_avatar,
    save_post_image,
    save_follower_avatar,
    batch_save_images
)

from apppiiii_client import api_client
from asyncRequests.loggingAsync import logger

# Конфигурация
IG_APP_ID = "936619743392459"
QUERY_HASH_FOLLOWERS = "c76146de99bb02f6415203be841dd25a"
QUERY_HASH_FOLLOWINGS = "d04b0a864b4b54837c0d870b0e77e076"

# server
#USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6133.0 Safari/537.36"

# Настройки парсинга - увеличенные лимиты для стабильности
BASE_DELAY = 15.0  # Увеличена задержка между запросами
TIMEOUT = 55      # Увеличен таймаут
MAX_RETRIES = 5   # Больше попыток при ошибках
PAGE_SIZE = 25    # Уменьшен размер страницы для меньшей нагрузки
MAX_FOLLOWERS = 50   # Уменьшено количество подписчиков
MAX_FOLLOWINGS = 50  # Уменьшено количество подписок

import json
def print_json(data):
    print(json.dumps(data, indent=4))

class InstagramParserV2:
    """Новый парсер Instagram на основе test.py"""

    def __init__(self):
        logger.info("Инициализация InstagramParserV2")
        self.async_session = api_client

    def _get_aiohttp_cookies(self, cookie_str: str) -> dict:
        """Установка куки из строки"""
        dict_cookie = {}
        for part in cookie_str.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            dict_cookie.update({key:value})
        return dict_cookie

    def _get_headers(self, user_agent: str) -> dict:
        """
        Устанавливаем User-Agent привязанный к cookie
        return: dict с установленный User-Agent в headers
        """
        return {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": IG_APP_ID,
        }


    async def _request(self, method: str, url: str, **kwargs) -> dict:
        """Выполнение запроса с retry логикой"""
        # Для тестов не оборачиваем в try except
        logger.info(f"Request method: {method} URL: {url} kwargs: {kwargs}")
        cookie, user_agent = cookie_rotator.get_next_cookie()

        # Default
        cookie_aihttp = self._get_aiohttp_cookies(cookie)
        headers = self._get_headers(user_agent)

        if 'user_agent' in kwargs:
            headers = self._get_headers(kwargs['user_agent'])

        if 'headers' in kwargs:
            # Проверяем, есть ли там User-Agent, если да, считаем, что это mobile proxy заголовки и заменяем headers,
            # иначе добавляем их в текущие headers
            if kwargs['headers'].get('User-Agent'):
                headers = kwargs['headers']
            else:
                headers.update(kwargs['headers'])

        if 'cookie' in kwargs:
            cookie_aihttp = self._get_aiohttp_cookies(kwargs['cookie'])

        print_json(cookie_aihttp)
        print_json(headers)

        #proxy = "http://MTAbvU:k5AU8L@77.73.133.79:8000"
        response = await api_client.request(
            method=method,
            full_url=url,
            headers=headers,
            cookies=cookie_aihttp,
        )

        return response

    async def get_profile(self, username: str) -> Dict[str, Any]:
        """Получение базовой информации профиля"""
        logger.debug("Получение базовой информации профиля")
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {"Referer": f"https://www.instagram.com/{username}/"}

        resp = await self._request("GET", url, headers=headers)
        data = resp.get("data", {}).get("user", {})

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

    async def _get_user_list(self, user_id: str, query_hash: str, max_count: int = 0) -> List[Dict]:
        """Получение списка подписчиков или подписок через GraphQL"""
        logger.debug("Получение списка подписчиков или подписок через GraphQL")
        collected = []
        after = None
        has_next_page = True
        fetched = 0

        # Получаем cookie
        cookie, user_agent = cookie_rotator.get_next_cookie()
        cookie_aihttp = self._get_aiohttp_cookies(cookie)
        csrf_token = cookie_aihttp.get("csrftoken", "missing")
        logger.info(f'LOG Check csrf_token: {csrf_token}')
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
            resp = await self._request("GET", url, headers=headers, cookie=cookie, user_agent=user_agent)
            data = resp

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

    async def get_followers(self, user_id: str, max_count: int = MAX_FOLLOWERS) -> List[Dict]:
        """Получение подписчиков"""
        logger.debug("Получение подписчиков")
        return await self._get_user_list(user_id, QUERY_HASH_FOLLOWERS, max_count)

    async def get_followings(self, user_id: str, max_count: int = MAX_FOLLOWINGS) -> List[Dict]:
        """Получение подписок"""
        logger.debug("Получение подписок")
        return await self._get_user_list(user_id, QUERY_HASH_FOLLOWINGS, max_count)

    def find_mutual_followers(self, followers: List[Dict], followings: List[Dict]) -> List[Dict]:
        """Поиск взаимных подписок"""
        logger.debug("Поиск взаимных подписок")
        followers_by_id = {f["follower_pk"]: f for f in followers if f.get("follower_pk")}
        mutuals = []

        for following in followings:
            following_id = following.get("follower_pk")
            if following_id and following_id in followers_by_id:
                # Объединяем данные из обоих списков
                mutual = followers_by_id[following_id].copy()
                mutuals.append(mutual)

        return mutuals


    def _mobile_headers(self) -> dict:
        """Заголовки для мобильного API"""
        logger.debug("Заголовки для мобильного API")
        cookie, user_agent = cookie_rotator.get_next_cookie()
        cookie_aihttp = self._get_aiohttp_cookies(cookie)
        csrf = cookie_aihttp.get("csrftoken", "missing")
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

    async def get_recent_media_mobile(self, user_id: str, count: int = 12) -> List[Dict]:
        """Получение недавних медиа через мобильный API"""
        logger.debug("Получение недавних медиа через мобильный API")
        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/?count={max(1, min(50, count))}"
        headers = self._mobile_headers()

        try:
            response = await self._request("GET", url, headers=headers)
            items = response.get("items") or []

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

    async def get_comments_for_media(self, media_ref: str, limit: int = 2, post_shortcode: Optional[str] = None) -> List[Dict]:
        """Получение комментариев для медиа"""
        logger.debug("Получение комментариев для медиа")
        media_pk = None
        if str(media_ref).isdigit():
            media_pk = str(media_ref)
        else:
            try:
                url_sc = f"https://i.instagram.com/api/v1/media/shortcode/{media_ref}/"
                resp_sc = await self._request("GET", url_sc, headers=self._mobile_headers())
                j_sc = resp_sc
                media_pk = str(j_sc.get("items", [{}])[0].get("pk") or j_sc.get("media", {}).get("pk") or "")
            except Exception as e:
                print(f"⚠️ Shortcode resolve failed for {media_ref}: {e}")
                return []

        if not media_pk:
            return []

        async def _norm(j, post_url=None):
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
            resp = await self._request("GET", url_i, headers=self._mobile_headers())
            j = resp
            out = await _norm(j, post_url)
            if out:
                return out
        except Exception as e:
            logger.warning(f"⚠️ Mobile comments failed: {e}")

        # Fallback к веб API
        try:
            url_w = f"https://www.instagram.com/api/v1/media/{media_pk}/comments/?can_support_threading=true&permalink_enabled=true&count={count}"
            headers_w = self._mobile_headers()
            headers_w["Referer"] = f"https://www.instagram.com/p/{media_ref}/" if not str(media_ref).isdigit() else "https://www.instagram.com/"
            resp2 = await self._request("GET", url_w, headers=headers_w)
            j2 = resp2
            return await _norm(j2, post_url)
        except Exception as e:
            logger.warning(f"⚠️ Web comments failed: {e}")
            return []

    def get_comments_fallback_instagrapi(self, shortcode: str, limit: int = 2) -> List[Dict]:
        """Fallback с использованием instagrapi как в test.py"""
        logger.debug("Fallback с использованием instagrapi как в test.py")
        try:
            # Извлекаем sessionid из куков текущей сессии парсера
            sessionid = None
            # Просто получаем куки
            cookies_str = cookie_rotator.get_next_cookie()

            for part in cookies_str.split(';'):
                part = part.strip()
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
            logger.warning(f"⚠️ instagrapi fallback failed: {e}")
            return []

    async def collect_comments(self, username: str) -> List[Dict]:
        """Сбор комментариев из недавних постов (до 5 шт)"""
        logger.debug("Сбор комментариев из недавних постов (до 5 шт)")
        comments: List[Dict] = []
        try:
            # 1) Брали несуществующий метод + неправильный ключ. Исправляем:
            profile = await self.get_profile(username)
            user_id = profile.get("id")          # было "user_id"
            if not user_id:
                print(f"⚠️ User ID not found for {username}")
                return []

            print(f"🔍 Collecting comments for @{username} (ID: {user_id})")

            # 2) Берем недавние медиа через мобильный feed
            try:
                media_list = await self.get_recent_media_mobile(user_id, count=12)
                print(f"📱 Found {len(media_list)} media items via mobile feed")
            except Exception as e:
                print(f"⚠️ Mobile feed failed, fallback to web media list: {e}")
                # fallback к web_profile_info
                web_profile = await self.get_profile(username)
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
                cmts = await self.get_comments_for_media(
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
from parser_config import get_parser_config, ParserConfig

USE_INSTAGRAPI_FALLBACK = True

class CookieRotator:
    """Ротация cookies для балансировки нагрузки с динамической конфигурацией"""
    def __init__(self):
        self.current_index = 0

    def get_user_agent(self, cookie: str, user_agent_list: list, config_obj: ParserConfig) -> str:
        """
        Получить User-Agent для cookie

        Если у cookie не привязан User-Agent, то мы привязываем, и сохраняем в parser_config.json
        """

        # Получение ds_user_id
        ds_user_id = ''
        for part in cookie.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key == "ds_user_id":
                ds_user_id = value
                break
        # Получение User-Agent
        user_agent = ''
        for agent in user_agent_list:
            if ds_user_id == agent.get("ds_user_id", None):
                user_agent = agent.get("userAgent")
                break
        # Если не установлен User-Agent
        if not user_agent:
            for agent in user_agent_list:
                if agent.get("ds_user_id", None) == '':
                    user_agent = agent.get("userAgent")
                    agent['ds_user_id'] = ds_user_id
                    break
            # Обновляем json конфигурацию с новым привязанным User-Agent
            config_obj.update_user_agent(user_agent_list)

        return user_agent


    def get_next_cookie(self) -> tuple[str, str]:
        """
        Получить следующий cookie из пула (round-robin) и User_agent

        return: tuple(cookie, User-Agent
        """
        # Получаем актуальный список cookies из конфигурации
        config = get_parser_config()
        cookies_pool = config.get_cookies()
        list_user_agent = config.get_user_agent()

        if not cookies_pool:
            raise ValueError("Cookie pool is empty! Add cookies in admin panel.")

        cookie = cookies_pool[self.current_index]
        self.current_index = (self.current_index + 1) % len(cookies_pool)
        user_agent = self.get_user_agent(cookie, list_user_agent, config)

        logger.info(f"🔄 Using cookie #{self.current_index + 1}/{len(cookies_pool)}")
        return cookie, user_agent

# Глобальный ротатор куков
cookie_rotator = CookieRotator()

def get_parser() -> InstagramParserV2:
    """Получить новый парсер с следующим cookie из пула"""
    return InstagramParserV2()

def get_parser_timings() -> dict:
    """Получить актуальные тайминги из конфигурации"""
    config = get_parser_config()
    return config.get_timings()


async def scrape_profile_basic(username: str) -> Dict[str, Any]:
    """Получение базовой информации профиля (aсинхронно)"""
    try:
        # Используем ротацию cookies для снижения нагрузки
        profile_parser = get_parser()
        profile_data = await profile_parser.get_profile(username)
        
        print(f"🔍 DEBUG scrape_profile_basic - profile_data type: {type(profile_data)}")
        print(f"🔍 DEBUG scrape_profile_basic - profile_data keys: {list(profile_data.keys()) if isinstance(profile_data, dict) else 'NOT A DICT'}")
        
        # Генерируем фиктивную аналитику
        analytics_data = generate_analytics(profile_data)
        posts_data = await generate_posts_data(profile_data, profile_parser)
        
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
        logger.error(f"Profile scraping failed for {username}: {e} \n error_trace: {error_trace}")
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
            "active_days": random.sample(["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"], 3)
        }
    }


async def generate_posts_data(profile_data: Dict, profile_parser: InstagramParserV2 = None) -> List[Dict[str, Any]]:
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
            media_list = await profile_parser.get_recent_media_mobile(user_id, count=12)
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
                    "date": datetime.fromtimestamp(media.get("taken_at_timestamp", time.time())).isoformat() if media.get("taken_at_timestamp") else (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                    "caption_length": random.randint(50, 300),
                    "thumbnail_url": local_image_path or image_url or f"https://picsum.photos/400/400?random={i}",
                    "thumbnail_url_original": image_url,  # Сохраняем оригинальный URL
                    "is_video": media.get("is_video", False),
                    "caption": f"Реальный пост {shortcode or i+1}"
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
                "date": datetime.fromtimestamp(media.get("taken_at_timestamp", time.time())).isoformat() if media.get("taken_at_timestamp") else (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "caption_length": random.randint(50, 300),
                "thumbnail_url": f"https://picsum.photos/400/400?random={media.get('id', i)}",  # Используем ID для уникальности
                "is_video": media.get("is_video", False),
                "caption": f"Реальный пост {media.get('shortcode', i+1)}"
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
                "caption": f"Пост #{i+1} - интересное содержание поста..."
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


