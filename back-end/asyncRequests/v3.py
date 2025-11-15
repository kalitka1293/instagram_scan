import aiohttp
import asyncio
import time
import logging
from typing import Optional, Dict, Any, Union, List
from functools import wraps
from dataclasses import dataclass, asdict
import json
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class APIMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_breaker_trips: int = 0
    session_refreshes: int = 0
    parallel_requests_sent: int = 0
    fastest_wins: int = 0
    cancelled_requests: int = 0
    last_reset: float = 0

    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def should_reset(self, window_seconds: int = 3600) -> bool:
        return time.time() - self.last_reset > window_seconds

    def reset(self):
        for field in self.__dataclass_fields__:
            if field not in ['last_reset']:
                setattr(self, field, 0)
        self.last_reset = time.time()


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def execute(self, func, *args, **kwargs):
        async with self._lock:
            current_time = time.time()

            if self.state == "OPEN":
                if current_time - self.last_failure_time > self.recovery_timeout:
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(current_time, e)
            raise

    async def _on_success(self):
        async with self._lock:
            self.failures = 0
            if self.state == "HALF_OPEN":
                logger.info("Circuit breaker transitioning to CLOSED")
                self.state = "CLOSED"

    async def _on_failure(self, timestamp: float, error: Exception):
        async with self._lock:
            self.failures += 1
            self.last_failure_time = timestamp

            if self.failures >= self.failure_threshold or self.state == "HALF_OPEN":
                logger.warning(f"Circuit breaker opening after {self.failures} failures")
                self.state = "OPEN"
                self.failures = 0


class CircuitBreakerError(Exception):
    pass


