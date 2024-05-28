#!/usr/bin/env python3

# adm_bot управляет конфигурацией предприятий, пользователей, номенклатурой запчастей
import os
import datetime
import time
import telebot
from telebot import types
import configparser
from configparser import ConfigParser
import mysql.connector
import logging
import re
import csv
import threading

# Константы
CHECK_TIME = 60  # Время проверки БД на новые задания в секундах
ALERTS_PERIODS = "60 60 120 300 1800"  # Периоды в секундах, через которые бот будет присылать сообщения о новых заявках. Последний период зацикливается, пока активные заявки не кончатся. !!! Ниже по коду она дублируется перед def check_tasks !!! Не забудь удалить дубль внизу!
# Сразу объявим current_time
def get_current_time():
    return datetime.datetime.now().strftime("[%d.%m.%Y %H:%M:%S]")
current_time = get_current_time()

# Инициализация конфига
config_file = 'config.ini'

if os.path.exists(config_file):
    print(f'{get_current_time()} Конфигурационный файл {config_file} найден.')
else:
    create_file = input('Создать новый конфигурационный файл? (да/нет): ')
    if create_file.lower() in ['да', 'д', 'yes', 'y']:
        host = input('Введите адрес базы данных (просто Enter для значения "localhost"): ') or 'localhost'
        user = input('Введите имя пользователя БД (просто Enter для значения "user"): ') or 'user'
        password = input('Введите пароль пользователя БД (просто Enter для значения "password"): ') or 'password'
        database = input('Введите название БД (просто Enter для значения "mydatabase"): ') or 'mydatabase'
        admin_chat_id = input('Введите пользовательский идентификатор администратора бота в Телеграмм (просто Enter для значения "000000000"): ') or '000000000'
        bot_token = input('Введите токен вашего бота (просто Enter для пустого значения): ') or ''
                
        with open(config_file, 'w') as file:
            file.write(f"""[start]
# Установите configured = 1, если все настройки выставлены правильно и изменений больше не будет
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
# Токен вашего бота в Телеграмм
bot_token = {bot_token}
""")
        print(f'{get_current_time()} Создан новый конфигурационный файл {config_file}.')
    else:
        print(f'{get_current_time()} Новый конфигурационный файл не создан.')
        print(f'{get_current_time()} Программа завершена.')

# Чтение параметров подключения из конфигурационного файла
config = ConfigParser()
config.read('config.ini')
configured = config.get('start', 'configured')
host = config.get('mysql', 'host')
user = config.get('mysql', 'user')
password = config.get('mysql', 'password')
database = config.get('mysql', 'database')

if configured == '1':
    print(f"{get_current_time()} Настройки уже сконфигурированы. Пропуск проверок.")
else:
    # Подключение к базе данных
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
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
bot_token = get_config_value('telegram', 'bot_token')
admin_chat_id = get_config_value('telegram', 'admin_chat_id')

# Подключение к базе данных MySQL
db_connection = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
db_cursor = db_connection.cursor()

# Создание объекта бота
bot = telebot.TeleBot(config['telegram']['bot_token'])

# Проверка на администратора
def check_admin_rights(message):
    if str(message.chat.id) == admin_chat_id:
        return True
    else:
        bot.send_message(message.chat.id, "⛔У Вас нет прав администратора⛔", reply_markup=telebot.types.ReplyKeyboardRemove())
        return False

# Инициализация логгера
logger = telebot.logger
telebot.logger.setLevel(logging.INFO) # Устанавливаем уровень логирования DEBUG/INFO/WARNING/ERROR/CRITICAL

@bot.message_handler(commands=['save_user'])
def handle_save_user(message):
    if check_admin_rights(message):
        save_new_user(message)

@bot.message_handler(commands=['cancel_user'])
def handle_cancel_user(message):
    if check_admin_rights(message):
        process_cancel_flags(message)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    if check_admin_rights(message):
        db_connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        db_cursor = db_connection.cursor()

        bot.send_message(message.chat.id, "Права администратора подтверждены.", reply_markup=telebot.types.ReplyKeyboardRemove())
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

