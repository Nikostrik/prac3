import asyncio
import logging
import sqlite3

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup
from flask import Flask, jsonify

TOKEN = ""

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

markup = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(
        text="Відкрити веб-сторінку",
        web_app=types.WebAppInfo(url='https://www.roshen.com/')
    )]
])

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    balance REAL DEFAULT 0.0
)""")
conn.commit()

async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (id, name) VALUES (?, ?)", (user_id, message.from_user.full_name))
        conn.commit()
        await message.answer("Вітаю!", reply_markup=markup)
    else:
        await message.reply("Вітаю! Ви вже зареєстровані. Введіть /help для перегляду команд.")

dp.message.register(send_welcome, Command(commands=["start"]))

async def send_help(message: types.Message):
    await message.reply("Доступні команди:\n/start - Почати роботу\n/help - Допомога\n/info - Інформація про бота\n/register - Зареєструватися\n/balance - Перевірити баланс\n/topup - Поповнити баланс")

dp.message.register(send_help, Command(commands=["help"]))

async def send_info(message: types.Message):
    await message.reply("Цей бот допомагає замовляти продукцію Рошен та отримувати актуальні дані про оплату.")

dp.message.register(send_info, Command(commands=["info"]))

async def show_web_app(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="Відкрити веб-сторінку",
            web_app=types.WebAppInfo(url="https://roshen.com")
        )]
    ])
    await message.answer("Натисніть кнопку нижче, щоб відкрити веб-сторінку Roshen:", reply_markup=markup)

dp.message.register(show_web_app, Command(commands=["web"]))

async def get_balance(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        await message.reply(f"Ваш баланс: {user[0]} грн.")
    else:
        await message.reply("Ви не зареєстровані. Введіть /start для реєстрації.")

dp.message.register(get_balance, Command(commands=["balance"]))

async def top_up_balance(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        cursor.execute("UPDATE users SET balance = balance + 100 WHERE id = ?", (user_id,))
        conn.commit()
        await message.reply("Ваш баланс поповнено на 100 грн.")
    else:
        await message.reply("Ви не зареєстровані. Введіть /start для реєстрації.")

dp.message.register(top_up_balance, Command(commands=["topup"]))

async def pay_balance(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        if user[0] >= 100:
            cursor.execute("UPDATE users SET balance = balance - 100 WHERE id = ?", (user_id,))
            conn.commit()
            await message.reply("Оплата успішна! З вашого рахунку списано 100 грн.")
        else:
            await message.reply("Недостатньо коштів на рахунку для оплати.")
    else:
        await message.reply("Ви не зареєстровані. Введіть /start для реєстрації.")

dp.message.register(pay_balance, Command(commands=["pay"]))

def get_currency_rate(currency):
    response = requests.get(f"https://api.exchangerate-api.com/v4/latest/USD")
    if response.status_code == 200:
        data = response.json()
        return data['rates'].get(currency, "Курс не знайдено")
    else:
        return "Помилка під час отримання даних."

async def get_rate(message: types.Message):
    rate = get_currency_rate('UAH')
    await message.reply(f"Актуальний курс долара до гривні: {rate}")

dp.message.register(get_rate, Command(commands=["rate"]))

@app.route('/')
def home():
    return jsonify({"message": "Вітаємо у веб-інтерфейсі Roshen Bot API!"})

@app.route('/users', methods=['GET'])
def list_users():
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return jsonify(users)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        return jsonify(user)
    else:
        return jsonify({"error": "Користувача не знайдено"}), 404

async def main():
    from threading import Thread

    def run_flask():
        app.run(host="0.0.0.0", port=5000)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

