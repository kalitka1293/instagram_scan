import aiohttp
import asyncio
import time
import logging
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, asdict
from functools import wraps
import json
import random
import sys
import os
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asyncRequests', 'ProxyManager')
config_path_2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'asyncRequests', 'loggingAsync')
sys.path.append(os.path.dirname(config_path))
sys.path.append(os.path.dirname(config_path_2))
from ProxyManager import proxy_manager
from loggingAsync import logger


#Датакласс для хранения метрик работы запросов
@dataclass
class APIMetrics:
    total_requests: int = 0 # Общее кол-во запросов
    successful_requests: int = 0 # Кол успеш запросов
    failed_requests: int = 0 # Кол неуспешных запросов
    circuit_breaker_trips: int = 0 # Кол-во срабатываний автоматических выключений
    session_refreshes: int = 0 # кол пересозданий сессий
    parallel_requests_sent: int =0 # Общее кол-во отправленных параллельных запросов
    fastest_wins: int =0 # кол-во срабатываний стратегий "самый быстрый ответ" то есть на 1 запрос пользователя, делается несколько запросов
    cancelled_requests: int = 0 # Отмененные запросы
    last_reset: float = 0 # Время когда сбросились метрики в последний раз

    def success_rate(self) -> float:
        """
        Определяем кол-во успешных запросов от общего количества
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def should_reset(self, window_seconds: int = 3600) -> bool:
        """
        Проверяем необходимо ли сбросить метрики
        """
        return time.time() - self.last_reset > window_seconds

    def reset(self) -> None:
        """
        Сброс метрик
        """
        for field in self.__dataclass_fields__:
            if field not in ['last_reset']:
                setattr(self, field, 0)
        self.last_reset = time.time()


class CircuitBreakerError(Exception):
    pass

class CircuitBreaker:
    """
    Класс для защиты от деградироваших API
    Защита API от перегрузки
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold # Кол-во ошибок для блокировки
        self.recovery_timeout = recovery_timeout # Время "остывания" для попытки восстановления
        self.failures: int = 0 # Кол-во неудачных попыток
        self.state: str = 'CLOSED' # текущее состояние: CLOSED (работает), OPEN (блокировка), HALF_OPEN (тестирование)
        self.last_failure_time: Optional[float] = None # Последнее время ошибки
        self._lock = asyncio.Lock() # Предотвращение параллельных изменений состояния и защита от thundering herd problem

    async def execute(self, func, *args, **kwargs) -> any:
        async with self._lock:
            current_time = time.time()
            if self.state == 'OPEN':
                # Проверяем время последней ошибки, при состоянии OPEN(Закрыт)
                # Если время уже больше self.recovery_timeout после последней ошибки, переходим в состояния проверки HALF_OPEN
                if current_time - self.last_failure_time > self.recovery_timeout:
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self.state = "HALF_OPEN"
                else: # Эту часть протестировать, при каких случаях появляется ошибка и что за ней идет
                    # Ошибка необходима в декораторе для определения того, что circuit breaker в данный момент в состоянии OPEN
                    raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            logger.error(e, exc_info=True)
            await self._on_failure(current_time, e)
            raise

    async def _on_success(self) -> None:
        """
        Обработка успешного запроса
        Сбрасываем счетчик неуспешных запросов и если state стоит
          в состоянии HALF_OPEN меняем на CLOSED
        """
        async with self._lock:
            self.failures = 0
            if self.state == 'HALF_OPEN':
                logger.info("Circuit breaker transitioning to CLOSED")
                self.state = "CLOSED"

    async def _on_failure(self, timestamp, error: Exception) -> None:
        """
        Обработка НЕуспешного запроса
        Проверяем сколько было неудачных запросов
        Если превышает трешхолд мы блокируем запросы для "остывания
        """
        async with self._lock:
            self.failures += 1
            self.last_failure_time = timestamp

            if self.failures >= self.failure_threshold or self.state == 'HALF_OPEN':
                logger.warning(f"Circuit breaker opening after {self.failures} failures\nWith error {error}")
                self.state = 'OPEN'


