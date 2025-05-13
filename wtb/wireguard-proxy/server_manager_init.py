import os
import sys
import logging
import threading
import time
from server_manager import ServerManager
from cache_manager import CacheManager
from utils.errors import RemoteServerError, DatabaseError

# Настройка логирования
logger = logging.getLogger('wireguard-proxy.server_manager_init')

def initialize_server_manager(cache_manager=None, shutdown_event=None, background_threads=None):
    """
    Инициализирует менеджер серверов и запускает фоновую задачу обновления информации о серверах.
    
    Args:
        cache_manager (CacheManager, optional): Уже созданный экземпляр CacheManager
        shutdown_event (threading.Event, optional): Событие для сигнализации о завершении работы
        background_threads (list, optional): Список фоновых потоков для добавления нового потока
    
    Returns:
        ServerManager: Инициализированный экземпляр менеджера серверов
    """
    # Получение URL сервиса базы данных из переменных окружения
    database_service_url = os.environ.get('DATABASE_SERVICE_URL')
    if not database_service_url:
        logger.warning("DATABASE_SERVICE_URL не указан в переменных окружения. "
                      "Будет использоваться значение по умолчанию: http://database-service:5002")
        database_service_url = "http://database-service:5002"
    
    # Настройка интервала обновления из переменных окружения (по умолчанию 60 секунд)
    try:
        update_interval = int(os.environ.get('SERVER_UPDATE_INTERVAL', 60))
    except ValueError:
        logger.warning("Некорректное значение SERVER_UPDATE_INTERVAL. "
                      "Будет использоваться значение по умолчанию: 60 секунд")
        update_interval = 60
    
    # Инициализация кэш-менеджера, если не предоставлен
    if cache_manager is None:
        logger.info("Создание нового экземпляра CacheManager")
        cache_manager = CacheManager()
    
    # Создаем событие для завершения работы, если не предоставлено
    if shutdown_event is None:
        shutdown_event = threading.Event()
    
    # Инициализируем список фоновых потоков, если не предоставлен
    if background_threads is None:
        background_threads = []
    
    # Инициализация менеджера серверов
    try:
        logger.info(f"Инициализация ServerManager")
        server_manager = ServerManager(
            cache_manager=cache_manager
        )
        
        # В ServerManager.database_service_url будет использоваться значение из settings.py,
        # но можем обновить его здесь для использования из переменной окружения
        server_manager.database_service_url = database_service_url
        
        # Запуск обновления информации о серверах в фоновом режиме
        start_server_update_thread(
            server_manager, 
            update_interval=update_interval,
            shutdown_event=shutdown_event,
            background_threads=background_threads
        )
        
        logger.info(f"Менеджер серверов успешно инициализирован. Интервал обновления: {update_interval} сек.")
        
        return server_manager
    except Exception as e:
        logger.exception(f"Ошибка при инициализации менеджера серверов: {e}")
        raise

def start_server_update_thread(server_manager, update_interval=60, shutdown_event=None, background_threads=None):
    """
    Запускает фоновый поток для обновления информации о серверах.
    
    Args:
        server_manager (ServerManager): Экземпляр менеджера серверов
        update_interval (int): Интервал обновления в секундах
        shutdown_event (threading.Event): Событие для сигнализации о завершении работы
        background_threads (list): Список фоновых потоков для добавления нового потока
    """
    if shutdown_event is None:
        shutdown_event = threading.Event()
    
    if background_threads is None:
        background_threads = []
    
    # Создаем фоновый поток для обновления информации о серверах
    server_updater = threading.Thread(
        target=_background_server_updater,
        args=(server_manager, update_interval, shutdown_event),
        name="ServerUpdater",
        daemon=True
    )
    
    # Запускаем поток
    server_updater.start()
    
    # Добавляем поток в список фоновых потоков
    background_threads.append(server_updater)
    
    logger.info(f"Запущен фоновый поток обновления информации о серверах с интервалом {update_interval} сек.")

def _background_server_updater(server_manager, update_interval, shutdown_event):
    """
    Фоновая задача для обновления информации о серверах.
    
    Args:
        server_manager (ServerManager): Экземпляр менеджера серверов
        update_interval (int): Интервал обновления в секундах
        shutdown_event (threading.Event): Событие для сигнализации о завершении работы
    """
    logger.info("Запущена фоновая задача обновления серверов")
    
    retry_count = 0
    max_retry_count = 10
    retry_delay = 5
    
    while not shutdown_event.is_set():
        try:
            # Обновление информации о серверах
            server_manager.update_servers_info()
            
            # При успехе сбрасываем счетчик повторных попыток
            retry_count = 0
            retry_delay = 5
            
            # Ожидание следующего обновления (проверка на событие завершения)
            shutdown_event.wait(update_interval)
            
        except Exception as e:
            # Увеличиваем счетчик повторных попыток
            retry_count += 1
            logger.error(f"Ошибка в фоновой задаче обновления серверов: {e}")
            
            if retry_count >= max_retry_count:
                logger.warning(f"Достигнуто максимальное количество повторных попыток ({max_retry_count}), увеличиваем интервал")
                # Используем более длительный интервал при постоянных ошибках
                shutdown_event.wait(300)  # 5 минут после достижения лимита повторов
                retry_count = 0  # Сбрасываем счетчик
            else:
                # Экспоненциальное увеличение задержки между попытками
                retry_delay = min(retry_delay * 2, 120)
                logger.info(f"Повторная попытка через {retry_delay} секунд...")
                shutdown_event.wait(retry_delay)

