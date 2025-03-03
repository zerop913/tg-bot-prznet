from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    """Состояния для машины состояний администратора"""
    
    # Состояние ожидания ввода сообщения для рассылки
    waiting_for_broadcast_message = State()
    
    # Состояние ожидания ввода кодовой фразы
    waiting_for_code_phrase = State()