def retry_with_backoff(
        max_retries: int = 2,
        initial_delay: float = 0.1,
        max_delay: float = 2.0,
        exponential_base: float = 2.0
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    if hasattr(e, 'status') and getattr(e, 'status', None) == 429:
                        logger.warning("Rate limit hit, not retrying")
                        break
                    if isinstance(e, CircuitBreakerError):
                        break

                    jitter = random.uniform(0.1, 0.3)
                    actual_delay = delay + jitter
                    logger.debug(f"Attempt {attempt + 1} failed, retrying in {actual_delay:.2f}s: {e}")

                    await asyncio.sleep(actual_delay)
                    delay = min(delay * exponential_base, max_delay)
                except asyncio.CancelledError:
                    logger.warning("Request was cancelled during retry")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected exception in retry: {e}")
                    last_exception = e
                    break

            if last_exception:
                raise last_exception
            else:
                raise Exception("All retry attempts failed")

        return wrapper

    return decorator


class ResilientAPIClient:
    def __init__(
            self,
            base_url: str,
            max_concurrent: int = 10,
            request_timeout: int = 10,
            metrics_window: int = 3600,
            max_parallel_requests: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.max_concurrent = max_concurrent
        self.request_timeout = request_timeout
        self.metrics_window = metrics_window
        self.max_parallel_requests = max_parallel_requests

        self.session: Optional[aiohttp.ClientSession] = None
        self.global_semaphore = asyncio.Semaphore(max_concurrent)
        self.circuit_breaker = CircuitBreaker()
        self.metrics = APIMetrics(last_reset=time.time())
        self._session_lock = asyncio.Lock()
        self._closing = False
        self._active_tasks: set[asyncio.Task] = set()
        self._metrics_lock = asyncio.Lock()

    async def _ensure_session(self):
        """Гарантирует создание сессии"""
        if self._closing:
            raise RuntimeError("Client is closing")

        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    await self._create_session()

    async def _create_session(self):
        """Создание сессии с оптимальными настройками"""
        if self._closing:
            raise RuntimeError("Cannot create session while closing")

        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.max_concurrent,
            keepalive_timeout=15,
            enable_cleanup_closed=True,
            use_dns_cache=True,
            ttl_dns_cache=300,
            force_close=False
        )

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout,
            connect=3,
            sock_read=8,
            sock_connect=3
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'ResilientAPIClient/1.0',
                'Accept': 'application/json'
            }
        )

        async with self._metrics_lock:
            self.metrics.session_refreshes += 1

        logger.info("Created new session")

    async def _close_current_session(self):
        """Безопасное закрытие сессии"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                await asyncio.sleep(0.1)  # Короткая пауза для cleanup
            except Exception as e:
                logger.error(f"Error closing session: {e}")

    async def _refresh_session_if_needed(self, error: Optional[Exception] = None) -> bool:
        """Обновление сессии при необходимости"""
        if self._closing:
            return False

        async with self._metrics_lock:
            if self.metrics.should_reset(self.metrics_window):
                self.metrics.reset()
            current_success_rate = self.metrics.success_rate()

        should_refresh = (
                current_success_rate < 0.7 or
                isinstance(error, (
                    aiohttp.ServerDisconnectedError,
                    aiohttp.ClientConnectorError,
                    aiohttp.ClientOSError
                ))
        )

        if should_refresh:
            async with self._session_lock:
                # Двойная проверка внутри блокировки
                async with self._metrics_lock:
                    current_success_rate = self.metrics.success_rate()

                refresh_condition = (
                        current_success_rate < 0.7 or
                        isinstance(error, (
                            aiohttp.ServerDisconnectedError,
                            aiohttp.ClientConnectorError,
                            aiohttp.ClientOSError
                        ))
                )

                if refresh_condition:
                    logger.info("Refreshing session due to errors")
                    await self._close_current_session()
                    try:
                        await self._create_session()
                        return True
                    except RuntimeError:
                        logger.error("Failed to create new session - client is closing")
                        return False

        return False

    def _track_task(self, task: asyncio.Task):
        """Отслеживание активных задач"""
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _safe_cancel_tasks(self, tasks: List[asyncio.Task]):
        """Безопасная отмена задач"""
        # Сначала отменяем все задачи
        for task in tasks:
            if not task.done():
                task.cancel()

        # Затем ждем их завершения параллельно
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.debug(f"Error during task cancellation: {e}")

    async def _make_single_request(
            self,
            method: str,
            endpoint: str,
            **kwargs
    ) -> Union[Dict[str, Any], str, bytes]:
        """Выполнение одного HTTP запроса"""
        await self._ensure_session()

        if self._closing:
            raise RuntimeError("Client is closing")
        if not self.session or self.session.closed:
            raise RuntimeError("Session is not available")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with self.global_semaphore:
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    # Обработка HTTP статусов
                    if response.status >= 500:
                        raise aiohttp.ClientResponseError(
                            status=response.status,
                            message=f"Server error {response.status}",
                            request_info=response.request_info,
                            history=response.history
                        )
                    elif response.status == 429:
                        raise aiohttp.ClientResponseError(
                            status=429,
                            message="Rate limit exceeded",
                            request_info=response.request_info,
                            history=response.history
                        )
                    elif response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            status=response.status,
                            message=f"Client error {response.status}",
                            request_info=response.request_info,
                            history=response.history
                        )

                    # Обработка контента
                    content_type = response.headers.get('Content-Type', '').lower()

                    if 'application/json' in content_type:
                        try:
                            return await response.json()
                        except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                            logger.warning(f"JSON decode error, falling back to text: {e}")
                            text = await response.text()
                            return {'raw_text': text, 'status': response.status}
                    elif 'text/' in content_type:
                        return await response.text()
                    else:
                        return await response.read()

            except (aiohttp.ServerDisconnectedError,
                    aiohttp.ClientConnectorError,
                    aiohttp.ClientOSError) as e:
                logger.warning(f"Connection error: {e}")
                raise
            except asyncio.TimeoutError:
                logger.warning("Request timeout")
                raise
            except aiohttp.ClientPayloadError as e:
                logger.error(f"Payload error: {e}")
                raise

    async def _execute_parallel_requests(
            self,
            method: str,
            endpoint: str,
            num_parallel: int,
            **kwargs
    ) -> Union[Dict[str, Any], str, bytes]:
        """
        Параллельные запросы с последовательным запуском:
        - Сначала один запрос
        - Если нет ответа за время ожидания - запускаем второй
        - Если все еще нет ответа - запускаем третий
        - Ждем ответа от всех запущенных запросов
        """
        if num_parallel <= 1:
            return await self._make_single_request(method, endpoint, **kwargs)

        # Рассчитываем время ожидания перед запуском следующего запроса
        individual_timeout = self.request_timeout / (num_parallel + 1)

        tasks = []

        try:
            # ШАГ 1: Запускаем первый запрос
            task1 = asyncio.create_task(
                self._make_single_request(method, endpoint, **kwargs)
            )
            self._track_task(task1)
            tasks.append(task1)

            async with self._metrics_lock:
                self.metrics.parallel_requests_sent += 1

            # Ждем ответа от первого запроса
            first_wait_start = time.time()
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=individual_timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Проверяем результат первого запроса
                for task in done:
                    if not task.cancelled():
                        try:
                            result = task.result()
                            # Первый запрос успешен - отменяем остальные и возвращаем результат
                            await self._safe_cancel_tasks([t for t in tasks if t != task])

                            async with self._metrics_lock:
                                self.metrics.fastest_wins += 1
                            return result
                        except Exception:
                            # Первый запрос завершился с ошибкой, продолжаем
                            pass
            except asyncio.TimeoutError:
                # Таймаут первого ожидания - продолжаем
                pass

            # Вычисляем оставшееся время для следующих этапов
            elapsed_time = time.time() - first_wait_start
            remaining_time_after_first = self.request_timeout - elapsed_time

            # Если время вышло, отменяем все и выходим
            if remaining_time_after_first <= 0:
                await self._safe_cancel_tasks(tasks)
                raise asyncio.TimeoutError("Request timeout after first attempt")

            # ШАГ 2: Запускаем второй запрос
            task2 = asyncio.create_task(
                self._make_single_request(method, endpoint, **kwargs)
            )
            self._track_task(task2)
            tasks.append(task2)

            async with self._metrics_lock:
                self.metrics.parallel_requests_sent += 1

            # Ждем ответа от любого из двух запросов
            second_wait_start = time.time()
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=min(individual_timeout, remaining_time_after_first),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Проверяем результаты двух запросов
                for task in done:
                    if not task.cancelled():
                        try:
                            result = task.result()
                            # Нашли успешный ответ - отменяем остальные
                            await self._safe_cancel_tasks([t for t in tasks if t != task])

                            async with self._metrics_lock:
                                self.metrics.fastest_wins += 1
                            return result
                        except Exception:
                            # Запрос завершился с ошибкой, продолжаем
                            pass
            except asyncio.TimeoutError:
                # Таймаут второго ожидания - продолжаем
                pass

            # Вычисляем оставшееся время для третьего этапа
            elapsed_time += time.time() - second_wait_start
            remaining_time_after_second = self.request_timeout - elapsed_time

            # Если время вышло, отменяем все и выходим
            if remaining_time_after_second <= 0:
                await self._safe_cancel_tasks(tasks)
                raise asyncio.TimeoutError("Request timeout after second attempt")

            # ШАГ 3: Запускаем третий запрос (если разрешено и есть время)
            if num_parallel >= 3 and remaining_time_after_second > 0:
                task3 = asyncio.create_task(
                    self._make_single_request(method, endpoint, **kwargs)
                )
                self._track_task(task3)
                tasks.append(task3)

                async with self._metrics_lock:
                    self.metrics.parallel_requests_sent += 1

                # Ждем ответа от любого из трех запросов
                try:
                    done, pending = await asyncio.wait(
                        tasks,
                        timeout=remaining_time_after_second,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Проверяем результаты всех запросов
                    for task in done:
                        if not task.cancelled():
                            try:
                                result = task.result()
                                # Нашли успешный ответ - отменяем остальные
                                await self._safe_cancel_tasks([t for t in tasks if t != task])

                                async with self._metrics_lock:
                                    self.metrics.fastest_wins += 1
                                return result
                            except Exception:
                                # Запрос завершился с ошибкой, продолжаем собирать ошибки
                                pass
                except asyncio.TimeoutError:
                    # Таймаут третьего ожидания - продолжаем сбор ошибок
                    pass

            # ДАЕМ ПОСЛЕДНИЙ ШАНС: проверяем все задачи на успешный результат
            successful_result = None
            exceptions = []

            # Сначала даем короткое время для завершения всех задач
            if tasks:
                try:
                    done, pending = await asyncio.wait(
                        tasks,
                        timeout=min(0.5, remaining_time_after_second),
                        return_when=asyncio.ALL_COMPLETED
                    )
                except asyncio.TimeoutError:
                    # Игнорируем - переходим к проверке завершенных задач
                    pass

            # Проверяем все задачи на успешный результат
            for task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        successful_result = result
                        break
                    except Exception as e:
                        exceptions.append(e)

            # Если нашли успешный результат
            if successful_result is not None:
                await self._safe_cancel_tasks([t for t in tasks if t != task])

                async with self._metrics_lock:
                    self.metrics.fastest_wins += 1
                return successful_result

            # Отменяем все оставшиеся задачи
            await self._safe_cancel_tasks(tasks)

            # Если успешных результатов нет, собираем все исключения
            for task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        task.result()  # Должно вызвать исключение
                    except Exception as e:
                        if e not in exceptions:
                            exceptions.append(e)

            # Выбираем наиболее информативную ошибку
            if exceptions:
                best_error = exceptions[0]
                for exc in exceptions[1:]:
                    if isinstance(exc, aiohttp.ClientResponseError):
                        best_error = exc
                        break
                raise best_error
            else:
                raise asyncio.TimeoutError(f"All {len(tasks)} requests timed out or were cancelled")

        except asyncio.CancelledError:
            # Отменяем все задачи при отмене родительской
            await self._safe_cancel_tasks(tasks)
            async with self._metrics_lock:
                self.metrics.cancelled_requests += 1
            raise

    def _calculate_parallel_requests(self) -> int:
        """Расчет количества параллельных запросов на основе нагрузки"""
        try:
            available_slots = self.global_semaphore._value
            if available_slots <= 2:  # Оставляем запас
                return 1

            load_factor = 1 - (available_slots / self.max_concurrent)

            if load_factor < 0.3:
                return self.max_parallel_requests
            elif load_factor < 0.6:
                return max(2, self.max_parallel_requests - 1)
            else:
                return 1
        except Exception:
            return 1

    async def request(
            self,
            method: str,
            endpoint: str,
            num_parallel_requests: Optional[int] = None,
            **kwargs
    ) -> Union[Dict[str, Any], str, bytes]:
        """Основной метод для выполнения запросов"""
        if self._closing:
            raise RuntimeError("Client is closing and cannot accept new requests")

        await self._ensure_session()

        # Определяем количество параллельных запросов
        if num_parallel_requests is None:
            num_parallel_requests = self._calculate_parallel_requests()
        else:
            num_parallel_requests = min(
                max(1, num_parallel_requests),
                self.max_parallel_requests
            )

        async with self._metrics_lock:
            self.metrics.total_requests += 1

        try:
            # Выполняем через Circuit Breaker
            result = await self.circuit_breaker.execute(
                self._execute_parallel_requests,
                method,
                endpoint,
                num_parallel_requests,
                **kwargs
            )

            async with self._metrics_lock:
                self.metrics.successful_requests += 1
            return result

        except Exception as e:
            async with self._metrics_lock:
                self.metrics.failed_requests += 1

            # Асинхронно обновляем сессию при необходимости
            refresh_task = asyncio.create_task(self._refresh_session_if_needed(e))
            self._track_task(refresh_task)

            # Детальное логирование
            if isinstance(e, aiohttp.ClientResponseError):
                if e.status == 429:
                    logger.warning(f"Rate limit hit for {endpoint}: {e}")
                elif e.status >= 500:
                    logger.error(f"Server error {e.status} for {endpoint}: {e}")
                else:
                    logger.warning(f"Client error {e.status} for {endpoint}: {e}")
            elif isinstance(e, asyncio.CancelledError):
                logger.info(f"Request to {endpoint} was cancelled")
            elif isinstance(e, asyncio.TimeoutError):
                logger.warning(f"Request to {endpoint} timed out")
            else:
                logger.error(f"Request to {endpoint} failed: {e}")

            raise

    async def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик"""
        async with self._metrics_lock:
            metrics_dict = asdict(self.metrics)
            metrics_dict['success_rate'] = self.metrics.success_rate()
            metrics_dict['circuit_breaker_state'] = self.circuit_breaker.state

            # Безопасное получение информации о семафоре
            try:
                available_slots = self.global_semaphore._value
                metrics_dict['available_slots'] = available_slots
                metrics_dict['current_load'] = self.max_concurrent - available_slots
            except Exception:
                metrics_dict['available_slots'] = 0
                metrics_dict['current_load'] = self.max_concurrent

            metrics_dict['max_parallel_requests'] = self.max_parallel_requests
            metrics_dict['active_tasks_count'] = len(self._active_tasks)

            # Информация о соединениях
            if self.session and not self.session.closed:
                try:
                    connector = self.session.connector
                    if hasattr(connector, '_conns'):
                        metrics_dict['active_connections'] = len(connector._conns)
                    else:
                        metrics_dict['active_connections'] = 0
                except Exception:
                    metrics_dict['active_connections'] = 0
            else:
                metrics_dict['active_connections'] = 0

            return metrics_dict

    async def close(self):
        """Корректное закрытие клиента"""
        if self._closing:
            return

        self._closing = True
        logger.info("Closing API client...")

        # Отменяем все активные задачи
        if self._active_tasks:
            logger.info(f"Cancelling {len(self._active_tasks)} active tasks")
            tasks_to_cancel = list(self._active_tasks)
            await self._safe_cancel_tasks(tasks_to_cancel)

        # Закрываем сессию
        await self._close_current_session()

        logger.info("API client closed successfully")

    async def __aenter__(self):
        if self._closing:
            raise RuntimeError("Cannot use closed client as context manager")
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Пример использования
async def main():
    async with ResilientAPIClient(
            base_url="https://catfact.ninja",
            max_concurrent=10,
            request_timeout=30,
            max_parallel_requests=3
    ) as client:
        try:
            # Первый запрос
            result1 = await client.request("GET", "/facts")
            print("Факты о котах:", result1)

            # Второй запрос
            result2 = await client.request("GET", "/fact")
            print("Случайный факт:", result2)

            # Метрики
            metrics = await client.get_metrics()
            print("Метрики:", metrics)

        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())