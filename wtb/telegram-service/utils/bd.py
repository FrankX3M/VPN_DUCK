import logging
import requests
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from core.settings import DATABASE_SERVICE_URL, WIREGUARD_SERVICE_URL, logger

# В начале файла добавить:
from functools import lru_cache
import time

# Время жизни кэша в секундах
GEO_CACHE_TTL = 300
# Переменная для хранения времени последнего обновления
_geo_cache_last_update = 0
# Кэш геолокаций
_geo_cache = []

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
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DATABASE_SERVICE_URL}/geolocations/available", timeout=10) as response:
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


# Функция для получения доступных геолокаций
async def get_available_geolocations():
    """Получает список доступных геолокаций из базы данных."""
    try:
        logger.info("Получение доступных геолокаций")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DATABASE_SERVICE_URL}/geolocations/available", timeout=10) as response:
                logger.info(f"Ответ API: код {response.status}")
                
                if response.status == 200:
                    return (await response.json()).get("geolocations", [])
                
                # Подробный вывод информации об ошибке
                logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                
                return []
                
    except Exception as e:
        logger.error(f"Ошибка запроса доступных геолокаций: {str(e)}")
        return []


# async def change_config_geolocation(user_id, geolocation_id, server_id=None):
#     """Изменяет геолокацию активной конфигурации пользователя."""
#     try:
#         logger.info(f"Изменение геолокации для пользователя {user_id} на {geolocation_id}")
        
#         import aiohttp
        
#         async with aiohttp.ClientSession() as session:
#             # Если server_id не предоставлен, нужно получить его
#             if not server_id:
#                 # Получаем список серверов для выбранной геолокации
#                 logger.info(f"Запрашиваем список серверов для геолокации {geolocation_id}")
#                 async with session.get(
#                     f"{DATABASE_SERVICE_URL}/servers/geolocation/{geolocation_id}",
#                     timeout=10
#                 ) as server_response:
                    
#                     logger.info(f"Получен ответ о серверах: {server_response.status}")
                    
#                     if server_response.status == 200:
#                         servers_data = await server_response.json()
#                         servers = servers_data.get("servers", [])
#                         if servers:
#                             # Выбираем первый доступный сервер
#                             server_id = servers[0].get("id")
#                             logger.info(f"Автоматически выбран сервер {server_id} для геолокации {geolocation_id}")
                
#                 if not server_id:
#                     return {"error": "Не удалось найти подходящий сервер для выбранной геолокации"}
            
#             # Формируем данные запроса
#             data = {
#                 "user_id": user_id,
#                 "geolocation_id": geolocation_id,
#                 "server_id": server_id
#             }
            
#             logger.info(f"Отправляем запрос на изменение геолокации: {data}")
            
#             # Отправляем запрос на изменение геолокации
#             async with session.post(
#                 f"{DATABASE_SERVICE_URL}/configs/change_geolocation",
#                 json=data,
#                 timeout=30
#             ) as response:
                
#                 logger.info(f"Ответ API на изменение геолокации: код {response.status}")
                
#                 if response.status == 200:
#                     return await response.json()
                
#                 # Подробный вывод информации об ошибке
#                 error_message = "Ошибка при изменении геолокации."
#                 response_text = await response.text()
                
#                 if response.headers.get('content-type') == 'application/json':
#                     try:
#                         response_data = await response.json()
#                         if "error" in response_data:
#                             error_message = response_data.get("error")
#                     except:
#                         logger.error(f"Не удалось декодировать JSON-ответ: {response_text}")
                
#                 logger.error(f"Ошибка API при изменении геолокации: {error_message}")
#                 return {"error": error_message}
                
#     except aiohttp.ClientError as e:
#         logger.error(f"Ошибка клиента aiohttp при запросе к API: {str(e)}")
#         return {"error": f"Ошибка соединения при изменении геолокации: {str(e)}. Пожалуйста, попробуйте позже."}
#     except asyncio.TimeoutError:
#         logger.error("Превышено время ожидания ответа от сервера")
#         return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
#     except Exception as e:
#         logger.error(f"Неожиданная ошибка при запросе к API: {str(e)}")
#         return {"error": f"Ошибка при изменении геолокации: {str(e)}. Пожалуйста, попробуйте позже."}

