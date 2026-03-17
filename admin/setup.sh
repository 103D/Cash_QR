#!/bin/bash
# setup.sh — Первоначальная настройка на Oracle Cloud Ubuntu сервере
# Запустить один раз: bash setup.sh

set -e

echo "=== Обновление системы ==="
sudo apt update && sudo apt upgrade -y

echo "=== Установка Python ==="
sudo apt install -y python3 python3-pip python3-venv git

echo "=== Создание виртуального окружения ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Установка зависимостей ==="
pip install -r requirements.txt

echo "=== Открытие порта 8000 в Ubuntu firewall ==="
sudo ufw allow 8000/tcp
sudo ufw allow 22/tcp
sudo ufw --force enable

echo ""
echo "✅ Готово! Теперь:"
echo "   1. Создай файл .env (скопируй из .env.example)"
echo "   2. Запусти: bash start.sh"
