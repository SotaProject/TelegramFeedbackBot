from utils import get_env_var
import os

FEEDBACK_CHAT = int(get_env_var("FEEDBACK_CHAT"))
TOKEN = get_env_var("TOKEN")
DB_URL = get_env_var("DB_URL")
LOGGING_LEVEL = "info"

COMMANDS = {
    "start": {
        "set_command": False,
        "description": "",
        "text": os.environ.get("START_TEXT", "Привет! Это бот поддержки")
    }
}
