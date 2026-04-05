import os
import sqlite3
import time
from io import BytesIO

import telebot
from telebot import apihelper
from telebot import types
from PIL import Image

from src.database import add_defect, init_db
from src.detection import RoadDetector
from src.engine import RoadAnalyzer


# Токен можно передать через переменную окружения TELEGRAM_BOT_TOKEN.
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ТВОЙ_ТОКЕН_БОТА")

if not TOKEN or TOKEN == "ТВОЙ_ТОКЕН_БОТА":
    raise RuntimeError(
        "Не задан токен Telegram-бота. Установите TELEGRAM_BOT_TOKEN или замените TOKEN в src/bot.py"
    )

bot = telebot.TeleBot(TOKEN)
analyzer = RoadAnalyzer()
detector = RoadDetector()

# Гарантируем, что таблица существует до старта polling.
init_db()


def _processed_db_path():
    return os.path.join("data", "roadsense.db")


def _ensure_processed_messages_table():
    conn = sqlite3.connect(_processed_db_path())
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_processed_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, message_id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _is_already_processed(chat_id: int, message_id: int) -> bool:
    conn = sqlite3.connect(_processed_db_path())
    try:
        row = conn.execute(
            "SELECT 1 FROM bot_processed_messages WHERE chat_id = ? AND message_id = ? LIMIT 1",
            (chat_id, message_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _mark_processed(chat_id: int, message_id: int):
    conn = sqlite3.connect(_processed_db_path())
    try:
        conn.execute(
            "INSERT OR IGNORE INTO bot_processed_messages (chat_id, message_id) VALUES (?, ?)",
            (chat_id, message_id),
        )
        conn.commit()
    finally:
        conn.close()


_ensure_processed_messages_table()


WELCOME_TEXT = (
    "Привет! Я бот RoadSense AI.\n\n"
    "Что умею:\n"
    "1) Принимать фото дефектов дорог\n"
    "2) Добавлять заявку в систему мониторинга\n"
    "3) Передавать точку на карту дашборда\n\n"
    "Отправьте фото дефекта, и я сначала проверю, есть ли на снимке яма."
)


def _main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Отправить фото дефекта"))
    keyboard.add(types.KeyboardButton("Помощь"))
    return keyboard


@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=_main_keyboard())


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_message(
        message.chat.id,
        "Инструкция:\n"
        "1) Нажмите скрепку и прикрепите фото\n"
        "2) Дождитесь подтверждения\n"
        "3) Проверьте новую точку в дашборде",
        reply_markup=_main_keyboard(),
    )


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if _is_already_processed(message.chat.id, message.message_id):
        return

    _mark_processed(message.chat.id, message.message_id)
    try:
        photo_info = message.photo[-1]
        file_info = bot.get_file(photo_info.file_id)
        photo_bytes = bot.download_file(file_info.file_path)
        image = Image.open(BytesIO(photo_bytes)).convert("RGB")

        detection_result = detector.detect_and_process(image)
        detected_data = detection_result.get("defect") if detection_result else None

        if not detected_data:
            bot.reply_to(
                message,
                "На изображении ям не обнаружено. Заявка не добавлена на карту. "
                "Попробуйте сделать фото ближе и при хорошем освещении.",
            )
            return

        # В MVP используем базовые контекстные параметры участка.
        traffic_level = 2
        is_near_social = True
        analysis = analyzer.calculate_priority(
            "pothole",
            float(detected_data.get("size_cm", 15.0)),
            traffic_level,
            is_near_social=is_near_social,
        )

        lat = 43.2389 + float(detected_data.get("lat_offset", 0.0))
        lon = 76.8897 + float(detected_data.get("lon_offset", 0.0))

        new_point = {
            "type": "pothole",
            "lat": lat,
            "lon": lon,
            "size_cm": float(detected_data.get("size_cm", 15.0)),
            "traffic_level": traffic_level,
            "is_near_social": is_near_social,
            **analysis,
        }
        new_id = add_defect(new_point)

        bot.reply_to(
            message,
            "Спасибо! Яма подтверждена и добавлена на карту RoadSense AI "
            f"(ID заявки: {new_id}).",
        )
    except Exception as e:
        print(f"[PHOTO PROCESSING ERROR] {e}")
        bot.reply_to(
            message,
            "Не удалось обработать фото. Попробуйте отправить другое изображение.",
        )


@bot.message_handler(content_types=["text"])
def handle_text(message):
    text = (message.text or "").strip().lower()
    if text.startswith("/"):
        return

    if text == "помощь":
        handle_help(message)
        return

    if text == "отправить фото дефекта":
        bot.reply_to(message, "Пришлите, пожалуйста, фото дефекта дороги в этом чате.")
        return

    bot.reply_to(
        message,
        "Я пока обрабатываю только фото дефектов. Отправьте фото, и я добавлю заявку.",
        reply_markup=_main_keyboard(),
    )


if __name__ == "__main__":
    print("Telegram-бот RoadSense AI запущен...")
    # Если у бота был настроен webhook, long polling не сможет работать стабильно.
    try:
        bot.remove_webhook(drop_pending_updates=True)
    except TypeError:
        # Совместимость со старыми версиями pyTelegramBotAPI.
        bot.remove_webhook()

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except apihelper.ApiTelegramException as e:
            err_text = str(e)
            print(f"[Telegram API ERROR] {err_text}")

            if "409" in err_text:
                print("Причина: конфликт getUpdates. Скорее всего запущен второй экземпляр бота.")
            elif "401" in err_text:
                print("Причина: неверный токен. Проверьте TELEGRAM_BOT_TOKEN.")
            elif "429" in err_text:
                print("Причина: лимит запросов. Повтор через несколько секунд.")

            time.sleep(3)
        except Exception as e:
            print(f"[BOT ERROR] {e}")
            time.sleep(3)
