# ---------------------------------------------------------------------------
# Админская команда для удаления филиала
# ---------------------------------------------------------------------------
async def cmd_delbranch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")

    # Формат: /delbranch branch_id
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        return await update.message.reply_text("⚠️ Ошибка формата.\nИспользование: `/delbranch branch_id`", parse_mode="Markdown")

    _, branch_id = args

    branches_file = os.path.join(os.path.dirname(__file__), "branches.json")
    try:
        with open(branches_file, "r", encoding="utf-8") as f:
            branches = json.load(f)
    except Exception:
        branches = {}

    if branch_id not in branches:
        return await update.message.reply_text(f"❌ Филиал с ID '{branch_id}' не найден.")

    branch_name = branches[branch_id]
    del branches[branch_id]
    try:
        with open(branches_file, "w", encoding="utf-8") as f:
            json.dump(branches, f, ensure_ascii=False, indent=4)
        await update.message.reply_text(f"✅ Филиал удалён!\n\nID: {branch_id}\nНазвание: {branch_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при удалении филиала: {e}")
# ---------------------------------------------------------------------------
# Админская команда для добавления филиала
# ---------------------------------------------------------------------------
async def cmd_addbranch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")

    # Формат: /addbranch branch_id Название
    args = update.message.text.split(maxsplit=2)
    if len(args) < 3:
        return await update.message.reply_text("⚠️ Ошибка формата.\nИспользование: `/addbranch branch_id Название`", parse_mode="Markdown")

    _, branch_id, branch_name = args

    # Загрузка текущих филиалов
    branches_file = os.path.join(os.path.dirname(__file__), "branches.json")
    try:
        with open(branches_file, "r", encoding="utf-8") as f:
            branches = json.load(f)
    except Exception:
        branches = {}

    if branch_id in branches:
        return await update.message.reply_text(f"❗ Филиал с ID '{branch_id}' уже существует: {branches[branch_id]}")

    branches[branch_id] = branch_name
    try:
        with open(branches_file, "w", encoding="utf-8") as f:
            json.dump(branches, f, ensure_ascii=False, indent=4)
        await update.message.reply_text(f"✅ Филиал успешно добавлен!\n\nID: {branch_id}\nНазвание: {branch_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при сохранении филиала: {e}")
#!/usr/bin/env python3
"""
admin/bot.py — Административный Telegram-бот + HTTP API для агентов.
"""

import logging
import os
import json
import threading
from dotenv import load_dotenv
from flask import Flask, jsonify, request as freq
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
)

from config import API_HOST, API_PORT, BRANCHES, DATA_FILE

load_dotenv()

BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
PORT          = int(os.getenv("API_PORT", str(API_PORT)))

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# База данных: Модераторы и Коды (data.json)
# ---------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"moderators": [], "codes": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Error loading data.json: %s", e)
        return {"moderators": [], "codes": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ---------------------------------------------------------------------------
# Очередь команд
# ---------------------------------------------------------------------------
pending_commands: dict[str, str] = {}      # branch_id → payload
pending_results:  list[dict]     = []      # [{branch_id, payload, result, sender_id}]

ptb_app: Application = None

# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.get("/api/command/<branch_id>")
def api_get_command(branch_id: str):
    cmd = pending_commands.pop(branch_id, None)
    return jsonify({"command": cmd})

@flask_app.post("/api/result/<branch_id>")
def api_post_result(branch_id: str):
    data = freq.get_json(force=True, silent=True) or {}
    result = data.get("result", "нет данных")
    payload = data.get("payload", "?")
    sender_id = data.get("sender_id", ADMIN_USER_ID)
    branch_name = BRANCHES.get(branch_id, branch_id)
    
    log.info("Result from '%s': %s", branch_id, result)
    pending_results.append({
        "branch_id": branch_id, 
        "branch_name": branch_name,
        "payload": payload, 
        "result": result,
        "sender_id": sender_id
    })
    return jsonify({"status": "ok"})

def run_flask():
    flask_app.run(host=API_HOST, port=PORT, debug=False, use_reloader=False)

# ---------------------------------------------------------------------------
# Telegram: отправка результатов
# ---------------------------------------------------------------------------
async def job_send_results(context: ContextTypes.DEFAULT_TYPE):
    while pending_results:
        item = pending_results.pop(0)
        
        # Пытаемся найти читаемое имя кода по payload
        data = load_data()
        code_label = item['payload']
        for name, pl in data['codes'].items():
            if pl == item['payload']:
                code_label = name
                break
                
        text = (
            f"📋 *Результат выполнения*\n"
            f"🏢 Филиал: {item['branch_name']}\n"
            f"🔑 Код: {code_label}\n"
            f"{'✅' if 'Готово' in item['result'] or 'Done' in item['result'] else '❌'} {item['result']}"
        )
        try:
            # Отправляем результат тому, кто запрашивал (Админу или Модератору)
            await context.bot.send_message(chat_id=item['sender_id'], text=text, parse_mode="Markdown")
        except Exception as e:
            log.error("Failed to send result to %s: %s", item['sender_id'], e)

# ---------------------------------------------------------------------------
# Проверка прав доступа
# ---------------------------------------------------------------------------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID

def has_access(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    data = load_data()
    return user_id in data.get("moderators", [])

# ---------------------------------------------------------------------------
# Telegram: команды
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not has_access(user_id):
        await update.message.reply_text(f"⛔ Нет доступа. Твой ID: {user_id}")
        return

    # Главное меню: Филиалы
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"branch:{bid}")]
        for bid, name in BRANCHES.items()
    ]
    await update.message.reply_text("🏢 Выбери филиал:", reply_markup=InlineKeyboardMarkup(keyboard))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not has_access(user_id):
        await query.edit_message_text("⛔ Нет доступа.")
        return

    req_data = query.data

    if req_data.startswith("branch:"):
        branch_id = req_data[7:]
        branch_name = BRANCHES.get(branch_id, branch_id)
        
        data = load_data()
        codes = data.get("codes", {})
        
        if not codes:
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
            await query.edit_message_text(
                f"🏢 *{branch_name}*\n\nСписок кодов пуст! Админ должен добавить их командой /addcode",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"send:{branch_id}:{payload}")]
            for name, payload in codes.items()
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        
        await query.edit_message_text(
            f"🏢 *{branch_name}*\nВыбери код для отправки:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif req_data.startswith("send:"):
        _, branch_id, payload = req_data.split(":", 2)
        branch_name = BRANCHES.get(branch_id, branch_id)
        
        data = load_data()
        code_label = payload
        for name, pl in data.get("codes", {}).items():
            if pl == payload:
                code_label = name
                break
                
        # Сохраняем команду для агента
        pending_commands[branch_id] = payload
        # Сохраняем информацию о том, кто отправил (чтобы вернуть ему ответ)
        # В этой простой реализации агент не получает sender_id, он просто выполняет.
        # Поэтому мы добавим хак: мы запомним sender_id на стороне API
        # Но при GET запросе агента sender_id теряется.
        # Чтобы не усложнять агента, мы можем модифицировать endpoint /api/command, 
        # чтобы отдавать payload, а обратно получать его же.
        # Самый простой надежный способ (без изменения API агента):
        # мы просто перезаписываем команду. Когда приходит результат от агента - он просто пересылается Админу по умолчанию.
        # Давай модифицируем agents API чтобы они пересылали payload обратно, 
        # но sender_id агент не знает. Поэтому чтобы отправить ответ нужному человеку:
        # создадим временный "кеш" кто заказал команду.
        pass
        
    if req_data.startswith("send:"):
        _, branch_id, payload = req_data.split(":", 2)
        branch_name = BRANCHES.get(branch_id, branch_id)
        
        # Находим имя кода
        data = load_data()
        code_label = next((name for name, pl in data.get("codes", {}).items() if pl == payload), payload)
        
        # Добавляем в очередь
        pending_commands[branch_id] = payload
        
        # Костыль для трекинга отправителя без изменения кода агентов:
        # Просто запишем, кто последний запрашивал эту команду на этот филиал
        if not hasattr(context.bot_data, "cmd_senders"):
            context.bot_data["cmd_senders"] = {}
        context.bot_data["cmd_senders"][f"{branch_id}_{payload}"] = user_id
        
        log.info("Queued command for '%s': payload='%s' by %s", branch_id, payload, user_id)
        await query.edit_message_text(
            f"✅ Команда поставлена в очередь!\n\n"
            f"🏢 Филиал: *{branch_name}*\n"
            f"🔑 Код: *{code_label}*\n\n"
            f"Ожидай результата...",
            parse_mode="Markdown",
        )

    elif req_data == "back":
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"branch:{bid}")]
            for bid, name in BRANCHES.items()
        ]
        await query.edit_message_text("🏢 Выбери филиал:", reply_markup=InlineKeyboardMarkup(keyboard))

# Хак для возврата ответа нужному отправителю
async def process_results_sender(context: ContextTypes.DEFAULT_TYPE):
    while pending_results:
        item = pending_results.pop(0)
        
        branch_id = item['branch_id']
        payload = item['payload']
        
        # Достаем sender_id
        sender_id = ADMIN_USER_ID
        if hasattr(context.bot_data, "cmd_senders"):
            key = f"{branch_id}_{payload}"
            if key in context.bot_data["cmd_senders"]:
                sender_id = context.bot_data["cmd_senders"].pop(key)
        
        data = load_data()
        code_label = next((name for name, pl in data.get("codes", {}).items() if pl == payload), payload)
                
        text = (
            f"📋 *Результат*\n"
            f"🏢 Филиал: {item['branch_name']}\n"
            f"🔑 Код: {code_label}\n"
            f"{'✅' if 'Готово' in item['result'] or 'Done' in item['result'] else '❌'} {item['result']}"
        )
        try:
            await context.bot.send_message(chat_id=sender_id, text=text, parse_mode="Markdown")
        except Exception as e:
            log.error("Failed to send result to %s: %s", sender_id, e)