async def change_config_geolocation(user_id, geolocation_id, server_id=None):
    """Изменяет геолокацию активной конфигурации пользователя."""
    try:
        logger.info(f"Изменение геолокации для пользователя {user_id} на {geolocation_id}")
        
        import aiohttp
        import asyncio
        
        async with aiohttp.ClientSession() as session:
            # Если server_id не предоставлен, нужно получить его
            if not server_id:
                # Получаем список серверов для выбранной геолокации с таймаутом
                logger.info(f"Запрашиваем список серверов для геолокации {geolocation_id}")
                try:
                    async with session.get(
                        f"{DATABASE_SERVICE_URL}/servers/geolocation/{geolocation_id}",
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
                    f"{DATABASE_SERVICE_URL}/configs/change_geolocation",
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
        
# Функция для получения всех конфигураций пользователя
async def get_all_user_configs(user_id):
    """Получает все конфигурации пользователя из базы данных."""
    try:
        logger.info(f"Получение всех конфигураций для пользователя {user_id}")
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DATABASE_SERVICE_URL}/configs/get_all/{user_id}", 
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

# Функция для получения конфигурации пользователя
# async def get_user_config(user_id):
#     """Получает конфигурацию пользователя из базы данных."""
#     try:
#         logger.info(f"Получение конфигурации для пользователя {user_id}")
#         logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/config/{user_id}")
        
#         import aiohttp
        
#         async with aiohttp.ClientSession() as session:
#             async with session.get(
#                 f"{DATABASE_SERVICE_URL}/config/{user_id}", 
#                 timeout=10
#             ) as response:
                
#                 logger.info(f"Ответ API: код {response.status}")
                
#                 if response.status == 200:
#                     return await response.json()
                    
#                 # Подробный вывод информации об ошибке
#                 if response.status != 404:  # 404 - нормальный ответ, если конфиг не найден
#                     logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                    
#                 return None
                
#     except aiohttp.ClientError as e:
#         logger.error(f"Ошибка клиента aiohttp при запросе конфигурации пользователя: {str(e)}")
#         return None
#     except asyncio.TimeoutError:
#         logger.error("Превышено время ожидания ответа от сервера")
#         return None
#     except Exception as e:
#         logger.error(f"Ошибка запроса конфигурации пользователя: {str(e)}")
#         return None

async def get_user_config(user_id):
    """Получает конфигурацию пользователя из базы данных."""
    try:
        logger.info(f"Получение конфигурации для пользователя {user_id}")
        logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/config/{user_id}")
        
        import aiohttp
        import asyncio
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{DATABASE_SERVICE_URL}/config/{user_id}", 
                    timeout=10
                ) as response:
                    
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
                            
                            async with session.get(
                                f"{DATABASE_SERVICE_URL}/config/{user_id}", 
                                timeout=10
                            ) as retry_response:
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
        
# Функция для создания новой конфигурации
# async def create_new_config(user_id, geolocation_id=None):
#     """Создает новую конфигурацию WireGuard с возможностью выбора геолокации."""
#     try:
#         logger.info(f"Создание новой конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
#         # Формируем данные для запроса к wireguard-service
#         request_data = {"user_id": user_id}
#         if geolocation_id:
#             request_data["geolocation_id"] = geolocation_id
            
#         # Запрашиваем создание конфигурации у wireguard-service
#         wg_response = requests.post(
#             f"{WIREGUARD_SERVICE_URL}/create",
#             json=request_data,
#             timeout=30  # увеличиваем таймаут для надежности
#         )
        
#         logger.info(f"Ответ API wireguard-service: код {wg_response.status_code}")
        
#         if wg_response.status_code == 201:
#             wg_data = wg_response.json()
#             config_text = wg_data.get("config")
#             public_key = wg_data.get("public_key")
#             server_id = wg_data.get("server_id")
            
#             logger.info(f"Конфигурация получена успешно. Public key: {public_key}, Server ID: {server_id}")
            
#             # Рассчитываем дату истечения (7 дней от текущей даты)
#             expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
            
#             # Сохраняем в базе данных через database-service
#             logger.info(f"Сохраняем в БД. URL: {DATABASE_SERVICE_URL}/config")
            
#             db_data = {
#                 "user_id": user_id,
#                 "config": config_text,
#                 "expiry_time": expiry_time,
#                 "active": True
#             }
            
#             # Добавляем информацию о геолокации и сервере, если они указаны
#             if geolocation_id:
#                 db_data["geolocation_id"] = geolocation_id
#             if server_id:
#                 db_data["server_id"] = server_id
                
