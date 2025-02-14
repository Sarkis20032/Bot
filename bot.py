from flask import Flask, request
import telebot
import sqlite3
import os

# Переменная окружения для токена
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Flask-приложение
app = Flask(__name__)

# Подключение к базе данных
conn = sqlite3.connect("clients.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы клиентов
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        gender TEXT,
        age_group TEXT,
        used_before TEXT
    )
""")
conn.commit()

# Словарь для временного хранения данных клиента
user_data = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Проверяем, есть ли пользователь в базе
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
    else:
        user_data[user_id] = {"username": username, "full_name": full_name}
        bot.send_message(message.chat.id, "Привет! Как вас зовут?")
        bot.register_next_step_handler(message, get_gender)

# Запрашиваем пол
def get_gender(message):
    user_id = message.from_user.id
    user_data[user_id]["full_name"] = message.text

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Укажите ваш пол:", reply_markup=markup)
    bot.register_next_step_handler(message, get_age)

# Запрашиваем возрастную группу
def get_age(message):
    user_id = message.from_user.id
    gender = message.text

    if gender not in ["Мужской", "Женский"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите 'Мужской' или 'Женский' с помощью кнопок.")
        return get_gender(message)

    user_data[user_id]["gender"] = gender

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("18-21", "21-26", "26-32", "32+")
    bot.send_message(message.chat.id, "Укажите вашу возрастную группу:", reply_markup=markup)
    bot.register_next_step_handler(message, set_used_before)

# Запрашиваем, пользовались ли услугами магазина
def set_used_before(message):
    user_id = message.from_user.id
    age_group = message.text

    if age_group not in ["18-21", "21-26", "26-32", "32+"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите возрастную группу с помощью кнопок.")
        return get_age(message)

    user_data[user_id]["age_group"] = age_group

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Да", "Нет")
    bot.send_message(message.chat.id, "Вы пользовались услугами магазина ранее?", reply_markup=markup)
    bot.register_next_step_handler(message, save_to_db)

# Сохраняем данные в базу
def save_to_db(message):
    user_id = message.from_user.id
    used_before = message.text

    if used_before not in ["Да", "Нет"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите 'Да' или 'Нет' с помощью кнопок.")
        return set_used_before(message)

    user_data[user_id]["used_before"] = used_before

    # Сохраняем данные в базу
    data = user_data[user_id]
    cursor.execute("""
        INSERT INTO users (user_id, username, full_name, gender, age_group, used_before)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, data["username"], data["full_name"], data["gender"], data["age_group"], data["used_before"]))
    conn.commit()

    bot.send_message(message.chat.id, "Спасибо за регистрацию!")

# Обработчик Webhook
@app.route('/', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

# Запуск приложения
if __name__ == "__main__":
    bot.remove_webhook()
    webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