# Обработчик команды /offices
last_office_id = 0  # Предположим, что изначально у нас нет записей в базе
@bot.message_handler(commands=['offices'])
def offices_command(message):
    if check_admin_rights(message):
        global last_office_id
        
        if str(message.chat.id) == admin_chat_id:
            db_cursor.execute("SELECT * FROM offices")
            offices = db_cursor.fetchall()

            if not offices:
                bot.send_message(message.chat.id, "В таблице offices нет данных", reply_markup=telebot.types.ReplyKeyboardRemove())
            else:
                emojis_mapping = {
                    '0': '0⃣',
                    '1': '1⃣',
                    '2': '2⃣',
                    '3': '3⃣',
                    '4': '4⃣',
                    '5': '5⃣',
                    '6': '6⃣',
                    '7': '7⃣',
                    '8': '8⃣',
                    '9': '9⃣'
                }

                for office in offices:
                    last_office_id = int(office[0])  # Обновляем last_office_id

                    emojis_office_id = ''.join([emojis_mapping[char] for char in str(office[0])])
                    message_text = f"{emojis_office_id}, <b>{office[1]}</b>, {office[2]}"
                    bot.send_message(message.chat.id, message_text, parse_mode='HTML')

            bot.send_message(message.chat.id, "Добавить /add, Удалить /del, Отмена /cancel", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, process_offices_action)
        
        else:
            bot.send_message(message.chat.id, "⛔️ Недостаточно прав для выполнения этой команды ⛔️", reply_markup=telebot.types.ReplyKeyboardRemove())

def confirm_delete_office(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Операция удаления отменена")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    office_id = message.text

    db_cursor.execute("SELECT * FROM offices WHERE office_id = %s", (office_id,))
    office = db_cursor.fetchone()

    if not office:
        bot.send_message(message.chat.id, "❌Предприятие/отдел с таким ID не найдено❌")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    else:
        confirm_text = f"❗Вы действительно хотите удалить {office_id}: {office[1]}? (да/нет)"
        bot.send_message(message.chat.id, confirm_text)
        bot.register_next_step_handler(message, delete_confirmation, office_id)

def delete_confirmation(message, office_id):
    if message.text.lower() == 'да':
        db_cursor.execute("DELETE FROM offices WHERE office_id = %s", (office_id,))
        db_connection.commit()
        bot.send_message(message.chat.id, f"Предприятие/отдел {office_id} удалено")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    else:
        bot.send_message(message.chat.id, "✋Удаление отменено🤚")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    bot.send_message(message.chat.id, "Добавить /add, Удалить /del, Отмена /cancel", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_offices_action)

def process_offices_action(message):
    action = message.text.lower()
    
    if action == '/add':
        bot.send_message(message.chat.id, "Введите краткое название предприятия/отдела или /cancel :", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, add_office_name)
    
    elif action == '/del':
        bot.send_message(message.chat.id, "Введите ID предприятия/отдела для удаления или /cancel :", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, confirm_delete_office)
    
    elif action == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())

def add_office_name(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return
    
    global new_office_name
    new_office_name = message.text
    
    bot.send_message(message.chat.id, "Введите подробное описание предприятия/отдела или /cancel :", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, add_office_description)

def add_office_description(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users")
        return
    
    office_description = message.text
    new_office_id = last_office_id + 1
    db_cursor.execute("INSERT INTO offices (office_id, office_name, office_description) VALUES (%s, %s, %s)", (new_office_id, new_office_name, office_description))
    db_connection.commit()    
    bot.send_message(message.chat.id, f"✅Предприятие/отдел '{new_office_name}' добавлен✅")
    bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove()) 
    
# Обработчик команды /functions
last_function_id = 0  # Предположим, что изначально у нас нет записей в базе
@bot.message_handler(commands=['functions'])
def functions_command(message):
    global last_function_id
    
    if check_admin_rights(message):
        db_cursor.execute("SELECT * FROM functions")
        functions = db_cursor.fetchall()

        if not functions:
            bot.send_message(message.chat.id, "В таблице functions нет данных", reply_markup=telebot.types.ReplyKeyboardRemove())
        else:
            emojis_mapping = {
                '0': '0⃣',
                '1': '1⃣',
                '2': '2⃣',
                '3': '3⃣',
                '4': '4⃣',
                '5': '5⃣',
                '6': '6⃣',
                '7': '7⃣',
                '8': '8⃣',
                '9': '9⃣'
            }

            for function in functions:
                last_function_id = int(function[0])  # Обновляем last_function_id

                emojis_function_id = ''.join([emojis_mapping[char] for char in str(function[0])])
                message_text = f"{emojis_function_id}, <b>{function[1]}</b>, {function[2]}"
                bot.send_message(message.chat.id, message_text, parse_mode='HTML')
        
        bot.send_message(message.chat.id, "Добавить /add Удалить /del Отмена /cancel", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_functions_action)

def process_functions_action(message):
    action = message.text.lower()
    
    if action == '/add':
        bot.send_message(message.chat.id, "Введите *название должности/функции* или /cancel :", parse_mode='Markdown', reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, add_function_name)
    
    elif action == '/del':
        bot.send_message(message.chat.id, "Введите ID должности/функции для удаления или /cancel :")
        bot.register_next_step_handler(message, confirm_delete_function)
    
    elif action == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())

def confirm_delete_function(message):    
    function_id = message.text

    db_cursor.execute("SELECT * FROM functions WHERE function_id = %s", (function_id,))
    function = db_cursor.fetchone()

    if not function:
        bot.send_message(message.chat.id, "❌Должность/функция с таким ID не найдена❌")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return    
    if function_id == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return
    else:    
        bot.send_message(message.chat.id, f"⁉Вы уверены, что хотите удалить запись с ID {function_id}? (да/нет) или /cancel")
        bot.register_next_step_handler(message, process_confirm_delete, function_id)

def process_confirm_delete(message, function_id):    
    confirmation = message.text.lower()
    if confirmation == 'да':
        db_cursor.execute("DELETE FROM functions WHERE function_id = %s", (function_id,))        
        db_connection.commit()
        bot.send_message(message.chat.id, f"✅Запись с ID {function_id} удалена✅")    
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    else:
        bot.send_message(message.chat.id, "✋Удаление отменено🤚")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return

def add_function_name(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return
    
    function_name = message.text
    
    if function_name:
        bot.send_message(message.chat.id, "Введите *описание* для должности/функции или /cancel", parse_mode='Markdown')
        bot.register_next_step_handler(message, add_function_description, function_name)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное название должности/функции или /cancel")

def add_function_description(message, function_name):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return
    function_description = message.text
    if function_description:
        function_description = message.text
        new_function_id = last_function_id + 1
        db_cursor.execute("INSERT INTO functions (function_id, function_name, function_description) VALUES (%s, %s, %s)", (new_function_id, function_name, function_description))
        db_connection.commit()
    
        bot.send_message(message.chat.id, f"✅Должность/функция '{function_name}' с описанием '{function_description}' создана✅")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())        
        return
    else:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное описание для должности/функции", reply_markup=telebot.types.ReplyKeyboardRemove())

# Обработчик команды /users
last_name_id = 0  # Предположим, что изначально у нас нет записей в базе
@bot.message_handler(commands=['users'])
def users_command(message):
    if check_admin_rights(message):
        db_cursor.execute("SELECT * FROM users")
        users = db_cursor.fetchall()
        print(f"{get_current_time()} Администратор: список пользователей")

        if not users:
            bot.send_message(message.chat.id, "В таблице users нет данных")
        else:
            bot.send_message(message.chat.id, "Список данных из таблицы users:")
            emojis_mapping = {
                '0': '0️⃣',
                '1': '1️⃣',
                '2': '2️⃣',
                '3': '3️⃣',
                '4': '4️⃣',
                '5': '5️⃣',
                '6': '6️⃣',
                '7': '7️⃣',
                '8': '8️⃣',
                '9': '9️⃣'
            }

            for user in users:
                last_user_id = int(user[0])  # Обновляем last_user_id
                emojis_user_id = ''.join([emojis_mapping[char] for char in str(user[0])])
                message_text = f"{emojis_user_id}, Имя: {user[1]}, Должность: {user[2]}, Офис: {user[3]}, Email: {user[4]}, Chat ID: {user[5]}, Флаги: {user[6]}"
                bot.send_message(message.chat.id, message_text)
        
        bot.send_message(message.chat.id, "Добавить /add Удалить /del Отмена /cancel")
        bot.register_next_step_handler(message, process_users_action)

def process_users_action(message):
    reset_global_variables()
    action = message.text.lower()
    
    if action == '/add':
        print(f"{get_current_time()} Администратор: добавить пользователя")
        bot.send_message(message.chat.id, "Введите *имя* пользователя или /cancel :", parse_mode='Markdown', reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, add_new_user_name)
    
    elif action == '/del':
        print(f"{get_current_time()} Администратор: удалить пользователя")
        bot.send_message(message.chat.id, "Введите ID пользователя для удаления или /cancel :", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, confirm_delete_user)
    
    elif action == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())