#             db_response = requests.post(
#                 f"{DATABASE_SERVICE_URL}/config",
#                 json=db_data,
#                 timeout=20
#             )
            
#             logger.info(f"Ответ API database-service: код {db_response.status_code}")
            
#             if db_response.status_code in [200, 201]:
#                 # Возвращаем успешный результат
#                 logger.info("Конфигурация успешно создана и сохранена в БД")
#                 return {
#                     "config_text": config_text,
#                     "public_key": public_key,
#                     "server_id": server_id,
#                     "geolocation_id": geolocation_id
#                 }
#             else:
#                 # Логируем ошибку сохранения в БД
#                 error_msg = f"Ошибка сохранения в БД: код {db_response.status_code}"
#                 if db_response.headers.get('content-type') == 'application/json':
#                     try:
#                         error_data = db_response.json()
#                         if "error" in error_data:
#                             error_msg = error_data.get("error")
#                     except Exception as e:
#                         logger.error(f"Ошибка при разборе JSON: {str(e)}")
                
#                 logger.error(error_msg)
#                 # Но все равно возвращаем конфигурацию, так как она создана успешно
#                 return {
#                     "config_text": config_text,
#                     "public_key": public_key,
#                     "server_id": server_id,
#                     "geolocation_id": geolocation_id
#                 }
        
#         # В случае ошибки от wireguard-service
#         error_message = "Ошибка при создании конфигурации."
#         if wg_response.headers.get('content-type') == 'application/json':
#             try:
#                 response_data = wg_response.json()
#                 if "error" in response_data:
#                     error_message = response_data.get("error")
#             except json.JSONDecodeError:
#                 pass
        