# def retry_with_backoff(
#         max_retries: int = 2, # кол-во максимальных попыток Если стоит значение 2 значит всего 3 запроса (1 оригинал + 2 повторных)
#         initial_delay: float = 0.1, # Начальная задержка
#         max_delay: float = 2.0, # Максимальная задержка между повторными запросами
#         exponential_base: float = 2.0 # основание экспоненты для увеличения задержки
# ):
#     """
#     Декоратор для создания стратегии повторных попыток
#     """
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             delay = initial_delay
#             last_exception = None # Переделать в список чтобы собирать все ошибки
#
#             for attempt in range(max_retries + 1):
#                 try:
#                     return await func(*args, **kwargs)
#                 except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
#                     last_exception = e
#
#                     if attempt == max_retries:
#                         break
#
#                     if hasattr(e, 'status') and getattr(e, 'status', None) == 429:
#                         # Обработка превышения лимита запросов, (дописать обработку, чтобы убрать на остывание прокси и куки)
#                         logger.warning("Rate limit hit, not retrying")
#                         break
#
#                     if isinstance(e, CircuitBreakerError): # Правильно обработать ошибку
#                         break
#
#                     # Создаем минимальную задержку для предотвращения "эффекта толпы" запросов
#                     jitter = random.uniform(0.1, 0.5)
#                     actual_delay = delay + jitter
#                     logger.debug(f"Attempt {attempt + 1} failed, retrying in {actual_delay:.2f} sec. \n{e}")
#
#                     await asyncio.sleep(actual_delay)
#
#                     # Поиграть со значением max_delay
#                     delay = min(delay * exponential_base, max_delay)
#                 # Срабатывание ошибки при отмены запросов или закрытия клиента, мы вызываем ошибку для управления потоком
#                 except asyncio.CancelledError:
#                     logger.warning("Request was cancelled during retry")
#                     raise
#                 except Exception as e:
#                     logger.warning(f"!!!!!!!!!!!!!!!!!!!!!!!!\nUnexpected exception in retry: {e}\n!!!!!!!!!!!!!!!!!!!!!!!!")
#                     last_exception = e
#                     break
#
#             if last_exception:
#                 raise last_exception
#             else:
#                 Exception("All retry attempts failed")
#         return wrapper
#     return decorator

