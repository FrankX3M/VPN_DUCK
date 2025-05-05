import os
import sys
import time
import requests
import logging
import functools
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    Retrying
)
# Добавляем текущую директорию в PYTHONPATH
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.errors import RemoteServerError, DatabaseError

logger = logging.getLogger('wireguard-proxy.retry')

def with_retry(max_attempts=3, min_wait=1, max_wait=10, 
               exceptions=(RemoteServerError, DatabaseError, requests.RequestException),
               retry_on_result=None):
    """
    Декоратор для выполнения функции с повторными попытками при возникновении ошибки
    
    Args:
        max_attempts (int): Максимальное количество попыток
        min_wait (int): Минимальное время ожидания между попытками в секундах
        max_wait (int): Максимальное время ожидания между попытками в секундах
        exceptions (tuple): Типы исключений, при которых нужно повторять попытки
        retry_on_result (callable): Функция для проверки результата, возвращает True для повтора
        
    Returns:
        Декоратор для применения к функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    result = func(*args, **kwargs)
                    
                    # Проверка результата, если указана функция retry_on_result
                    if retry_on_result is not None and retry_on_result(result):
                        attempt += 1
                        wait_time = min(max_wait, min_wait * (2 ** (attempt - 1))) + random.uniform(0, 1)
                        logger.warning(f"Retrying due to result condition: {result}. Attempt {attempt}/{max_attempts}. Waiting {wait_time:.2f} seconds...")
                        time.sleep(wait_time)
                        continue
                    
                    return result
                    
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    # Экспоненциальное увеличение времени ожидания
                    wait_time = min(max_wait, min_wait * (2 ** (attempt - 1))) + random.uniform(0, 1)
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
            
            # Этот код не должен выполняться из-за проверки выше, но на всякий случай
            raise last_exception
        
        return wrapper
    
    return decorator

def retry_on_connection_error(func=None, max_attempts=3, min_wait=1, max_wait=10):
    """
    Декоратор для повторных попыток при ошибках соединения
    
    Args:
        func (callable): Декорируемая функция
        max_attempts (int): Максимальное количество попыток
        min_wait (int): Минимальное время ожидания между попытками в секундах
        max_wait (int): Максимальное время ожидания между попытками в секундах
        
    Returns:
        Декорированная функция
    """
    # Импортируем requests здесь для избежания циклических импортов
    import requests
    
    if func is None:
        return functools.partial(
            retry_on_connection_error,
            max_attempts=max_attempts,
            min_wait=min_wait,
            max_wait=max_wait
        )
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == max_attempts - 1:
                    # Последняя попытка, пробрасываем исключение дальше
                    logger.error(f"Connection error after {max_attempts} attempts: {e}")
                    raise
                
                # Экспоненциальное увеличение задержки
                wait_time = min_wait * (2 ** attempt) + random.uniform(0, 1)
                if wait_time > max_wait:
                    wait_time = max_wait
                
                logger.warning(f"Connection error: {e}. Retrying ({attempt+1}/{max_attempts}) in {wait_time:.2f}s")
                time.sleep(wait_time)
    
    return wrapper

# Готовые конфигурации retry для распространенных случаев
retry_remote_server = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RemoteServerError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

retry_database = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(DatabaseError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

class RetryManager:
    """
    Менеджер повторных попыток для блоков кода с несколькими операциями
    
    Пример использования:
    
    with RetryManager(max_attempts=3, retry_exceptions=(RemoteServerError,)) as retry:
        for attempt in retry:
            try:
                # Выполнение операции, которая может вызвать исключение
                result = some_operation()
                
                # Проверка результата
                if result and result.get('status') == 'success':
                    return result
                else:
                    retry.retry(f"Operation returned unexpected result: {result}")
                    
            except RemoteServerError as e:
                retry.retry(f"Remote server error: {e}")
    """
    
    def __init__(self, max_attempts=3, min_wait=1, max_wait=10, 
                 retry_exceptions=(Exception,), 
                 jitter=True, logger=None):
        """
        Инициализация менеджера повторных попыток
        
        Args:
            max_attempts (int): Максимальное количество попыток
            min_wait (int): Минимальное время ожидания между попытками в секундах
            max_wait (int): Максимальное время ожидания между попытками в секундах
            retry_exceptions (tuple): Типы исключений, при которых нужно повторять попытки
            jitter (bool): Флаг использования случайной составляющей в задержке
            logger (Logger): Логгер для вывода сообщений
        """
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.retry_exceptions = retry_exceptions
        self.jitter = jitter
        self.logger = logger or logging.getLogger('wireguard-proxy.retry_manager')
        
        self.current_attempt = 0
        self.last_error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Если произошло исключение, которое мы не обрабатываем
        if exc_type and not issubclass(exc_type, self.retry_exceptions):
            return False
        
        # Если достигнуто максимальное количество попыток, пробрасываем последнюю ошибку
        if self.current_attempt >= self.max_attempts and self.last_error:
            self.logger.error(f"Max retry attempts ({self.max_attempts}) reached. Last error: {self.last_error}")
            if exc_val:
                # Пробрасываем исходное исключение
                return False
            
            # Если исключение не произошло, но мы все равно не смогли выполнить операцию
            if isinstance(self.last_error, Exception):
                raise self.last_error
            else:
                # Если ошибка не является исключением, создаем новое
                raise RuntimeError(f"Operation failed after {self.max_attempts} attempts: {self.last_error}")
        
        return True
    
    def __iter__(self):
        self.current_attempt = 0
        self.last_error = None
        return self
    
    def __next__(self):
        if self.current_attempt >= self.max_attempts:
            raise StopIteration
        
        if self.current_attempt > 0:
            # Вычисление времени ожидания
            wait_time = self.min_wait * (2 ** (self.current_attempt - 1))
            if wait_time > self.max_wait:
                wait_time = self.max_wait
                
            # Добавление случайной составляющей
            if self.jitter:
                wait_time += random.uniform(0, min(self.min_wait, 1.0))
            
            self.logger.info(f"Retry attempt {self.current_attempt}/{self.max_attempts}. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
        
        self.current_attempt += 1
        return self.current_attempt
    
    def retry(self, error_message):
        """
        Запрос на повторную попытку
        
        Args:
            error_message: Сообщение об ошибке или исключение
        
        Returns:
            bool: True если будет выполнена повторная попытка, иначе False
            
        Raises:
            StopIteration: Если достигнуто максимальное количество попыток
        """
        self.last_error = error_message
        self.logger.warning(f"Retry requested: {error_message}")
        
        # Проверка, можно ли выполнить повторную попытку
        if self.current_attempt < self.max_attempts:
            # Вычисление времени ожидания
            wait_time = self.min_wait * (2 ** (self.current_attempt - 1))
            if wait_time > self.max_wait:
                wait_time = self.max_wait
                
            # Добавление случайной составляющей
            if self.jitter:
                wait_time += random.uniform(0, min(self.min_wait, 1.0))
            
            self.logger.info(f"Retrying operation. Attempt {self.current_attempt}/{self.max_attempts}. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            return True
        else:
            self.logger.error(f"Maximum retry attempts ({self.max_attempts}) reached. Last error: {error_message}")
            # Если ошибка является исключением, пробрасываем его
            if isinstance(error_message, Exception):
                raise error_message
            # Иначе создаем новое исключение
            raise StopIteration(f"Maximum retry attempts ({self.max_attempts}) reached")
            
    def should_retry(self, condition_func=None, result=None, error=None):
        """
        Проверка, нужно ли выполнять повторную попытку
        
        Args:
            condition_func (callable): Функция для проверки условия повтора
            result: Результат операции
            error: Ошибка операции
            
        Returns:
            bool: True если нужно повторить операцию, иначе False
        """
        # Проверка, достигнуто ли максимальное количество попыток
        if self.current_attempt >= self.max_attempts:
            return False
            
        # Если передана функция проверки, используем её
        if condition_func is not None:
            return condition_func(result, error)
            
        # По умолчанию повторяем при наличии ошибки
        return error is not None