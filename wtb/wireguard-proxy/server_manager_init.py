#!/usr/bin/env python3
import os
import logging
import threading
import time
from server_manager import ServerManager

# Настройка логирования
logger = logging.getLogger('wireguard-proxy.server_manager_init')

def initialize_server_manager(cache_manager, shutdown_event, background_threads):
    """
    Инициализирует менеджер серверов и запускает фоновые потоки обновления.
    
    Args:
        cache_manager: Экземпляр CacheManager для кэширования данных
        shutdown_event: Событие для сигнализации о завершении работы потоков
        background_threads: Список для регистрации фоновых потоков
        
    Returns:
        ServerManager: Инициализированный экземпляр ServerManager
    """
    logger.info("Инициализация ServerManager")
    
    # Создаем экземпляр менеджера серверов
    server_manager = ServerManager(cache_manager)
    
    # Функция для обновления информации о серверах в фоновом режиме
    def update_servers_periodically():
        while not shutdown_event.is_set():
            try:
                server_manager.update_servers_info()
            except Exception as e:
                logger.error(f"Ошибка в фоновом обновлении серверов: {e}")
            
            # Ждем указанное время до следующего обновления
            # Проверяем событие завершения каждую секунду
            for _ in range(60):  # 60 секунд = 1 минута
                if shutdown_event.is_set():
                    break
                time.sleep(1)
    
    # Создаем и запускаем фоновый поток
    update_thread = threading.Thread(
        target=update_servers_periodically,
        name="ServerUpdater",
        daemon=True
    )
    update_thread.start()
    
    # Регистрируем поток в списке фоновых потоков
    background_threads.append(update_thread)
    
    logger.info("Запущена фоновая задача обновления серверов")
    logger.info("Запущен фоновый поток обновления информации о серверах с интервалом 60 сек.")
    logger.info("Менеджер серверов успешно инициализирован. Интервал обновления: 60 сек.")
    
    # Выполняем первоначальное обновление данных о серверах
    server_manager.update_servers_info()
    
    return server_manager