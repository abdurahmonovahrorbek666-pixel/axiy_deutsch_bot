import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# ENVIRONMENT VARIABLES
# Render -> Environment Groups orqali beriladi
# ============================================================

def get_required_env(name: str) -> str:
    """Majburiy environment variable ni oladi."""
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Majburiy environment variable topilmadi: {name}"
        )

    return value


BOT_TOKEN = get_required_env("BOT_TOKEN")
GITHUB_JSON_URL = get_required_env("GITHUB_JSON_URL")

try:
    ADMIN_ID = int(get_required_env("ADMIN_ID"))
except ValueError as exc:
    raise RuntimeError("ADMIN_ID faqat raqam bo'lishi kerak.") from exc


# ============================================================
# LOCAL STORAGE
# ============================================================
# MUHIM:
# Render oddiy filesystem'ni restart/redeploy paytida saqlab qolmaydi.
# Agar Persistent Disk ulansa, USERS_FILE ni Render'da:
# /data/users.json
# qilib berish mumkin.
#
# Default holatda loyiha papkasidagi users.json ishlatiladi.
# ============================================================

USERS_FILE = os.getenv("USERS_FILE", "users.json").strip() or "users.json"


# ============================================================
# HTTP SETTINGS
# ============================================================

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))

# GitHub JSON ni har bir tugma bosilganda qayta yuklamaslik uchun cache.
TESTS_CACHE_TTL = int(os.getenv("TESTS_CACHE_TTL", "60"))

_tests_cache = {
    "data": None,
    "loaded_at": 0.0,
}


# ============================================================
# USERS JSON DATABASE
# ============================================================

def load_users() -> dict:
    """users.json faylini o'qiydi."""
    path = Path(USERS_FILE)

    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            logger.warning("users.json noto'g'ri formatda. Bo'sh baza ishlatiladi.")
            return {}

        return data

    except json.JSONDecodeError as exc:
        logger.error("users.json JSON formatida xato: %s", exc)
        return {}

    except OSError as exc:
        logger.error("users.json ni o'qishda xatolik: %s", exc)
        return {}


def save_users(users: dict) -> bool:
    """Users ma'lumotlarini xavfsizroq usulda saqlaydi."""
    path = Path(USERS_FILE)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                users,
                file,
                ensure_ascii=False,
                indent=4,
            )

        temp_path.replace(path)
        return True

    except OSError as exc:
        logger.error("Users ma'lumotlarini saqlashda xatolik: %s", exc)
        return False


def save_user_data(user) -> None:
    """Foydalanuvchini bazaga qo'shadi yoki yangilaydi."""
    if user is None:
        return

    users = load_users()
    user_id = str(user.id)

    if user_id not in users:
        users[user_id] = {
            "first_name": user.first_name or "",
            "username": user.username or "",
            "joined_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "tests_taken": 0,
        }
    else:
        users[user_id]["first_name"] = user.first_name or ""
        users[user_id]["username"] = user.username or ""

    save_users(users)


def increment_user_tests(user_id: int) -> None:
    """Foydalanuvchi boshlagan testlar sonini oshiradi."""
    users = load_users()
    user_id_str = str(user_id)

    if user_id_str not in users:
        return

    users[user_id_str]["tests_taken"] = (
        users[user_id_str].get("tests_taken", 0) + 1
    )

    save_users(users)


# ============================================================
# GITHUB TEST DATA
# ============================================================

