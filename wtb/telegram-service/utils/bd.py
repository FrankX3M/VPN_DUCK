import logging
import requests
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from functools import lru_cache
import time

from core.settings import DATABASE_SERVICE_URL, WIREGUARD_SERVICE_URL, logger, normalize_api_url



# Время жизни кэша в секундах
GEO_CACHE_TTL = 300
# Переменная для хранения времени последнего обновления
_geo_cache_last_update = 0
# Кэш геолокаций
_geo_cache = []

# Интервал проверки сервисов в секундах (10 минут)
_SERVICES_CHECK_INTERVAL = 600
# Время последней проверки доступности сервисов - ДОЛЖНО БЫТЬ ПОСЛЕ определения _SERVICES_CHECK_INTERVAL
_services_check_last_time = time.time() - _SERVICES_CHECK_INTERVAL - 1
# Состояние сервисов
_services_status = {
    "wireguard": False,
    "database": False
}




# Функция проверки доступности сервисов
async def check_services_availability():
    """
    Проверяет доступность сервисов WireGuard и Database.
    Обновляет глобальное состояние сервисов.
    Вызывается периодически для отслеживания состояния.
    """
    global _services_check_last_time, _services_status
    
    # Проверяем, не слишком ли рано для повторной проверки
    current_time = time.time()
    if (current_time - _services_check_last_time) < _SERVICES_CHECK_INTERVAL:
        # Если прошло мало времени с последней проверки, возвращаем текущее состояние
        return _services_status
    
    logger.info("Выполняем проверку доступности сервисов")
    
    # Проверка database-service
    try:
        async with aiohttp.ClientSession() as session:
            url = _verify_url(DATABASE_SERVICE_URL, "status")
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    _services_status["database"] = True
                    logger.info("database-service доступен")
                else:
                    _services_status["database"] = False
                    logger.warning(f"database-service недоступен, код: {response.status}")
    except Exception as e:
        _services_status["database"] = False
        logger.error(f"Ошибка при проверке database-service: {str(e)}")
    
    # Проверка wireguard-service
    if WIREGUARD_SERVICE_URL:
        try:
            # Получаем базовый URL без /api для wireguard-proxy
            wireguard_base_url = WIREGUARD_SERVICE_URL
            if wireguard_base_url.endswith('/api'):
                wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
            
            async with aiohttp.ClientSession() as session:
                # Сначала пробуем через эндпоинт /status
                url = f"{wireguard_base_url}/status"
                logger.info(f"Проверка доступности wireguard-service по URL: {url}")
                
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            _services_status["wireguard"] = True
                            logger.info("wireguard-service доступен через /status")
                        else:
                            logger.warning(f"Эндпоинт /status вернул код: {response.status}")
                except Exception as e:
                    logger.warning(f"Ошибка при проверке /status: {str(e)}")
                
                # Если /status недоступен или вернул ошибку, пробуем через /health
                if not _services_status["wireguard"]:
                    url = f"{wireguard_base_url}/health"
                    logger.info(f"Пробуем запасной URL для проверки: {url}")
                    
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                _services_status["wireguard"] = True
                                logger.info("wireguard-service доступен через /health")
                            else:
                                _services_status["wireguard"] = False
                                logger.warning(f"Эндпоинт /health вернул код: {response.status}")
                    except Exception as e:
                        _services_status["wireguard"] = False
                        logger.error(f"Ошибка при проверке /health: {str(e)}")
                
                # Если предыдущие проверки не сработали, пробуем /servers
                if not _services_status["wireguard"]:
                    url = f"{wireguard_base_url}/servers"
                    logger.info(f"Пробуем проверку через /servers: {url}")
                    
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                _services_status["wireguard"] = True
                                logger.info("wireguard-service доступен через /servers")
                            else:
                                _services_status["wireguard"] = False
                                logger.warning(f"Эндпоинт /servers вернул код: {response.status}")
                    except Exception as e:
                        _services_status["wireguard"] = False
                        logger.error(f"Ошибка при проверке /servers: {str(e)}")
        except Exception as e:
            _services_status["wireguard"] = False
            logger.error(f"Ошибка при проверке wireguard-service: {str(e)}")
    else:
        _services_status["wireguard"] = False
        logger.warning("URL wireguard-service не настроен")
    
    # Обновляем время последней проверки
    _services_check_last_time = current_time
    
    return _services_status

