from dotenv import load_dotenv
import os

load_dotenv()  # .env faylni yuklaymiz

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))