def confirm_delete_user(message):
    user_id = message.text

    if user_id == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        # Проверка существования пользователя в базе данных
        db_cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = db_cursor.fetchone()

        if user:
            bot.send_message(message.chat.id, f"⁉Вы уверены, что хотите удалить запись с ID {user_id}? (да/нет) или /cancel", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, process_confirm_delete, user_id)
        else:
            bot.send_message(message.chat.id, f"❌Пользователя с ID {user_id} не существует❌")
            print(f"{get_current_time()} Ошибка ввода ID пользователя.")
            bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())

def process_confirm_delete(message, user_id):
    confirmation = message.text.lower()

    if confirmation == 'да':
        db_cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        db_connection.commit()
        print(f"{get_current_time()} Пользователь с ID:{user_id} удалён")
        bot.send_message(message.chat.id, f"✅Пользователь с ID:{user_id} удалён✅")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "✋Удаление отменено🤚")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())

def create_functions_keyboard():
    functions_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    db_cursor.execute("SELECT function_name FROM functions")
    functions = db_cursor.fetchall()
    
    for function in functions:
        functions_keyboard.add(telebot.types.KeyboardButton(function[0]))
    
    cancel_button = telebot.types.KeyboardButton("❌Отмена❌")
    functions_keyboard.add(cancel_button)

    return functions_keyboard

def create_offices_keyboard():
    offices_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    db_cursor.execute("SELECT office_name FROM offices")
    offices = db_cursor.fetchall()
    
    for office in offices:
        offices_keyboard.add(telebot.types.KeyboardButton(office[0]))
    
    cancel_button = telebot.types.KeyboardButton("❌Отмена❌")
    offices_keyboard.add(cancel_button)

    return offices_keyboard

def add_user_office(message):
    global new_user_office
    new_user_office = message.text
    
    if new_user_office == '❌Отмена❌':
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    else:
        db_cursor.execute("INSERT INTO user_offices (user_name, office_name) VALUES (%s, %s)", (user_name, office_name))
        db_connection.commit()
        bot.send_message(message.chat.id, f"✅Офис '{office_name}' выбран для пользователя '{user_name}'✅")
        bot.send_message(message.chat.id, "Операция завершена. Команды: /offices /functions /users")

new_user_function_id = None  # Глобальная переменная для хранения function_id

# Главная функция добавления пользователя
def add_new_user_name(message):
    global new_user_name
    new_user_name = message.text
    
    if new_user_name == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    else:
        pattern = r'^[А-Я][а-я]{1,20} [А-Я][а-я]{1,20} (?:[А-Я][а-я]{1,20}вна|[А-Я][а-я]{1,20}вич)$'
        if not re.match(pattern, new_user_name):
            bot.send_message(message.chat.id, "❌Неверный формат Фамилии Имени Отчества!")
            bot.register_next_step_handler(message, add_new_user_name)
            return
        new_user_name = message.text
        print(f"{get_current_time()} Имя пользователя: ", new_user_name)
        bot.send_message(message.chat.id, "Выберите должность пользователя из списка:", reply_markup=create_functions_keyboard())
        bot.register_next_step_handler(message, add_new_user_function)

# Получаем function_id по function_name
def get_function_id(function_name):
    db_cursor.execute("SELECT function_id FROM functions WHERE function_name = %s", (function_name,))
    result = db_cursor.fetchone()
    if result:
        return result[0]
    else:
        return 0  # Возвращаем 0, если function_id не найден

def add_new_user_function(message):
    global new_user_function, new_user_function_id
    new_user_function = message.text
    new_user_function_id = get_function_id(new_user_function)
    
    if new_user_function == '❌Отмена❌' or new_user_function == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # Получаем список всех должностей из базы данных
    db_cursor.execute("SELECT function_name FROM functions")
    function_names = [row[0] for row in db_cursor.fetchall()]

    if new_user_function not in function_names:
        print(f"{get_current_time()} Введены неверные данные. Повторный запрос должности")
        bot.send_message(message.chat.id, "❌Выберите должность из списка!❌")
        bot.register_next_step_handler(message, add_new_user_function)
    else:
        new_user_function = message.text
        bot.send_message(message.chat.id, f"✅Должность выбрана: {message.text}✅")
        print(f"{get_current_time()} Должность пользователя:", new_user_function)
        print(f"{get_current_time()} ID должности пользователя:", new_user_function_id)
        bot.send_message(message.chat.id, "Выберите офис/отдел пользователя из списка:", reply_markup=create_offices_keyboard())
        bot.register_next_step_handler(message, add_new_user_office)

