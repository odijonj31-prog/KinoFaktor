import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bir nechta admin ID'ni vergul bilan ajratib yozish mumkin: "111,222,333"
_admin_ids_raw = os.getenv("SUPER_ADMIN_ID", "0")
SUPER_ADMIN_IDS = set(int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip())
SUPER_ADMIN_ID = next(iter(SUPER_ADMIN_IDS), 0)

DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylida topilmadi!")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL .env faylida topilmadi!")
