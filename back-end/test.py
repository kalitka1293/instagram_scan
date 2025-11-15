#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram profile scraper (followers, followings & mutuals)

⚠️ Disclaimer: Unofficial use. Respect Instagram ToS and local laws. Use on public data or with permission.

Features
- Fetch basic profile info via web_profile_info
- Fetch full followers & followings via GraphQL pagination
- Computes mutuals (users who are both followers and followings)
- Saves results to JSON/CSV
- Collects up to 2 comments from posts (recent or specified shortcodes)
"""

import json
import os
import sys
import time
import csv
import random
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

# ---------------- Configuration ----------------
USERNAME = "pashtetussus"  # target username
COOKIES = 'ps_n=1;datr=rtIlaJE9NVQ7vv-ihz_02H0J;ds_user_id=76134626580;csrftoken=spDVV1JW6Skut7V06HBnUMwqZZtcUypD;oo=v1;ig_did=48306C4A-3AEE-4701-AB3D-64A1015CEF4E;ps_l=1;wd=572x738;mid=aCXSrgALAAFHm-jClbK9Ggq97I1P;sessionid=76134626580%3A8E9BLvBBDc65gc%3A26%3AAYcEOYJ_erBhamMc49Y6OAQWDcLWW6QCINmIhPaApQ;dpr=1.25;rur="LDC\05476134626580\0541788469773:01fef74168ab3abde326607bec4057d1cd6d229591847d5b898a339bfaae53a2a3b92d80"'  # put your cookies here
SAVE_DIR = "out"
BASE_DELAY = 2.5
TIMEOUT = 30
MAX_RETRIES = 5
PAGE_SIZE = 50
MAX_FOLLOWERS = 0  # 0 = all
MAX_FOLLOWINGS = 0  # 0 = all
TARGET_POST_SHORTCODES: List[str] = []  # empty = try recent posts
# Optional: if web API returns 0 comments, try instagrapi fallback using sessionid from cookies
USE_INSTAGRAPI_FALLBACK = True

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
)
IG_APP_ID = "936619743392459"
QUERY_HASH_FOLLOWERS = "c76146de99bb02f6415203be841dd25a"
QUERY_HASH_FOLLOWINGS = "d04b0a864b4b54837c0d870b0e77e076"

# ---------------- Helpers ----------------
class RateLimiter:
    def __init__(self, base_delay: float):
        self.base_delay = max(0.0, base_delay)

    def sleep(self):
        jitter = random.uniform(0, self.base_delay * 0.3)
        time.sleep(self.base_delay + jitter)


def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    jar = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            jar[k.strip()] = v.strip()
    return jar


class InstaScraper:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": IG_APP_ID,
        })
        if COOKIES:
            cookie_dict = parse_cookie_string(COOKIES)
            for k, v in cookie_dict.items():
                self.s.cookies.set(k, v, domain=".instagram.com")
        self.timeout = TIMEOUT
        self.max_retries = MAX_RETRIES
        self.rl = RateLimiter(BASE_DELAY)

    def _mobile_headers(self):
        csrf = self.s.cookies.get("csrftoken") or "missing"
        # Some setups require the claim header; '0' works as a neutral value in many cases
        return {
            "User-Agent": MOBILE_UA,
            "Accept": "*/*",
            "Referer": "https://www.instagram.com/",
            "X-IG-App-ID": IG_APP_ID,
            "X-ASBD-ID": "129477",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrf,
            "X-IG-WWW-Claim": "0",
        }

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.s.request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code in (200, 201):
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(min(60, 2 ** attempt))
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_exc = e
                time.sleep(min(30, 1.5 * attempt))
        if last_exc:
            raise last_exc
        raise RuntimeError("Failed request")

    def get_profile(self, username: str) -> Dict:
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {"Referer": f"https://www.instagram.com/{username}/"}
        resp = self._request("GET", url, headers=headers)
        data = resp.json().get("data", {}).get("user", {})
        profile = {
            "id": data.get("id"),
            "username": data.get("username"),
            "full_name": data.get("full_name"),
            "is_private": data.get("is_private"),
            "is_verified": data.get("is_verified"),
            "followers": (data.get("edge_followed_by") or {}).get("count"),
            "followings": (data.get("edge_follow") or {}).get("count"),
        }
        # collect recent media for comments (best-effort, may be empty)
        media_edges = (data.get("edge_owner_to_timeline_media") or {}).get("edges") or []
        profile["recent_media"] = [{"id": n.get("id"), "shortcode": n.get("shortcode")} for e in media_edges for n in [e.get("node", {})]]
        return profile

    def _graphql_edges(self, user_id: str, query_hash: str, first: int = 50, max_count: int = 0) -> List[Dict]:
        collected = []
        after = None
        has_next_page = True
        csrf = self.s.cookies.get("csrftoken") or "missing"
        headers = {"Referer": "https://www.instagram.com/", "X-CSRFToken": csrf}

        while has_next_page:
            variables = {"id": str(user_id), "first": first}
            if after:
                variables["after"] = after
            params = {"query_hash": query_hash, "variables": json.dumps(variables)}
            url = f"https://www.instagram.com/graphql/query/?{urlencode(params)}"
            resp = self._request("GET", url, headers=headers)
            j = resp.json()
            edge_key = "edge_followed_by" if query_hash == QUERY_HASH_FOLLOWERS else "edge_follow"
            edges = j["data"]["user"][edge_key]["edges"]
            page_info = j["data"]["user"][edge_key]["page_info"]
            for e in edges:
                node = e.get("node", {})
                collected.append({"id": node.get("id"), "username": node.get("username")})
                if max_count and len(collected) >= max_count:
                    return collected
            has_next_page = page_info.get("has_next_page")
            after = page_info.get("end_cursor")
            if has_next_page:
                self.rl.sleep()
        return collected

    def get_followers(self, user_id: str, max_count: int = 0):
        return self._graphql_edges(user_id, QUERY_HASH_FOLLOWERS, first=PAGE_SIZE, max_count=max_count)

    def get_followings(self, user_id: str, max_count: int = 0):
        return self._graphql_edges(user_id, QUERY_HASH_FOLLOWINGS, first=PAGE_SIZE, max_count=max_count)

    # -------- recent media via mobile feed (more reliable) --------
    def get_recent_media_mobile(self, user_id: str, count: int = 12) -> List[Dict]:
        """Fetch recent media using mobile feed endpoint; returns list of dicts with pk and shortcode.
        Requires valid session cookies.
        """
        url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/?count={max(1, min(50, count))}"
        resp = self._request("GET", url, headers=self._mobile_headers())
        j = resp.json()
        items = j.get("items") or []
        out = []
        for it in items:
            pk = str(it.get("pk") or "")
            code = it.get("code") or it.get("shortcode") or ""
            disabled = bool(it.get("comments_disabled") or it.get("commenting_disabled"))
            comment_count = int(it.get("comment_count") or 0)
            out.append({"pk": pk, "shortcode": code, "comments_disabled": disabled, "comment_count": comment_count})
        return out

    def get_comments_for_media(self, media_ref: str, limit: int = 2, post_shortcode: Optional[str] = None) -> List[Dict]:
        """Fetch up to N comments via web API. media_ref can be pk or shortcode.
        Returns [] on failure; caller may try fallback.
        """
        # Resolve shortcode -> pk if needed
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
                sys.stderr.write(f"[warn] shortcode resolve failed for {media_ref}: {e}")
                media_pk = None
        if not media_pk:
            return []

        def _norm(j):
            items = j.get("comments") or j.get("items") or []
            out = []
            post_url = f"https://www.instagram.com/p/{post_shortcode}/" if post_shortcode else None
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
                if len(out) >= limit:
                    break
            return out

        count = max(1, min(50, limit))
        # Try mobile (i.instagram.com)
        try:
            url_i = f"https://i.instagram.com/api/v1/media/{media_pk}/comments/?can_support_threading=true&permalink_enabled=true&count={count}"
            resp = self._request("GET", url_i, headers=self._mobile_headers())
            j = resp.json()
            out = _norm(j)
            if out:
                return out
        except Exception as e:
            sys.stderr.write(f"[warn] i.instagram comments failed: {e}")

        # Fallback to www host
        try:
            url_w = f"https://www.instagram.com/api/v1/media/{media_pk}/comments/?can_support_threading=true&permalink_enabled=true&count={count}"
            headers_w = self._mobile_headers()
            headers_w["Referer"] = f"https://www.instagram.com/p/{media_ref}/" if not str(media_ref).isdigit() else "https://www.instagram.com/"
            resp2 = self._request("GET", url_w, headers=headers_w)
            j2 = resp2.json()
            out2 = _norm(j2)
            return out2
        except Exception as e:
            sys.stderr.write(f"[warn] www.instagram comments failed: {e}")
            return []

    def get_comments_fallback_instagrapi(self, shortcode: str, limit: int = 2) -> List[Dict]:
        """Optional fallback using instagrapi when web API yields 0 comments.
        Requires `pip install instagrapi` and a valid sessionid in COOKIES.
        """
        if not USE_INSTAGRAPI_FALLBACK:
            return []
        # extract sessionid from COOKIES
        sessionid = None
        for part in COOKIES.split(';'):
            part = part.strip()
            if part.startswith('sessionid='):
                sessionid = part.split('=',1)[1]
                break
        if not sessionid or sessionid == 'YOUR_SESSIONID':
            return []
        try:
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
                if len(out) >= limit:
                    break
            return out
        except Exception as e:
            sys.stderr.write(f"[warn] instagrapi fallback failed: {e}")
            return []

    def collect_two_comments(self, username: str, shortcodes: Optional[List[str]] = None) -> List[Dict]:
        profile = self.get_profile(username)
        comments: List[Dict] = []
        # Prefer mobile feed for pk (more reliable for comments)
        user_id = profile.get("id")
        media_list = []
        try:
            media_list = self.get_recent_media_mobile(user_id, count=12)
        except Exception as e:
            sys.stderr.write(f"[warn] mobile feed failed, fallback to web media list: {e}")
            # Fallback to web_profile_info media
            media_list = [{"pk": None, "shortcode": m.get("shortcode"), "comments_disabled": False, "comment_count": None} for m in (profile.get("recent_media") or [])]

        # If explicit shortcodes provided, put them first
        codes = (shortcodes[:] if shortcodes else [])
        if codes:
            media_list = ([{"pk": None, "shortcode": c, "comments_disabled": False, "comment_count": None} for c in codes] + media_list)

        for m in media_list:
            if len(comments) >= 2:
                break
            if m.get("comments_disabled"):
                continue
            # We try by pk if present, else by shortcode
            ref = m.get("pk") or m.get("shortcode")
            if not ref:
                continue
            cmts = self.get_comments_for_media(ref, limit=2 - len(comments), post_shortcode=m.get("shortcode"))
            if not cmts and USE_INSTAGRAPI_FALLBACK and m.get("shortcode"):
                cmts = self.get_comments_fallback_instagrapi(m.get("shortcode"), limit=2 - len(comments))
            comments.extend(cmts)
            if len(comments) < 2:
                self.rl.sleep()
        return comments

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(path: str, rows: List[Dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def compute_mutuals(followers: List[Dict], followings: List[Dict]) -> List[Dict]:
    by_id = {u["id"]: u for u in followers}
    return [u for u in followings if u.get("id") in by_id]


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    scraper = InstaScraper()
    profile = scraper.get_profile(USERNAME)
    print(json.dumps(profile, indent=2))

    uid = profile.get("id")
    followers = scraper.get_followers(uid, MAX_FOLLOWERS)
    followings = scraper.get_followings(uid, MAX_FOLLOWINGS)
    mutuals = compute_mutuals(followers, followings)
    comments = scraper.collect_two_comments(USERNAME)

    base = os.path.join(SAVE_DIR, USERNAME)
    save_json(base + "_profile.json", profile)
    save_json(base + "_followers.json", followers)
    save_csv(base + "_followers.csv", followers)
    save_json(base + "_followings.json", followings)
    save_csv(base + "_followings.csv", followings)
    save_json(base + "_mutuals.json", mutuals)
    save_csv(base + "_mutuals.csv", mutuals)
    save_json(base + "_comments.json", comments)
    save_csv(base + "_comments.csv", comments)

    print(f"Done. Followers: {len(followers)} | Followings: {len(followings)} | Mutuals: {len(mutuals)} | Comments: {len(comments)}")


if __name__ == "__main__":
    main()
