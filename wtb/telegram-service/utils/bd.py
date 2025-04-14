import logging
import requests
import json
from datetime import datetime, timedelta
from core.settings import DATABASE_SERVICE_URL, WIREGUARD_SERVICE_URL, logger




# Функция для получения доступных геолокаций
async def get_available_geolocations():
    """Получает список доступных геолокаций из базы данных."""
    try:
        logger.info("Получение доступных геолокаций")
        
        response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations/available", timeout=10)
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json().get("geolocations", [])
        
        # Подробный вывод информации об ошибке
        logger.error(f"Ошибка API: {response.status_code}, тело: {response.text}")
        
        return []
    except requests.RequestException as e:
        logger.error(f"Ошибка запроса доступных геолокаций: {str(e)}")
        return []

# Функция для изменения геолокации конфигурации пользователя
async def change_config_geolocation(user_id, geolocation_id, server_id=None):
    """Изменяет геолокацию активной конфигурации пользователя."""
    try:
        logger.info(f"Изменение геолокации для пользователя {user_id} на {geolocation_id}")
        
        # Формируем данные запроса
        data = {
            "user_id": user_id,
            "geolocation_id": geolocation_id
        }
        
        # Если указан конкретный сервер, добавляем его ID
        if server_id:
            data["server_id"] = server_id
        
        # Отправляем запрос на изменение геолокации
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/configs/change_geolocation",
            json=data,
            timeout=30
        )
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        
        # Подробный вывод информации об ошибке
        error_message = "Ошибка при изменении геолокации."
        if response.headers.get('content-type') == 'application/json':
            try:
                response_data = response.json()
                if "error" in response_data:
                    error_message = response_data.get("error")
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Ошибка API: {error_message}")
        return {"error": error_message}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при изменении геолокации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для получения всех конфигураций пользователя
async def get_all_user_configs(user_id):
    """Получает все конфигурации пользователя из базы данных."""
    try:
        logger.info(f"Получение всех конфигураций для пользователя {user_id}")
        
        response = requests.get(f"{DATABASE_SERVICE_URL}/configs/get_all/{user_id}", timeout=15)
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        
        # Подробный вывод информации об ошибке
        error_message = "Ошибка при получении конфигураций."
        if response.headers.get('content-type') == 'application/json':
            try:
                response_data = response.json()
                if "error" in response_data:
                    error_message = response_data.get("error")
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Ошибка API: {error_message}")
        return {"error": error_message}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении конфигураций: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для получения конфигурации пользователя
async def get_user_config(user_id):
    """Получает конфигурацию пользователя из базы данных."""
    try:
        logger.info(f"Получение конфигурации для пользователя {user_id}")
        logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/config/{user_id}")
        
        response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}", timeout=10)
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
            
        # Подробный вывод информации об ошибке
        if response.status_code != 404:  # 404 - нормальный ответ, если конфиг не найден
            logger.error(f"Ошибка API: {response.status_code}, тело: {response.text}")
            
        return None
    except requests.RequestException as e:
        logger.error(f"Ошибка запроса конфигурации пользователя: {str(e)}")
        return None

# # Функция для создания новой конфигурации
# async def create_new_config(user_id):
#     """Создает новую конфигурацию WireGuard."""
#     try:
#         logger.info(f"Создание новой конфигурации для пользователя {user_id}")
#         logger.info(f"Используем URL wireguard-service: {WIREGUARD_SERVICE_URL}/create")
        
#         # Сначала запрашиваем создание конфигурации у wireguard-service
#         wg_response = requests.post(
#             f"{WIREGUARD_SERVICE_URL}/create",
#             json={"user_id": user_id},
#             timeout=30  # увеличиваем таймаут для надежности
#         )
        
#         logger.info(f"Ответ API wireguard-service: код {wg_response.status_code}")
        
#         if wg_response.status_code == 201:
#             wg_data = wg_response.json()
#             config_text = wg_data.get("config")
#             public_key = wg_data.get("public_key")
            
#             logger.info(f"Конфигурация получена успешно. Public key: {public_key}")
            
#             # Рассчитываем дату истечения (7 дней от текущей даты)
#             expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
            
#             # Сохраняем в базе данных через database-service
#             logger.info(f"Сохраняем в БД. URL: {DATABASE_SERVICE_URL}/config")
            
#             db_response = requests.post(
#                 f"{DATABASE_SERVICE_URL}/config",
#                 json={
#                     "user_id": user_id,
#                     "config": config_text,
#                     "expiry_time": expiry_time,
#                     "active": True
#                 },
#                 timeout=20
#             )
            
#             logger.info(f"Ответ API database-service: код {db_response.status_code}")
            
