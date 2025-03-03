import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from config import ADMIN_ID
from database.db_operations import (
    get_all_users, save_broadcast_message, get_confirmations_for_message,
    get_unconfirmed_users, get_last_message, register_user, get_user_by_id,
    get_all_code_phrases, update_code_phrase_status, get_message_by_id
)
from keyboards.admin_keyboards import (
    admin_main_menu, admin_message_status, cancel_button, 
    user_info_buttons, code_phrase_status_buttons
)
from states.admin_states import AdminStates
from utils.notifications import send_message_to_users
from aiogram.exceptions import TelegramAPIError

router = Router()

@router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: Message):
    """Команда для входа в админ-панель"""
    # Регистрируем админа при первом использовании админ-команды
    await register_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        is_admin=1
    )
    
    await message.answer(
        "🎮 *Панель администратора*\n\n"
        "Добро пожаловать в панель управления ботом. Выберите действие:",
        reply_markup=admin_main_menu(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📢 Создать рассылку", F.from_user.id == ADMIN_ID)
async def create_broadcast(message: Message, state: FSMContext):
    """Обработчик создания новой рассылки"""
    await message.answer(
        "📝 Введите текст сообщения для рассылки всем пользователям:",
        reply_markup=cancel_button()
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)

@router.message(F.text == "🔑 Создать кодовую фразу", F.from_user.id == ADMIN_ID)
async def create_code_phrase(message: Message, state: FSMContext):
    """Обработчик создания новой кодовой фразы"""
    await message.answer(
        "🔑 Введите текст кодовой фразы для отправки всем пользователям:\n\n"
        "Эта фраза будет сохранена у пользователей в разделе \"Мои кодовые фразы\".",
        reply_markup=cancel_button()
    )
    await state.set_state(AdminStates.waiting_for_code_phrase)

@router.message(StateFilter(AdminStates.waiting_for_broadcast_message), F.from_user.id == ADMIN_ID)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка введенного текста рассылки"""
    broadcast_text = message.text
    
    # Записываем сообщение в базу данных
    message_id = await save_broadcast_message(broadcast_text, message.from_user.id)
    
    await message.answer("⏳ Начинаю рассылку сообщения всем пользователям...")
    
    # Отправляем сообщение всем пользователям
    sent_count, failed_count = await send_message_to_users(message.bot, broadcast_text, message_id)
    
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"- Отправлено: {sent_count}\n"
        f"- Не удалось отправить: {failed_count}",
        reply_markup=admin_message_status(message_id)
    )
    
    # Сбрасываем состояние
    await state.clear()

@router.message(StateFilter(AdminStates.waiting_for_code_phrase), F.from_user.id == ADMIN_ID)
async def process_code_phrase(message: Message, state: FSMContext):
    """Обработка введенной кодовой фразы"""
    code_phrase_text = message.text
    
    # Записываем кодовую фразу в базу данных (is_code_phrase=1)
    message_id = await save_broadcast_message(code_phrase_text, message.from_user.id, is_code_phrase=1)
    
    await message.answer("⏳ Начинаю рассылку кодовой фразы всем пользователям...")
    
    # Отправляем сообщение всем пользователям
    sent_count, failed_count = await send_message_to_users(message.bot, code_phrase_text, message_id)
    
    await message.answer(
        f"✅ Рассылка кодовой фразы завершена!\n\n"
        f"🔑 Фраза: `{code_phrase_text}`\n\n"
        f"📊 Статистика:\n"
        f"- Отправлено: {sent_count}\n"
        f"- Не удалось отправить: {failed_count}",
        reply_markup=admin_message_status(message_id),
        parse_mode="Markdown"
    )
    
    # Сбрасываем состояние
    await state.clear()

@router.message(F.text == "📚 Управление фразами", F.from_user.id == ADMIN_ID)
async def manage_code_phrases(message: Message):
    """Показывает список всех кодовых фраз с возможностью управления"""
    code_phrases = await get_all_code_phrases()
    
    if not code_phrases:
        await message.answer("❌ Кодовые фразы еще не были отправлены.")
        return
    
    for phrase in code_phrases:
        status_text = ""
        if phrase['status'] == 'active':
            status_text = "🟢 Активна"
        elif phrase['status'] == 'outdated':
            status_text = "🟠 Устарела"
        elif phrase['status'] == 'deleted':
            continue  # Пропускаем удаленные фразы
        
        text = (
            f"🔑 *Кодовая фраза ID#{phrase['id']}*\n\n"
            f"Статус: {status_text}\n"
            f"Текст: `{phrase['message_text']}`\n"
        )
        
        # Отправляем сообщение с кнопками управления статусом
        await message.answer(
            text,
            reply_markup=code_phrase_status_buttons(phrase['id']),
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("code_active:"), F.from_user.id == ADMIN_ID)
async def set_code_active(callback: CallbackQuery):
    """Устанавливает статус кодовой фразы как активный"""
    phrase_id = int(callback.data.split(":")[1])
    
    # Проверяем текущий статус
    all_phrases = await get_all_code_phrases()
    current_phrase = next((p for p in all_phrases if p['id'] == phrase_id), None)
    
    # Если статус уже активен, просто показываем уведомление
    if current_phrase and current_phrase['status'] == 'active':
        await callback.answer("✅ Фраза уже имеет статус 'Активна'")
        return
    
    # Обновляем статус в базе данных
    await update_code_phrase_status(phrase_id, "active")
    await callback.answer("✅ Статус изменен на 'Активна'")
    
    # Обновляем сообщение
    text = callback.message.text.replace("🟠 Устарела", "🟢 Активна")
    await callback.message.edit_text(
        text,
        reply_markup=code_phrase_status_buttons(phrase_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("code_outdated:"), F.from_user.id == ADMIN_ID)
async def set_code_outdated(callback: CallbackQuery):
    """Устанавливает статус кодовой фразы как устаревший"""
    phrase_id = int(callback.data.split(":")[1])
    
    # Проверяем текущий статус
    all_phrases = await get_all_code_phrases()
    current_phrase = next((p for p in all_phrases if p['id'] == phrase_id), None)
    
    # Если статус уже устаревший, просто показываем уведомление
    if current_phrase and current_phrase['status'] == 'outdated':
        await callback.answer("🟠 Фраза уже имеет статус 'Устарела'")
        return
    
    # Обновляем статус в базе данных
    await update_code_phrase_status(phrase_id, "outdated")
    await callback.answer("🟠 Статус изменен на 'Устарела'")
    
    # Обновляем сообщение
    text = callback.message.text.replace("🟢 Активна", "🟠 Устарела")
    await callback.message.edit_text(
        text,
        reply_markup=code_phrase_status_buttons(phrase_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("code_delete:"), F.from_user.id == ADMIN_ID)
async def delete_code_phrase(callback: CallbackQuery):
    """Удаляет кодовую фразу"""
    phrase_id = int(callback.data.split(":")[1])
    
    # Обновляем статус в базе данных на 'deleted'
    await update_code_phrase_status(phrase_id, "deleted")
    
    await callback.answer("🗑️ Фраза удалена")
    
    # Удаляем сообщение с информацией о фразе
    await callback.message.delete()

@router.message(F.text == "👥 Список пользователей", F.from_user.id == ADMIN_ID)
async def list_users(message: Message):
    """Показывает список всех пользователей бота"""
    users = await get_all_users()
    
    if not users:
        await message.answer("😔 У бота пока нет пользователей.")
        return
    
    text = f"👥 *Список пользователей бота* ({len(users)})\n\n"
    
    for idx, user in enumerate(users, start=1):
        username = user['username'] if user['username'] else 'Нет username'
        name = f"{user['first_name']} {user['last_name'] or ''}".strip()
        freebilet = "✅" if user['freebilet_confirmed'] else "❌"
        
        text += f"{idx}. {name} (@{username}) - ID: `{user['user_id']}` | Freebilet: {freebilet}\n"
        
        # Telegram имеет ограничение на длину сообщения,
        # поэтому разбиваем на части, если список большой
        if idx % 50 == 0 and idx < len(users):
            await message.answer(text, parse_mode="Markdown")
            text = ""
    
    if text:
        await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📊 Статистика последней рассылки", F.from_user.id == ADMIN_ID)
async def last_broadcast_stats(message: Message):
    """Показывает статистику последней рассылки"""
    last_message = await get_last_message()
    
    if not last_message:
        await message.answer("❌ Рассылок пока не было.")
        return
    
    confirmations = await get_confirmations_for_message(last_message['id'])
    unconfirmed = await get_unconfirmed_users(last_message['id'])
    
    all_users = len(confirmations) + len(unconfirmed)
    
    text = (
        f"📊 *Статистика последней рассылки*\n\n"
    )
    
    if last_message['is_code_phrase'] == 1:
        text += f"🔑 Кодовая фраза: `{last_message['message_text'][:100]}`...\n\n"
    else:
        text += f"📝 Сообщение: {last_message['message_text'][:100]}...\n\n"
    
    text += (
        f"✅ Подтвердили: {len(confirmations)} из {all_users} ({int(len(confirmations)/all_users*100 if all_users else 0)}%)\n"
        f"❌ Не подтвердили: {len(unconfirmed)} из {all_users} ({int(len(unconfirmed)/all_users*100 if all_users else 0)}%)\n"
    )
    
    await message.answer(
        text,
        reply_markup=admin_message_status(last_message['id']),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("confirmed_list:"), F.from_user.id == ADMIN_ID)
async def show_confirmed_users(callback: CallbackQuery):
    """Показывает список пользователей, подтвердивших получение сообщения"""
    await callback.answer()
    
    message_id = int(callback.data.split(":")[1])
    confirmations = await get_confirmations_for_message(message_id)
    
    if not confirmations:
        await callback.message.answer("❌ Пока никто не подтвердил получение сообщения.")
        return
    
    text = f"✅ *Пользователи, подтвердившие получение* ({len(confirmations)})\n\n"
    
    for idx, conf in enumerate(confirmations, start=1):
        username = conf['username'] if conf['username'] else 'Нет username'
        name = f"{conf['first_name']} {conf['last_name'] or ''}".strip()
        
        text += f"{idx}. {name} (@{username}) - ID: `{conf['user_id']}`\n"
        
        if idx % 50 == 0 and idx < len(confirmations):
            await callback.message.answer(text, parse_mode="Markdown")
            text = ""
    
    if text:
        await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("unconfirmed_list:"), F.from_user.id == ADMIN_ID)
async def show_unconfirmed_users(callback: CallbackQuery):
    """Показывает список пользователей, не подтвердивших получение сообщения"""
    await callback.answer()
    
    message_id = int(callback.data.split(":")[1])
    unconfirmed = await get_unconfirmed_users(message_id)
    
    if not unconfirmed:
        await callback.message.answer("✅ Все пользователи подтвердили получение сообщения!")
        return
    
    text = f"❌ *Пользователи, не подтвердившие получение* ({len(unconfirmed)})\n\n"
    
    for idx, user in enumerate(unconfirmed, start=1):
        username = user['username'] if user['username'] else 'Нет username'
        name = f"{user['first_name']} {user['last_name'] or ''}".strip()
        
        text += f"{idx}. {name} (@{username}) - ID: `{user['user_id']}`\n"
        
        if idx % 50 == 0 and idx < len(unconfirmed):
            await callback.message.answer(text, parse_mode="Markdown")
            text = ""
    
    if text:
        await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("update_status:"), F.from_user.id == ADMIN_ID)
async def update_message_status(callback: CallbackQuery):
    """Обновляет статус сообщения"""
    await callback.answer("Обновляю статус...")
    
    message_id = int(callback.data.split(":")[1])
    message_info = await get_message_by_id(message_id)
    confirmations = await get_confirmations_for_message(message_id)
    unconfirmed = await get_unconfirmed_users(message_id)
    
    all_users = len(confirmations) + len(unconfirmed)
    confirmation_percent = int(len(confirmations)/all_users*100 if all_users else 0)
    unconfirmed_percent = int(len(unconfirmed)/all_users*100 if all_users else 0)
    
    # Создаем уникальный текст, добавляя метку времени или случайный индентификатор
    import time
    unique_id = int(time.time())
    
    text = (
        f"📊 *Обновленная статистика рассылки* (обн. {unique_id})\n\n"
    )
    
    if message_info and message_info['is_code_phrase'] == 1:
        text += f"🔑 Кодовая фраза: `{message_info['message_text'][:100]}`...\n\n"
    else:
        text += f"📝 Сообщение: {message_info['message_text'][:100] if message_info else ''}...\n\n"
    
    text += (
        f"✅ Подтвердили: {len(confirmations)} из {all_users} ({confirmation_percent}%)\n"
        f"❌ Не подтвердили: {len(unconfirmed)} из {all_users} ({unconfirmed_percent}%)\n"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_message_status(message_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "cancel", F.from_user.id == ADMIN_ID)
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    
    if current_state is not None:
        await state.clear()
    
    await callback.message.answer(
        "❌ Действие отменено. Вы вернулись в главное меню.",
        reply_markup=admin_main_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("message_user:"), F.from_user.id == ADMIN_ID)
async def message_user(callback: CallbackQuery, state: FSMContext):
    """Отправка личного сообщения пользователю"""
    user_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден в базе данных")
        return
    
    # Здесь можно добавить логику для отправки личных сообщений пользователю
    
    await callback.answer(f"Функция личных сообщений будет доступна в следующей версии")

def register_admin_handlers(dp: Router):
    """Регистрация обработчиков администратора"""
    dp.include_router(router)