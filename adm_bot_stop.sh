#!/bin/bash

# Ищем процесс по имени "adm_bot_wd.sh"
pid=$(pgrep -f adm_bot_wd.sh)

if [ -z "$pid" ]; then
    echo "Процесс не найден"
else
    echo "Процесс найден, PID: $pid"
    # Убиваем процесс по PID
    kill -9 $pid
fi

# Останавливаем screen с именем "adm_bot"
screen -S adm_bot -X quit