# Получаем office_id по office_name
def get_office_id(office_name):
    db_cursor.execute("SELECT office_id FROM offices WHERE office_name = %s", (office_name,))
    result = db_cursor.fetchone()
    if result:
        return result[0]
    else:
        return 0  # Возвращаем 0, если office_id не найден

# Добавляем новый офис пользователя
def add_new_user_office(message):
    global new_user_office, new_user_office_id
    new_user_office = message.text
    new_user_office_id = get_office_id(new_user_office)
    
    if new_user_office == '❌Отмена❌' or new_user_office == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # Получаем список всех офисов из базы данных
    db_cursor.execute("SELECT office_name FROM offices")
    office_names = [row[0] for row in db_cursor.fetchall()]

    if new_user_office not in office_names:
        print(f"{get_current_time()} Введены неверные данные. Повторный запрос офиса/отдела")
        bot.send_message(message.chat.id, "❌Выберите офис из списка!❌")
        bot.register_next_step_handler(message, add_new_user_office)
    else:
        new_user_office = message.text
        bot.send_message(message.chat.id, f"✅Офис/отдел выбран: {message.text}✅")
        print(f"{get_current_time()} Офис пользователя:", new_user_office)
        print(f"{get_current_time()} ID офиса пользователя:", new_user_office_id)
        bot.send_message(message.chat.id, "Введите email пользователя или /skip. /cancel для отмены")
        bot.register_next_step_handler(message, add_new_user_email)

# Добавляем email нового пользователя
def add_new_user_email(message):
    global new_user_email
    new_user_email = message.text

    if new_user_email == '/cancel':
        print(f"{get_current_time()} Администратор: отмена")
        bot.send_message(message.chat.id, "🚧Операция отменена🚧")
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
    if new_user_email == '/skip':
        print(f"{get_current_time()} Администратор: пустой email")
        bot.send_message(message.chat.id, "⏭Вы пропустили ввод email⏭")
        new_user_email = None
        bot.send_message(message.chat.id, "Введите chat_id пользователя или /skip. /cancel для отмены")
        bot.register_next_step_handler(message, add_new_user_chat_id)
        return
    else:
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if re.match(email_pattern, new_user_email):
            print(f"{get_current_time()} Email пользователя:", new_user_email)
            bot.send_message(message.chat.id, f"✅Email: {new_user_email} ✅")
            bot.send_message(message.chat.id, "Введите chat_id пользователя или /skip. /cancel для отмены")
            bot.register_next_step_handler(message, add_new_user_chat_id)
        else:
            new_user_email = None
            print(f"{get_current_time()} Введен неверный формат email. Необходимо ввести email в корректном формате.")
            bot.send_message(message.chat.id, "❌Пожалуйста, введите корректный email!❌")
            bot.send_message(message.chat.id, "/cancel - отмена, /skip - пропустить")
            bot.register_next_step_handler(message, add_new_user_email)

new_user_flags = []
users_chat_id = {}