#         logger.error(f"Ошибка от wireguard-service: {error_message}")
#         return {"error": error_message}
#     except requests.RequestException as e:
#         logger.error(f"Ошибка при запросе к API: {str(e)}")
#         return {"error": f"Ошибка при создании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}
async def create_new_config(user_id, geolocation_id=None):
    """Создает новую конфигурацию WireGuard с возможностью выбора геолокации."""
    try:
        logger.info(f"Создание новой конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
        # Проверяем, есть ли уже активная конфигурация и деактивируем ее
        current_config = await get_user_config(user_id)
        if current_config and current_config.get("active") and current_config.get("public_key"):
            public_key = current_config.get("public_key")
            logger.info(f"Деактивируем существующую конфигурацию с public_key: {public_key}")
            
            import aiohttp
            import asyncio
            
            # Деактивируем через асинхронный запрос для лучшей производительности
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", 
                        timeout=10
                    ) as deactivate_response:
                        logger.info(f"Ответ API на деактивацию: код {deactivate_response.status}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации: {str(e)}")
                # Продолжаем, даже если деактивация не удалась
            
            # Деактивируем в базе данных для согласованности данных
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{DATABASE_SERVICE_URL}/config/deactivate",
                        json={"user_id": user_id},
                        timeout=10
                    ) as db_deactivate_response:
                        logger.info(f"Ответ API на деактивацию в БД: код {db_deactivate_response.status}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации в БД: {str(e)}")
        
        # Формируем данные для запроса к wireguard-service
        request_data = {"user_id": user_id}
        if geolocation_id:
            request_data["geolocation_id"] = geolocation_id
            
        # Используем aiohttp для асинхронных запросов
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Запрашиваем создание конфигурации у wireguard-service
            try:
                async with session.post(
                    f"{WIREGUARD_SERVICE_URL}/create",
                    json=request_data,
                    timeout=30
                ) as wg_response:
                    logger.info(f"Ответ API wireguard-service: код {wg_response.status}")
                    
                    if wg_response.status == 201:
                        wg_data = await wg_response.json()
                        config_text = wg_data.get("config")
                        public_key = wg_data.get("public_key")
                        server_id = wg_data.get("server_id")
                        
                        logger.info(f"Конфигурация получена успешно. Public key: {public_key}, Server ID: {server_id}")
                        
                        # Рассчитываем дату истечения (7 дней от текущей даты)
                        expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
                        
                        # Сохраняем в базе данных через database-service
                        logger.info(f"Сохраняем в БД. URL: {DATABASE_SERVICE_URL}/config")
                        
                        db_data = {
                            "user_id": user_id,
                            "config": config_text,
                            "public_key": public_key,  # Добавляем public_key для согласованности
                            "expiry_time": expiry_time,
                            "active": True
                        }
                        
                        # Добавляем информацию о геолокации и сервере, если они указаны
                        if geolocation_id:
                            db_data["geolocation_id"] = geolocation_id
                        if server_id:
                            db_data["server_id"] = server_id
                        
                        try:
                            async with session.post(
                                f"{DATABASE_SERVICE_URL}/config",
                                json=db_data,
                                timeout=20
                            ) as db_response:
                                logger.info(f"Ответ API database-service: код {db_response.status}")
                                
                                if db_response.status in [200, 201]:
                                    # Возвращаем успешный результат
                                    logger.info("Конфигурация успешно создана и сохранена в БД")
                                    return {
                                        "config_text": config_text,
                                        "public_key": public_key,
                                        "server_id": server_id,
                                        "geolocation_id": geolocation_id
                                    }
                                else:
                                    # Логируем ошибку сохранения в БД
                                    error_msg = f"Ошибка сохранения в БД: код {db_response.status}"
                                    response_text = await db_response.text()
                                    if db_response.headers.get('content-type') == 'application/json':
                                        try:
                                            error_data = await db_response.json()
                                            if "error" in error_data:
                                                error_msg = error_data.get("error")
                                        except Exception as e:
                                            logger.error(f"Ошибка при разборе JSON: {str(e)}")
                                    
                                    logger.error(f"{error_msg} - {response_text}")
                                    
                                    # В случае ошибки в БД, пытаемся откатить создание конфигурации
                                    logger.warning(f"Пытаемся удалить созданную конфигурацию из WireGuard из-за ошибки сохранения в БД")
                                    try:
                                        async with session.delete(
                                            f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", 
                                            timeout=10
                                        ) as rollback_response:
                                            logger.info(f"Ответ API на откат: код {rollback_response.status}")
                                    except Exception as rollback_error:
                                        logger.error(f"Ошибка при откате: {str(rollback_error)}")
                                    
                                    return {"error": error_msg}
                        except Exception as db_error:
                            logger.error(f"Ошибка при сохранении в БД: {str(db_error)}")
                            return {"error": f"Ошибка при сохранении конфигурации: {str(db_error)}"}
                    
                    # В случае ошибки от wireguard-service
                    error_message = "Ошибка при создании конфигурации."
                    response_text = await wg_response.text()
                    if wg_response.headers.get('content-type') == 'application/json':
                        try:
                            response_data = await wg_response.json()
                            if "error" in response_data:
                                error_message = response_data.get("error")
                        except Exception as json_error:
                            logger.error(f"Ошибка при разборе JSON: {str(json_error)}")
                    
                    logger.error(f"Ошибка от wireguard-service: {error_message} - {response_text}")
                    return {"error": error_message}
            except asyncio.TimeoutError:
                logger.error("Превышено время ожидания ответа от wireguard-service")
                return {"error": "Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже."}
            except Exception as request_error:
                logger.error(f"Ошибка при запросе к wireguard-service: {str(request_error)}")
                return {"error": f"Ошибка при создании конфигурации: {str(request_error)}"}
    except Exception as e:
        logger.error(f"Общая ошибка при создании конфигурации: {str(e)}")
        return {"error": f"Ошибка при создании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

async def are_servers_available():
    """Проверяет наличие доступных серверов."""
    try:
        # Получаем список серверов с wireguard-service
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{WIREGUARD_SERVICE_URL}/servers", 
                timeout=10
            ) as response:
                if response.status != 200:
                    logger.error(f"Ошибка при получении списка серверов: {response.status}")
                    return False
                
                servers_data = await response.json()
                servers = servers_data.get("servers", [])
                
                # Проверяем наличие активных серверов
                active_servers = [s for s in servers if s.get("active", False)]
                
                if not active_servers:
                    logger.info("Нет активных серверов")
                    return False
                
                logger.info(f"Доступно {len(active_servers)} активных серверов")
                return True
                
    except Exception as e:
        logger.error(f"Ошибка при проверке доступных серверов: {str(e)}")
        # В случае ошибки возвращаем False, чтобы предотвратить создание конфигурации
        return False