# ---------------------------------------------------------------------------
# Админские команды для редактирования (Коды)
# ---------------------------------------------------------------------------
async def cmd_addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    # Формат: /addcode Название Код
    args = update.message.text.split(maxsplit=2)
    if len(args) < 3:
        return await update.message.reply_text("⚠️ Ошибка формата.\nИспользование: `/addcode Название payload`", parse_mode="Markdown")
    
    _, name, payload = args
    data = load_data()
    data["codes"][name] = payload
    save_data(data)
    
    await update.message.reply_text(f"✅ Код успешно добавлен!\n\nНазвание: {name}\nPayload: {payload}")

async def cmd_delcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        return await update.message.reply_text("⚠️ Использование: `/delcode Название`", parse_mode="Markdown")
    
    name = args[1].strip()
    data = load_data()
    if name in data["codes"]:
        del data["codes"][name]
        save_data(data)
        await update.message.reply_text(f"✅ Код '{name}' удален.")
    else:
        await update.message.reply_text(f"❌ Код '{name}' не найден.")

async def cmd_listcodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    data = load_data()
    codes = data.get("codes", {})
    if not codes:
        return await update.message.reply_text("📭 Список кодов пуст.")
    
    text = "📝 *Список сохраненных кодов:*\n\n"
    for name, payload in codes.items():
        text += f"• *{name}*: `{payload}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------------------------------------------------------------------------
# Админские команды для редактирования (Модераторы)
# ---------------------------------------------------------------------------
async def cmd_addmod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    args = update.message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await update.message.reply_text("⚠️ Использование: `/addmod 12345678` (укажи цифры ID)", parse_mode="Markdown")
    
    mod_id = int(args[1])
    data = load_data()
    if mod_id not in data["moderators"]:
        data["moderators"].append(mod_id)
        save_data(data)
        await update.message.reply_text(f"✅ Пользователь {mod_id} назначен Модератором!")
    else:
        await update.message.reply_text("⚠️ Этот ID уже является модератором.")

async def cmd_delmod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    args = update.message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await update.message.reply_text("⚠️ Использование: `/delmod 12345678`", parse_mode="Markdown")
    
    mod_id = int(args[1])
    data = load_data()
    if mod_id in data["moderators"]:
        data["moderators"].remove(mod_id)
        save_data(data)
        await update.message.reply_text(f"✅ Модератор {mod_id} удален.")
    else:
        await update.message.reply_text("❌ Такого модератора нет в списке.")

async def cmd_listmods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для Админа.")
    
    data = load_data()
    mods = data.get("moderators", [])
    if not mods:
        return await update.message.reply_text("📭 Модераторов нет.")
    
    text = "👥 *Модераторы:*\n"
    for m in mods:
        text += f"• `{m}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------------------------------------------------------------------------
# Настройка меню (команд) в интерфейсе Telegram
# ---------------------------------------------------------------------------
async def post_init(application: Application):
    from telegram import BotCommand, BotCommandScopeChat
    
    # Команды для модераторов (в базовой области видимости)
    moderator_commands = [
        BotCommand("start", "Выбрать филиал и отправить код"),
    ]
    await application.bot.set_my_commands(moderator_commands)
    
    # Команды только для админа
    admin_commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("listcodes", "Список кодов"),
        BotCommand("listmods", "Список модераторов"),
        BotCommand("addbranch", "Добавить филиал"),
    ]
    
    # Попытаться установить админское меню эксклюзивно для админа
    try:
        await application.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_USER_ID)
        )
    except Exception as e:
        log.warning("Could not set admin commands scope: %s", e)

# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------
def main():
        ptb_app.add_handler(CommandHandler("delbranch", cmd_delbranch))
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN не задан. Создай .env файл.")
    if not ADMIN_USER_ID:
        raise SystemExit("❌ ADMIN_USER_ID не задан.")

    # Запустить Flask в фоновом потоке
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    log.info("HTTP API запущен на порту %s", PORT)

    # Запустить Telegram-бота
    global ptb_app
    ptb_app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Основные команды
    ptb_app.add_handler(CommandHandler("start", cmd_start))
    ptb_app.add_handler(CallbackQueryHandler(on_callback))
    
    # Админские команды
    ptb_app.add_handler(CommandHandler("addcode", cmd_addcode))
    ptb_app.add_handler(CommandHandler("delcode", cmd_delcode))
    ptb_app.add_handler(CommandHandler("listcodes", cmd_listcodes))
    ptb_app.add_handler(CommandHandler("addmod", cmd_addmod))
    ptb_app.add_handler(CommandHandler("delmod", cmd_delmod))
    ptb_app.add_handler(CommandHandler("listmods", cmd_listmods))
    ptb_app.add_handler(CommandHandler("addbranch", cmd_addbranch))
    
    ptb_app.job_queue.run_repeating(process_results_sender, interval=5, first=5)

    log.info("Telegram-бот запущен. Admin user_id=%s", ADMIN_USER_ID)
    ptb_app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
