from aiogram import Dispatcher

# Импортируем все обработчики
from . import direct_callbacks  # Прямые обработчики
from . import start
from . import cancel
from . import create
from . import extend
from . import status
from . import payments
from . import help
from . import recreate
from . import stars_info
from . import config
from . import geolocation  # Добавляем импорт геолокаций
from . import unknown
from . import callback_handlers

def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков."""
    # ВАЖНО: регистрируем обработчики в правильном порядке - от более специфичного к более общему
    
    # 1. Сначала регистрируем прямые обработчики колбэков (наивысший приоритет)
    direct_callbacks.register_direct_handlers(dp)
    
    # 2. Затем регистрируем обработчики отмены операций
    cancel.register_handlers_cancel(dp)
    
    # 3. Регистрируем обработчики создания конфигурации и другие основные обработчики
    create.register_handlers_create(dp)
    extend.register_handlers_extend(dp)
    status.register_handlers_status(dp)
    config.register_handlers_config(dp)
    recreate.register_handlers_recreate(dp)
    geolocation.register_handlers_geolocation(dp)  # Регистрируем обработчики геолокаций
    
    # 4. Регистрируем обработчики информационных команд
    start.register_handlers_start(dp)
    payments.register_handlers_payments(dp)
    stars_info.register_handlers_stars_info(dp)
    help.register_handlers_help(dp)
    
    # 5. Регистрируем общие обработчики (наименьший приоритет)
    callback_handlers.register_handlers_callbacks(dp)
    
    # 6. В самом конце регистрируем обработчик неизвестных сообщений
    unknown.register_handlers_unknown(dp)