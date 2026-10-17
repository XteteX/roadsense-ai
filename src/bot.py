"""RoadSense AI Telegram bot: residents send a photo, confirmed potholes go on the map.

Run from the project root:

    export TELEGRAM_BOT_TOKEN="your-token"      # PowerShell: $env:TELEGRAM_BOT_TOKEN="your-token"
    python -m src.bot

Replies are in Russian by default and in English for users whose Telegram
interface language is English.
"""
import os
import sqlite3
import time
from contextlib import closing
from io import BytesIO

import telebot
from PIL import Image
from telebot import apihelper, types

from src.database import DB_PATH, add_defect, init_db
from src.detection import RoadDetector
from src.engine import RoadAnalyzer

ALMATY_CENTER = (43.2389, 76.8897)

# Context of the reported road section. Until map data is connected, the bot uses
# fixed defaults; the dashboard lets an operator adjust them (see README).
DEFAULT_TRAFFIC_LEVEL = 2
DEFAULT_NEAR_SOCIAL = True

TEXTS = {
    "ru": {
        "welcome": (
            "Привет! Я бот RoadSense AI.\n\n"
            "Что я умею:\n"
            "1) Принимать фото дефектов дороги\n"
            "2) Проверять снимок нейросетью YOLOv8\n"
            "3) Добавлять подтверждённую яму на карту города\n\n"
            "Отправьте фото дефекта, и я проверю, есть ли на снимке яма."
        ),
        "help": (
            "Инструкция:\n"
            "1) Нажмите на скрепку и прикрепите фото\n"
            "2) Дождитесь проверки\n"
            "3) Новая точка появится на дашборде"
        ),
        "btn_photo": "Отправить фото дефекта",
        "btn_help": "Помощь",
        "ask_photo": "Пришлите, пожалуйста, фото дефекта дороги в этот чат.",
        "only_photos": "Я пока обрабатываю только фото дефектов. Отправьте фото, и я добавлю заявку.",
        "no_pothole": ("На изображении ям не обнаружено, заявка не добавлена. "
                       "Попробуйте сфотографировать ближе и при хорошем освещении."),
        "added": "Спасибо! Яма подтверждена (уверенность {conf:.0%}) и добавлена на карту RoadSense AI. "
                 "ID заявки: {id}, приоритет: {score}/100.",
        "error": "Не удалось обработать фото. Попробуйте отправить другое изображение.",
    },
    "en": {
        "welcome": (
            "Hi! I'm the RoadSense AI bot.\n\n"
            "What I do:\n"
            "1) Accept photos of road defects\n"
            "2) Check each photo with a YOLOv8 neural network\n"
            "3) Put confirmed potholes on the city map\n\n"
            "Send a photo of a defect and I will check whether it shows a pothole."
        ),
        "help": (
            "How to use:\n"
            "1) Tap the paperclip and attach a photo\n"
            "2) Wait for the check\n"
            "3) The new point appears on the dashboard"
        ),
        "btn_photo": "Send a defect photo",
        "btn_help": "Help",
        "ask_photo": "Please send a photo of the road defect in this chat.",
        "only_photos": "For now I only process photos of road defects. Send a photo and I will file a report.",
        "no_pothole": "No pothole found in this photo, so no report was filed. Try a closer photo in good light.",
        "added": "Thank you! Pothole confirmed (confidence {conf:.0%}) and added to the RoadSense AI map. "
                 "Report ID: {id}, priority: {score}/100.",
        "error": "Could not process the photo. Please try another image.",
    },
}

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Set the TELEGRAM_BOT_TOKEN environment variable (see README).")

bot = telebot.TeleBot(TOKEN)
analyzer = RoadAnalyzer()
detector = RoadDetector()
init_db()


# --- de-duplication: Telegram may deliver the same update twice after a reconnect ---

