from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def confirm_button(message_id: int) -> InlineKeyboardMarkup:
    """Кнопка подтверждения получения сообщения"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="✅ Подтверждаю получение", callback_data=f"confirm:{message_id}")
    )
    
    return builder.as_markup()

def freebilet_check_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура проверки регистрации в freebilet"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="✅ Да, я зарегистрирован", callback_data="freebilet_confirmed")
    )
    builder.add(
        InlineKeyboardButton(text="❌ Нет, еще не зарегистрирован", callback_data="freebilet_not_confirmed")
    )
    
    builder.adjust(1)
    
    return builder.as_markup()

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Основное меню пользователя"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔑 Мои кодовые фразы")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard