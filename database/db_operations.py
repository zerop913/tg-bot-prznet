import aiosqlite
import logging
from datetime import datetime
from config import DB_PATH

async def setup_database():
    """Создание и настройка базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TIMESTAMP,
            is_admin INTEGER DEFAULT 0,
            freebilet_confirmed INTEGER DEFAULT 0
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_text TEXT,
            sent_at TIMESTAMP,
            sender_id INTEGER,
            is_code_phrase INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active', -- 'active', 'outdated', 'deleted'
            FOREIGN KEY (sender_id) REFERENCES users(user_id)
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS confirmations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            confirmed_at TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        await db.commit()
        logging.info("База данных настроена")

async def register_user(user_id, username, first_name, last_name, is_admin=0, freebilet_confirmed=0):
    """Регистрация пользователя в базе данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверка наличия пользователя
        cursor = await db.execute("SELECT user_id, freebilet_confirmed FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, joined_at, is_admin, freebilet_confirmed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, first_name, last_name, datetime.now(), is_admin, freebilet_confirmed)
            )
            await db.commit()
            logging.info(f"Зарегистрирован новый пользователь: {username} ({user_id})")
            return True, freebilet_confirmed
        else:
            return False, user[1]

async def update_freebilet_status(user_id, confirmed):
    """Обновление статуса подтверждения регистрации в freebilet"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET freebilet_confirmed = ? WHERE user_id = ?",
            (1 if confirmed else 0, user_id)
        )
        await db.commit()
        return True

async def get_all_users():
    """Получение списка всех пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE is_admin = 0")
        users = await cursor.fetchall()
        return [dict(user) for user in users]

async def get_freebilet_users(confirmed=True):
    """Получение списка пользователей с подтвержденной/неподтвержденной регистрацией в freebilet"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_admin = 0 AND freebilet_confirmed = ?", 
            (1 if confirmed else 0,)
        )
        users = await cursor.fetchall()
        return [dict(user) for user in users]

async def check_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        
        if result is None:
            return False
        
        return bool(result[0])

async def save_broadcast_message(message_text, sender_id, is_code_phrase=0):
    """Сохранение сообщения для рассылки в базу данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO messages (message_text, sent_at, sender_id, is_code_phrase) VALUES (?, ?, ?, ?)",
            (message_text, datetime.now(), sender_id, is_code_phrase)
        )
        await db.commit()
        return cursor.lastrowid

async def register_confirmation(message_id, user_id):
    """Регистрация подтверждения получения сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, не подтверждал ли пользователь уже это сообщение
        cursor = await db.execute(
            "SELECT id FROM confirmations WHERE message_id = ? AND user_id = ?",
            (message_id, user_id)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            await db.execute(
                "INSERT INTO confirmations (message_id, user_id, confirmed_at) VALUES (?, ?, ?)",
                (message_id, user_id, datetime.now())
            )
            await db.commit()
            return True
        return False

async def get_message_by_id(message_id):
    """Получение сообщения по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        message = await cursor.fetchone()
        return dict(message) if message else None

async def get_user_by_id(user_id):
    """Получение информации о пользователе по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def get_confirmations_for_message(message_id):
    """Получение списка подтверждений для сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT c.*, u.username, u.first_name, u.last_name
            FROM confirmations c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.message_id = ?
            """,
            (message_id,)
        )
        confirmations = await cursor.fetchall()
        return [dict(confirmation) for confirmation in confirmations]

async def get_unconfirmed_users(message_id):
    """Получение списка пользователей, не подтвердивших сообщение"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT u.*
            FROM users u
            WHERE u.is_admin = 0 AND u.user_id NOT IN (
                SELECT c.user_id
                FROM confirmations c
                WHERE c.message_id = ?
            )
            """,
            (message_id,)
        )
        users = await cursor.fetchall()
        return [dict(user) for user in users]

async def get_last_message():
    """Получение последнего отправленного сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT 1"
        )
        message = await cursor.fetchone()
        return dict(message) if message else None

async def get_all_code_phrases():
    """Получение всех кодовых фраз"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages WHERE is_code_phrase = 1 AND status != 'deleted' ORDER BY id DESC"
        )
        messages = await cursor.fetchall()
        return [dict(message) for message in messages]

async def update_code_phrase_status(message_id, status):
    """Обновление статуса кодовой фразы"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE messages SET status = ? WHERE id = ?",
            (status, message_id)
        )
        await db.commit()
        return True