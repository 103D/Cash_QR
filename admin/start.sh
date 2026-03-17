#!/bin/bash
# start.sh — Запуск бота в фоне через tmux
# Использование: bash start.sh

SESSION="cashdesk_bot"

# Проверить что .env существует
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден! Скопируй из .env.example и заполни."
    exit 1
fi

# Если сессия уже есть — убить
tmux kill-session -t $SESSION 2>/dev/null || true

# Активировать venv и запустить бота в tmux
tmux new-session -d -s $SESSION "source venv/bin/activate && python bot.py"

echo "✅ Бот запущен в фоне (tmux сессия: $SESSION)"
echo ""
echo "Посмотреть логи:  tmux attach -t $SESSION"
echo "Остановить:       tmux kill-session -t $SESSION"
