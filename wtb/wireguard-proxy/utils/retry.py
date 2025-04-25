import time
import logging
import functools
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from utils.errors import RemoteServerError, DatabaseError

logger = logging.getLogger('wireguard-proxy.retry')

def with_retry(max_attempts=3, min_wait=1, max_wait=10, exceptions=(RemoteServerError, DatabaseError)):
    """
    Декоратор для выполнения функции с повторными попытками при возникновении ошибки
    
    Args:
        max_attempts (int): Максимальное количество попыток
        min_wait (int): Минимальное время ожидания между попытками в секундах
        max_wait (int): Максимальное время ожидания между попытками в секундах
        exceptions (tuple): Типы исключений, при которых нужно повторять попытки
        
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
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    # Экспоненциальное увеличение времени ожидания
                    wait_time = min(max_wait, min_wait * (2 ** (attempt - 1))) + random.uniform(0, 1)
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
            
            # Этот код не должен выполняться из-за проверки above, но на всякий случай
            raise last_exception
        
        return wrapper
    
    return decorator


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