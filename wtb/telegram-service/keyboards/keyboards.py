from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from core.settings import EXTEND_OPTIONS

# Функция для получения постоянной клавиатуры
def get_permanent_keyboard():
    """Создает основную клавиатуру бота."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("🔑 Создать"),
        KeyboardButton("⏰ Продлить"),
        KeyboardButton("📊 Статус"),
        KeyboardButton("💳 История платежей"),
        KeyboardButton("ℹ️ Помощь")
    ]
    keyboard.add(*buttons)
    
    return keyboard

# Клавиатура для продления подписки
def get_extend_keyboard():
    """Возвращает клавиатуру с опциями продления."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    for option in EXTEND_OPTIONS:
        keyboard.add(
            InlineKeyboardButton(
                option["label"],
                callback_data=f"extend_{option['days']}_{option['stars']}"
            )
        )
    
    # Добавляем кнопку для отмены
    keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel_extend"))
    return keyboard

# Клавиатура для подтверждения создания
def get_create_confirm_keyboard():
    """Возвращает клавиатуру для подтверждения создания конфигурации."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="direct_create"),
        InlineKeyboardButton("❌ Отменить", callback_data="direct_cancel")
    )
    return keyboard

# Клавиатура для пересоздания конфигурации
def get_recreate_confirm_keyboard():
    """Возвращает клавиатуру для подтверждения пересоздания конфигурации."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_recreate"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_recreate")
    )
    return keyboard

# Клавиатура для активной конфигурации
def get_active_config_keyboard():
    """Возвращает клавиатуру для активной конфигурации."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
        InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
    )
    keyboard.add(InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config"))
    return keyboard

# Клавиатура для создания новой конфигурации
def get_create_config_keyboard():
    """Возвращает клавиатуру для создания новой конфигурации."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config"))
    return keyboard

# Клавиатура для проверки статуса
def get_status_keyboard():
    """Возвращает клавиатуру для проверки статуса."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("📊 Проверить статус", callback_data="status"))
    return keyboard