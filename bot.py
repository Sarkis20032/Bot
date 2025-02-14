import os
import sqlite3
from flask import Flask, request
import telebot

# Временно указываем токен напрямую
TOKEN = "7840228365:AAGdBlBeeao5g0l9JT369Pz6h3qRN2T_38c"  # Вставьте сюда свой токен
# Если всё работает, верните обратно использование os.getenv
# TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# Создаем Flask-приложение
app = Flask(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("clients.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            gender TEXT,
            age_group TEXT
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# Начало регистрации
@bot.message_handler(commands=["start", "register"])
def start_registration(message):
    user_id = message.chat.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        bot.send_message(user_id, "Вы уже зарегистрированы!")
    else:
        bot.send_message(user_id, "Здравствуйте! Как вас зовут?")
        bot.register_next_step_handler(message, ask_name)

def ask_name(message):
    full_name = message.text
    user_id = message.chat.id
    username = message.chat.username
    bot.send_message(user_id, "Укажите ваш возрастной диапазон:", reply_markup=age_keyboard())
    bot.register_next_step_handler(message, lambda msg: ask_age(msg, full_name, username))

def ask_age(message, full_name, username):
    age_group = message.text
    if age_group not in ["18-21", "22-26", "27-32"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите возраст из предложенных вариантов.")
        bot.register_next_step_handler(message, lambda msg: ask_age(msg, full_name, username))
        return

    bot.send_message(message.chat.id, "Укажите ваш пол:", reply_markup=gender_keyboard())
    bot.register_next_step_handler(message, lambda msg: ask_gender(msg, full_name, username, age_group))

def ask_gender(message, full_name, username, age_group):
    gender = message.text
    if gender not in ["Мужской", "Женский"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите пол из предложенных вариантов.")
        bot.register_next_step_handler(message, lambda msg: ask_gender(msg, full_name, username, age_group))
        return

    # Сохраняем данные в базу
    cursor.execute("INSERT INTO users (user_id, username, full_name, gender, age_group) VALUES (?, ?, ?, ?, ?)",
                   (message.chat.id, username, full_name, gender, age_group))
    conn.commit()

    bot.send_message(message.chat.id, "Спасибо за регистрацию! Ваши данные сохранены.")

# Отправка количества клиентов
@bot.message_handler(commands=["count_clients"])
def count_clients(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"Количество зарегистрированных клиентов: {count}")

# Очистка базы (только для администратора)
@bot.message_handler(commands=["clear_db"])
def clear_database(message):
    if message.chat.id == ADMIN_ID:  # Укажите ваш ID администратора
        cursor.execute("DELETE FROM users")
        conn.commit()
        bot.send_message(message.chat.id, "База данных успешно очищена.")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

# Рассылка сообщений всем клиентам
@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    if message.chat.id == 641521378:  # Укажите ваш ID администратора
        bot.send_message(message.chat.id, "Введите текст для рассылки:")
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

def send_broadcast(message):
    text = message.text
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for user in users:
        try:
            bot.send_message(user[0], text)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")
    bot.send_message(message.chat.id, "Рассылка завершена.")

# Клавиатуры для опроса
def age_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("18-21", "22-26", "27-32")
    return keyboard

def gender_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Мужской", "Женский")
    return keyboard

# Роут для обработки вебхуков
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Устанавливаем вебхук и запускаем Flask
if __name__ == "__main__":
    bot.remove_webhook()
    webhook_url = f"https://ваш-домен.herokuapp.com/{TOKEN}"  # Укажите ваш домен на Heroku
    bot.set_webhook(url=webhook_url)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
