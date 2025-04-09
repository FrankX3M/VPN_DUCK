from aiogram import Dispatcher

# Импортируем все обработчики
from . import direct_callbacks  # Новый модуль
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
from . import unknown
from . import callback_handlers

def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков."""
    # Регистрируем прямые обработчики в первую очередь
    direct_callbacks.register_direct_handlers(dp)
    
    # Регистрируем обработчики в правильном порядке
    cancel.register_handlers_cancel(dp)
    start.register_handlers_start(dp)
    create.register_handlers_create(dp)
    extend.register_handlers_extend(dp)
    status.register_handlers_status(dp)
    payments.register_handlers_payments(dp)
    stars_info.register_handlers_stars_info(dp)
    help.register_handlers_help(dp)
    recreate.register_handlers_recreate(dp)
    config.register_handlers_config(dp)
    
    # Общие обработчики в последнюю очередь
    callback_handlers.register_handlers_callbacks(dp)
    unknown.register_handlers_unknown(dp)