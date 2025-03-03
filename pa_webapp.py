#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# Настройка логирования для файла веб-приложения
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pa_webapp_log.log")
    ]
)

def run_bot():
    """Запускает бота и перезапускает его в случае сбоя"""
    while True:
        try:
            logging.info(f"Запуск бота: {datetime.now()}")
            # Запускаем бота как отдельный процесс
            subprocess.run([sys.executable, "bot.py"])
        except Exception as e:
            logging.error(f"Ошибка при запуске бота: {e}")
        
        # Пауза перед перезапуском
        logging.info("Перезапуск бота через 10 секунд...")
        time.sleep(10)

# Для PythonAnywhere: Создаем функцию для запуска через API
def application(environ, start_response):
    # Проверяем, запущен ли уже бот
    if not os.path.exists("bot_running.lock"):
        # Создаем файл блокировки
        with open("bot_running.lock", "w") as f:
            f.write(str(datetime.now()))
        
        # Запускаем бота в отдельном процессе
        try:
            subprocess.Popen([sys.executable, "bot.py"])
            status = "200 OK"
            output = "Bot started successfully".encode("utf-8")
        except Exception as e:
            status = "500 Internal Server Error"
            output = f"Error starting bot: {e}".encode("utf-8")
    else:
        status = "200 OK"
        output = "Bot is already running".encode("utf-8")
    
    response_headers = [("Content-type", "text/plain"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)
    
    return [output]

# Для запуска локально
if __name__ == "__main__":
    run_bot()