from aiogram.dispatcher.filters.state import State, StatesGroup

# Создаем состояния для FSM (машина состояний)
class ExtendConfigStates(StatesGroup):
    selecting_duration = State()
    confirming_payment = State()

class CreateConfigStates(StatesGroup):
    confirming_create = State()

# Добавляем состояние для выбора геолокации
class GeoLocationStates(StatesGroup):
    selecting_geolocation = State()