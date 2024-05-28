while true; do
    if ! ps aux | grep '/home/analgin/2TeleBotInventory/adm_bot.py' | grep -v grep > /dev/null; then
        cd /home/analgin/2TeleBotInventory/ && screen -L -Logfile /home/analgin/2TeleBotInventory/adm_bot.log -dmS adm_bot /home/analgin/2TeleBotInventory/adm_bot.py
    fi
    sleep 1
done
