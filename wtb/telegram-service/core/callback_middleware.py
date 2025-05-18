from aiogram import types, Bot, Dispatcher
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import logging
import uuid
import asyncio
import time
from keyboards.keyboards import get_active_config_keyboard, get_create_config_keyboard
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard
from utils.qr import generate_config_qr
# Импортируем API_HEADERS из настроек
from core.settings import bot, logger, API_HEADERS
from utils.bd import get_user_config, create_new_config, get_config_from_wireguard, are_servers_available


# Прямой обработчик для создания конфигурации
async def direct_create_handler(callback_query: types.CallbackQuery):
    """Обработчик прямого создания конфигурации."""
    logger.info(f"Вызван direct_create_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    # Помечаем колбэк как обработанный
    callback_query._handled = True
    
    # В случае если ни одна проверка не сработала, продолжаем обычную обработку
    logger.info("Обрабатываем колбэк в прямом обработчике")
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    
    # Проверяем наличие доступных серверов
    try:
        servers_available = await are_servers_available()
        
        if not servers_available:
            # Если серверов нет, выводим сообщение пользователю
            await bot.edit_message_text(
                "⚠️ <b>Создание конфигурации невозможно</b>\n\n"
                "В данный момент нет доступных серверов. "
                "Сервис находится в тестовом режиме.\n\n"
                "Пожалуйста, попробуйте позже, когда серверы будут доступны.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке доступных серверов: {str(e)}")
        # В случае ошибки продолжаем, так как это может быть проблема с API
    
    # Сообщаем пользователю о начале процесса создания
    await bot.edit_message_text(
        "🔄 <b>Создание конфигурации...</b>\n\n"
        "Пожалуйста, подождите. Это может занять несколько секунд.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем новую конфигурацию
        config_data = await create_new_config(user_id)
        
        if "error" in config_data:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{config_data['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        config_text = config_data.get("config_text")
        
        if not config_text:
            await bot.edit_message_text(
                "❌ <b>Ошибка при создании конфигурации</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем данные о сроке действия из базы данных
        db_data = await get_user_config(user_id)
        
        expiry_text = ""
        if db_data:
            expiry_time = db_data.get("expiry_time")
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                expiry_text = f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
        
        # Создаем файл конфигурации
        config_file = BytesIO(config_text.encode('utf-8'))
        config_file.name = f"vpn_duck_{user_id}.conf"
        
        # Генерируем QR-код
        qr_buffer = await generate_config_qr(config_text)
        
        # Обновляем сообщение об успешном создании
        await bot.edit_message_text(
            f"✅ <b>Конфигурация успешно создана!</b>\n\n"
            f"{expiry_text}\n"
            f"⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
            f"Сервис находится в тестовом режиме.\n\n"
            f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        if qr_buffer:
            # Отправляем QR-код
            await bot.send_photo(
                user_id,
                qr_buffer,
                caption="🔑 <b>QR-код вашей конфигурации WireGuard</b>\n\n"
                        "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем файл конфигурации
        await bot.send_document(
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
            "⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
            "Сервис находится в тестовом режиме.\n\n"
            "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
        )
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить конфигурацию", callback_data="start_extend")
        )
        
        await bot.send_message(
            user_id,
            instructions_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        await bot.edit_message_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )

# Прямой обработчик для отмены создания конфигурации
async def direct_cancel_handler(callback_query: types.CallbackQuery):
    """Обработчик прямой отмены создания."""
    logger.info(f"Вызван direct_cancel_handler с данными: {callback_query.data}")
    
    # ВАЖНО: Проверяем, был ли колбэк уже обработан middleware
    if getattr(callback_query, '_handled', False):
        logger.info("Колбэк уже обработан middleware, пропускаем")
        return
    
    # Помечаем колбэк как обработанный
    callback_query._handled = True
    
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Создание конфигурации отменено.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )

def register_direct_handlers(dp: Dispatcher):
    """Регистрирует прямые обработчики."""
    # Регистрация прямых обработчиков
    dp.register_callback_query_handler(
        direct_create_handler,
        lambda c: c.data == 'direct_create',
        state='*'
    )
    dp.register_callback_query_handler(
        direct_cancel_handler,
        lambda c: c.data == 'direct_cancel',
        state='*'
    )

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
        
        if callback_data in ["direct_create", "direct_cancel"]:
            self.logger.info(f"Middleware: колбэк {callback_data} будет обработан прямым обработчиком")
            # НЕ ПОМЕЧАЕМ как handled, чтобы прямой обработчик мог его обработать
            self._cleanup_tracking(callback_query)
            return None

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
        
        # Проверяем, должен ли колбэк обрабатываться прямыми обработчиками
        if callback_data in ["direct_create", "direct_cancel"]:
            self.logger.info(f"Middleware: колбэк {callback_data} будет обработан прямым обработчиком")
            self._cleanup_tracking(callback_query)
            return None


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
                    
            # # start_extend - обработка продления
            # elif callback_data == "start_extend":
            #     # Этот колбэк не обрабатываем в middleware, передаем обработчикам
            #     self.logger.info("Middleware: получен колбэк start_extend, передаем в обработчики")
            #     self._cleanup_tracking(callback_query)
            #     return None
        
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
    
    def get_active_config_keyboard(self):
        """Возвращает клавиатуру для активной конфигурации."""
        return get_active_config_keyboard()
    
    def get_create_config_keyboard(self):
        """Возвращает клавиатуру для создания конфигурации."""
        return get_create_config_keyboard()
    
    async def _handle_status(self, callback_query: types.CallbackQuery):
        """Обработчик проверки статуса (расширенный с клавиатурой)."""
        self.logger.info("Middleware: обрабатываем колбэк status")

        await self.bot.answer_callback_query(callback_query.id)
        user_id = callback_query.from_user.id

        try:
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
                try:
                    created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
                except (ValueError, TypeError):
                    created_at = "Неизвестно"

                try:
                    expiry_time = datetime.fromisoformat(config.get("expiry_time"))
                    expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")

                    now = datetime.now()
                    remaining_time = expiry_time - now
                    remaining_days = max(0, remaining_time.days)
                    remaining_hours = max(0, remaining_time.seconds // 3600)
                except (ValueError, TypeError):
                    self.logger.error(f"Ошибка при парсинге даты: {config.get('expiry_time')}")
                    expiry_formatted = "неизвестно"
                    remaining_days = 0
                    remaining_hours = 0

                geolocation_name = config.get("geolocation_name", "Неизвестно")

                status_text = (
                    f"📊 <b>Статус вашей конфигурации WireGuard</b>\n\n"
                    f"▫️ Активна: <b>Да</b>\n"
                    f"▫️ Создана: <b>{created_at}</b>\n"
                    f"▫️ Действует до: <b>{expiry_formatted}</b>\n"
                    f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n"
                    f"▫️ Геолокация: <b>{geolocation_name}</b>\n\n"
                    f"⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
                    f"Сервис находится в тестовом режиме."
                )

                keyboard = self.get_active_config_keyboard()

                await self.bot.send_message(
                    user_id,
                    status_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            else:
                keyboard = self.get_create_config_keyboard()

                await self.bot.send_message(
                    user_id,
                    "❌ <b>У вас нет активной конфигурации</b>\n\n"
                    "Создайте новую с помощью команды /create или кнопки ниже.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
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
                f"⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
                f"Мы работаем над расширением нашей сети. "
                f"Следите за обновлениями!\n\n"
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
                "⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
                "Сервис находится в тестовом режиме.\n\n"
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
            # Проверка наличия серверов
            try:
                # Здесь можно добавить проверку на наличие серверов
                servers_available = await are_servers_available()
                if not servers_available:
                    await self.bot.send_message(
                        user_id,
                        "⚠️ <b>Получение конфигурации невозможно</b>\n\n"
                        "В данный момент нет доступных серверов. "
                        "Сервис находится в тестовом режиме.\n\n"
                        "Пожалуйста, попробуйте позже, когда серверы будут доступны.",
                        parse_mode=ParseMode.HTML
                    )
                    return True
                    
            except Exception as e:
                self.logger.error(f"Ошибка при проверке серверов: {str(e)}")
                # Продолжаем работу, возможно серверы есть
            
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
                "⚠️ <b>Внимание:</b> В данный момент настроенных серверов нет. "
                "Сервис находится в тестовом режиме.\n\n"
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