def get_tests_data(force_refresh: bool = False) -> dict:
    """
    GitHub'dagi JSON fayldan testlarni oladi.

    Kutilayotgan format:
    {
        "tests": {
            "test1": [...],
            "test2": [...]
        }
    }
    """
    import time

    now = time.monotonic()

    if (
        not force_refresh
        and _tests_cache["data"] is not None
        and now - _tests_cache["loaded_at"] < TESTS_CACHE_TTL
    ):
        return _tests_cache["data"]

    try:
        response = requests.get(
            GITHUB_JSON_URL,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": "German-A1-Grammar-Bot/1.0",
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        payload = response.json()

        tests = payload.get("tests", {})

        if not isinstance(tests, dict):
            logger.error("GitHub JSON ichidagi 'tests' dict emas.")
            return {}

        _tests_cache["data"] = tests
        _tests_cache["loaded_at"] = now

        logger.info("GitHub'dan %s ta test yuklandi.", len(tests))

        return tests

    except requests.RequestException as exc:
        logger.error("GitHub JSON yuklashda HTTP xatolik: %s", exc)

    except ValueError as exc:
        logger.error("GitHub JSON noto'g'ri JSON formatida: %s", exc)

    except Exception:
        logger.exception("Testlarni yuklashda kutilmagan xatolik.")

    # GitHub vaqtincha ishlamasa, eski cache bo'lsa undan foydalanamiz.
    if _tests_cache["data"] is not None:
        return _tests_cache["data"]

    return {}


# ============================================================
# TELEGRAM HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "📚 Testlarni boshlash",
                callback_data="show_tests",
            )
        ]
    ]

    if is_admin(user_id):
        keyboard.append(
            [
                InlineKeyboardButton(
                    "⚙️ Admin Panel",
                    callback_data="admin_panel",
                )
            ]
        )

    return InlineKeyboardMarkup(keyboard)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 Statistika",
                    callback_data="admin_stats",
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 Foydalanuvchilar",
                    callback_data="admin_users",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Bosh menyu",
                    callback_data="main_menu",
                )
            ],
        ]
    )


