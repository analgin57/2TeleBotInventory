#!/usr/bin/env python3

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

config_file = 'config.ini'
config = ConfigParser()
config.read(config_file)

# Инициализация начального значения для configured
configured = 0

# Проверка наличия секции 'start' в конфигурационном файле
if 'start' in config:
    configured = config.getboolean('start', 'configured')
if not configured:
    create_file = input('Создать новый конфигурационный файл? (да/нет): ')
    if create_file.lower() in ['да', 'д', 'yes', 'y']:
        host = input('Введите адрес базы данных (просто Enter для значения "localhost"): ') or 'localhost'
        user = input('Введите имя пользователя БД (просто Enter для значения "user"): ') or 'user'
        password = input('Введите пароль пользователя БД (просто Enter для значения "password"): ') or 'password'
        database = input('Введите название БД (просто Enter для значения "mydatabase"): ') or 'mydatabase'
        admin_chat_id = input('Введите пользовательский идентификатор администратора бота в Телеграмм (просто Enter для значения "000000000"): ') or '000000000'
        adm_bot_token = input('Введите токен администраторского бота (просто Enter для пустого значения): ') or ''
        usr_bot_token = input('Введите токен пользовательского бота (просто Enter для пустого значения): ') or ''

        with open(config_file, 'w') as file:
            file.write(f"""[start]
configured = 0

[mysql]
# Адрес базы данных
host = {host}
# Имя (логин) пользователя БД
user = {user}
# Пароль пользователя БД
password = {password}
# Название БД
database = {database}

[telegram]
# Пользовательский идентификатор администратора бота в Телеграмм
admin_chat_id = {admin_chat_id}
# Токен администраторского бота
adm_bot_token = {adm_bot_token}
# Токен пользовательского бота
usr_bot_token = {usr_bot_token}
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



if configured == '1':
    print(f"{get_current_time()} Настройки уже сконфигурированы. Пропуск проверок.")
else:
    # Подключение к базе данных
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

    # Проверка наличия таблицы users
    cursor = conn.cursor(buffered=True)
    table_name_users = "users"
    try:
        cursor.execute(f"SELECT * FROM {table_name_users}")
        print(f"{get_current_time()} Таблица {table_name_users} найдена.")
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Таблица {table_name_users} не существует. Ошибка: {e}")
        create_table = input("Создать таблицу 'users'? (да/нет): ")
        if create_table.lower() in ['да', 'д', 'yes', 'y']:
            try:
                cursor.execute(f"""CREATE TABLE {table_name_users} (
                                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                                    user_name VARCHAR(255),
                                    user_function VARCHAR(255),
                                    user_office VARCHAR(255),
                                    user_email VARCHAR(255),
                                    user_chat_id VARCHAR(20),
                                    user_flags VARCHAR(255)
                                )""")

                print(f"{get_current_time()} Таблица 'users' успешно создана.")
            except mysql.connector.Error as e:
                print(f"{get_current_time()} Ошибка при создании таблицы: {e}")
                exit()
        else:
            print(f"{get_current_time()} Программа завершена.")
            exit()

    # Проверка наличия таблицы offices
    table_name_offices = "offices"
    try:
        cursor.execute(f"SELECT * FROM {table_name_offices}")
        print(f"{get_current_time()} Таблица {table_name_offices} найдена.")
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Таблица {table_name_offices} не существует. Ошибка: {e}")
        create_table_offices = input("Создать таблицу 'offices'? (да/нет): ")
        if create_table_offices.lower() in ['да', 'д', 'yes', 'y']:
            try:
                cursor.execute(f"""CREATE TABLE {table_name_offices} (
                                    office_id INT AUTO_INCREMENT PRIMARY KEY,
                                    office_name VARCHAR(255),
                                    office_description VARCHAR(255)
                                )""")

                print(f"{get_current_time()} Таблица 'offices' успешно создана.")
            except mysql.connector.Error as e:
                print(f"{get_current_time()} Ошибка при создании таблицы offices: {e}")
                exit()

        else:
            print(f"{get_current_time()} Программа завершена.")
            exit()

    # Проверка наличия таблицы functions
    table_name_functions = "functions"
    try:
        cursor.execute(f"SELECT * FROM {table_name_functions}")
        print(f"{get_current_time()} Таблица {table_name_functions} найдена.")
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Таблица {table_name_functions} не существует. Ошибка: {e}")
        create_table_functions = input("{current_time} Создать таблицу 'functions'? (да/нет): ")
        if create_table_functions.lower() in ['да', 'д', 'yes', 'y']:
            try:
                cursor.execute(f"""CREATE TABLE {table_name_functions} (
                                    function_id INT AUTO_INCREMENT PRIMARY KEY,
                                    function_name VARCHAR(255),
                                    function_description VARCHAR(255)
                                )""")

                print(f"{get_current_time()} Таблица 'functions' успешно создана.")
            except mysql.connector.Error as e:
                print(f"{get_current_time()} Ошибка при создании таблицы functions: {e}")
                exit()

        else:
            print(f"{get_current_time()} Программа завершена.")
            exit()
    config.set('start', 'configured', '1')
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

    print(f"{get_current_time()} Все таблицы успешно созданы. Настройки сконфигурированы.")
    # Закрытие соединения
    cursor.close()
    conn.close()

def get_config_value(section, key):
    value = config.get(section, key)
    return value

config = configparser.ConfigParser()
config.read('config.ini')

host = get_config_value('mysql', 'host')
user = get_config_value('mysql', 'user')
password = get_config_value('mysql', 'password')
database = get_config_value('mysql', 'database')
admin_chat_id = get_config_value('telegram', 'admin_chat_id')

# Функции для создания клавиатур
def create_offices_keyboard():
    offices_keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    db_cursor.execute("SELECT office_name FROM offices")
    offices = db_cursor.fetchall()
    
    for office in offices:
        offices_keyboard.add(types.KeyboardButton(office[0]))
    
    cancel_button = types.KeyboardButton("❌Отмена❌")
    offices_keyboard.add(cancel_button)

    return offices_keyboard

def create_functions_keyboard():
    functions_keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    db_cursor.execute("SELECT function_name FROM functions")
    functions = db_cursor.fetchall()
    
    for function in functions:
        functions_keyboard.add(types.KeyboardButton(function[0]))
    
    cancel_button = types.KeyboardButton("❌Отмена❌")
    functions_keyboard.add(cancel_button)

    return functions_keyboard

# Обработчики для adm_bot
adm_bot = telebot.TeleBot(config['telegram']['adm_bot_token'])

@adm_bot.message_handler(commands=['start'])
def start_adm_bot(message):
    if check_admin_rights(message):
        bot.send_message(message.chat.id, "Права администратора подтверждены.")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        # Проверка наличия и заполненности таблиц offices, functions и users
        table_names = ["offices", "functions", "users"]
        for table_name in table_names:
            try:
                db_cursor.execute(f"SELECT * FROM {table_name}")
                result = db_cursor.fetchall()
                if not result:
                    bot.send_message(message.chat.id, f"Таблица {table_name} пустая.")
                    bot.send_message(message.chat.id, f"Заполнить таблицу - /{table_name}")
            except mysql.connector.Error as e:
                bot.send_message(message.chat.id, f"Ошибка при проверке таблицы {table_name}: {e}")

# Обработчики для usr_bot
usr_bot = telebot.TeleBot(config['telegram']['usr_bot_token'])

@usr_bot.message_handler(commands=['start'])
def start_usr_bot(message):
    chat_id = message.chat.id
    db_cursor.execute("SELECT * FROM users WHERE user_chat_id = %s", (chat_id,))
    user = db_cursor.fetchone()

    if user:
        usr_bot.send_message(chat_id, "Добро пожаловать! Вы уже зарегистрированы.")
    else:
        usr_bot.send_message(chat_id, "Для начала работы, пожалуйста, зарегистрируйтесь.")
        usr_bot.send_message(chat_id, "Введите свою Фамилию Имя Отчество:")
        usr_bot.register_next_step_handler(message, process_user_name)

def process_user_name(message):
    user_name = message.text
    pattern = r'^[А-Я][а-я]{1,20} [А-Я][а-я]{1,20} (?:[А-Я][а-я]{1,20}вна|[А-Я][а-я]{1,20}вич)$'
    if not re.match(pattern, user_name):
        usr_bot.send_message(message.chat.id, "❌Неверный формат Фамилии Имени Отчества!")
        usr_bot.register_next_step_handler(message, process_user_name)
        return
    usr_bot.send_message(message.chat.id, "Выберите предприятие из списка:", reply_markup=create_offices_keyboard())
    usr_bot.register_next_step_handler(message, process_user_office, user_name)

def process_user_office(message, user_name):
    user_office = message.text
    usr_bot.send_message(message.chat.id, "Выберите должность из списка:", reply_markup=create_functions_keyboard())
    usr_bot.register_next_step_handler(message, process_user_function, user_name, user_office)

def process_user_function(message, user_name, user_office):
    user_function = message.text
    user_info = f"Имя: {user_name}\nОфис: {user_office}\nДолжность: {user_function}"
    usr_bot.send_message(message.chat.id, f"Проверьте данные:\n{user_info}\n\n", reply_markup=create_actions_keyboard())
    usr_bot.register_next_step_handler(message, process_user_confirmation, user_name, user_office, user_function)

def process_user_confirmation(message, user_name, user_office, user_function):
    if message.text == "/save_user":
        save_new_user_task(message, user_name, user_office, user_function)
    elif message.text == "/cancel":
        usr_bot.send_message(message.chat.id, "🚧 Операция отменена 🚧")
    else:
        usr_bot.send_message(message.chat.id, "Выберите действие из клавиатуры.")

def save_new_user_task(message, user_name, user_office, user_function):
    chat_id = message.chat.id
    db_cursor.execute("INSERT INTO users (user_name, user_office, user_function, user_chat_id) VALUES (%s, %s, %s, %s)", (user_name, user_office, user_function, chat_id))
    db_connection.commit()
    usr_bot.send_message(chat_id, "✅Заявка на регистрацию отправлена!")

adm_bot.polling()
usr_bot.polling()

cursor.close()
conn.close()