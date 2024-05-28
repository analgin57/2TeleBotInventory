while true; do
    if ! ps aux | grep '/home/analgin/2TeleBotInventory/usr_bot.py' | grep -v grep > /dev/null; then
        cd /home/analgin/2TeleBotInventory/ && screen -L -Logfile /home/analgin/2TeleBotInventory/usr_bot.log -dmS usr_bot /home/analgin/2TeleBotInventory/usr_bot.py
    fi
    sleep 1
done