def _ensure_processed_messages_table():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_processed_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, message_id)
            )
        """)


def _mark_processed(chat_id: int, message_id: int) -> bool:
    """Record the message; return False if it had already been processed."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO bot_processed_messages (chat_id, message_id) VALUES (?, ?)",
            (chat_id, message_id),
        )
        return cur.rowcount == 1


_ensure_processed_messages_table()


# --- handlers ---

def _lang(message) -> str:
    code = getattr(message.from_user, "language_code", None) or ""
    return "en" if code.startswith("en") else "ru"


def _keyboard(lang: str):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(TEXTS[lang]["btn_photo"]))
    keyboard.add(types.KeyboardButton(TEXTS[lang]["btn_help"]))
    return keyboard


@bot.message_handler(commands=["start"])
def handle_start(message):
    lang = _lang(message)
    bot.send_message(message.chat.id, TEXTS[lang]["welcome"], reply_markup=_keyboard(lang))


@bot.message_handler(commands=["help"])
def handle_help(message):
    lang = _lang(message)
    bot.send_message(message.chat.id, TEXTS[lang]["help"], reply_markup=_keyboard(lang))


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if not _mark_processed(message.chat.id, message.message_id):
        return
    t = TEXTS[_lang(message)]
    try:
        file_info = bot.get_file(message.photo[-1].file_id)  # largest available size
        image = Image.open(BytesIO(bot.download_file(file_info.file_path))).convert("RGB")

        detected = detector.detect_and_process(image)["defect"]
        if not detected:
            bot.reply_to(message, t["no_pothole"])
            return

        analysis = analyzer.calculate_priority(
            "pothole", detected["size_cm"], DEFAULT_TRAFFIC_LEVEL, is_near_social=DEFAULT_NEAR_SOCIAL
        )
        new_id = add_defect({
            "type": "pothole",
            "lat": ALMATY_CENTER[0] + detected["lat_offset"],
            "lon": ALMATY_CENTER[1] + detected["lon_offset"],
            "size_cm": detected["size_cm"],
            "traffic_level": DEFAULT_TRAFFIC_LEVEL,
            "is_near_social": DEFAULT_NEAR_SOCIAL,
            **analysis,
        })
        bot.reply_to(message, t["added"].format(conf=detected["confidence"], id=new_id, score=analysis["score"]))
    except Exception as e:
        print(f"[PHOTO PROCESSING ERROR] {e!r}")
        bot.reply_to(message, t["error"])


@bot.message_handler(content_types=["text"])
def handle_text(message):
    lang = _lang(message)
    text = (message.text or "").strip().lower()
    if text.startswith("/"):
        return
    if text in (TEXTS["ru"]["btn_help"].lower(), TEXTS["en"]["btn_help"].lower()):
        handle_help(message)
    elif text in (TEXTS["ru"]["btn_photo"].lower(), TEXTS["en"]["btn_photo"].lower()):
        bot.reply_to(message, TEXTS[lang]["ask_photo"])
    else:
        bot.reply_to(message, TEXTS[lang]["only_photos"], reply_markup=_keyboard(lang))


if __name__ == "__main__":
    print("RoadSense AI Telegram bot is running…")
    # Long polling does not work while a webhook is set.
    try:
        bot.remove_webhook(drop_pending_updates=True)
    except TypeError:  # older pyTelegramBotAPI versions
        bot.remove_webhook()

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except apihelper.ApiTelegramException as e:
            err_text = str(e)
            print(f"[Telegram API ERROR] {err_text}")
            if "409" in err_text:
                print("Cause: getUpdates conflict — another instance of the bot is probably running.")
            elif "401" in err_text:
                print("Cause: invalid token. Check TELEGRAM_BOT_TOKEN.")
            elif "429" in err_text:
                print("Cause: rate limit. Retrying in a few seconds.")
            time.sleep(3)
        except Exception as e:
            print(f"[BOT ERROR] {e!r}")
            time.sleep(3)
