from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import sqlite3
import datetime
import pytz
import asyncio
import os
from telegram.error import Conflict

TOKEN = "7392929368:AAEiMeWKDSQ8dYUBqr8ekYy4J1ilagtYuQo"
DEFAULT_TIMEZONE = "Europe/Moscow"

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        print("⚠️ Обнаружен конфликт: уже запущен другой экземпляр бота")
    else:
        print(f"⚠️ Ошибка: {context.error}")


def init_db():
    conn = None
    try:
        conn = sqlite3.connect('pills.db')
        cursor = conn.cursor()
        
        # Простой и надежный запрос в одну строку без сложного форматирования
        cursor.execute("""CREATE TABLE IF NOT EXISTS reminders (
            chat_id INTEGER,
            drug_name TEXT,
            time TEXT,
            timezone TEXT DEFAULT 'Europe/Moscow',
            PRIMARY KEY (chat_id, drug_name))""")
        
        conn.commit()
    except Exception as e:
        print(f"Ошибка при создании БД: {e}")
    finally:
        if conn:
            conn.close()

def add_to_db(chat_id, drug_name, time_str, timezone=DEFAULT_TIMEZONE):
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO reminders VALUES (?, ?, ?, ?)", 
                 (chat_id, drug_name, time_str, timezone))
    conn.commit()
    conn.close()

def del_from_db(chat_id, drug_name):
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE chat_id=? AND drug_name=?", 
                 (chat_id, drug_name))
    conn.commit()
    conn.close()

def get_reminders(chat_id):
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("SELECT drug_name, time, timezone FROM reminders WHERE chat_id=?", 
                 (chat_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_reminders():
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, drug_name, time, timezone FROM reminders")
    result = cursor.fetchall()
    conn.close()
    return result

def update_timezone(chat_id, timezone):
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET timezone=? WHERE chat_id=?", 
                 (timezone, chat_id))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💊 **Бот-напоминание о лекарствах**\n\n"
        f"Часовой пояс по умолчанию: {DEFAULT_TIMEZONE}\n"
        "Изменить: `/timezone Europe/Moscow`\n"
        "Добавить: `/add Миртазапин 22:00`\n"
        "Удалить: `/del Миртазапин`\n"
        "Список: `/list`\n\n"
        "Список таймзон: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
    )

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    try:
        timezone = context.args[0]
        
        if timezone not in pytz.all_timezones:
            await update.message.reply_text("⛔ Неверная таймзона. Пример: `/timezone Europe/Moscow`")
            return
            
        update_timezone(chat_id, timezone)
        await update.message.reply_text(f"✅ Часовой пояс установлен: {timezone}")
        
    except IndexError:
        await update.message.reply_text("⛔ Используйте: `/timezone Europe/Moscow`")

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    try:
        drug_name = context.args[0]
        drug_time = context.args[1]
        
        try:
            datetime.datetime.strptime(drug_time, "%H:%M")
        except ValueError:
            await update.message.reply_text("⛔ Формат времени: `22:00`")
            return

        timezone = 'UTC'
        reminders = get_reminders(chat_id)
        if reminders and reminders[0][2]:  # Если уже есть записи с таймзоной
            timezone = reminders[0][2]
            
        add_to_db(chat_id, drug_name, drug_time, timezone)
        await update.message.reply_text(f"✅ Добавлено: {drug_name} в {drug_time} (по времени {timezone})")

    except IndexError:
        await update.message.reply_text("⛔ Используйте: `/add Лекарство 22:00`")

async def del_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    try:
        drug_name = context.args[0]
        del_from_db(chat_id, drug_name)
        await update.message.reply_text(f"❌ Удалено: {drug_name}")
    except IndexError:
        await update.message.reply_text("⛔ Используйте: `/del Лекарство`")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    reminders = get_reminders(chat_id)
    
    if reminders:
        message = "📋 Ваши напоминания:\n"
        for drug, time_str, timezone in reminders:
            message += f"- {drug} в {time_str} (по времени {timezone})\n"
    else:
        message = "ℹ️ Нет активных напоминаний"
    
    await update.message.reply_text(message)

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    reminders = get_all_reminders()
    
    for chat_id, drug_name, time_str, timezone in reminders:
        try:
            # Если timezone не указана, используем московское время
            tz = pytz.timezone(timezone or DEFAULT_TIMEZONE)
            now = datetime.datetime.now(tz).strftime("%H:%M")
            
            if now == time_str:
                await context.bot.send_message(
                    chat_id, 
                    text=f"🔔 Пора принять {drug_name}!\n"
                         f"⏰ Текущее время: {now} ({timezone})"
                )
        except Exception as e:
            print(f"Ошибка при проверке напоминания: {e}")

def main():
    try:
        if os.path.exists('pills.db'):
            os.remove('pills.db')
            print("Старая БД удалена")
        
        init_db()
        print("База данных успешно инициализирована")
        
        app = Application.builder().token(TOKEN).build()
        app.add_error_handler(error_handler) 
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("timezone", set_timezone))
        app.add_handler(CommandHandler("add", add_reminder))
        app.add_handler(CommandHandler("del", del_reminder))
        app.add_handler(CommandHandler("list", list_reminders))
        
        # Настраиваем проверку напоминаний
        job_queue = app.job_queue
        job_queue.run_repeating(check_reminders, interval=60.0)
        
        print("Бот успешно запущен")
        app.run_polling()
        
    except Exception as e:
        print(f"Ошибка при запуске: {str(e)}")

if __name__ == '__main__':
    try:
        from telegram.ext import Application, CommandHandler, ContextTypes
        from telegram import Update
        import pytz
        main()
    except ImportError:
        print("Ошибка: Не установлены необходимые библиотеки.")
        print("Установите их командой: pip install python-telegram-bot==20.3 pytz")