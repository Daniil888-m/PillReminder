from telegram.ext import Application, CommandHandler
import sqlite3
import datetime
import asyncio
import os

TOKEN = "7392929368:AAEiMeWKDSQ8dYUBqr8ekYy4J1ilagtYuQo"

# --- Функции для работы с БД ---
def init_db():
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            chat_id INTEGER,
            drug_name TEXT,
            time TEXT,
            PRIMARY KEY (chat_id, drug_name)
        )
    ''')
    conn.commit()
    conn.close()

def add_to_db(chat_id, drug_name, time_str):
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO reminders VALUES (?, ?, ?)", 
                 (chat_id, drug_name, time_str))
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
    cursor.execute("SELECT drug_name, time FROM reminders WHERE chat_id=?", 
                 (chat_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_reminders():
    conn = sqlite3.connect('pills.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, drug_name, time FROM reminders")
    result = cursor.fetchall()
    conn.close()
    return result

# --- Обработчики команд ---
async def start(update, context):
    await update.message.reply_text(
        "💊 **Бот-напоминание о лекарствах**\n\n"
        "Добавить: `/add Миртазапин 22:00`\n"
        "Удалить: `/del Миртазапин`\n"
        "Список: `/list`"
    )

async def add_reminder(update, context):
    chat_id = update.message.chat_id
    try:
        drug_name = context.args[0]
        drug_time = context.args[1]
        
        try:
            datetime.datetime.strptime(drug_time, "%H:%M")
        except ValueError:
            await update.message.reply_text("⛔ Формат времени: `22:00`")
            return

        add_to_db(chat_id, drug_name, drug_time)
        await update.message.reply_text(f"✅ Добавлено: {drug_name} в {drug_time}")

    except IndexError:
        await update.message.reply_text("⛔ Используйте: `/add Лекарство 22:00`")

async def del_reminder(update, context):
    chat_id = update.message.chat_id
    try:
        drug_name = context.args[0]
        del_from_db(chat_id, drug_name)
        await update.message.reply_text(f"❌ Удалено: {drug_name}")
    except IndexError:
        await update.message.reply_text("⛔ Используйте: `/del Лекарство`")

async def list_reminders(update, context):
    chat_id = update.message.chat_id
    reminders = get_reminders(chat_id)
    
    if reminders:
        message = "📋 Ваши напоминания:\n"
        for drug, time_str in reminders:
            message += f"- {drug} в {time_str}\n"
    else:
        message = "ℹ️ Нет активных напоминаний"
    
    await update.message.reply_text(message)

async def check_reminders(context):
    reminders = get_all_reminders()
    now = datetime.datetime.now().strftime("%H:%M")
    
    for chat_id, drug_name, time_str in reminders:
        if now == time_str:
            await context.bot.send_message(chat_id, text=f"🔔 Пора принять {drug_name}!")

def main():
    try:
        # Удаляем старую БД
        if os.path.exists('pills.db'):
            os.remove('pills.db')
            print("Старая БД удалена")
        
        init_db()
        print("База данных успешно инициализирована")
        
        # Создаем Application с включенным JobQueue
        app = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        app.add_handler(CommandHandler("start", start))
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
    # Проверяем установку зависимостей
    try:
        import telegram.ext
        main()
    except ImportError:
        print("Ошибка: Не установлены необходимые библиотеки.")
        print("Установите их командой: pip install python-telegram-bot==20.3")