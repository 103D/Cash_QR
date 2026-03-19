# Папка Admin (Центральный сервер / Telegram-бот)

Эта часть системы устанавливается на облачном сервере (Ubuntu 22.04) и работает круглосуточно 24/7. В ней хранится база данных кодов, модераторов и запущено HTTP API для общения с агентами из филиалов.

## 🚀 Инструкция по запуску (или обновлению после изменения кода)

### 1. Подключение к серверу
Подключитесь к вашему Ubuntu-серверу по SSH, например через PowerShell:
```bash
ssh -i "C:\Users\user\Downloads\Telegram Desktop\ssh-key-2026-03-17.key" ubuntu@151.145.33.116
```

### 2. Передача файлов на сервер (Пуш обновлений)
На вашем **локальном** компьютере перейдите в консоль и скопируйте всю папку `admin` на сервер:
```bash
scp -o StrictHostKeyChecking=no -i "C:\Users\user\Desktop\ssh-key-2026-03-17.key" -r "C:\Users\user\Desktop\Diyar\Cash_QR\cash_desk_app\admin" ubuntu@151.145.33.116:/home/ubuntu/
```

### 3. Настройка переменных (`.env`)
На сервере (по ssh) перейдите в папку `admin` и убедитесь, что `.env` заполнен:
```bash
cd admin
cp .env.example .env
nano .env # Отредактируйте: внесите BOT_TOKEN и ADMIN_USER_ID, после чего нажмите Ctrl+O, Enter, Ctrl+X.
```

### 4. Запуск / Перезапуск бота
На сервере перейдите в папку `admin` и выполните:

**Первая установка бота:**
```bash
bash setup.sh
bash start.sh
```

**Перезагрузка бота (после обновлений в коде Python):**
```bash
tmux kill-session -t cashdesk_bot
sudo apt install doc2unix
doc2unix starts.sh
bash start.sh
```

### Возможные вопросы:
* **Могу ли я посмотреть, что бот делает сейчас?** Да: `tmux attach -t cashdesk_bot`. Выход из просмотра логов: `Ctrl + B`, отпустить и нажать `D`.
* **Я перезагрузил весь Ubuntu, что делать?** Бот сам не запустится. Войдите по SSH и напишите `cd admin && bash start.sh`.
