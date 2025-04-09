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
        self.logger.info(f"Middleware: получен колбэк {callback_query.data}")
        
        # Обрабатываем колбэк direct_create
        if callback_query.data == "direct_create":
            self.logger.info("Middleware: обрабатываем колбэк direct_create")
            
            # Отвечаем на колбэк, чтобы убрать часы ожидания
            await self.bot.answer_callback_query(callback_query.id)
            user_id = callback_query.from_user.id
            
            # Сообщаем пользователю о начале процесса создания
            await self.bot.edit_message_text(
                "🔄 *Создание конфигурации...*\n\n"
                "Пожалуйста, подождите. Это может занять несколько секунд.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
            
            try:
                # Создаем новую конфигурацию
                config_data = await create_new_config(user_id)
                
                if "error" in config_data:
                    await self.bot.edit_message_text(
                        f"❌ *Ошибка!*\n\n{config_data['error']}",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ для обхода ошибки aiogram
                    data['_handled'] = True
                    callback_query._handled = True
                    return True
                
                config_text = config_data.get("config_text")
                
                if not config_text:
                    await self.bot.edit_message_text(
                        "❌ *Ошибка при создании конфигурации*\n\n"
                        "Пожалуйста, попробуйте позже.",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        parse_mode=ParseMode.MARKDOWN
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
                        expiry_text = f"▫️ Срок действия: до *{expiry_formatted}*\n"
                
                # Создаем файл конфигурации
                config_file = BytesIO(config_text.encode('utf-8'))
                config_file.name = f"vpn_duck_{user_id}.conf"
                
                # Генерируем QR-код
                qr_buffer = await generate_config_qr(config_text)
                
                # Обновляем сообщение об успешном создании
                await self.bot.edit_message_text(
                    f"✅ *Конфигурация успешно создана!*\n\n"
                    f"{expiry_text}\n"
                    f"Файл конфигурации и QR-код будут отправлены отдельными сообщениями.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                if qr_buffer:
                    # Отправляем QR-код
                    await self.bot.send_photo(
                        user_id,
                        qr_buffer,
                        caption="🔑 *QR-код вашей конфигурации WireGuard*\n\n"
                                "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Отправляем файл конфигурации
                await self.bot.send_document(
                    user_id,
                    config_file,
                    caption="📋 *Файл конфигурации WireGuard*\n\n"
                            "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Отправляем инструкции
                instructions_text = (
                    "📱 *Как использовать конфигурацию:*\n\n"
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
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
                
                # Помечаем колбэк как обработанный - НЕСКОЛЬКИМИ СПОСОБАМИ для обхода ошибки aiogram
                data['_handled'] = True
                callback_query._handled = True
                return True
                
            except Exception as e:
                self.logger.error(f"Middleware: ошибка при создании конфигурации: {str(e)}")
                await self.bot.edit_message_text(
                    "❌ *Произошла ошибка*\n\n"
                    "Пожалуйста, попробуйте позже.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    parse_mode=ParseMode.MARKDOWN
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
                        f"⚠️ *Ошибка при получении конфигурации*\n\n{config_data['error']}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    data['_handled'] = True
                    callback_query._handled = True
                    return True
                
                config_text = config_data.get("config_text")
                
                if not config_text:
                    await self.bot.send_message(
                        user_id,
                        "⚠️ *Ошибка при получении конфигурации*\n\n"
                        "Конфигурация не найдена. Пожалуйста, создайте новую с помощью команды /create.",
                        parse_mode=ParseMode.MARKDOWN
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
                        caption="🔑 *QR-код вашей конфигурации WireGuard*\n\n"
                                "Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Отправляем файл конфигурации
                await self.bot.send_document(
                    user_id,
                    config_file,
                    caption="📋 *Файл конфигурации WireGuard*\n\n"
                            "Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Отправляем инструкции
                instructions_text = (
                    "📱 *Как использовать конфигурацию:*\n\n"
                    "1️⃣ Установите приложение WireGuard на ваше устройство\n"
                    "2️⃣ Откройте приложение и нажмите кнопку '+'\n"
                    "3️⃣ Выберите 'Сканировать QR-код' или 'Импорт из файла'\n"
                    "4️⃣ После импорта нажмите на добавленную конфигурацию для подключения\n\n"
                    "Готово! Теперь ваше соединение защищено VPN Duck 🦆"
                )
                
                await self.bot.send_message(
                    user_id,
                    instructions_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
                
            except Exception as e:
                self.logger.error(f"Middleware: ошибка при получении конфигурации: {str(e)}")
                await self.bot.send_message(
                    user_id,
                    "❌ *Ошибка при получении конфигурации*\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
            
        # Колбэки на продление мы НЕ обрабатываем в middleware
        elif callback_query.data == "start_extend":
            self.logger.info("Middleware: получен колбэк start_extend")
            # Этот колбэк пропускаем в основные обработчики
            pass

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
                        f"📊 *Статус вашей конфигурации*\n\n"
                        f"▫️ Активна: *Да*\n"
                        f"▫️ Срок действия: до *{expiry_formatted}*\n"
                        f"▫️ Осталось: *{remaining_days} дн. {remaining_hours} ч.*\n",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await self.bot.send_message(
                        user_id,
                        "❌ *У вас нет активной конфигурации*\n\n"
                        "Создайте новую с помощью команды /create.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True
            except Exception as e:
                self.logger.error(f"Middleware: ошибка при получении данных о конфигурации: {str(e)}")
                await self.bot.send_message(
                    user_id,
                    "❌ *Ошибка при получении данных о конфигурации*\n\n"
                    "Пожалуйста, попробуйте позже.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Помечаем колбэк как обработанный
                data['_handled'] = True
                callback_query._handled = True
                return True

        return None  # Продолжаем обработку другими обработчиками