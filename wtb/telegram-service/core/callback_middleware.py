from aiogram import types, Bot
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import logging
import uuid
import asyncio
import time

from utils.bd import get_user_config, create_new_config, get_config_from_wireguard
from utils.qr import generate_config_qr

class CallbackMiddleware(BaseMiddleware):
    """Middleware для обработки колбэков напрямую."""
    
    def __init__(self, bot: Bot, logger):
        """Инициализирует middleware с объектом бота и логгером."""
        self.bot = bot
        self.logger = logger
        # Словарь для отслеживания обрабатываемых колбэков
        self.processing_callbacks = {}
        super(CallbackMiddleware, self).__init__()
    
    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        """Обрабатывает колбэки перед основной диспетчеризацией."""
        callback_id = callback_query.id
        callback_data = callback_query.data
        user_id = callback_query.from_user.id
        
        # Создаем уникальный ключ для отслеживания обработки
        tracking_key = f"{user_id}:{callback_data}:{callback_id}"
        
        # Проверяем, обрабатывается ли уже такой колбэк
        if getattr(callback_query, '_handled', False) or data.get('_handled', False):
            self.logger.info(f"Колбэк {callback_data} (ID: {callback_id}) уже обработан, пропускаем")
            return True
            
        # Проверяем, есть ли уже такой callback в обработке
        if tracking_key in self.processing_callbacks:
            self.logger.info(f"Колбэк {callback_data} (ID: {callback_id}) уже в процессе обработки, пропускаем")
            return True
            
        # Добавляем в список обрабатываемых
        self.processing_callbacks[tracking_key] = datetime.now()
        callback_query._processing_key = tracking_key
        
        self.logger.info(f"Middleware: получен колбэк {callback_data} (ID: {callback_id}, Key: {tracking_key})")
        
        # Обрабатываем различные типы колбэков
        try:
            # direct_create - обработка создания конфигурации
            if callback_data == "direct_create":
                result = await self._handle_direct_create(callback_query)
                if result:
                    self._mark_as_handled(callback_query, data)
                    return True
                    
            # direct_cancel - отмена создания конфигурации    
            elif callback_data == "direct_cancel":
                result = await self._handle_direct_cancel(callback_query)
                if result:
                    self._mark_as_handled(callback_query, data)
                    return True
                    
            # get_config - получение конфигурации
            elif callback_data == "get_config":
                result = await self._handle_get_config(callback_query)
                if result:
                    self._mark_as_handled(callback_query, data)
                    return True
                    
            # status - проверка статуса
            elif callback_data == "status":
                result = await self._handle_status(callback_query)
                if result:
                    self._mark_as_handled(callback_query, data)
                    return True
                    
            # start_extend - обработка продления
            elif callback_data == "start_extend":
                # Этот колбэк не обрабатываем в middleware, передаем обработчикам
                self.logger.info("Middleware: получен колбэк start_extend, передаем в обработчики")
                self._cleanup_tracking(callback_query)
                return None
        
        except Exception as e:
            self.logger.error(f"Middleware: ошибка при обработке колбэка {callback_data}: {str(e)}", exc_info=True)
            # Отправляем сообщение пользователю о непредвиденной ошибке
            try:
                await self.bot.send_message(
                    user_id,
                    "❌ <b>Произошла непредвиденная ошибка</b>\n\n"
                    "Пожалуйста, попробуйте позже или используйте другую команду.",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            # Очищаем информацию о колбэке
            self._cleanup_tracking(callback_query)
            self._mark_as_handled(callback_query, data)
            return True
        
        # Если колбэк не обработан middleware, очищаем tracking
        self._cleanup_tracking(callback_query)
        return None  # Продолжаем обработку другими обработчиками
    
    def _mark_as_handled(self, callback_query, data):
        """Помечает колбэк как обработанный."""
        callback_query._handled = True
        data['_handled'] = True
        self._cleanup_tracking(callback_query)
        
    def _cleanup_tracking(self, callback_query):
        """Очищает информацию об обрабатываемом колбэке."""
        tracking_key = getattr(callback_query, '_processing_key', None)
        if tracking_key and tracking_key in self.processing_callbacks:
            del self.processing_callbacks[tracking_key]
    
    async def _handle_direct_create(self, callback_query: types.CallbackQuery):
        """Обработчик создания конфигурации."""
        self.logger.info("Middleware: обрабатываем колбэк direct_create")
        
        # Отвечаем на колбэк, чтобы убрать часы ожидания
        await self.bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id
        
        # Сообщаем пользователю о начале процесса создания
        await self.bot.edit_message_text(
            "🔄 <b>Создание конфигурации...</b>\n\n"
            "Пожалуйста, подождите. Это может занять несколько секунд.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Устанавливаем таймаут для операции создания
            create_task = asyncio.create_task(create_new_config(user_id))
            try:
                config_data = await asyncio.wait_for(create_task, timeout=30)
            except asyncio.TimeoutError:
                await self.bot.edit_message_text(
                    "⚠️ <b>Превышено время ожидания</b>\n\n"
                    "Сервер слишком долго не отвечает. Пожалуйста, попробуйте позже.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
                return True
            
            if "error" in config_data:
                await self.bot.edit_message_text(
                    f"❌ <b>Ошибка!</b>\n\n{config_data['error']}",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
                return True
            
            config_text = config_data.get("config_text")
            
            if not config_text:
                await self.bot.edit_message_text(
                    "❌ <b>Ошибка при создании конфигурации</b>\n\n"
                    "Пожалуйста, попробуйте позже.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.HTML
                )
                return True
            
            # Получаем данные о сроке действия из базы данных с таймаутом
            get_config_task = asyncio.create_task(get_user_config(user_id))
            try:
                db_data = await asyncio.wait_for(get_config_task, timeout=10)
            except asyncio.TimeoutError:
                db_data = None
                self.logger.warning(f"Таймаут при получении данных конфигурации для пользователя {user_id}")
            
            expiry_text = ""
            if db_data:
                expiry_time = db_data.get("expiry_time")
                if expiry_time:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_time)
                        expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                        expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
                    except ValueError:
                        self.logger.error(f"Ошибка при парсинге даты: {expiry_time}")
            
            # Создаем файл конфигурации
            config_file = BytesIO(config_text.encode('utf-8'))
            config_file.name = f"vpn_duck_{user_id}.conf"
            
            # Генерируем QR-код с таймаутом
            qr_task = asyncio.create_task(generate_config_qr(config_text))
            try:
                qr_buffer = await asyncio.wait_for(qr_task, timeout=10)
            except asyncio.TimeoutError:
                qr_buffer = None
                self.logger.warning(f"Таймаут при генерации QR-кода для пользователя {user_id}")
            
            # Обновляем сообщение об успешном создании
            await self.bot.edit_message_text(
                f"✅ <b>Конфигурация успешно создана!</b>\n\n"
                f"{expiry_text}\n"
                f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            
            if qr_buffer:
                # Отправляем QR-код
                await self.bot.send_photo(
                    user_id,
                    qr_buffer,
                    caption="🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
                            "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                    parse_mode=ParseMode.HTML
                )
            
            # Отправляем файл конфигурации
            await self.bot.send_document(
                user_id,
                config_file,
                caption="📋 <b>Файл конфигурации WireGuard</b>\n\n"
                        "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем инструкции
            instructions_text = (
                "📱 <b>Как использовать конфигурацию:</b>\n\n"
                "1️⃣ Установите приложение WireGuard на ваше устройство\n"
                "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
                "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
                "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
                "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
            )
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend")
            )
            
            await self.bot.send_message(
                user_id,
                instructions_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            
            return True
                
        except Exception as e:
            self.logger.error(f"Middleware: ошибка при создании конфигурации: {str(e)}", exc_info=True)
            await self.bot.edit_message_text(
                "❌ <b>Произошла ошибка</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            
            return True
    
    async def _handle_direct_cancel(self, callback_query: types.CallbackQuery):
        """Обработчик отмены создания конфигурации."""
        self.logger.info("Middleware: обрабатываем колбэк direct_cancel")
        
        await self.bot.answer_callback_query(callback_query.id)
        
        await self.bot.edit_message_text(
            "❌ Создание конфигурации отменено.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
        )
        
        return True
    
    async def _handle_get_config(self, callback_query: types.CallbackQuery):
        """Обработчик получения конфигурации."""
        self.logger.info("Middleware: обрабатываем колбэк get_config")
        
        await self.bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id
        
        try:
            # Запрашиваем данные о конфигурации с таймаутом
            get_config_task = asyncio.create_task(get_config_from_wireguard(user_id))
            try:
                config_data = await asyncio.wait_for(get_config_task, timeout=15)
            except asyncio.TimeoutError:
                await self.bot.send_message(
                    user_id,
                    "⚠️ <b>Превышено время ожидания при получении конфигурации</b>\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.HTML
                )
                return True
            
            if "error" in config_data:
                await self.bot.send_message(
                    user_id,
                    f"⚠️ <b>Ошибка при получении конфигурации</b>\n\n{config_data['error']}",
                    parse_mode=ParseMode.HTML
                )
                return True
            
            config_text = config_data.get("config_text")
            
            if not config_text:
                await self.bot.send_message(
                    user_id,
                    "⚠️ <b>Ошибка при получении конфигурации</b>\n\n"
                    "Конфигурация не найдена. Пожалуйста, создайте новую с помощью команды /create.",
                    parse_mode=ParseMode.HTML
                )
                return True
            
            # Создаем файл конфигурации
            config_file = BytesIO(config_text.encode('utf-8'))
            config_file.name = f"vpn_duck_{user_id}.conf"
            
            # Генерируем QR-код с таймаутом
            qr_task = asyncio.create_task(generate_config_qr(config_text))
            try:
                qr_buffer = await asyncio.wait_for(qr_task, timeout=10)
            except asyncio.TimeoutError:
                qr_buffer = None
                self.logger.warning(f"Таймаут при генерации QR-кода для пользователя {user_id}")
            
            if qr_buffer:
                # Отправляем QR-код
                await self.bot.send_photo(
                    user_id,
                    qr_buffer,
                    caption="🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
                            "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                    parse_mode=ParseMode.HTML
                )
            
            # Отправляем файл конфигурации
            await self.bot.send_document(
                user_id,
                config_file,
                caption="📋 <b>Файл конфигурации WireGuard</b>\n\n"
                        "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем инструкции
            instructions_text = (
                "📱 <b>Как использовать конфигурацию:</b>\n\n"
                "1️⃣ Установите приложение WireGuard на ваше устройство\n"
                "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
                "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
                "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
                "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
            )
            
            await self.bot.send_message(
                user_id,
                instructions_text,
                parse_mode=ParseMode.HTML
            )
            
            return True
                
        except Exception as e:
            self.logger.error(f"Middleware: ошибка при получении конфигурации: {str(e)}", exc_info=True)
            await self.bot.send_message(
                user_id,
                "❌ <b>Ошибка при получении конфигурации</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            
            return True
    
    async def _handle_status(self, callback_query: types.CallbackQuery):
        """Обработчик проверки статуса."""
        self.logger.info("Middleware: обрабатываем колбэк status")
        
        await self.bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id
        
        try:
            # Запрашиваем данные о конфигурации с таймаутом
            get_config_task = asyncio.create_task(get_user_config(user_id))
            try:
                config = await asyncio.wait_for(get_config_task, timeout=10)
            except asyncio.TimeoutError:
                await self.bot.send_message(
                    user_id,
                    "⚠️ <b>Превышено время ожидания при получении статуса</b>\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.HTML
                )
                return True
            
            if config and config.get("active", False):
                # Безопасное извлечение и форматирование дат
                try:
                    expiry_time = datetime.fromisoformat(config.get("expiry_time"))
                    expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
                    
                    # Расчет оставшегося времени
                    now = datetime.now()
                    remaining_time = expiry_time - now
                    remaining_days = max(0, remaining_time.days)
                    remaining_hours = max(0, remaining_time.seconds // 3600)
                except (ValueError, TypeError):
                    self.logger.error(f"Ошибка при парсинге даты: {config.get('expiry_time')}")
                    expiry_formatted = "неизвестно"
                    remaining_days = 0
                    remaining_hours = 0
                
                # Получаем информацию о геолокации
                geolocation_name = config.get("geolocation_name", "Неизвестно")
                
                await self.bot.send_message(
                    user_id,
                    f"📊 <b>Статус вашей конфигурации</b>\n\n"
                    f"▫️ Активна: <b>Да</b>\n"
                    f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
                    f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n"
                    f"▫️ Геолокация: <b>{geolocation_name}</b>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await self.bot.send_message(
                    user_id,
                    "❌ <b>У вас нет активной конфигурации</b>\n\n"
                    "Создайте новую с помощью команды /create.",
                    parse_mode=ParseMode.HTML
                )
                
            return True
        except Exception as e:
            self.logger.error(f"Middleware: ошибка при получении данных о конфигурации: {str(e)}", exc_info=True)
            await self.bot.send_message(
                user_id,
                "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            
            return True