import logging
import asyncio
import time
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database.db_operations import (
    register_user, register_confirmation, get_message_by_id,
    update_freebilet_status, get_all_code_phrases
)
from keyboards.user_keyboards import confirm_button, freebilet_check_keyboard, main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Регистрация пользователя в базе данных
    is_new, freebilet_confirmed = await register_user(user_id, username, first_name, last_name)
    
    # Запрос о регистрации в @freebilet_bot
    if not freebilet_confirmed:
        welcome_text = (
            f"👋 Здравствуйте, {first_name}!\n\n"
            f"*Важно!* Перед началом использования бота, пожалуйста, убедитесь, что вы зарегистрировались в боте @freebilet_bot. "
            f"Вам необходимо дойти до сообщения: *\"🎉 Спасибо за регистрацию на розыгрыш!\"*\n\n"
            f"Вы уже зарегистрировались в @freebilet_bot?"
        )
        
        await message.answer(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=freebilet_check_keyboard()
        )
    else:
        await show_main_menu(message)

@router.callback_query(F.data == "freebilet_confirmed")
async def freebilet_confirm(callback: CallbackQuery):
    """Обработчик подтверждения регистрации в freebilet"""
    await update_freebilet_status(callback.from_user.id, True)
    
    await callback.answer("✅ Спасибо за подтверждение!")
    await callback.message.delete()
    
    # Показываем основное меню
    await show_main_menu(callback.message)

@router.callback_query(F.data == "freebilet_not_confirmed")
async def freebilet_not_confirm(callback: CallbackQuery):
    """Обработчик отрицания регистрации в freebilet"""
    await callback.answer("Перенаправляем вас на бота @freebilet_bot")
    
    # Создаем кнопку для перехода к боту
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Перейти к @freebilet_bot", url="https://t.me/freebilet_bot")],
        [InlineKeyboardButton(text="✅ Я уже зарегистрировался", callback_data="freebilet_confirmed")]
    ])
    
    await callback.message.edit_text(
        "🎟 Пожалуйста, перейдите к боту @freebilet_bot и пройдите регистрацию.\n\n"
        "После завершения регистрации и получения сообщения *\"🎉 Спасибо за регистрацию на розыгрыш!\"* "
        "вернитесь сюда и нажмите кнопку \"✅ Я уже зарегистрировался\".",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def show_main_menu(message: Message):
    """Показывает основное меню бота"""
    welcome_text = (
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        f"Вы успешно зарегистрированы в системе уведомлений. "
        f"Теперь вы будете получать важные сообщения от администратора.\n\n"
        f"Когда придет сообщение, нажмите кнопку *Подтверждаю получение*, "
        f"чтобы администратор знал, что вы ознакомились с информацией.\n\n"
        f"В разделе \"🔑 Мои кодовые фразы\" вы всегда можете посмотреть сохраненные кодовые фразы."
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🔍 *Справка по использованию бота*\n\n"
        "Этот бот предназначен для получения важных уведомлений от администратора.\n\n"
        "Доступные команды:\n"
        "• /start - Запустить бота и зарегистрироваться\n"
        "• /help - Показать эту справку\n"
        "• /codes - Показать все актуальные кодовые фразы\n\n"
        "Когда администратор отправляет важное сообщение, вы получите уведомление "
        "с кнопкой *Подтверждаю получение*. Нажмите на нее, чтобы подтвердить, "
        "что вы прочитали сообщение.\n\n"
        "Кодовые фразы будут сохранены в разделе \"🔑 Мои кодовые фразы\" "
        "и всегда доступны для просмотра."
    )
    
    await message.answer(
        help_text,
        parse_mode="Markdown"
    )

@router.message(Command("codes"))
@router.message(F.text == "🔑 Мои кодовые фразы")
async def cmd_codes(message: Message):
    """Показывает список всех кодовых фраз"""
    code_phrases = await get_all_code_phrases()
    
    if not code_phrases:
        await message.answer(
            "🔒 У вас пока нет кодовых фраз. Ожидайте отправки от администратора.",
            parse_mode="Markdown"
        )
        return
    
    text = "🔑 *Ваши кодовые фразы:*\n\n"
    
    for idx, phrase in enumerate(code_phrases, start=1):
        if phrase['status'] == 'active':
            text += f"{idx}. `{phrase['message_text']}`\n\n"
        elif phrase['status'] == 'outdated':
            text += f"{idx}. ~~`{phrase['message_text']}`~~ _(устарело)_\n\n"
    
    await message.answer(
        text,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("confirm:"))
async def confirm_message_receipt(callback: CallbackQuery):
    """Обработчик подтверждения получения сообщения"""
    message_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Регистрируем подтверждение в базе данных
    confirmation_result = await register_confirmation(message_id, user_id)
    
    if confirmation_result:
        # Получаем информацию о сообщении
        message_info = await get_message_by_id(message_id)
        
        if message_info and message_info['is_code_phrase'] == 1:
            # Если это кодовая фраза, меняем формат подтверждения
            # Добавляем временную метку для уникальности сообщения
            unique_id = int(time.time())
            
            text = f"✅ Вы подтвердили получение кодовой фразы! (#{unique_id})\n\n"
            
            if message_info['status'] == 'active':
                text += f"🔑 *Кодовая фраза:* `{message_info['message_text']}`\n\n"
            elif message_info['status'] == 'outdated':
                text += f"🔑 *Кодовая фраза:* ~~`{message_info['message_text']}`~~ _(устарело)_\n\n"
                
            text += "📋 Эта фраза сохранена в разделе \"🔑 Мои кодовые фразы\"."
                
            await callback.message.edit_text(
                text,
                parse_mode="Markdown"
            )
        else:
            # Обычное сообщение с уникальной меткой
            unique_id = int(time.time())
            
            await callback.message.edit_text(
                f"✅ Спасибо! Вы подтвердили получение сообщения (#{unique_id}):\n\n"
                f"{message_info['message_text'] if message_info else 'Сообщение'}"
            )
        
        # Отправляем уведомление админу о подтверждении
        try:
            admin_id = message_info['sender_id'] if message_info else None
            if admin_id:
                first_name = callback.from_user.first_name
                last_name = callback.from_user.last_name or ""
                username = callback.from_user.username or "Нет username"
                
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=f"✅ Пользователь {first_name} {last_name} (@{username}) "
                         f"подтвердил получение "
                         f"{'кодовой фразы' if message_info and message_info['is_code_phrase'] == 1 else 'сообщения'}!"
                )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления админу: {e}")
    else:
        # Если пользователь уже подтверждал это сообщение
        await callback.answer("✅ Вы уже подтвердили получение этого сообщения.")

def register_user_handlers(dp: Router):
    """Регистрация обработчиков пользователя"""
    dp.include_router(router)