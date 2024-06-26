#!/usr/bin/env python3

# user_bot регистрирует и обрабатывает запросы зарегистрированных пользователей
import os
import datetime
import telebot
from telebot import types
import configparser
from configparser import ConfigParser
import mysql.connector
import logging
import re
import csv

def get_current_time():
    return datetime.datetime.now().strftime("[%d.%m.%Y %H:%M:%S]")
current_time = get_current_time()

# Инициализация начального значения для configured
configured = 0

config_file = 'userbot.ini'
config = ConfigParser()
config.read(config_file)

# Проверка наличия секции 'start' в конфигурационном файле
if 'start' in config:
    configured = config.getboolean('start', 'configured')

if not configured:
    create_file = input('Создать новый конфигурационный файл? (да/нет): ')
    if create_file.lower() in ['да', 'д', 'yes', 'y']:
        bot_token = input('Введите токен Вашего бота (просто Enter для пустого значения): ') or ''

        adm_bot_config = ConfigParser()
        adm_bot_config.read('config.ini')
        mysql_config = adm_bot_config['mysql']

        with open(config_file, 'w') as file:
            file.write(f"""[start]
configured = 0

[telegram]
bot_token = {bot_token}

[mysql]
host = {mysql_config['host']}
user = {mysql_config['user']}
password = {mysql_config['password']}
database = {mysql_config['database']}
""")
        print(f'{get_current_time()} Создан новый конфигурационный файл {config_file}.')
        # Перечитать файл после записи
        config.read(config_file)
    else:
        print(f'{get_current_time()} Новый конфигурационный файл не создан.')
        print(f'{get_current_time()} Программа завершена.')
        exit()

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

try:
    conn = mysql.connector.connect(
        host=config['mysql']['host'],
        user=config['mysql']['user'],
        password=config['mysql']['password'],
        database=config['mysql']['database']
    )
    print(f"{get_current_time()} Подключение к базе данных успешно.")
except mysql.connector.Error as e:
    print(f"{get_current_time()} Ошибка подключения к базе данных: {e}")
    exit()

cursor = conn.cursor()

table_name_tasks = "tasks"

def function_call_logger(func):
    def wrapper(*args, **kwargs):
        print(f"Вызов функции {func.__name__} с аргументами: {args}, {kwargs}")
        result = func(*args, **kwargs)
        return result
    return wrapper

try:
    cursor.execute(f"SELECT * FROM {table_name_tasks}")
    results = cursor.fetchall()  # Обработка результатов запроса
except mysql.connector.Error as e:
    print(f"{get_current_time()} Таблица {table_name_tasks} не существует. Ошибка: {e}")
    create_table = input("Создать таблицу 'tasks'? (да/нет): ")
    if create_table.lower() in ['да', 'д', 'yes', 'y']:
        try:
            cursor.execute(f"""CREATE TABLE {table_name_tasks} (
                                task_id INT AUTO_INCREMENT PRIMARY KEY,
                                receiver VARCHAR(255),
                                status ENUM('new', 'in_progress', 'completed', 'canceled') NOT NULL DEFAULT 'new',
                                name VARCHAR(255),
                                function VARCHAR(255),
                                office VARCHAR(255),
                                email VARCHAR(255),
                                chat_id VARCHAR(20),
                                flags VARCHAR(255),
                                comment TEXT,
                                target TEXT,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )""")
            print(f"{get_current_time()} Таблица 'tasks' успешно создана.")
        except mysql.connector.Error as e:
            print(f"{get_current_time()} Ошибка при создании таблицы: {e}")
            exit()
    else:
        print(f"{get_current_time()} Программа завершена.")
        exit()

config.set('start', 'configured', '1')
with open(config_file, 'w') as configfile:
    config.write(configfile)

print(f"{get_current_time()} Все таблицы успешно созданы. Настройки сконфигурированы.")

bot_token = config['telegram']['bot_token']
bot = telebot.TeleBot(bot_token)

