# =============================================================================
#  admin/config.py  —  Настройки бота
# =============================================================================


# Названия филиалов теперь хранятся в branches.json
import json
import os

BRANCHES_FILE = os.path.join(os.path.dirname(__file__), "branches.json")
def load_branches():
    if not os.path.exists(BRANCHES_FILE):
        return {}
    try:
        with open(BRANCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

BRANCHES = load_branches()

# HTTP-сервер (агенты опрашивают этот адрес)
API_HOST = "0.0.0.0"
API_PORT = 8000

# Файл базы данных для хранения кодов и модераторов
DATA_FILE = "data.json"
