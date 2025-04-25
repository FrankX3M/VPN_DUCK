import logging
import time
import threading
from cachetools import TTLCache

logger = logging.getLogger('wireguard-proxy.cache_manager')

class CacheManager:
    """
    Менеджер кэширования для хранения часто используемых данных
    
    Отвечает за:
    - Кэширование информации о серверах и пирах
    - Очистку устаревших данных в кэше
    - Предоставление статистики использования кэша
    """
    
    def __init__(self, max_size=1000, ttl=300):
        """
        Инициализация менеджера кэша
        
        Args:
            max_size (int): Максимальный размер кэша
            ttl (int): Время жизни элементов в кэше в секундах (по умолчанию 5 минут)
        """
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
        self.custom_ttl_cache = {}  # Для элементов с нестандартным TTL
        self.custom_ttl_expiry = {}  # Время истечения для элементов с нестандартным TTL
        self.stats = {"hits": 0, "misses": 0}
        self.lock = threading.RLock()
        
        # Запуск фоновой задачи для очистки кэша с пользовательским TTL
        self.cleanup_thread = threading.Thread(target=self._cleanup_task, daemon=True)
        self.cleanup_thread.start()
    
    def get(self, key):
        """
        Получение значения из кэша
        
        Args:
            key (str): Ключ кэша
            
        Returns:
            any: Значение из кэша или None, если ключ не найден
        """
        with self.lock:
            # Проверка кэша с TTL по умолчанию
            if key in self.cache:
                self.stats["hits"] += 1
                return self.cache[key]
            
            # Проверка кэша с пользовательским TTL
            if key in self.custom_ttl_cache:
                # Проверка истечения срока
                if time.time() < self.custom_ttl_expiry[key]:
                    self.stats["hits"] += 1
                    return self.custom_ttl_cache[key]
                else:
                    # Удаление устаревшего значения
                    del self.custom_ttl_cache[key]
                    del self.custom_ttl_expiry[key]
            
            self.stats["misses"] += 1
            return None
    
    def set(self, key, value, ttl=None):
        """
        Установка значения в кэш
        
        Args:
            key (str): Ключ кэша
            value (any): Значение для сохранения
            ttl (int, optional): Время жизни в секундах, если отличается от стандартного
        """
        with self.lock:
            if ttl is None:
                # Используем кэш с TTL по умолчанию
                self.cache[key] = value
            else:
                # Используем кэш с пользовательским TTL
                self.custom_ttl_cache[key] = value
                self.custom_ttl_expiry[key] = time.time() + ttl
    
    def delete(self, key):
        """
        Удаление значения из кэша
        
        Args:
            key (str): Ключ кэша
        """
        with self.lock:
            # Удаление из обоих кэшей
            self.cache.pop(key, None)
            self.custom_ttl_cache.pop(key, None)
            self.custom_ttl_expiry.pop(key, None)
    
    def clear(self):
        """Очистка всего кэша"""
        with self.lock:
            self.cache.clear()
            self.custom_ttl_cache.clear()
            self.custom_ttl_expiry.clear()
    
    def get_stats(self):
        """
        Получение статистики использования кэша
        
        Returns:
            dict: Статистика использования кэша
        """
        with self.lock:
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "size": len(self.cache) + len(self.custom_ttl_cache),
                "hit_ratio": self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) * 100 if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
            }
    
    def _cleanup_task(self):
        """Фоновая задача для очистки устаревших элементов с пользовательским TTL"""
        while True:
            try:
                with self.lock:
                    current_time = time.time()
                    expired_keys = [k for k, exp_time in self.custom_ttl_expiry.items() if current_time > exp_time]
                    
                    for key in expired_keys:
                        self.custom_ttl_cache.pop(key, None)
                        self.custom_ttl_expiry.pop(key, None)
                
                # Спим 10 секунд перед следующей проверкой
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
                time.sleep(30)  # При ошибке спим дольше