from database import SessionLocal
import crud
from asyncRequests.loggingAsync import logger
from instagram_parser_v2 import get_parser
import asyncio
import random
from image_storage import batch_save_images

"""
Основная часть работы по парсингу данных
"""

async def async_work_parsing(username: str, user_id):
    db = SessionLocal()

    try:
        # Обновляем статус в БД
        crud.update_profile_parsing_status(db, username, "processing")
        task_parser = get_parser()

        followers = await task_parser.get_followers(user_id)
        await asyncio.sleep(random.random())
        followings = await task_parser.get_followings(user_id)
        await asyncio.sleep(random.random())
        mutuals = task_parser.find_mutual_followers(followers, followings)

        # Собираем комментарии
        comments = task_parser.collect_comments(username)

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
        profile = crud.get_instagram_profile_by_username(db, username)
        if profile and mutuals:
            crud.save_instagram_followers(db, profile.id, mutuals)

        # Сохраняем комментарии в профиль
        if profile and comments:
            profile.comments_data = comments
            db.commit()

        # Обновляем статус парсинга
        crud.update_profile_parsing_status(db, username, "completed")

        logger.info(
            f"Task completed. Followers: {len(followers)}, Followings: {len(followings)}, Mutuals: {len(mutuals)}")
    except Exception as e:
        logger.error(f"Task failed: {e}")
        crud.update_profile_parsing_status(db, username, "failed")
    finally:
        db.close()