# Проверка при импорте модуля
# asyncio.create_task(check_services_availability())
# Примечание: нельзя запускать задачи при импорте модуля, 
# проверка сервисов будет автоматически происходить при первом вызове функций

# Вспомогательная функция для проверки корректности URL перед запросом
def _verify_url(url, endpoint=""):
    """
    Проверяет и корректирует URL перед отправкой запроса.
    
    Args:
        url (str): Базовый URL сервиса
        endpoint (str): Эндпоинт для запроса (без начального слеша)
        
    Returns:
        str: Корректный URL для запроса
    """
    if not url:
        return ""
    
    # Проверяем базовый URL
    base_url = url.rstrip('/')
    
    # Формируем полный URL с эндпоинтом
    if endpoint:
        # Убираем начальный слеш у эндпоинта, если есть
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        full_url = f"{base_url}/{endpoint}"
    else:
        full_url = base_url
    
    # Исправляем возможные ошибки
    if '/api/api/' in full_url:
        full_url = full_url.replace('/api/api/', '/api/')
    
    logger.debug(f"Нормализованный URL: {full_url}")
    return full_url

async def get_available_geolocations():
    """Получает список доступных геолокаций из базы данных с кэшированием."""
    global _geo_cache, _geo_cache_last_update
    
    # Проверяем, не истек ли срок действия кэша
    current_time = time.time()
    if _geo_cache and (current_time - _geo_cache_last_update < GEO_CACHE_TTL):
        logger.info("Возвращаем кэшированные геолокации")
        return _geo_cache
    
    try:
        logger.info("Получение доступных геолокаций (обновление кэша)")
        
        async with aiohttp.ClientSession() as session:
            url = _verify_url(DATABASE_SERVICE_URL, "geolocations/available")
            async with session.get(url, timeout=10) as response:
                logger.info(f"Ответ API: код {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    geolocations = data.get("geolocations", [])
                    
                    # Обновляем кэш и время обновления
                    _geo_cache = geolocations
                    _geo_cache_last_update = current_time
                    
                    return geolocations
                
                # Подробный вывод информации об ошибке
                logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                
                # Возвращаем кэшированные данные даже если они устарели, вместо пустого списка
                if _geo_cache:
                    logger.warning("Возвращаем устаревшие кэшированные данные из-за ошибки API")
                    return _geo_cache
                
                return []
                
    except Exception as e:
        logger.error(f"Ошибка запроса доступных геолокаций: {str(e)}")
        
        # Возвращаем кэшированные данные даже если они устарели, в случае ошибки
        if _geo_cache:
            logger.warning("Возвращаем устаревшие кэшированные данные из-за ошибки")
            return _geo_cache
            
        return []

async def change_config_geolocation(user_id, geolocation_id, server_id=None):
    """Изменяет геолокацию активной конфигурации пользователя."""
    try:
        logger.info(f"Изменение геолокации для пользователя {user_id} на {geolocation_id}")
        
        async with aiohttp.ClientSession() as session:
            # Если server_id не предоставлен, нужно получить его
            if not server_id:
                # Получаем список серверов для выбранной геолокации с таймаутом
                logger.info(f"Запрашиваем список серверов для геолокации {geolocation_id}")
                try:
                    async with session.get(
                        _verify_url(DATABASE_SERVICE_URL, f"servers/geolocation/{geolocation_id}"),
                        timeout=10
                    ) as server_response:
                        
                        logger.info(f"Получен ответ о серверах: {server_response.status}")
                        
                        if server_response.status == 200:
                            servers_data = await server_response.json()
                            servers = servers_data.get("servers", [])
                            if servers:
                                # Выбираем первый доступный сервер
                                server_id = servers[0].get("id")
                                logger.info(f"Автоматически выбран сервер {server_id} для геолокации {geolocation_id}")
                except asyncio.TimeoutError:
                    logger.error(f"Превышено время ожидания при запросе серверов для геолокации {geolocation_id}")
                    return {"error": "Превышено время ожидания при запросе серверов. Пожалуйста, попробуйте позже."}
                
                if not server_id:
                    return {"error": "Не удалось найти подходящий сервер для выбранной геолокации"}
            
            # Формируем данные запроса
            data = {
                "user_id": user_id,
                "geolocation_id": geolocation_id,
                "server_id": server_id
            }
            
            logger.info(f"Отправляем запрос на изменение геолокации: {data}")
            
            # Отправляем запрос на изменение геолокации с увеличенным таймаутом
            try:
                async with session.post(
                    _verify_url(DATABASE_SERVICE_URL, "configs/change_geolocation"),
                    json=data,
                    timeout=30
                ) as response:
                    
                    logger.info(f"Ответ API на изменение геолокации: код {response.status}")
                    
                    if response.status == 200:
                        return await response.json()
                    
                    # Подробный вывод информации об ошибке
                    error_message = "Ошибка при изменении геолокации."
                    response_text = await response.text()
                    
                    if response.headers.get('content-type') == 'application/json':
                        try:
                            response_data = await response.json()
                            if "error" in response_data:
                                error_message = response_data.get("error")
                        except:
                            logger.error(f"Не удалось декодировать JSON-ответ: {response_text}")
                    
                    logger.error(f"Ошибка API при изменении геолокации: {error_message}")
                    return {"error": error_message}
            except asyncio.TimeoutError:
                logger.error("Превышено время ожидания ответа при изменении геолокации")
                return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
                
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе к API: {str(e)}")
        return {"error": f"Ошибка соединения при изменении геолокации: {str(e)}. Пожалуйста, попробуйте позже."}
    except asyncio.TimeoutError:
        logger.error("Превышено время ожидания ответа от сервера")
        return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при изменении геолокации: {str(e)}. Пожалуйста, попробуйте позже."}

async def create_new_config(user_id, geolocation_id=None):
    """Создает новую конфигурацию WireGuard с возможностью выбора геолокации."""
    try:
        logger.info(f"Создание новой конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
        # Проверяем доступность сервисов
        services_status = await check_services_availability()
        if not services_status["wireguard"]:
            logger.error("WireGuard сервис недоступен, невозможно создать конфигурацию")
            return {"error": "WireGuard сервис недоступен. Пожалуйста, попробуйте позже."}
        
        # Проверяем текущую конфигурацию и деактивируем ее
        current_config = await get_user_config(user_id)
        if current_config and current_config.get("active") and current_config.get("public_key"):
            public_key = current_config.get("public_key")
            logger.info(f"Деактивируем существующую конфигурацию с public_key: {public_key}")
            
            try:
                # Очистка URL wireguard от /api
                wireguard_base_url = WIREGUARD_SERVICE_URL
                if wireguard_base_url.endswith('/api'):
                    wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
                
                deactivate_url = f"{wireguard_base_url}/remove/{public_key}"
                logger.info(f"Отправляем запрос на деактивацию на URL: {deactivate_url}")
                
                deactivate_response = requests.delete(
                    deactivate_url, 
                    timeout=10
                )
                logger.info(f"Ответ API на деактивацию: код {deactivate_response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации: {str(e)}")
        
        # Определяем URL сервиса WireGuard
        wireguard_url = WIREGUARD_SERVICE_URL
        logger.info(f"Используем URL wireguard-service: {wireguard_url}")
        
        # Если URL не установлен, получаем список серверов
        if not wireguard_url:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        _verify_url(DATABASE_SERVICE_URL, "servers/all"), 
                        timeout=10
                    ) as servers_response:
                        if servers_response.status == 200:
                            servers_data = await servers_response.json()
                            servers = servers_data.get("servers", [])
                            active_servers = [s for s in servers if s.get("status") == "active"]
                            
                            if active_servers:
                                # Берем первый активный сервер
                                server = active_servers[0]
                                endpoint = server.get('endpoint')
                                port = server.get('port', 5000)  # Используем 5000 как порт по умолчанию
                                wireguard_url = normalize_api_url(f"http://{endpoint}:{port}")
                                
                                logger.info(f"Используем сервер: {wireguard_url}")
                            else:
                                logger.error("Нет активных серверов")
                                return {"error": "Нет доступных серверов. Добавьте сервер через админ-панель."}
                        else:
                            logger.error(f"Ошибка при получении списка серверов: {servers_response.status}")
                            return {"error": "Ошибка при получении списка серверов"}
                except Exception as e:
                    logger.error(f"Ошибка при получении списка серверов: {str(e)}")
                    return {"error": "Ошибка при получении списка серверов"}
        
        # Формируем данные для запроса
        request_data = {"user_id": user_id}
        if geolocation_id:
            request_data["geolocation_id"] = geolocation_id
        
        logger.info(f"Отправляем запрос на создание с данными: {request_data}")
        
        # Отправляем запрос на создание новой конфигурации
        async with aiohttp.ClientSession() as session:
            try:
                # Формируем URL для запроса
                wireguard_base_url = wireguard_url
                # Удаляем /api из базового URL, если он присутствует
                if wireguard_base_url.endswith('/api'):
                    wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
                
                create_url = f"{wireguard_base_url}/create"
                logger.info(f"Отправляем запрос на URL: {create_url}")
                
                async with session.post(
                    create_url,
                    json=request_data,
                    timeout=30
                ) as wg_response:
                    logger.info(f"Ответ API wireguard-service: код {wg_response.status}")
                    
                    if wg_response.status == 201:
                        wg_data = await wg_response.json()
                        config_text = wg_data.get("config")
                        public_key = wg_data.get("public_key")
                        server_id = wg_data.get("server_id")
                        server_geolocation_id = wg_data.get("geolocation_id")
                        
                        logger.info(f"Конфигурация получена успешно. Public key: {public_key}, Server ID: {server_id}")
                        
                        # Рассчитываем дату истечения (7 дней от текущей даты)
                        expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
                        
                        # Сохраняем в базе данных через database-service
                        db_data = {
                            "user_id": user_id,
                            "config": config_text,
                            "public_key": public_key,
                            "expiry_time": expiry_time,
                            "active": True
                        }
                        
                        # Добавляем информацию о геолокации и сервере
                        if server_geolocation_id:
                            db_data["geolocation_id"] = server_geolocation_id
                        elif geolocation_id:
                            db_data["geolocation_id"] = geolocation_id
                        if server_id:
                            db_data["server_id"] = server_id
                        
                        async with session.post(
                            _verify_url(DATABASE_SERVICE_URL, "config"),
                            json=db_data,
                            timeout=20
                        ) as db_response:
                            logger.info(f"Ответ API database-service: код {db_response.status}")
                            
                            if db_response.status in [200, 201]:
                                logger.info("Конфигурация успешно создана и сохранена в БД")
                                return {
                                    "config_text": config_text,
                                    "public_key": public_key,
                                    "server_id": server_id,
                                    "geolocation_id": server_geolocation_id or geolocation_id
                                }
                            else:
                                # Логируем ошибку сохранения в БД
                                error_msg = f"Ошибка сохранения в БД: код {db_response.status}"
                                try:
                                    error_data = await db_response.json()
                                    if "error" in error_data:
                                        error_msg = error_data.get("error")
                                except:
                                    pass
                                
                                logger.error(error_msg)
                                return {"error": error_msg}
                    
                    # В случае ошибки от wireguard-service
                    error_message = "Ошибка при создании конфигурации."
                    try:
                        response_data = await wg_response.json()
                        if "error" in response_data:
                            error_message = response_data.get("error")
                    except:
                        pass
                    
                    logger.error(f"Ошибка от wireguard-service: {error_message}")
                    return {"error": error_message}
            except asyncio.TimeoutError:
                logger.error("Превышено время ожидания ответа от wireguard-service")
                return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
            except Exception as request_error:
                logger.error(f"Ошибка при запросе к wireguard-service: {str(request_error)}")
                return {"error": f"Ошибка при создании конфигурации: {str(request_error)}. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Общая ошибка при создании конфигурации: {str(e)}")
        return {"error": f"Ошибка при создании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

async def get_all_user_configs(user_id):
    """Получает все конфигурации пользователя из базы данных."""
    try:
        logger.info(f"Получение всех конфигураций для пользователя {user_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _verify_url(DATABASE_SERVICE_URL, f"configs/get_all/{user_id}"), 
                timeout=15
            ) as response:
                
                logger.info(f"Ответ API: код {response.status}")
                
                if response.status == 200:
                    return await response.json()
                
                # Подробный вывод информации об ошибке
                error_message = "Ошибка при получении конфигураций."
                response_text = await response.text()
                
                if response.headers.get('content-type') == 'application/json':
                    try:
                        response_data = await response.json()
                        if "error" in response_data:
                            error_message = response_data.get("error")
                    except:
                        logger.error(f"Не удалось декодировать JSON-ответ: {response_text}")
                
                logger.error(f"Ошибка API: {error_message}")
                return {"error": error_message}
                
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе к API: {str(e)}")
        return {"error": f"Ошибка соединения при получении конфигураций: {str(e)}. Пожалуйста, попробуйте позже."}
    except asyncio.TimeoutError:
        logger.error("Превышено время ожидания ответа от сервера")
        return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении конфигураций: {str(e)}. Пожалуйста, попробуйте позже."}

async def get_user_config(user_id):
    """Получает конфигурацию пользователя из базы данных."""
    try:
        logger.info(f"Получение конфигурации для пользователя {user_id}")
        url = _verify_url(DATABASE_SERVICE_URL, f"config/{user_id}")
        logger.info(f"Используем URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as response:
                    logger.info(f"Ответ API: код {response.status}")
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.info(f"Конфигурация для пользователя {user_id} не найдена (404)")
                        return None
                    else:
                        # Подробный вывод информации об ошибке
                        logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                        
                        # Пытаемся повторить запрос один раз при серверных ошибках
                        if response.status >= 500:
                            logger.info(f"Повторяем запрос после серверной ошибки {response.status}")
                            await asyncio.sleep(1)  # Небольшая задержка перед повторным запросом
                            
                            async with session.get(url, timeout=10) as retry_response:
                                if retry_response.status == 200:
                                    logger.info("Повторный запрос успешен")
                                    return await retry_response.json()
                        
                        return None
            except asyncio.TimeoutError:
                logger.error(f"Превышено время ожидания при запросе конфигурации пользователя {user_id}")
                return None
                
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе конфигурации пользователя: {str(e)}")
        return None
    except asyncio.TimeoutError:
        logger.error("Превышено время ожидания ответа от сервера")
        return None
    except Exception as e:
        logger.error(f"Ошибка запроса конфигурации пользователя: {str(e)}")
        return None

# Обновленная функция проверки доступности серверов
async def are_servers_available():
    """Проверяет наличие доступных внешних серверов."""
    # Вызываем общую проверку сервисов
    services_status = await check_services_availability()
    
    # Если wireguard уже проверен и доступен, возвращаем результат
    if services_status["wireguard"]:
        return True
        
    # Пробуем напрямую обратиться к эндпоинту /servers
    try:
        wireguard_base_url = WIREGUARD_SERVICE_URL
        if wireguard_base_url.endswith('/api'):
            wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{wireguard_base_url}/servers", timeout=10) as response:
                if response.status == 200:
                    servers_data = await response.json()
                    servers = servers_data.get("servers", [])
                    active_count = servers_data.get("active", 0)
                    
                    # Проверяем наличие активных серверов
                    if active_count <= 0 or not servers:
                        logger.info("Нет активных серверов")
                        return False
                    
                    logger.info(f"Доступно {active_count} активных серверов")
                    return True
                else:
                    logger.error(f"Ошибка при получении списка серверов: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при проверке доступных серверов: {str(e)}")
        return False

async def get_servers_for_geolocation(geolocation_id):
    """
    Получает список серверов для указанной геолокации.
    
    Args:
        geolocation_id: ID геолокации
        
    Returns:
        list: Список серверов для данной геолокации
    """
    try:
        logger.info(f"Получение серверов для геолокации {geolocation_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _verify_url(DATABASE_SERVICE_URL, f"servers/geolocation/{geolocation_id}"),
                timeout=10
            ) as response:
                logger.info(f"Ответ API получения серверов: код {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    return data.get("servers", [])
                
                # Если серверы не найдены, возвращаем пустой список
                if response.status == 404:
                    logger.warning(f"Серверы для геолокации {geolocation_id} не найдены")
                    return []
                
                # Подробный вывод информации об ошибке
                logger.error(f"Ошибка API при получении серверов: {response.status}, тело: {await response.text()}")
                return []
                
    except Exception as e:
        logger.error(f"Ошибка при получении серверов для геолокации: {str(e)}", exc_info=True)
        return []

async def get_user_location(user_id):
    """
    Получает текущую геолокацию пользователя.
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        str or None: Геолокация пользователя или None, если не найдена
    """
    try:
        config = await get_user_config(user_id)
        if config and "location" in config:
            return config["location"]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении локации пользователя: {str(e)}", exc_info=True)
        return None

async def update_user_location(user_id, location):
    """
    Обновляет геолокацию пользователя.
    
    Args:
        user_id (int): ID пользователя
        location (str): Новая геолокация
        
    Returns:
        bool: True, если обновление прошло успешно, иначе False
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                _verify_url(DATABASE_SERVICE_URL, "user/location"),
                json={
                    "user_id": user_id,
                    "location": location
                },
                timeout=10
            ) as response:
                if response.status in [200, 201]:
                    return True
                
                logger.error(f"Ошибка при обновлении локации: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении локации пользователя: {str(e)}", exc_info=True)
        return False

async def get_config_from_wireguard(user_id):
    """Получает конфигурацию из базы данных."""
    try:
        logger.info(f"Получение конфигурации для пользователя {user_id}")
        
        # Получаем информацию о конфигурации пользователя из базы данных
        config_info = await get_user_config(user_id)
        
        if not config_info or not config_info.get("active"):
            logger.warning(f"Активная конфигурация не найдена для пользователя {user_id}")
            return {"error": "Активная конфигурация не найдена"}
        
        # Конфигурация хранится непосредственно в БД
        config_text = config_info.get("config")
        
        if not config_text:
            logger.warning(f"Текст конфигурации отсутствует в БД для пользователя {user_id}")
            return {"error": "Текст конфигурации отсутствует в базе данных"}
        
        logger.info(f"Конфигурация успешно получена для пользователя {user_id}")
        return {"config_text": config_text}
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {str(e)}")
        return {"error": f"Ошибка при получении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}


async def extend_config(user_id, days, stars, transaction_id):
    """
    Продлевает срок действия конфигурации WireGuard.
    
    Args:
        user_id (int): ID пользователя
        days (int): Количество дней продления
        stars (int): Количество звезд для продления
        transaction_id (str): ID транзакции
    
    Returns:
        dict: Результат продления конфигурации или словарь с ошибкой
    """
    try:
        logger.info(f"Начало процесса продления конфигурации для пользователя {user_id}")
        logger.info(f"Параметры продления: {days} дней, {stars} звезд, транзакция {transaction_id}")

        # Проверка текущей конфигурации
        current_config = await get_user_config(user_id)
        
        # Валидация наличия и активности конфигурации
        if not current_config:
            logger.warning(f"Конфигурация для пользователя {user_id} не найдена")
            return {"error": "Конфигурация не найдена. Создайте новую конфигурацию."}
        
        if not current_config.get("active", False):
            logger.warning(f"Конфигурация пользователя {user_id} неактивна")
            return {"error": "Неактивная конфигурация. Создайте новую конфигурацию."}
        
        # Проверка срока действия текущей конфигурации
        try:
            expiry_time = current_config.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                now = datetime.now()
                
                # Обработка просроченной, но технически активной конфигурации
                if expiry_dt < now:
                    logger.warning(f"Конфигурация пользователя {user_id} истекла")
                    config_data = await get_config_from_wireguard(user_id)
                    
                    if "error" in config_data:
                        logger.error(f"Не удалось проверить истекшую конфигурацию: {config_data['error']}")
                        return {"error": "Невозможно продлить истекшую конфигурацию. Создайте новую."}
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при проверке срока действия: {str(e)}")
        
        # Выполнение продления через базу данных
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    _verify_url(DATABASE_SERVICE_URL, "config/extend"),
                    json={
                        "user_id": user_id,
                        "days": days,
                        "stars_amount": stars,
                        "transaction_id": transaction_id
                    },
                    timeout=15
                ) as response:
                    # Логирование результата запроса
                    logger.info(f"Ответ сервера на продление: код {response.status}")
                    
                    # Успешное продление
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Конфигурация успешно продлена для пользователя {user_id}")
                        return result
                    
                    # Обработка ошибок от сервера
                    response_text = await response.text()
                    logger.error(f"Ошибка продления: код {response.status}, тело: {response_text}")
                    
                    # Извлечение сообщения об ошибке
                    error_message = "Не удалось продлить конфигурацию. Обратитесь в поддержку."
                    if response.headers.get('content-type') == 'application/json':
                        try:
                            error_data = await response.json()
                            if "error" in error_data:
                                error_message = error_data.get("error")
                        except Exception as json_error:
                            logger.error(f"Ошибка разбора JSON-ответа: {str(json_error)}")
                    
                    return {"error": error_message}
            
            except asyncio.TimeoutError:
                logger.error("Превышено время ожидания при продлении конфигурации")
                return {"error": "Превышено время ожидания. Пожалуйста, попробуйте позже."}
            
            except aiohttp.ClientError as network_error:
                logger.error(f"Сетевая ошибка при продлении: {str(network_error)}")
                return {"error": "Ошибка сети при продлении. Проверьте подключение."}
    
    except Exception as unexpected_error:
        logger.error(f"Неожиданная ошибка при продлении конфигурации: {str(unexpected_error)}", exc_info=True)
        return {"error": "Внутренняя ошибка при продлении. Обратитесь в поддержку."}

async def get_payment_history(user_id):
    """Получает историю платежей пользователя."""
    try:
        logger.info(f"Получение истории платежей для пользователя {user_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                _verify_url(DATABASE_SERVICE_URL, f"payments/history/{user_id}"), 
                timeout=10
            ) as response:
                logger.info(f"Ответ API: код {response.status}")
                
                if response.status == 200:
                    return await response.json()
                
                # Подробный вывод информации об ошибке
                logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                
                error_message = "Не удалось получить историю платежей. Попробуйте позже."
                if response.headers.get('content-type') == 'application/json':
                    try:
                        response_data = await response.json()
                        if "error" in response_data:
                            error_message = response_data.get("error")
                    except Exception as json_error:
                        logger.error(f"Ошибка при разборе JSON: {str(json_error)}")
                
                return {"error": error_message}
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка клиента aiohttp при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении истории платежей: {str(e)}. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении истории платежей: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для пересоздания конфигурации
async def recreate_config(user_id, geolocation_id=None):
    """
    Пересоздает конфигурацию WireGuard с сохранением или изменением геолокации.
    
    Args:
        user_id (int): ID пользователя
        geolocation_id (int, optional): ID геолокации. Если не указан, 
                                        будет использована текущая локация.
        
    Returns:
        dict: Словарь с данными конфигурации или информацией об ошибке
    """
    try:
        logger.info(f"Пересоздание конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
        # Проверяем доступность сервисов
        services_status = await check_services_availability()
        if not services_status["wireguard"]:
            logger.error("WireGuard сервис недоступен, невозможно пересоздать конфигурацию")
            return {"error": "WireGuard сервис недоступен. Пожалуйста, попробуйте позже."}
        
        # Получаем текущую конфигурацию
        current_config = await get_user_config(user_id)
        logger.info(f"Текущая конфигурация пользователя: {current_config}")
        
        # Определяем срок действия для новой конфигурации
        current_expiry = None
        if current_config and current_config.get("expiry_time"):
            try:
                # Парсим текущее время истечения
                current_expiry = datetime.fromisoformat(current_config.get("expiry_time"))
                now = datetime.now()
                
                # Проверяем, не истек ли срок действия
                if current_expiry > now:
                    logger.info(f"Сохраняем текущий срок действия: {current_expiry.isoformat()}")
                    expiry_time = current_expiry.isoformat()
                else:
                    logger.info("Срок действия уже истек, устанавливаем стандартный период")
                    expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка при парсинге даты: {str(e)}")
                expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
        else:
            logger.info("Нет активной конфигурации, устанавливаем стандартный период")
            expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
        
        # Если геолокация не указана, используем текущую из конфигурации
        if not geolocation_id and current_config:
            geolocation_id = current_config.get("geolocation_id")
            logger.info(f"Используем текущую геолокацию: {geolocation_id}")
        
        # Если геолокация всё ещё не определена, получаем доступные геолокации
        if not geolocation_id:
            geolocations = await get_available_geolocations()
            if geolocations:
                geolocation_id = geolocations[0].get('id')
                logger.info(f"Используем первую доступную геолокацию: {geolocation_id}")
        
        # Деактивируем текущую конфигурацию, если она есть
        if current_config and current_config.get("public_key"):
            public_key = current_config.get("public_key")
            logger.info(f"Деактивация текущей конфигурации с public_key: {public_key}")
            
            try:
                # Очистка URL wireguard от /api
                wireguard_base_url = WIREGUARD_SERVICE_URL
                if wireguard_base_url.endswith('/api'):
                    wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
                
                deactivate_url = f"{wireguard_base_url}/remove/{public_key}"
                logger.info(f"Отправляем запрос на деактивацию на URL: {deactivate_url}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        deactivate_url, 
                        timeout=10
                    ) as deactivate_response:
                        logger.info(f"Ответ API на деактивацию: код {deactivate_response.status}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации: {str(e)}")
        
        # Формируем данные для запроса
        request_data = {"user_id": user_id}
        if geolocation_id:
            request_data["geolocation_id"] = geolocation_id
        
        logger.info(f"Отправляем запрос на создание с данными: {request_data}")
        
        # Отправляем запрос на создание новой конфигурации
        async with aiohttp.ClientSession() as session:
            try:
                # Формируем URL для запроса
                wireguard_base_url = WIREGUARD_SERVICE_URL
                # Удаляем /api из базового URL, если он присутствует
                if wireguard_base_url.endswith('/api'):
                    wireguard_base_url = wireguard_base_url[:-4]  # Удаляем '/api'
                
                create_url = f"{wireguard_base_url}/create"
                logger.info(f"Отправляем запрос на URL: {create_url}")
                
                async with session.post(
                    create_url,
                    json=request_data,
                    timeout=30
                ) as wg_response:
                    logger.info(f"Ответ API wireguard-service: код {wg_response.status}")
                    
                    if wg_response.status == 201:
                        wg_data = await wg_response.json()
                        config_text = wg_data.get("config")
                        public_key = wg_data.get("public_key")
                        server_id = wg_data.get("server_id")
                        server_geolocation_id = wg_data.get("geolocation_id")
                        
                        logger.info(f"Конфигурация получена успешно. Public key: {public_key}, Server ID: {server_id}")
                        
                        # Сохраняем в базе данных через database-service
                        db_data = {
                            "user_id": user_id,
                            "config": config_text,
                            "public_key": public_key,
                            "expiry_time": expiry_time,
                            "active": True
                        }
                        
                        # Добавляем информацию о геолокации и сервере
                        if server_geolocation_id:
                            db_data["geolocation_id"] = server_geolocation_id
                        elif geolocation_id:
                            db_data["geolocation_id"] = geolocation_id
                        if server_id:
                            db_data["server_id"] = server_id
                        
                        async with session.post(
                            _verify_url(DATABASE_SERVICE_URL, "config"),
                            json=db_data,
                            timeout=20
                        ) as db_response:
                            logger.info(f"Ответ API database-service: код {db_response.status}")
                            
                            if db_response.status in [200, 201]:
                                # Возвращаем успешный результат
                                logger.info("Конфигурация успешно создана и сохранена в БД")
                                result_data = {
                                    "config_text": config_text,
                                    "public_key": public_key,
                                    "server_id": server_id,
                                    "geolocation_id": server_geolocation_id or geolocation_id,
                                    "expiry_time": expiry_time
                                }
                                logger.info(f"Возвращаем результат: {result_data}")
                                return result_data
                            else:
                                # Логируем ошибку сохранения в БД
                                error_message = f"Ошибка сохранения в БД: код {db_response.status}"
                                try:
                                    error_data = await db_response.json()
                                    if "error" in error_data:
                                        error_message = error_data.get("error")
                                except:
                                    pass
                                
                                logger.error(error_message)
                                return {"error": error_message}
                    
                    # В случае ошибки от wireguard-service
                    error_message = f"Ошибка при создании конфигурации: код {wg_response.status}"
                    try:
                        error_data = await wg_response.json()
                        if "error" in error_data:
                            error_message = error_data.get("error")
                    except:
                        pass
                    
                    logger.error(error_message)
                    return {"error": error_message}
            except asyncio.TimeoutError:
                logger.error("Превышено время ожидания ответа от wireguard-service")
                return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
            except Exception as request_error:
                logger.error(f"Ошибка при запросе к wireguard-service: {str(request_error)}")
                return {"error": f"Ошибка при пересоздании конфигурации: {str(request_error)}. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Общая ошибка при пересоздании конфигурации: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при пересоздании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}
