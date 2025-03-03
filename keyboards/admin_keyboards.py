from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Создать рассылку"), KeyboardButton(text="🔑 Создать кодовую фразу")],
            [KeyboardButton(text="👥 Список пользователей"), KeyboardButton(text="📚 Управление фразами")],
            [KeyboardButton(text="📊 Статистика последней рассылки")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def admin_message_status(message_id: int) -> InlineKeyboardMarkup:
    """Клавиатура статуса сообщения"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердили", callback_data=f"confirmed_list:{message_id}")
    )
    builder.add(
        InlineKeyboardButton(text="❌ Не подтвердили", callback_data=f"unconfirmed_list:{message_id}")
    )
    builder.add(
        InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"update_status:{message_id}")
    )
    
    builder.adjust(1)
    
    return builder.as_markup()

def cancel_button() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()

def user_info_buttons(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки действий с пользователем"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="✉️ Написать лично", callback_data=f"message_user:{user_id}")
    )
    
    return builder.as_markup()

def code_phrase_status_buttons(phrase_id: int) -> InlineKeyboardMarkup:
    """Кнопки управления статусом кодовой фразы"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="🟢 Пометить как активную", callback_data=f"code_active:{phrase_id}")
    )
    builder.add(
        InlineKeyboardButton(text="🟠 Пометить как устаревшую", callback_data=f"code_outdated:{phrase_id}")
    )
    builder.add(
        InlineKeyboardButton(text="🗑️ Удалить фразу", callback_data=f"code_delete:{phrase_id}")
    )
    
    builder.adjust(1)
    
    return builder.as_markup()