#             if db_response.status_code in [200, 201]:
#                 # Возвращаем успешный результат
#                 logger.info("Конфигурация успешно создана и сохранена в БД")
#                 return {
#                     "config_text": config_text,
#                     "public_key": public_key
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
#                     "public_key": public_key
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

# Функция для создания новой конфигурации
async def create_new_config(user_id, geolocation_id=None):
    """Создает новую конфигурацию WireGuard с возможностью выбора геолокации."""
    try:
        logger.info(f"Создание новой конфигурации для пользователя {user_id} с геолокацией {geolocation_id}")
        
        # Формируем данные для запроса к wireguard-service
        request_data = {"user_id": user_id}
        if geolocation_id:
            request_data["geolocation_id"] = geolocation_id
            
        # Запрашиваем создание конфигурации у wireguard-service
        wg_response = requests.post(
            f"{WIREGUARD_SERVICE_URL}/create",
            json=request_data,
            timeout=30  # увеличиваем таймаут для надежности
        )
        
        logger.info(f"Ответ API wireguard-service: код {wg_response.status_code}")
        
        if wg_response.status_code == 201:
            wg_data = wg_response.json()
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
                "expiry_time": expiry_time,
                "active": True
            }
            
            # Добавляем информацию о геолокации и сервере, если они указаны
            if geolocation_id:
                db_data["geolocation_id"] = geolocation_id
            if server_id:
                db_data["server_id"] = server_id
                
            db_response = requests.post(
                f"{DATABASE_SERVICE_URL}/config",
                json=db_data,
                timeout=20
            )
            
            logger.info(f"Ответ API database-service: код {db_response.status_code}")
            
            if db_response.status_code in [200, 201]:
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
                error_msg = f"Ошибка сохранения в БД: код {db_response.status_code}"
                if db_response.headers.get('content-type') == 'application/json':
                    try:
                        error_data = db_response.json()
                        if "error" in error_data:
                            error_msg = error_data.get("error")
                    except Exception as e:
                        logger.error(f"Ошибка при разборе JSON: {str(e)}")
                
                logger.error(error_msg)
                # Но все равно возвращаем конфигурацию, так как она создана успешно
                return {
                    "config_text": config_text,
                    "public_key": public_key,
                    "server_id": server_id,
                    "geolocation_id": geolocation_id
                }
        
        # В случае ошибки от wireguard-service
        error_message = "Ошибка при создании конфигурации."
        if wg_response.headers.get('content-type') == 'application/json':
            try:
                response_data = wg_response.json()
                if "error" in response_data:
                    error_message = response_data.get("error")
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Ошибка от wireguard-service: {error_message}")
        return {"error": error_message}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при создании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для пересоздания конфигурации
async def recreate_config(user_id):
    """Пересоздает конфигурацию WireGuard."""
    try:
        logger.info(f"Пересоздание конфигурации для пользователя {user_id}")
        
        # Получаем текущую конфигурацию
        current_config = await get_user_config(user_id)
        
        if current_config and current_config.get("public_key"):
            # Деактивируем текущую конфигурацию в WireGuard
            public_key = current_config.get("public_key")
            logger.info(f"Деактивация текущей конфигурации с public_key: {public_key}")
            
            try:
                logger.info(f"Отправляем запрос на удаление: {WIREGUARD_SERVICE_URL}/remove/{public_key}")
                deactivate_response = requests.delete(
                    f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", 
                    timeout=10
                )
                logger.info(f"Ответ API на деактивацию: код {deactivate_response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при деактивации: {str(e)}")
                # Продолжаем, даже если деактивация не удалась
        
        # Создаем новую конфигурацию (с сохранением в БД)
        logger.info("Создаем новую конфигурацию для пользователя")
        return await create_new_config(user_id)
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при пересоздании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

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
async def extend_config(user_id, days, stars, transaction_id):
    """Продлевает срок действия конфигурации."""
    try:
        logger.info(f"Продление конфигурации для пользователя {user_id} на {days} дней за {stars} звезд")
        logger.info(f"Используем URL: {DATABASE_SERVICE_URL}/config/extend")
        
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/config/extend",
            json={
                "user_id": user_id,
                "days": days,
                "stars_amount": stars,
                "transaction_id": transaction_id
            },
            timeout=10
        )
        
        logger.info(f"Ответ API: код {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Конфигурация успешно продлена")
            return response.json()
        
        # Подробный вывод информации об ошибке
        logger.error(f"Ошибка API: {response.status_code}, тело: {response.text}")
        
        error_message = "Ошибка при продлении конфигурации. Обратитесь в поддержку."
        if response.headers.get('content-type') == 'application/json':
            try:
                response_data = response.json()
                if "error" in response_data:
                    error_message = response_data.get("error")
            except json.JSONDecodeError:
                pass
        
        return {"error": error_message}
    except requests.RequestException as e:
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
