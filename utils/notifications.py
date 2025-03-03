import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from database.db_operations import get_all_users
from keyboards.user_keyboards import confirm_button

async def send_message_to_users(bot: Bot, message_text: str, message_id: int):
    """Отправляет сообщение всем пользователям бота"""
    users = await get_all_users()
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            # Отправляем сообщение с кнопкой подтверждения
            await bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *Важное сообщение:*\n\n{message_text}",
                reply_markup=confirm_button(message_id),
                parse_mode="Markdown"
            )
            sent_count += 1
            # Небольшая задержка, чтобы не превысить лимиты Telegram API
            await asyncio.sleep(0.1)
        except TelegramAPIError as e:
            logging.error(f"Ошибка отправки сообщения пользователю {user['user_id']}: {e}")
            failed_count += 1
    
    return sent_count, failed_count