def add_new_user_chat_id(message):
    global new_user_chat_id
    user_id = message.chat.id
    if user_id not in users_chat_id:
        users_chat_id[user_id] = {"selected_flag": None, "score": 0}

    flags_keyboard = create_flags_keyboard(message)  # Создание клавиатуры с флагами

    bot.send_message(user_id, "Выберите флаг:", reply_markup=flags_keyboard)  # Отправка клавиатуры пользователю

    try:
        if message.text == '/skip':
            bot.send_message(message.chat.id, "⏭Вы пропустили ввод chat_id⏭")
            new_user_chat_id = None
            return create_flags_keyboard(message)
        
        if message.text == '❌Отмена❌' or message.text == '/cancel':
            bot.send_message(message.chat.id, "🚧Операция отменена🚧")
            bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        
        new_user_chat_id = int(message.text)
        
        # Проверка на совпадение chat_id в таблице users
        db_cursor.execute("SELECT * FROM users WHERE user_chat_id = %s", (new_user_chat_id,))
        result = db_cursor.fetchone()
        
        if result:
            bot.send_message(message.chat.id, "❗️Данный chat_id уже зарегистрирован❗️", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.send_message(message.chat.id, "Пожалуйста, введите другой или /cancel для отмены.")
            return
        return

    except ValueError:
        bot.send_message(message.chat.id, "❗️Некорректный формат chat_id❗️", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, "Введите chat_id в числовом формате")
        bot.register_next_step_handler(message, add_new_user_chat_id)
        return

def create_flags_keyboard(message):
    global new_user_flags
    bot.send_message(message.chat.id, f"Выбранные флаги: {new_user_flags}")

    if new_user_flags is None:
        new_user_flags = []

    if 'new_user_flags' not in globals():
        new_user_flags = []

    flags_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    
    with open('flags.csv', 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Пропускаем заголовок
        
        for row in reader:
            flag = row[0]
            name = row[1]
            description = row[2]
            
            if flag not in new_user_flags:
                flags_keyboard.row(telebot.types.KeyboardButton(f"{name} ({flag})"))
            else:
                flags_keyboard.row(telebot.types.KeyboardButton(f"🚩 {name} ({flag})"))

    return flags_keyboard

new_user_flags = []    

@bot.message_handler(func=lambda message: True)
def handle_flags_selection(message):
    global new_user_flags
    if message.text in [btn['text'] for row in create_flags_keyboard(message).keyboard for btn in row]:
        flag = message.text.split('(')[-1].split(')')[0]  # Извлекаем флаг из названия кнопки
        if flag in new_user_flags:
            new_user_flags.remove(flag)
            bot.send_message(message.chat.id, f"Флаг {message.text} был удален из списка выбранных.", reply_markup=create_flags_keyboard(message))
        else:
            if flag == 's':
                process_save_flags(message)
            elif flag == 'q':
                process_cancel_flags(message)
            else:
                new_user_flags.append(flag)
                bot.send_message(message.chat.id, f"Флаг {message.text} добавлен в список выбранных.", reply_markup=create_flags_keyboard(message))
    if message.text in ["💾Сохранить", "❌Отмена"]:
        if message.text == "💾Сохранить":
            handle_save_user(message)
        elif message.text == "❌Отмена❌":
            handle_cancel_user(message)
    else:
        bot.send_message(message.chat.id, "Выбери действие из клавиатуры.")

def process_save_flags(message):
    global new_user_flags
    if new_user_flags:
        bot.send_message(message.chat.id, f"Выбранные флаги были сохранены: {new_user_flags}", reply_markup=telebot.types.ReplyKeyboardRemove())
        print(f"{get_current_time()} Сохраненные флаги: {new_user_flags}")
        check_user(message)
    else:
        bot.send_message(message.chat.id, "Вы не выбрали ни одного флага.", reply_markup=create_flags_keyboard(message))
        return create_flags_keyboard(message)

def process_cancel_flags(message):
    global new_user_flags
    new_user_flags = []
    print(f"{get_current_time()} Администратор: отмена")
    bot.send_message(message.chat.id, "🚧Операция отменена🚧")
    reset_global_variables()
    bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
    return

def get_next_free_user_id():
    db_cursor.execute("SELECT MIN(user_id) FROM users WHERE user_id NOT IN (SELECT user_id FROM users WHERE user_id > 0)")
    result = db_cursor.fetchone()
    return result[0] if result else 0

def save_or_cancel(message):
    if message.text == "/save_user":
        save_new_user(message)
    elif message.text == "/cancel":
        process_cancel_flags(message)
    else:
        bot.send_message(message.chat.id, "Выберите действие из клавиатуры.")

def create_actions_keyboard():
    actions_keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
    save_button = telebot.types.KeyboardButton("/save_user")
    cancel_button = telebot.types.KeyboardButton("/cancel_user")
    actions_keyboard.add(save_button, cancel_button)

    return actions_keyboard

def print_table_structure(table_name):
    db_cursor.execute(f"DESCRIBE {table_name}")
    structure = db_cursor.fetchall()
    print(f"{get_current_time()} Структура таблицы {table_name}:")
    for row in structure:
        print(row)

def print_table_content(table_name):
    db_cursor.execute(f"SELECT * FROM {table_name}")
    content = db_cursor.fetchall()
    print(f"{get_current_time()} Содержимое таблицы {table_name}:")
    for row in content:
        print(row)

def check_user(message):
    global new_user_name, new_user_function, new_user_office, new_user_email, new_user_chat_id, new_user_flags, free_user_id
    user_info = f"Имя: {new_user_name}\nДолжность: {new_user_function}\nОфис: {new_user_office}\nEmail: {new_user_email}\nChat_id: {new_user_chat_id}\nФлаги: {', '.join(new_user_flags)}"
    bot.send_message(message.chat.id, f"⚠Проверьте данные:\n{user_info}\n\n", reply_markup=create_actions_keyboard())

def save_new_user(message):
    global new_user_name, new_user_function, new_user_office, new_user_email, new_user_chat_id, new_user_flags, free_user_id
    if message.text == "/save_user":
        free_user_id = get_next_free_user_id()
        user_data = (free_user_id, new_user_name, new_user_function, new_user_office, new_user_email, new_user_chat_id, ''.join(new_user_flags))
        db_cursor.execute("INSERT INTO users (user_id, user_name, user_function, user_office, user_email, user_chat_id, user_flags) VALUES (%s, %s, %s, %s, %s, %s, %s)", user_data)
        db_connection.commit()
        bot.send_message(message.chat.id, "✅Пользователь успешно сохранен!", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, "Команды: /offices /functions /users", reply_markup=telebot.types.ReplyKeyboardRemove())
        reset_global_variables()
    elif message.text == "/cancel":
        bot.send_message(message.chat.id, "🚧 Операция отменена 🚧")
        reset_global_variables()
    else:
        bot.send_message(message.chat.id, "Выберите действие из клавиатуры.")

def reset_global_variables():
    global new_user_name, new_user_function, new_user_office, new_user_email, new_user_chat_id, new_user_flags

    new_user_name = None
    new_user_function = None
    new_user_office = None
    new_user_email = None
    new_user_chat_id = None
    new_user_flags = []
    last_user_id = 0    
    free_user_id = 0    
    return

# Функция для периодической проверки заданий
ALERTS_PERIODS = "60 60 120 300 1800"
periods = [int(period) for period in ALERTS_PERIODS.split()]

def check_tasks():
    active_tasks = False
    while True:
        db_cursor.execute("SELECT * FROM tasks WHERE receiver = 'adm_bot' AND status = 'new'")
        tasks = db_cursor.fetchall()
        active_tasks = bool(tasks)
        
        new_task_alert(tasks, active_tasks, periods)
        time.sleep(CHECK_TIME)

def new_task_alert(tasks, active_tasks, periods):
    current_period = 0
    last_period = len(periods) - 1
    while active_tasks:
        process_task(tasks[0])
        time.sleep(int(periods[current_period]))
        
        current_period = (current_period + 1) % len(periods)
        if current_period == last_period:
            while active_tasks:
                process_task(tasks[0])
                time.sleep(int(periods[last_period]))

def process_task(task):
    bot.send_message(admin_chat_id, f"Новая заявка:\nID: {task[0]}\nИмя: {task[3]}\nФункция: {task[4]}\nОфис: {task[5]}\nСтатус: {task[2]}")
    bot.send_message(admin_chat_id, f"Выберите действие:\n/approve - Одобрить\n/reject - Отклонить\n/send_back - Отправить на доработку")

# Функция для обработки выбора действия
@bot.message_handler(func=lambda message: message.text.startswith('/'))
def handle_task_action(message):
    action = message.text.lower()
    if action == "/approve":
        # Одобрение задания
        approve_task(message)
    elif action == "/reject":
        # Отклонение задания
        reject_task(message)
    elif action == "/send_back":
        # Отправка на доработку
        send_back_task(message)

# Запуск потока для проверки заданий
task_checker_thread = threading.Thread(target=check_tasks)
task_checker_thread.start()

# Обработка ошибок в потоке
task_checker_thread.join()  # Ждём завершения потока
if task_checker_thread.is_alive():
    print("Поток завершился с ошибкой. Программа будет перезапущена.")
    # Здесь можно добавить код для перезапуска программы

def approve_task(task):
    bot.send_message(admin_chat_id, f"Заявка ID: {task[0]} одобрена.")

def reject_task(task):
    bot.send_message(admin_chat_id, f"Заявка ID: {task[0]} отклонена.")

def send_back_task(task):
    bot.send_message(admin_chat_id, f"Заявка ID: {task[0]} отправлена на доработку.")

bot.enable_save_next_step_handlers(delay=5)
bot.polling()

db_cursor.close()
db_connection.close()
