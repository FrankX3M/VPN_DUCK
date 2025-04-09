import logging
import requests
import json
from datetime import datetime
from core.settings import DATABASE_SERVICE_URL, WIREGUARD_SERVICE_URL, logger

# Функция для получения конфигурации пользователя
async def get_user_config(user_id):
    """Получает конфигурацию пользователя из базы данных."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/config/{user_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        logger.error(f"Ошибка запроса конфигурации пользователя: {str(e)}")
        return None

# Функция для эмуляции получения баланса Telegram Stars
async def get_stars_balance(user_id):
    """
    Эта функция не может напрямую получить баланс Telegram Stars пользователя.
    
    Согласно документации Telegram Bot API, нет прямого метода для проверки баланса звезд.
    Вместо этого мы должны использовать процесс создания инвойса и проверки возможности оплаты
    через pre_checkout_query.
    
    Возвращаем условное значение для продолжения работы бота.
    """
    logger.warning("Прямая проверка баланса звезд через API не доступна")
    return 10000  # Возвращаем условное значение

# Функция для создания новой конфигурации
async def create_new_config(user_id):
    """Создает новую конфигурацию WireGuard."""
    try:
        # Исправленный URL для создания конфигурации
        response = requests.post(
            f"{WIREGUARD_SERVICE_URL}/create",
            json={"user_id": user_id},
            timeout=20
        )
        
        if response.status_code == 201:  # Учитываем, что сервис возвращает 201 Created
            data = response.json()
            # Преобразуем ответ в нужный формат для бота
            return {
                "config_text": data.get("config"),
                "public_key": data.get("public_key")
            }
        
        error_message = "Ошибка при создании конфигурации."
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
        return {"error": f"Ошибка при создании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для пересоздания конфигурации
async def recreate_config(user_id):
    """Пересоздает конфигурацию WireGuard."""
    try:
        # Сначала получаем текущую конфигурацию для получения public_key
        current_config = await get_user_config(user_id)
        
        if current_config and current_config.get("public_key"):
            # Деактивируем текущую конфигурацию
            public_key = current_config.get("public_key")
            requests.delete(f"{WIREGUARD_SERVICE_URL}/remove/{public_key}", timeout=10)
        
        # Создаем новую конфигурацию
        return await create_new_config(user_id)
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при пересоздании конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для получения конфигурации из WireGuard сервиса
async def get_config_from_wireguard(user_id):
    """Получает конфигурацию из WireGuard сервиса."""
    try:
        # Получаем информацию о конфигурации пользователя из базы данных
        config_info = await get_user_config(user_id)
        
        if not config_info or not config_info.get("active"):
            return {"error": "Активная конфигурация не найдена"}
        
        # Конфигурация хранится непосредственно в БД
        config_text = config_info.get("config")
        
        if not config_text:
            return {"error": "Текст конфигурации отсутствует в базе данных"}
        
        return {"config_text": config_text}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении конфигурации: {str(e)}. Пожалуйста, попробуйте позже."}

# Функция для продления срока действия конфигурации
async def extend_config(user_id, days, stars, transaction_id):
    """Продлевает срок действия конфигурации."""
    try:
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
        
        if response.status_code == 200:
            return response.json()
        
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
        response = requests.get(f"{DATABASE_SERVICE_URL}/payments/history/{user_id}", timeout=5)
        
        if response.status_code == 200:
            return response.json()
        
        return {"error": "Не удалось получить историю платежей. Попробуйте позже."}
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return {"error": f"Ошибка при получении истории платежей: {str(e)}. Пожалуйста, попробуйте позже."}