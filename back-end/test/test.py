"""
Система парсинга Cat Facts на основе архитектуры Instagram парсера
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
from threading import Thread, Lock
from queue import Queue, Empty
import logging

# Настройка логирования
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

import os

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ["NO_PROXY"] = "*"

# Конфигурация
CAT_FACTS_API_URL = "https://catfact.ninja/facts"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Настройки парсинга
BASE_DELAY = 2.0  # Меньшая задержка для открытого API
TIMEOUT = 30
MAX_RETRIES = 3
MAX_FACTS = 100  # Максимальное количество фактов для сбора

# Глобальная очередь задач
cat_task_queue = Queue()
cat_task_results = {}  # {task_id: result}
cat_task_lock = Lock()
cat_worker_thread = None


class CatFactsRateLimiter:
    """Управление задержками между запросами для Cat Facts API"""

    def __init__(self, base_delay: float):
        self.base_delay = max(0.0, base_delay)

    def sleep(self):
        jitter = random.uniform(0, self.base_delay * 0.3)
        total_delay = self.base_delay + jitter
        logger.info(f"Cat Facts rate limiting: sleeping for {total_delay:.1f}s")
        time.sleep(total_delay)


class CatFactsParser:
    """Парсер для Cat Facts API"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })
        # self.session.proxies = {
        #     'http': 'http://46M2W2:0pdJpr@103.78.191.198:8000',
        #     'https': 'http://46M2W2:0pdJpr@103.78.191.198:8000'
        # }
        self.timeout = TIMEOUT
        self.max_retries = MAX_RETRIES
        self.rate_limiter = CatFactsRateLimiter(BASE_DELAY)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Выполнение запроса с retry логикой"""
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Making request to {url} (attempt {attempt}/{self.max_retries})")
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)

                if resp.status_code in (200, 201):
                    return resp

                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = min(30, 2 ** attempt) + random.uniform(0, 2.0)
                    logger.warning(
                        f"Status {resp.status_code} on {url}. Waiting {wait:.1f}s (attempt {attempt}/{self.max_retries})")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp

            except requests.RequestException as e:
                last_exc = e
                wait = min(15, 1.5 * attempt) + random.uniform(0, 1.0)
                logger.warning(f"Request exception: {e}. Retry in {wait:.1f}s (attempt {attempt}/{self.max_retries})")
                time.sleep(wait)

        if last_exc:
            raise last_exc
        raise RuntimeError("Failed request with unknown error")

    def get_cat_facts(self, max_facts: int = MAX_FACTS) -> Dict[str, Any]:
        """Получение фактов о котах"""
        all_facts = []
        current_page = 1
        has_more = True

        params = {
            "limit": 100,  # Максимум на страницу
            "max_length": 100
        }

        while has_more and len(all_facts) < max_facts:
            try:
                params["page"] = current_page
                logger.info(f"Fetching cat facts page {current_page}")

                resp = self._request("GET", CAT_FACTS_API_URL, params=params)
                data = resp.json()

                facts = data.get("data", [])
                if not facts:
                    logger.info("No more facts available")
                    break

                # Добавляем факты в общий список
                for fact in facts:
                    if len(all_facts) < max_facts:
                        all_facts.append({
                            "fact": fact.get("fact", ""),
                            "length": fact.get("length", 0),
                            "source": "catfact.ninja",
                            "collected_at": datetime.now().isoformat()
                        })
                    else:
                        break

                # Проверяем есть ли следующая страница
                has_more = data.get("current_page", 0) < data.get("last_page", 0)
                current_page += 1

                # Задержка между запросами для соблюдения rate limits
                if has_more and len(all_facts) < max_facts:
                    self.rate_limiter.sleep()

            except Exception as e:
                logger.error(f"Error fetching page {current_page}: {e}")
                break

        return {
            "success": True,
            "total_facts": len(all_facts),
            "facts": all_facts,
            "collected_at": datetime.now().isoformat(),
            "source": CAT_FACTS_API_URL
        }

    def get_facts_with_analysis(self, max_facts: int = MAX_FACTS) -> Dict[str, Any]:
        """Получение фактов с дополнительным анализом"""
        raw_data = self.get_cat_facts(max_facts)

        if not raw_data["success"] or not raw_data["facts"]:
            return raw_data

        facts = raw_data["facts"]

        # Анализ собранных фактов
        total_length = sum(fact.get("length", 0) for fact in facts)
        avg_length = total_length / len(facts) if facts else 0

        # Группировка по длине
        short_facts = [f for f in facts if f.get("length", 0) < 50]
        medium_facts = [f for f in facts if 50 <= f.get("length", 0) < 100]
        long_facts = [f for f in facts if f.get("length", 0) >= 100]

        # Поиск самых интересных фактов (основано на ключевых словах)
        interesting_keywords = ['amazing', 'interesting', 'surprising', 'unusual', 'unique']
        interesting_facts = []

        for fact in facts:
            fact_text = fact.get("fact", "").lower()
            if any(keyword in fact_text for keyword in interesting_keywords):
                interesting_facts.append(fact)

        # Добавляем аналитику к результатам
        raw_data["analysis"] = {
            "total_facts_analyzed": len(facts),
            "average_fact_length": round(avg_length, 2),
            "length_distribution": {
                "short": len(short_facts),
                "medium": len(medium_facts),
                "long": len(long_facts)
            },
            "interesting_facts_count": len(interesting_facts),
            "interesting_facts": interesting_facts[:5]  # Топ-5 интересных фактов
        }

        return raw_data


class CatFactsTask:
    """Задача парсинга Cat Facts"""

    def __init__(self, task_id: str, max_facts: int = MAX_FACTS, with_analysis: bool = True):
        self.task_id = task_id
        self.max_facts = max_facts
        self.with_analysis = with_analysis
        self.created_at = datetime.now()


def cat_facts_worker():
    """Воркер для обработки очереди парсинга Cat Facts"""
    while True:
        try:
            task = cat_task_queue.get(timeout=5)
            if task is None:  # Сигнал остановки
                break

            logger.info(f"Processing cat facts task {task.task_id}")

            try:
                # Создаем парсер и получаем данные
                parser = CatFactsParser()

                if task.with_analysis:
                    result = parser.get_facts_with_analysis(task.max_facts)
                else:
                    result = parser.get_cat_facts(task.max_facts)

                # Сохраняем результат
                with cat_task_lock:
                    cat_task_results[task.task_id] = {
                        "status": "completed",
                        "result": result,
                        "created_at": task.created_at,
                        "completed_at": datetime.now(),
                        "task_type": "cat_facts",
                        "max_facts": task.max_facts,
                        "with_analysis": task.with_analysis
                    }

                logger.info(f"Cat facts task {task.task_id} completed. Facts collected: {result.get('total_facts', 0)}")

            except Exception as e:
                logger.error(f"Cat facts task {task.task_id} failed: {e}")

                with cat_task_lock:
                    cat_task_results[task.task_id] = {
                        "status": "failed",
                        "error": str(e),
                        "created_at": task.created_at,
                        "completed_at": datetime.now(),
                        "task_type": "cat_facts"
                    }

            cat_task_queue.task_done()

        except Empty:
            continue
        except Exception as e:
            logger.error(f"Cat facts worker error: {e}")


def start_cat_facts_worker():
    """Запуск воркера Cat Facts в отдельном потоке"""
    global cat_worker_thread
    if cat_worker_thread is None or not cat_worker_thread.is_alive():
        cat_worker_thread = Thread(target=cat_facts_worker, daemon=True)
        cat_worker_thread.start()
        logger.info("Cat Facts parser worker started")


def stop_cat_facts_worker():
    """Остановка воркера Cat Facts"""
    cat_task_queue.put(None)
    if cat_worker_thread:
        cat_worker_thread.join(timeout=5)


def generate_cat_facts_task_id() -> str:
    """Генерация уникального ID задачи для Cat Facts"""
    return f"cat_facts_{int(time.time() * 1000)}"


def add_cat_facts_task(max_facts: int = MAX_FACTS, with_analysis: bool = True) -> str:
    """Добавление задачи парсинга Cat Facts в очередь"""
    task_id = generate_cat_facts_task_id()
    task = CatFactsTask(task_id, max_facts, with_analysis)

    # Инициализируем статус
    with cat_task_lock:
        cat_task_results[task_id] = {
            "status": "pending",
            "created_at": datetime.now(),
            "task_type": "cat_facts",
            "max_facts": max_facts,
            "with_analysis": with_analysis
        }

    cat_task_queue.put(task)
    logger.info(f"Added cat facts task {task_id} for {max_facts} facts")
    return task_id


def get_cat_facts_task_status(task_id: str) -> Dict[str, Any]:
    """Получение статуса задачи Cat Facts"""
    with cat_task_lock:
        return cat_task_results.get(task_id, {"status": "not_found"})


def get_cat_facts_queue_status() -> Dict[str, Any]:
    """Получить статус очереди Cat Facts"""
    with cat_task_lock:
        # Задачи в очереди
        pending_tasks = []
        temp_queue = Queue()

        queue_count = cat_task_queue.qsize()

        for _ in range(queue_count):
            try:
                task = cat_task_queue.get_nowait()
                pending_tasks.append({
                    "task_id": task.task_id,
                    "max_facts": task.max_facts,
                    "with_analysis": task.with_analysis,
                    "created_at": task.created_at.isoformat()
                })
                temp_queue.put(task)
            except Empty:
                break

        # Возвращаем задачи обратно
        while not temp_queue.empty():
            cat_task_queue.put(temp_queue.get())

        # Активные и завершенные задачи
        processing_tasks = []
        completed_tasks = []
        failed_tasks = []

        for task_id, result in cat_task_results.items():
            if result.get("task_type") != "cat_facts":
                continue

            task_info = {
                "task_id": task_id,
                "status": result.get("status"),
                "max_facts": result.get("max_facts"),
                "with_analysis": result.get("with_analysis"),
                "created_at": result.get("created_at").isoformat() if result.get("created_at") else None,
                "completed_at": result.get("completed_at").isoformat() if result.get("completed_at") else None
            }

            if result.get("status") == "processing":
                processing_tasks.append(task_info)
            elif result.get("status") == "completed":
                completed_tasks.append(task_info)
            elif result.get("status") == "failed":
                failed_tasks.append(task_info)

        return {
            "queue_summary": {
                "pending_in_queue": queue_count,
                "processing": len(processing_tasks),
                "completed": len(completed_tasks),
                "failed": len(failed_tasks),
                "total_tasks": len([r for r in cat_task_results.values() if r.get("task_type") == "cat_facts"])
            },
            "pending_tasks": pending_tasks,
            "processing_tasks": processing_tasks,
            "recent_completed": completed_tasks[-10:],
            "recent_failed": failed_tasks[-5:],
            "worker_status": {
                "is_alive": cat_worker_thread.is_alive() if cat_worker_thread else False,
                "queue_size": cat_task_queue.qsize()
            }
        }




def cleanup_old_cat_facts_results():
    """Очистка старых результатов Cat Facts (старше 1 часа)"""
    cutoff = datetime.now() - timedelta(hours=1)

    with cat_task_lock:
        to_remove = []
        for task_id, result in cat_task_results.items():
            if result.get("created_at", datetime.now()) < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            del cat_task_results[task_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old cat facts task results")


# Периодическая очистка старых результатов
def cat_facts_periodic_cleanup():
    while True:
        time.sleep(3600)  # Каждый час
        cleanup_old_cat_facts_results()


cat_facts_cleanup_thread = Thread(target=cat_facts_periodic_cleanup, daemon=True)
cat_facts_cleanup_thread.start()

# Запускаем воркер при импорте модуля
start_cat_facts_worker()

import time
import threading
from datetime import datetime
import requests

def test_queued_requests(count: int) -> dict:
    """Тест запросов через очередь задач"""
    task_ids = []

    # Добавляем все задачи в очередь
    for i in range(count):
        task_id = add_cat_facts_task(max_facts=100, with_analysis=False)
        task_ids.append(task_id)

        if (i + 1) % 10 == 0:
            print(f"   Добавлено в очередь: {i + 1}/{count} задач")

    print("Ожидание завершения задач")

    # Ожидаем завершения всех задач
    completed_tasks = 0
    failed_tasks = 0
    facts_collected = 0

    while task_ids:
        for task_id in task_ids[:]:  # Копируем список для безопасного удаления
            status = get_cat_facts_task_status(task_id)

            if status["status"] == "completed":
                completed_tasks += 1
                result = status.get("result", {})
                facts_collected += result.get("total_facts", 0)
                task_ids.remove(task_id)

            elif status["status"] == "failed":
                failed_tasks += 1
                task_ids.remove(task_id)

        # # Прогресс
        # if completed_tasks + failed_tasks < count:
        #     progress = (completed_tasks + failed_tasks) / count * 100
        #     print(f"   Прогресс: {completed_tasks + failed_tasks}/{count} ({progress:.1f}%)")
        #     time.sleep(2)  # Проверяем статус каждые 2 секунды

    return {
        "successful": completed_tasks,
        "failed": failed_tasks,
        "total_facts": facts_collected
    }


def run_performance_test():
    print("Создание 100 запросов и измерение времени выполнения")
    print("=" * 60)
    test_queued_requests(100)




if __name__ == "__main__":
    import time
    start= time.monotonic()
    run_performance_test()
    print("END: ", time.monotonic() - start)