def tests_keyboard(tests_data: dict) -> InlineKeyboardMarkup:
    keyboard = []
    row = []

    for index, test_key in enumerate(tests_data.keys(), start=1):
        # Telegram callback_data limiti 64 byte.
        # Juda uzun key bo'lsa ham xavfsiz ishlashi uchun index ishlatamiz.
        row.append(
            InlineKeyboardButton(
                f"Test {index}",
                callback_data=f"start:{index - 1}",
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                "⬅️ Bosh menyu",
                callback_data="main_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(keyboard)


async def send_question(
    query,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Joriy testdagi navbatdagi savolni yuboradi."""
    current_test = context.user_data.get("current_test", [])
    current_index = context.user_data.get("current_index", 0)

    if not current_test:
        await query.edit_message_text(
            "⚠️ Test ma'lumotlari topilmadi.",
        )
        return

    if current_index >= len(current_test):
        await query.edit_message_text(
            "⚠️ Test yakunlangan yoki savollar topilmadi.",
        )
        return

    question_data = current_test[current_index]

    question = question_data.get("question", "Savol topilmadi.")
    options = question_data.get("options", [])

    if not isinstance(options, list) or not options:
        await query.edit_message_text(
            "⚠️ Ushbu savol uchun javob variantlari topilmadi.",
        )
        return

    question_text = (
        f"<b>❓ {current_index + 1}-savol:</b>\n\n"
        f"{question}"
    )

    keyboard = []

    for index, option in enumerate(options):
        keyboard.append(
            [
                InlineKeyboardButton(
                    str(option),
                    callback_data=f"ans:{index}",
                )
            ]
        )

    await query.edit_message_text(
        question_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    """Adminga xabar yuboradi. Xatolik bot ishini to'xtatmaydi."""
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        logger.exception("Adminga xabar yuborishda xatolik.")


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    if user is None or update.message is None:
        return

    save_user_data(user)

    if not is_admin(user.id):
        username = (
            f"@{user.username}"
            if user.username
            else "Mavjud emas"
        )

        notify_text = (
            "🔔 <b>Yangi foydalanuvchi botga kirdi!</b>\n\n"
            f"👤 <b>Ism:</b> {user.first_name or 'Noma'lum'}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"🔗 <b>Username:</b> {username}\n"
            f"⏰ <b>Vaqt:</b> "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        await notify_admin(context, notify_text)

    await update.message.reply_text(
        (
            f"Hallo, {user.first_name or 'do‘st'}! 🇩🇪\n\n"
            "German A1 Grammatik botiga xush kelibsiz!\n"
            "Test yechish uchun quyidagi tugmani bosing:"
        ),
        reply_markup=main_menu_keyboard(user.id),
    )


# ============================================================
# /admin
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    if user is None or update.message is None:
        return

    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ Sizda admin huquqlari yo'q."
        )
        return

    await update.message.reply_text(
        "⚙️ <b>Admin boshqaruv paneli</b>",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def button_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    user = query.from_user
    data = query.data or ""

    # --------------------------------------------------------
    # Bosh menyu
    # --------------------------------------------------------

    if data == "main_menu":
        await query.edit_message_text(
            (
                f"Hallo, {user.first_name or 'do‘st'}! 🇩🇪\n\n"
                "German A1 Grammatik botiga xush kelibsiz!\n"
                "Kerakli bo'limni tanlang:"
            ),
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    # --------------------------------------------------------
    # Testlar ro'yxati
    # --------------------------------------------------------

    if data == "show_tests":
        tests_data = get_tests_data()

        if not tests_data:
            await query.edit_message_text(
                (
                    "⚠️ Testlarni yuklashda xatolik yuz berdi.\n\n"
                    "Iltimos, birozdan keyin qayta urinib ko'ring."
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Qayta urinish",
                                callback_data="show_tests",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⬅️ Bosh menyu",
                                callback_data="main_menu",
                            )
                        ],
                    ]
                ),
            )
            return

        await query.edit_message_text(
            "👇 <b>Kerakli testni tanlang:</b>",
            reply_markup=tests_keyboard(tests_data),
            parse_mode=ParseMode.HTML,
        )
        return

    # --------------------------------------------------------
    # Test boshlash
    # --------------------------------------------------------

    if data.startswith("start:"):
        tests_data = get_tests_data()

        if not tests_data:
            await query.edit_message_text(
                "⚠️ Testlar yuklanmadi. Keyinroq qayta urinib ko'ring."
            )
            return

        try:
            test_index = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.edit_message_text(
                "⚠️ Test tanlashda xatolik yuz berdi."
            )
            return

        test_keys = list(tests_data.keys())

        if test_index < 0 or test_index >= len(test_keys):
            await query.edit_message_text(
                "⚠️ Bunday test mavjud emas."
            )
            return

        test_key = test_keys[test_index]
        selected_test = tests_data[test_key]

        if not isinstance(selected_test, list) or not selected_test:
            await query.edit_message_text(
                "⚠️ Ushbu testda savollar mavjud emas."
            )
            return

        save_user_data(user)
        increment_user_tests(user.id)

        if not is_admin(user.id):
            await notify_admin(
                context,
                (
                    f"✍️ <b>{user.first_name or 'Noma'lum'}</b> "
                    f"(<code>{user.id}</code>) "
                    f"<b>{test_key}</b> testini boshladi."
                ),
            )

        # Eski test holatini tozalaymiz.
        context.user_data["current_test"] = selected_test
        context.user_data["current_index"] = 0
        context.user_data["score"] = 0
        context.user_data["test_key"] = test_key

        await send_question(query, context)
        return

    # --------------------------------------------------------
    # Javob
    # --------------------------------------------------------

    if data.startswith("ans:"):
        current_test = context.user_data.get("current_test", [])
        current_index = context.user_data.get("current_index", 0)

        if not current_test:
            await query.edit_message_text(
                "⚠️ Faol test topilmadi. Iltimos, testni qaytadan boshlang.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        if current_index >= len(current_test):
            await query.edit_message_text(
                "⚠️ Ushbu test allaqachon yakunlangan.",
                reply_markup=main_menu_keyboard(user.id),
            )
            return

        try:
            selected_option = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await query.edit_message_text(
                "⚠️ Javobni aniqlashda xatolik yuz berdi."
            )
            return

        question_data = current_test[current_index]
        options = question_data.get("options", [])

        try:
            correct_option = int(question_data.get("correct"))
        except (TypeError, ValueError):
            logger.error(
                "Savolda 'correct' qiymati noto'g'ri: %s",
                question_data,
            )
            correct_option = -1

        # Telegram callback bir necha marta bosilishi mumkin.
        # current_index o'zgartirilishi orqali ikkinchi javobni oldini olamiz.
        if selected_option == correct_option:
            context.user_data["score"] = (
                context.user_data.get("score", 0) + 1
            )

        context.user_data["current_index"] = current_index + 1

        next_index = context.user_data["current_index"]

        if next_index < len(current_test):
            await send_question(query, context)
            return

        # ----------------------------------------------------
        # Test tugadi
        # ----------------------------------------------------

        score = context.user_data.get("score", 0)
        total = len(current_test)
        test_key = context.user_data.get("test_key", "")

        percentage = round((score / total) * 100) if total else 0

        if percentage >= 90:
            result_comment = "🏆 A'lo natija!"
        elif percentage >= 70:
            result_comment = "👏 Yaxshi natija!"
        elif percentage >= 50:
            result_comment = "👍 Yomon emas, yana mashq qiling."
        else:
            result_comment = "📚 Grammatikani yana bir bor takrorlab chiqing."

        await query.edit_message_text(
            (
                "🎉 <b>Test yakunlandi!</b>\n\n"
                f"📊 <b>Natijangiz:</b> {score} / {total}\n"
                f"📈 <b>Foiz:</b> {percentage}%\n\n"
                f"{result_comment}"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📚 Boshqa test",
                            callback_data="show_tests",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 Bosh menyu",
                            callback_data="main_menu",
                        )
                    ],
                ]
            ),
            parse_mode=ParseMode.HTML,
        )

        if not is_admin(user.id):
            await notify_admin(
                context,
                (
                    f"🏁 <b>{user.first_name or 'Noma'lum'}</b> "
                    f"(<code>{user.id}</code>) "
                    f"<b>{test_key}</b> testini tugatdi.\n"
                    f"Natija: <b>{score}/{total}</b> ({percentage}%)"
                ),
            )

        return

    # --------------------------------------------------------
    # Admin panel
    # --------------------------------------------------------

    if data == "admin_panel":
        if not is_admin(user.id):
            await query.edit_message_text(
                "⛔ Sizda admin huquqlari yo'q."
            )
            return

        await query.edit_message_text(
            "⚙️ <b>Admin boshqaruv paneli</b>",
            reply_markup=admin_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    # --------------------------------------------------------
    # Admin statistika
    # --------------------------------------------------------

    if data == "admin_stats":
        if not is_admin(user.id):
            await query.edit_message_text(
                "⛔ Sizda admin huquqlari yo'q."
            )
            return

        users = load_users()

        total_users = len(users)
        total_tests_taken = sum(
            user_data.get("tests_taken", 0)
            for user_data in users.values()
        )

        text = (
            "📊 <b>Bot statistikasi</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
            f"📝 Jami boshlangan testlar: "
            f"<b>{total_tests_taken} marta</b>"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Orqaga",
                            callback_data="admin_panel",
                        )
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    # --------------------------------------------------------
    # Admin users
    # --------------------------------------------------------

    if data == "admin_users":
        if not is_admin(user.id):
            await query.edit_message_text(
                "⛔ Sizda admin huquqlari yo'q."
            )
            return

        users = load_users()

        if not users:
            text = "👥 Hozircha hech qanday foydalanuvchi yo'q."
        else:
            text = "👥 <b>Oxirgi foydalanuvchilar:</b>\n\n"

            # Oxirgi 15 ta yozuv.
            for user_id, user_info in list(users.items())[-15:]:
                first_name = user_info.get("first_name") or "Noma'lum"
                username = user_info.get("username")

                username_text = (
                    f"@{username}"
                    if username
                    else "Username yo'q"
                )

                tests_taken = user_info.get("tests_taken", 0)

                text += (
                    f"• <b>{first_name}</b> "
                    f"({username_text})\n"
                    f"  ID: <code>{user_id}</code> | "
                    f"Testlar: {tests_taken}\n\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Orqaga",
                            callback_data="admin_panel",
                        )
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )
        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logger.error(
        "Telegram update'da xatolik:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    logger.info("Bot ishga tushirilmoqda...")
    logger.info("ADMIN_ID: %s", ADMIN_ID)
    logger.info("GITHUB_JSON_URL: %s", GITHUB_JSON_URL)
    logger.info("USERS_FILE: %s", USERS_FILE)

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        CallbackQueryHandler(button_click)
    )

    application.add_error_handler(error_handler)

    logger.info("Bot polling rejimida ishga tushdi.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
