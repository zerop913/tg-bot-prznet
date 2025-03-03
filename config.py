import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администратора (введите ваш ID)
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Путь к файлу базы данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'bot_database.db')