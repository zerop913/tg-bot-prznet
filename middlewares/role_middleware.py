from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database.db_operations import check_admin, register_user

class RoleMiddleware(BaseMiddleware):
    """Middleware для определения роли пользователя (админ или обычный пользователь)"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        
        # Регистрируем пользователя, если он новый
        # Проверяем, является ли он администратором
        is_admin = await check_admin(user.id)
        data["is_admin"] = is_admin
        
        # Продолжаем выполнение обработчика
        return await handler(event, data)