@bot.message_handler(commands=['start'])
@function_call_logger
def start_command(message):
    chat_id = message.chat.id
    cursor.execute("SELECT * FROM users WHERE user_chat_id = %s", (chat_id,))
    user = cursor.fetchone()

    if user:
        bot.send_message(chat_id, "Добро пожаловать! Вы уже зарегистрированы.", reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        # Проверка наличия заявки в таблице tasks
        cursor.execute("SELECT * FROM tasks WHERE receiver = 'adm_bot' AND status = 'new' AND chat_id = %s", (chat_id,))
        task = cursor.fetchone()
        if task:
            bot.send_message(chat_id, "🐌 Ваша заявка ждёт одобрения администратором. Ожидайте ответа! ⏳", reply_markup=telebot.types.ReplyKeyboardRemove())
        else:
            bot.send_message(chat_id, "Для начала работы, пожалуйста, зарегистрируйтесь.", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.send_message(chat_id, "Введите свою Фамилию Имя Отчество:")
            bot.register_next_step_handler(message, process_user_name)

def process_cancel(message):
    global user_name, user_office, user_function
    user_name = None
    user_office = None
    user_function = None
    bot.send_message(message.chat.id, "🚧 Операция отменена 🚧", reply_markup=telebot.types.ReplyKeyboardRemove())
    return

def create_actions_keyboard():
    actions_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    save_button = telebot.types.KeyboardButton("📝Отправить")
    cancel_button = telebot.types.KeyboardButton("❌Отмена❌")
    actions_keyboard.add(save_button, cancel_button)
    return actions_keyboard

def create_functions_keyboard():
    functions_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    cursor.execute("SELECT function_name FROM functions")
    functions = cursor.fetchall()
    
    for function in functions:
        functions_keyboard.add(telebot.types.KeyboardButton(function[0]))
    
    cancel_button = telebot.types.KeyboardButton("❌Отмена❌")
    functions_keyboard.add(cancel_button)

    return functions_keyboard

def create_offices_keyboard():
    offices_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    cursor.execute("SELECT office_name FROM offices")
    offices = cursor.fetchall()
    
    for office in offices:
        offices_keyboard.add(telebot.types.KeyboardButton(office[0]))
    
    cancel_button = telebot.types.KeyboardButton("❌Отмена❌")
    offices_keyboard.add(cancel_button)

    return offices_keyboard

def process_user_name(message):
    user_name = message.text
    pattern = r'^[А-Я][а-я]{1,20} [А-Я][а-я]{1,20} (?:[А-Я][а-я]{1,20}вна|[А-Я][а-я]{1,20}вич)$'
    if not re.match(pattern, user_name):
        bot.send_message(message.chat.id, "❌Неверный формат Фамилии Имени Отчества!", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_user_name)
        return
    bot.send_message(message.chat.id, "Выберите предприятие из списка:", reply_markup=create_offices_keyboard())
    bot.register_next_step_handler(message, process_user_office, user_name)

def get_offices_list():
    try:
        cursor.execute("SELECT office_name FROM offices")
        return [office[0] for office in cursor.fetchall()]
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Ошибка при получении списка офисов: {e}")
        return None

def process_user_office(message, user_name):
    if message.text == "/cancel" or message.text == "❌Отмена❌":
        process_cancel(message)
        start_command(message)
    else:
        offices = get_offices_list()
        if offices is not None:
            if message.text not in offices:
                bot.send_message(message.chat.id, "❌Выберите офис из списка!❌", reply_markup=create_offices_keyboard())
                bot.register_next_step_handler(message, process_user_office, user_name)
            else:
                user_office = message.text
                bot.send_message(message.chat.id, "Выберите должность из списка:", reply_markup=create_functions_keyboard())
                bot.register_next_step_handler(message, process_user_function, user_name, user_office)
        else:
            bot.send_message(message.chat.id, "Ошибка при получении списка офисов. Попробуйте позже.")
            process_cancel(message)
            start_command(message)

def get_functions_list():
    try:
        cursor.execute("SELECT function_name FROM functions")
        return [function[0] for function in cursor.fetchall()]
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Ошибка при получении списка должностей: {e}")
        return None

def process_user_function(message, user_name, user_office):
    if message.text == "/cancel" or message.text == "❌Отмена❌":
        process_cancel(message)
        start_command(message)
    else:
        functions = get_functions_list()
        if functions is not None:
            if message.text not in functions:
                bot.send_message(message.chat.id, "❌Выберите должность из списка!❌", reply_markup=create_functions_keyboard())
                bot.register_next_step_handler(message, process_user_function, user_name, user_office)
            else:
                user_function = message.text
                user_info = f"Имя: {user_name}\nОфис: {user_office}\nДолжность: {user_function}"
                # Удаление предыдущей клавиатуры
                bot.send_message(message.chat.id, f"Проверьте данные:\n{user_info}\n\n", reply_markup=telebot.types.ReplyKeyboardRemove())
                # Добавление новой клавиатуры с действиями
                actions_keyboard = create_actions_keyboard()
                bot.send_message(message.chat.id, "Выберите действие:", reply_markup=actions_keyboard)
                bot.register_next_step_handler(message, process_user_confirmation, user_name, user_office, user_function)
        else:
            bot.send_message(message.chat.id, "Ошибка при получении списка должностей. Попробуйте позже.")
            process_cancel(message)
            start_command(message)

def process_user_confirmation(message, user_name, user_office, user_function):
    if message.text == "/save_user" or message.text == "📝Отправить":
        save_new_user_task(message, user_name, user_office, user_function)
    elif message.text == "/cancel" or message.text == "❌Отмена❌":
        process_cancel(message)
        start_command(message)
    else:
        bot.send_message(message.chat.id, "Выберите действие из клавиатуры.", reply_markup=create_actions_keyboard())

def save_new_user_task(message, user_name, user_office, user_function):
    chat_id = message.chat.id
    cursor.execute("INSERT INTO tasks (receiver, status, name, function, office, chat_id) VALUES (%s, %s, %s, %s, %s, %s)", ('adm_bot', 'new', user_name, user_function, user_office, chat_id))
    conn.commit()  # Используем conn вместо db_connection
    bot.send_message(chat_id, "✅Заявка на регистрацию отправлена!", reply_markup=telebot.types.ReplyKeyboardRemove())

bot.polling()
# Закрытие курсора и соединения с базой данных
cursor.close()
conn.close()
