#!/usr/bin/env python3

# user_bot для работы с пользователями
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

# Сразу объявим current_time
def get_current_time():
    return datetime.datetime.now().strftime("[%d.%m.%Y %H:%M:%S]")
current_time = get_current_time()
# Инициализация конфига
config_file = 'userbot.ini'

# Проверка наличия конфигурационного файла
if os.path.exists(config_file):
    print(f'{get_current_time()} Конфигурационный файл {config_file} найден.')
else:
    create_file = input('Создать новый конфигурационный файл? (да/нет): ')
    if create_file.lower() in ['да', 'д', 'yes', 'y']:
        bot_token = input('Введите токен Вашего бота (просто Enter для пустого значения): ') or ''

        with open(config_file, 'w') as file:
            file.write(f"""[start]
# Установите configured = 1, если все настройки выставлены правильно и изменений больше не будет
configured = 0

[telegram]
# Токен Вашего бота в Телеграмм
bot_token = {bot_token}
""")
        print(f'{get_current_time()} Создан новый конфигурационный файл {config_file}.')
    else:
        print(f'{get_current_time()} Новый конфигурационный файл не создан.')
        print(f'{get_current_time()} Программа завершена.')
        exit()

# Чтение параметров подключения из конфигурационного файла
config = ConfigParser()
config.read(config_file)
configured = config.get('start', 'configured')
bot_token = config.get('telegram', 'bot_token')

# Создание объекта бота
bot = telebot.TeleBot(bot_token)

# Инициализация логгера
logger = telebot.logger
telebot.logger.setLevel(logging.INFO) # Устанавливаем уровень логирования DEBUG/INFO/WARNING/ERROR/CRITICAL

# Проверка настроек конфигурации
if configured == '1':
    print(f"{get_current_time()} Настройки уже сконфигурированы. Пропуск проверок.")
else:
    # Здесь мы предполагаем, что у нас есть доступ к БД, настроенной в adm_bot, и мы можем использовать ее для проверок
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

    # Проверка наличия таблицы tasks
    cursor = conn.cursor()
    table_name_tasks = "tasks"
    try:
        cursor.execute(f"SELECT * FROM {table_name_tasks}")
        print(f"{get_current_time()} Таблица {table_name_tasks} найдена.")
    except mysql.connector.Error as e:
        print(f"{get_current_time()} Таблица {table_name_tasks} не существует. Ошибка: {e}")
        create_table = input("Создать таблицу 'tasks'? (да/нет): ")
        if create_table.lower() in ['да', 'д', 'yes', 'y']:
            try:
                cursor.execute(f"""CREATE TABLE {table_name_tasks} (
                                    task_id INT AUTO_INCREMENT PRIMARY KEY,
                                    receiver INT,
                                    status ENUM('new', 'in_progress', 'completed', 'canceled') NOT NULL DEFAULT 'new',
                                    name VARCHAR(255),
                                    function VARCHAR(255),
                                    office VARCHAR(255),
                                    email VARCHAR(255),
                                    chat_id VARCHAR(20),
                                    flags VARCHAR(255),
                                    comment TEXT,
                                    target TEXT
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
    # Закрытие соединения
    cursor.close()
    conn.close()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Добро пожаловать в user_bot! Введите /help для получения списка команд.")

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, "Список команд:\n/start - начать работу с ботом\n/help - получить список команд\n/tasks - получить список задач\n/new_task - создать новую задачу")

# Обработчик команды /tasks
@bot.message_handler(commands=['tasks'])
def tasks_message(message):
    # Здесь будет код для получения списка задач из базы данных и отправки их пользователю
    pass

# Обработчик команды /new_task
@bot.message_handler(commands=['new_task'])
def new_task_message(message):
    # Здесь будет код для создания новой задачи
    pass

bot.polling()
