#!/data/data/com.termux/files/usr/bin/bash

echo "Обновляем Termux и устанавливаем зависимости..."
pkg update -y && pkg upgrade -y
pkg install -y python git

echo "Клонируем репозиторий с ботом (замени ссылку на свою)"
if [ ! -d telegram-raffle-bot ]; then
    git clone https://github.com/Enot777ogg/telegram-raffle-bot.git
else
    echo "Папка telegram-raffle-bot уже существует, обновляем..."
    cd telegram-raffle-bot && git pull
    cd ..
fi

cd telegram-raffle-bot

echo "Устанавливаем Python зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Запускаем бота..."
python bot.py
