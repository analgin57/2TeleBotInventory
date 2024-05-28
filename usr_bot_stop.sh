#!/bin/bash

# Ищем процесс по имени "usr_bot_wd.sh"
pid=$(pgrep -f usr_bot_wd.sh)

if [ -z "$pid" ]; then
    echo "Процесс не найден"
else
    echo "Процесс найден, PID: $pid"
    # Убиваем процесс по PID
    kill -9 $pid
fi

# Останавливаем screen с именем "usr_bot"
screen -S usr_bot -X quit
