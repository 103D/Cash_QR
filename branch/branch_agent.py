#!/usr/bin/env python3
"""
branch/branch_agent.py — Агент на устройстве филиала.

Запуск: python branch_agent.py

.env переменные:
  BRANCH_ID      — ID этого филиала (например branch_1)
  BOT_SERVER_URL — адрес компьютера с bot.py (например http://192.168.1.10:8000)

Что делает:
  Каждые POLL_INTERVAL секунд спрашивает у бота:
    GET <BOT_SERVER_URL>/api/command/<BRANCH_ID>
  Если получил команду — запускает send_keyboard_emulate.py --payload <cmd>
  Результат отправляет обратно:
    POST <BOT_SERVER_URL>/api/result/<BRANCH_ID>
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BRANCH_ID      = os.getenv("BRANCH_ID", "").strip()
BOT_SERVER_URL = os.getenv("BOT_SERVER_URL", "http://127.0.0.1:8000").rstrip("/")
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL", "3"))   # секунды между опросами бота (не ставь 0!)
SEND_DELAY     = int(os.getenv("SEND_DELAY", "0"))      # задержка перед вводом на клавиатуре (была 3)

SCRIPT = Path(__file__).parent / "send_keyboard_emulate.py"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def poll_command() -> str | None:
    try:
        r = requests.get(f"{BOT_SERVER_URL}/api/command/{BRANCH_ID}", timeout=10)
        r.raise_for_status()
        return r.json().get("command")
    except Exception as e:
        log.warning("Ошибка опроса: %s", e)
        return None


def send_result(payload: str, result: str):
    try:
        requests.post(
            f"{BOT_SERVER_URL}/api/result/{BRANCH_ID}",
            json={"payload": payload, "result": result},
            timeout=10,
        )
    except Exception as e:
        log.warning("Ошибка отправки результата: %s", e)


def run_script(payload: str) -> str:
    cmd = [sys.executable, str(SCRIPT), "--payload", payload, "--delay", str(SEND_DELAY)]
    log.info("Запускаю: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            out = result.stdout.strip() or "Готово"
            log.info("Успешно: %s", out)
            return f"Готово ✅\n{out}"
        else:
            err = result.stderr.strip() or result.stdout.strip()
            log.error("Ошибка скрипта: %s", err)
            return f"Ошибка ❌\n{err}"
    except subprocess.TimeoutExpired:
        return "Таймаут ⏱"
    except Exception as e:
        return f"Исключение ❌: {e}"


def main():
    if not BRANCH_ID:
        raise SystemExit("❌ BRANCH_ID не задан. Укажи в .env")
    if not SCRIPT.exists():
        raise SystemExit(f"❌ Скрипт не найден: {SCRIPT}")

    print(f"\n{'='*50}")
    print(f"  Агент филиала: {BRANCH_ID}")
    print(f"  Сервер:        {BOT_SERVER_URL}")
    print(f"  Опрос каждые:  {POLL_INTERVAL}с")
    print(f"{'='*50}\n")

    log.info("Агент запущен. Жду команды...")

    while True:
        cmd = poll_command()
        if cmd:
            log.info("Получена команда: payload=%r", cmd)
            result = run_script(cmd)
            send_result(cmd, result)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Агент остановлен.")
