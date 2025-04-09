from aiogram import types, Bot
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from io import BytesIO
import logging

from utils.bd import get_user_config, create_new_config, get_config_from_wireguard
from utils.qr import generate_config_qr

class CallbackMiddleware(BaseMiddleware):
    """Middleware для обработки колбэков напрямую."""
    
    def __init__(self, bot: Bot, logger):
        """Инициализирует middleware с объектом бота и логгером."""
        self.bot = bot
        self.logger = logger
        super(CallbackMiddleware, self).__init__()
    
    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        """Обрабатывает колбэки перед основной диспетчеризацией."""
        # Проверяем, обрабатывался ли уже этот callback
        if getattr(callback_query, '_handled', False) or data.get('_handled', False):
            self.logger.info(f"Колбэк {callback_query.data} уже был обработан, пропускаем")
            return True
            
        self.logger.info(f"Middleware: получен колбэк {callback_query.data}")
        
        # Обрабатываем колбэк direct_create
        if callback_query.data == "direct_create":
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
                # Создаем новую конфигурацию
                config_data = await create_new_config(user_id)
                
                if "error" in config_data:
                    await self.bot.edit_message_text(
                        f"❌ <b>Ошибка!</b>\n\n{config_data['error']}",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        parse_mode=ParseMode.HTML
                    )
                    # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ для обхода ошибки aiogram
                    data['_handled'] = True
                    callback_query._handled = True
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
                    # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ для обхода ошибки aiogram
                    data['_handled'] = True
                    callback_query._handled = True
                    return True
                
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
                
                # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ для обхода ошибки aiogram
                data['_handled'] = True
                callback_query._handled = True
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
                
                # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ
                data['_handled'] = True
                callback_query._handled = True
                return True
        
        # Обрабатываем колбэк direct_cancel
        elif callback_query.data == "direct_cancel":
            self.logger.info("Middleware: обрабатываем колбэк direct_cancel")
            
            await self.bot.answer_callback_query(callback_query.id)
            
            await self.bot.edit_message_text(
                "❌ Создание конфигурации отменено.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id
            )
            
            # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ
            data['_handled'] = True
            callback_query._handled = True
            return True
            
        # ДОБАВЛЕНО: Обработка колбэка get_config
        elif callback_query.data == "get_config":
            self.logger.info("Middleware: обрабатываем колбэк get_config")
            
            await self.bot.answer_callback_query(callback_query.id)
            user_id = callback_query.from_user.id
            
            try:
                # Запрашиваем данные о конфигурации
                config_data = await get_config_from_wireguard(user_id)
                
                if "error" in config_data:
                    await self.bot.send_message(
                        user_id,
                        f"⚠️ <b>Ошибка при получении конфигурации</b>\n\n{config_data['error']}",
                        parse_mode=ParseMode.HTML
                    )
                    data['_handled'] = True
                    callback_query._handled = True
                    return True
                
                config_text = config_data.get("config_text")
                
                if not config_text:
                    await self.bot.send_message(
                        user_id,
                        "⚠️ <b>Ошибка при получении конфигурации</b>\n\n"
                        "Конфигурация не найдена. Пожалуйста, создайте новую с помощью команды /create.",
                        parse_mode=ParseMode.HTML
                    )
                    data['_handled'] = True
                    callback_query._handled = True
                    return True
                
                # Создаем файл конфигурации
                config_file = BytesIO(config_text.encode('utf-8'))
                config_file.name = f"vpn_duck_{user_id}.conf"
                
                # Генерируем QR-код
                qr_buffer = await generate_config_qr(config_text)
                
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
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
                
            except Exception as e:
                self.logger.error(f"Middleware: ошибка при получении конфигурации: {str(e)}", exc_info=True)
                await self.bot.send_message(
                    user_id,
                    "❌ <b>Ошибка при получении конфигурации</b>\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.HTML
                )
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
            
        # Колбэки на продление мы НЕ обрабатываем в middleware
        elif callback_query.data == "start_extend":
            self.logger.info("Middleware: получен колбэк start_extend, передаем в обработчики")
            # Этот колбэк пропускаем в основные обработчики
            return None

        # Обработка колбэка status
        elif callback_query.data == "status":
            self.logger.info("Middleware: обрабатываем колбэк status")
            
            await self.bot.answer_callback_query(callback_query.id)
            user_id = callback_query.from_user.id
            
            try:
                # Запрашиваем данные о конфигурации
                config = await get_user_config(user_id)
                
                if config and config.get("active", False):
                    # Парсим и форматируем данные о конфигурации
                    created_at = datetime.fromisoformat(config.get("created_at")).strftime("%d.%m.%Y %H:%M:%S")
                    expiry_time = datetime.fromisoformat(config.get("expiry_time"))
                    expiry_formatted = expiry_time.strftime("%d.%m.%Y %H:%M:%S")
                    
                    # Рассчитываем оставшееся время
                    now = datetime.now()
                    remaining_time = expiry_time - now
                    remaining_days = remaining_time.days
                    remaining_hours = remaining_time.seconds // 3600
                    
                    await self.bot.send_message(
                        user_id,
                        f"📊 <b>Статус вашей конфигурации</b>\n\n"
                        f"▫️ Активна: <b>Да</b>\n"
                        f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n"
                        f"▫️ Осталось: <b>{remaining_days} дн. {remaining_hours} ч.</b>\n",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await self.bot.send_message(
                        user_id,
                        "❌ <b>У вас нет активной конфигурации</b>\n\n"
                        "Создайте новую с помощью команды /create.",
                        parse_mode=ParseMode.HTML
                    )
                    
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
            except Exception as e:
                self.logger.error(f"Middleware: ошибка при получении данных о конфигурации: {str(e)}", exc_info=True)
                await self.bot.send_message(
                    user_id,
                    "❌ <b>Ошибка при получении данных о конфигурации</b>\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.HTML
                )
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True

        return None  # Продолжаем обработку другими обработчиками