class ResilientAPIClient:
    """
    Основной класс для отправки асинхронных запросов с помощью aiohttp для получения данных
    С логикой retry backoff и Circuit breaker
    """
    def __init__(
            self,
            max_concurrent: int = 10, # Максимальное кол-во соединений к API
            request_timeout: int = 60, # Общий таймаут
            metrics_window: int = 3600,
            max_parallel_requests: int = 3 # Кол-во максимальных параллельных запросов на один логический запрос
    ):
        self.max_concurrent = max_concurrent
        self.request_timeout = request_timeout
        self.metrics_window = metrics_window
        self.max_parallel_requests = max_parallel_requests

        self.session: Optional[aiohttp.ClientSession] = None # Объект ClientSession
        self.global_semaphore = asyncio.Semaphore(max_concurrent) # Объект
        self._session_lock = asyncio.Lock() # Зашита запросов от гонки данных
        self.metrics = APIMetrics(last_reset=time.time()) # Сбор метрик
        self.circuit_breaker = CircuitBreaker() # Защита API от перегрузки
        self._metrics_lock = asyncio.Lock() # защита операций с метриками
        self._active_tasks: set[asyncio.Task] = set() # Хранение активных задач
        self._closing = False # Флаг что клиент открыт\закрыт

    async def _ensure_session(self) -> None:
        """
        Функция для гарантированного создания сессии и предотвращения одновременных созданий сессий
        """
        if self._closing:
            raise RuntimeError("Client is closing")

        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    await self._create_session()

    async def _create_session(self) -> None:
        """Полное Создание сессии aiohttp"""
        if self._closing:
            raise RuntimeError("Cannot create session while closing")

        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.max_concurrent, # думаю логичнее установить кол-во такое, сколько есть прокси
            keepalive_timeout=15, # Время которое соединение будет еще открытым, для повторного использования
            enable_cleanup_closed=True, # Заставляет aiohttp  удалять "мертвые" запросы
            use_dns_cache=True, # Хранение кэша DNS
            ttl_dns_cache=300, # Время хранения кэша DNS
            force_close=False # False не закрывать TCP-соединение после ответа
        )

        # Необходимо поиграть с настройками соединения как раз для повторных запросов
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout, # Общий таймаут
            connect=300, # Макс. выделенное время на установление TCP соединение
            sock_read=800, # Макс. время на чтение данных из сокета
            sock_connect=300 # Макс. время установление TCP соединения, для прокси
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={ # Скорее всего headers будем добавлять в зависимости от прокси
                'User-Agent': 'ResilientAPIClient/1.0',
                'Accept': 'application/json'
            }
        )

        # Увеличиваем кол-во пересозданных сессий
        async with self._metrics_lock:
            self.metrics.session_refreshes += 1

        logger.info("Create new session")

    async def _close_current_session(self) -> None:
        """Безопасное закрытие сессии"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                await asyncio.sleep(0.3) # Даем время закрыть сессию
            except Exception as e:
                logger.warning(f"Error closing session {e}", exc_info=True)


    async def _refresh_session(self, error: Optional[Exception] = None) -> bool:
        """Пересоздание сессии aiohttp"""
        if self._closing:
            return False

        async with self._metrics_lock:
            if self.metrics.should_reset(self.metrics_window):
                self.metrics.reset() # Необходимо для всегда получения свежих метрик
            current_success_rate = self.metrics.success_rate()

        # Логирование во время разработки
        if error:
            logger.warning(error)

        # Решаем обновлять сессию или нет, на основе кол-ва успешных запросов и на основе ошибок, которых мы получили
        should_refresh = (                             #сервер неожиданно разорвал соединение  не может уст. соед. с сервером     ошибка операционной системы
            current_success_rate < 0.7 or isinstance(error, (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectorError, aiohttp.ClientOSError))
        )
        if should_refresh:
            async with self._session_lock:
                async with self._metrics_lock:
                    current_success_rate = self.metrics.success_rate()
                # Делаем повторную проверку
                refresh_condition = (
                        current_success_rate < 0.7 or
                        isinstance(error, (
                                        aiohttp.ServerDisconnectedError,
                                        aiohttp.ClientConnectorError,
                                        aiohttp.ClientOSError
                        ))
                )
                if refresh_condition:
                    logger.warning("Refreshing session due to errors")
                    await self._close_current_session()
                    try:
                        await self._create_session()
                        return True
                    except RuntimeError:
                        logger.error("Failed to create new session - client is closed")
                        return False

        return False

    def _track_task(self, task: asyncio.Task) -> None:
        """Отслеживание активных задач"""
        self._active_tasks.add(task) # Добавляем в set список
        task.add_done_callback(self._active_tasks.discard) # Добавляем функцию в каллбак когда задача удет завершена

    async def _safe_cancel_tasks(self, tasks: List[asyncio.Task]) -> None:
        """Безопасное завершение задач"""
        # Отменяем задачи
        for task in tasks:
            if not task.done():
                task.cancel()

        # Ожидаем завершение задач парралельно на случай ошибок
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Error during task cancellation: {e}")

    async def _make_single_request(
            self,
            method: str,
            endpoint: str, # У эндпоинта убираем последний слэш
            **kwargs
    ) -> Union[Dict[str, Any], str, bytes]:
        """Выполнение одного HTTP запроса"""
        # проверка что сессия создана
        await self._ensure_session()

        if self._closing:
            raise RuntimeError("Client is closing")
        if not self.session or self.session.closed:
            raise RuntimeError("Session is not available")

        url = endpoint.lstrip('/') # У эндпоинта убираем последний слэш

        # Используем Semaphore для контроля кол-ва одновременных соединений
        async with self.global_semaphore:
            try:
                # proxies, cookie, user_agent = proxy_manager.get_proxy_resource()
                # print(proxy_manager.get_stats())
                # print(proxies, kwargs)
                async with self.session.request(method, url, **kwargs) as response:
                    print('>>>', response.headers)
                    if response.status >= 500:
                        raise aiohttp.ClientResponseError(
                            status=response.status,
                            message=f"Server error with status code {response.status}",
                            request_info=response.request_info,
                            history=response.history # Последовательность ответов если происходило перенаправление
                        )
                    # Ошибка если превышено ограничение запросов к API
                    elif response.status == 429:
                        raise aiohttp.ClientResponseError(
                            status=response.status,
                            message=f"Rate limit exceeded {response.status}",
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

                    # Должны именно здесь читать данные, пока не закрылось соединение
                    # Обработка контента
                    content_type = response.headers.get('Content-Type', '').lower()

                    if 'application/json' in content_type:
                        try:
                            return await response.json()
                        except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                            text = await response.text()
                            logger.warning(f"JSON decode error, failing back to text: {e} data: {text} url:{url}")
                            return {"raw": text, "status": response.status}
                    if 'text/' in content_type:
                        data = await response.text()
                        logger.warning(f'Пришли данные типа "content_type=text": {data} url:{url}')
                        return data
                    else:
                        # Если мы получили неожиданное значение возвращаем хоть что то
                        data = await response.read()
                        logger.warning(f'Пришли данные типа "content_type=text": {data} url:{url}')
                        return data

            except (aiohttp.ServerDisconnectedError, aiohttp.ClientConnectorError, aiohttp.ClientOSError) as e:
                logger.warning(f"Connection Error: {e}")
                raise
            except asyncio.TimeoutError as e:
                logger.warning(f"Request Timeout: {e}")
                raise
            except aiohttp.ClientPayloadError as e:
                logger.warning(f"Payload Error: {e}")
                raise
            except Exception as e:
                logger.warning(f"!!!!!!!!! An unexpected error occurred: {e} !!!!!!")
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
        # На всякий случай только один запрос
        if num_parallel <= 1:
            return await self._make_single_request(method, endpoint, **kwargs)

        # Расчитываем время ожидания перед запуском первого запроса
        # Посмотреть стоит ли увеличивать таймаут или вообще вынести в отдельную переменную как таймаут для этой функции
        individual_timeout = self.request_timeout / (num_parallel + 1)
        print("individual_timeout", individual_timeout)

        tasks = []

        try:
            # Запускаем первый запрос
            task1 = asyncio.create_task(
                self._make_single_request(method, endpoint, **kwargs)
            )
            self._track_task(task1)
            tasks.append(task1)

            async with self._metrics_lock:
                self.metrics.parallel_requests_sent += 1

            # Ожидание ответа от первого запроса
            first_wait_time = time.time()
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=individual_timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    # Если запрос завершен
                    if not task.cancelled():
                        try:
                            result = await task
                            await self._safe_cancel_tasks([t for t in tasks if t != task])
                            async with self._metrics_lock:
                                self.metrics.fastest_wins += 1
                            return result
                        except Exception:
                            pass # Если первый пришел с ошибок, ошибку не обрабатываем тк есть еще 2 запроса
            except asyncio.TimeoutError:
                # Если произошел таймаут так же продолжаем
                pass

            # вычисляем оставшееся время
            elapsed_time = time.time() - first_wait_time
            remaining_time_after_first = self.request_timeout - elapsed_time
            print("remaining_time_after_first",remaining_time_after_first)
            # Проверяем осталось ли время для оставшихся запросов
            if remaining_time_after_first <= 0:
                await self._safe_cancel_tasks(tasks)
                raise asyncio.TimeoutError("request timeout after first attempt")

            # Запускаем второй запрос
            task2 = asyncio.create_task(
                self._make_single_request(method, endpoint, **kwargs)
            )
            self._track_task(task2)
            tasks.append(task2)

            async with self._metrics_lock:
                self.metrics.parallel_requests_sent += 1

            # Теперь ждем ответа от двух запросов
            second_wait_start = time.time()
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=min(individual_timeout, remaining_time_after_first),
                    return_when=asyncio.FIRST_COMPLETED
                )
                # Проверяем результаты двух запросов
                for task in done:
                    # Если запрос завершен
                    if not task.cancelled():
                        try:
                            result = await task
                            await self._safe_cancel_tasks([t for t in tasks if t != task])
                            async with self._metrics_lock:
                                self.metrics.fastest_wins += 1
                            return result
                        except Exception:
                            pass  # Если первый пришел с ошибок, ошибку не обрабатываем тк есть еще 2 запроса
            except asyncio.TimeoutError:
                # Если произошел таймаут так же продолжаем
                pass

            # Вычисляем оставшееся время для третьего этапа
            elapsed_time += time.time() - second_wait_start
            remaining_time_after_second = self.request_timeout - elapsed_time

            # Если время вышло, отменяем все и выходим
            if remaining_time_after_second <= 0:
                await self._safe_cancel_tasks(tasks)
                raise asyncio.TimeoutError("Request timeout after second attempt")

            #Запускаем третий запрос
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
                                result = await task
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

            # проверяем все задачи на успешный результат
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
                        result = await task
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
                        task.result()
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
            full_url: str,
            num_parallel_requests: Optional[int] = None,
            **kwargs
    ) -> aiohttp.ClientResponse:
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
                full_url,
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
            refresh_task = asyncio.create_task(self._refresh_session(e))
            self._track_task(refresh_task)

            # Детальное логирование
            if isinstance(e, aiohttp.ClientResponseError):
                if e.status == 429:
                    logger.warning(f"Rate limit hit for {full_url}: {e}")
                elif e.status >= 500:
                    logger.error(f"Server error {e.status} for {full_url}: {e}")
                else:
                    logger.warning(f"Client error {e.status} for {full_url}: {e}")
            elif isinstance(e, asyncio.CancelledError):
                logger.info(f"Request to {full_url} was cancelled")
            elif isinstance(e, asyncio.TimeoutError):
                logger.warning(f"Request to {full_url} timed out")
            else:
                logger.error(f"Request to {full_url} failed: {e}")

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




