# Функция для пересоздания конфигурации
async def recreate_config(user_id, geolocation_id=None):
    """
    Пересоздает конфигурацию WireGuard с сохранением или изменением геолокации.
    Сохраняет текущий срок действия конфигурации, если она активна.
    
    Args:
        user_id (int): ID пользователя
        geolocation_id (int, optional): ID геолокации. Если не указан, 
                                        будет использована текущая локация.
        
    Returns:
        dict: Словарь с данными конфигурации или информацией об ошибке
    """
    try:
        logger.info(f"Пересоздание конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
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
                import requests
                deactivate_response = requests.delete(
                    f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", 
                    timeout=10
                )
                logger.info(f"Ответ API на деактивацию: код {deactivate_response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации: {str(e)}")
                # Продолжаем, даже если деактивация не удалась
        
        # Создаем новую конфигурацию с указанной геолокацией
        logger.info(f"Создаем новую конфигурацию для пользователя с геолокацией {geolocation_id}")
        
        # Формируем данные для запроса
        request_data = {"user_id": user_id}
        if geolocation_id:
            request_data["geolocation_id"] = geolocation_id
        
        logger.info(f"Отправляем запрос на создание с данными: {request_data}")
        
        # Отправляем запрос на создание новой конфигурации
        wg_response = requests.post(
            f"{WIREGUARD_SERVICE_URL}/create",
            json=request_data,
            timeout=30
        )
        
        logger.info(f"Ответ API wireguard-service: код {wg_response.status_code}")
        
        if wg_response.status_code == 201:
            try:
                wg_data = wg_response.json()
                config_text = wg_data.get("config")
                public_key = wg_data.get("public_key")
                server_id = wg_data.get("server_id")
                server_geolocation_id = wg_data.get("geolocation_id")  # Получаем ID геолокации из ответа
                
                logger.info(f"Конфигурация получена успешно. Public key: {public_key}, Server ID: {server_id}, Geolocation ID: {server_geolocation_id}")
                
                # Сохраняем в базе данных через database-service
                logger.info(f"Сохраняем в БД. URL: {DATABASE_SERVICE_URL}/config")
                
                db_data = {
                    "user_id": user_id,
                    "config": config_text,
                    "public_key": public_key,
                    "expiry_time": expiry_time,  # Используем сохраненное или новое время истечения
                    "active": True
                }
                
                # Добавляем информацию о геолокации и сервере
                if server_geolocation_id:  # Используем геолокацию из ответа сервера, если есть
                    db_data["geolocation_id"] = server_geolocation_id
                    logger.info(f"Используем геолокацию из ответа сервера: {server_geolocation_id}")
                elif geolocation_id:  # Иначе используем переданную геолокацию
                    db_data["geolocation_id"] = geolocation_id
                    logger.info(f"Используем переданную геолокацию: {geolocation_id}")
                if server_id:
                    db_data["server_id"] = server_id
                
                logger.info(f"Отправляем в БД данные: {db_data}")
                
                db_response = requests.post(
                    f"{DATABASE_SERVICE_URL}/config",
                    json=db_data,
                    timeout=20
                )
                
                logger.info(f"Ответ API database-service: код {db_response.status_code}")
                
                if db_response.status_code in [200, 201]:
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
                    try:
                        error_data = db_response.json()
                        if "error" in error_data:
                            error_message = error_data.get("error")
                        else:
                            error_message = f"Ошибка сохранения в БД: код {db_response.status_code}"
                    except:
                        error_message = f"Ошибка сохранения в БД: код {db_response.status_code}"
                    
                    logger.error(error_message)
                    return {"error": error_message}
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа wireguard-service: {str(e)}", exc_info=True)
                return {"error": f"Ошибка при обработке ответа сервера: {str(e)}"}
        
        # В случае ошибки от wireguard-service
        try:
            error_data = wg_response.json()
            if "error" in error_data:
                error_message = error_data.get("error")
            else:
                error_message = f"Ошибка при создании конфигурации: код {wg_response.status_code}"
        except:
            error_message = f"Ошибка при создании конфигурации: код {wg_response.status_code}"
        
        logger.error(error_message)
        return {"error": error_message}
        
    except Exception as e:
        logger.error(f"Ошибка при пересоздании конфигурации: {str(e)}", exc_info=True)
        return {"error": f"Ошибка при пересоздании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}
        

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
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DATABASE_SERVICE_URL}/servers/geolocation/{geolocation_id}",
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

# Добавим функцию для получения текущей локации пользователя
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

# Добавим функцию для обновления локации пользователя
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
        result = await db.configs.update_one(
            {"user_id": user_id},
            {"$set": {"location": location}}
        )
        
        if result.matched_count == 0:
            # Если запись не найдена, создаем новую с минимальными данными
            await db.configs.insert_one({
                "user_id": user_id,
                "location": location,
                "active": False
            })
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении локации пользователя: {str(e)}", exc_info=True)
        return False
        
# Функция для получения конфигурации из WireGuard сервиса
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
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для продления срока действия конфигурации
# async def extend_config(user_id, days, stars, transaction_id):
#     """Продлевает срок действия конфигурации."""
#     try:
#         logger.info(f"Продление конфигурации для пользователя {user_id} на {days} дней за {stars} звезд")
#         logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/config/extend")
        
#         response = requests.post(
#             f"{DATABASE_SERVICE_URL}/config/extend",
#             json={
#                 "user_id": user_id,
#                 "days": days,
#                 "stars_amount": stars,
#                 "transaction_id": transaction_id
#             },
#             timeout=10
#         )
        
#         logger.info(f"Ответ API: код {response.status_code}")
        
#         if response.status_code == 200:
#             logger.info("Конфигурация успешно продлена")
#             return response.json()
        
#         # Подробный вывод информации об ошибке
#         logger.error(f"Ошибка API: {response.status_code}, тело: {response.text}")
        
#         error_message = "Ошибка при продлении конфигурации. Обратитесь в поддержку."
#         if response.headers.get('content-type') == 'application/json':
#             try:
#                 response_data = response.json()
#                 if "error" in response_data:
#                     error_message = response_data.get("error")
#             except json.JSONDecodeError:
#                 pass
        
#         return {"error": error_message}
#     except requests.RequestException as e:
#         logger.error(f"Ошибка при запросе к API: {str(e)}")
#         return {"error": f"Ошибка при продлении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

async def extend_config(user_id, days, stars, transaction_id):
    """Продлевает срок действия конфигурации."""
    try:
        logger.info(f"Продление конфигурации для пользователя {user_id} на {days} дней за {stars} звезд")
        
        # Проверяем текущее состояние конфигурации
        current_config = await get_user_config(user_id)
        
        if not current_config:
            logger.warning(f"Не найдена конфигурация для пользователя {user_id}")
            return {"error": "Конфигурация не найдена. Пожалуйста, создайте новую."}
        
        if not current_config.get("active", False):
            logger.warning(f"Конфигурация пользователя {user_id} неактивна")
            return {"error": "Ваша конфигурация неактивна. Пожалуйста, создайте новую."}
        
        # Проверяем, не истекла ли уже конфигурация
        try:
            expiry_time = current_config.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                now = datetime.now()
                
                # Если конфигурация уже истекла, но все еще отмечена как активная
                if expiry_dt < now:
                    logger.warning(f"Конфигурация пользователя {user_id} истекла, но отмечена как активная")
                    
                    # Получаем данные конфигурации для проверки возможности продления
                    config_data = await get_config_from_wireguard(user_id)
                    
                    if "error" in config_data:
                        logger.error(f"Ошибка при получении конфигурации: {config_data['error']}")
                        return {"error": "Не удалось продлить истекшую конфигурацию. Пожалуйста, создайте новую."}
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при проверке срока действия: {str(e)}")
        
        # Выполняем продление
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DATABASE_SERVICE_URL}/config/extend",
                json={
                    "user_id": user_id,
                    "days": days,
                    "stars_amount": stars,
                    "transaction_id": transaction_id
                },
                timeout=15
            ) as response:
                
                logger.info(f"Ответ API: код {response.status}")
                
                if response.status == 200:
                    logger.info("Конфигурация успешно продлена")
                    return await response.json()
                
                # Подробный вывод информации об ошибке
                logger.error(f"Ошибка API: {response.status}, тело: {await response.text()}")
                
                error_message = "Ошибка при продлении конфигурации. Обратитесь в поддержку."
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
        return {"error": f"Ошибка при продлении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при продлении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для получения истории платежей
async def get_payment_history(user_id):
    """Получает историю платежей пользователя."""
    try:
        logger.info(f"Получение истории платежей для пользователя {user_id}")
        logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/payments/history/{user_id}")
        
        response = requests.get(f"{DATABASE_SERVICE_URL}/payments/history/{user_id}", timeout=10)
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        
        # Подробный вывод информации об ошибке
        logger.error(f"Ошибка API: {response.status_code}, тело: {response.text}")
        
        return {"error": "Не удалось получить историю платежей. Попробуйте позже."}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении истории платежей: {str(e)}. Пожалуйста, попробуйте позже."}
