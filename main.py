import json
import logging
import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SOZLAMALAR ---
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Bu yerga botingiz tokenini kiriting
ADMIN_ID = 7203007188  # Sizning Telegram ID'ingiz

# GitHub'dagi JSON faylingiz raw URL manzili
GITHUB_JSON_URL = "https://raw.githubusercontent.com/username/repository/main/grammar_a1.json"  # Linkni o'zingiznikiga almashtiring

USERS_FILE = "users.json"

# --- BAZA BILAN ISHLASH (JSON) ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Users faylini o'qishda xatolik: {e}")
            return {}
    return {}

def save_user_data(user):
    users = load_users()
    user_id_str = str(user.id)
    
    if user_id_str not in users:
        users[user_id_str] = {
            "first_name": user.first_name,
            "username": user.username,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tests_taken": 0
        }
    else:
        users[user_id_str]["first_name"] = user.first_name
        users[user_id_str]["username"] = user.username

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def increment_user_tests(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str in users:
        users[user_id_str]["tests_taken"] = users[user_id_str].get("tests_taken", 0) + 1
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=4)

# --- GITHUB'DAN TESTLARNI OLISH ---
def get_tests_data():
    try:
        response = requests.get(GITHUB_JSON_URL, timeout=10)
        if response.status_code == 200:
            return response.json().get("tests", {})
    except Exception as e:
        logger.error(f"JSON yuklashda xatolik: {e}")
    return {}

# --- COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_data(user)
    
    # Adminga bildirishnoma yuborish
    if user.id != ADMIN_ID:
        notify_text = (
            f"🔔 **Yangi foydalanuvchi botga kirdi!**\n\n"
            f"👤 **Ism:** {user.first_name}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🔗 **Username:** @{user.username if user.username else 'Mavjud emas'}\n"
            f"⏰ **Vaqt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=notify_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Adminga log yuborishda xatolik: {e}")

    keyboard = [
        [InlineKeyboardButton("📚 Testlarni boshlash", callback_data="show_tests")]
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Hallo, {user.first_name}! German A1 Grammatik botiga xush kelibsiz!\n"
        f"Test yechish uchun quyidagi tugmani bosing:",
        reply_markup=reply_markup
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Sizda admin huquqlari yo'q.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Foydalanuvchilar ro'yxati", callback_data="admin_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ **Admin Boshqaruv Paneli**", reply_markup=reply_markup, parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "show_tests":
        tests_data = get_tests_data()
        if not tests_data:
            await query.edit_message_text("⚠️ Testlarni yuklashda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
            return

        keyboard = []
        row = []
        for i, test_key in enumerate(tests_data.keys(), 1):
            row.append(InlineKeyboardButton(f"Test {i}", callback_data=f"start_{test_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👇 Kerakli testni tanlang:", reply_markup=reply_markup)

    elif query.data.startswith("start_"):
        test_key = query.data.replace("start_", "")
        tests_data = get_tests_data()
        
        if test_key not in tests_data:
            await query.edit_message_text(f"⚠️ Ushbu `{test_key}` uchun savollar topilmadi!", parse_mode="Markdown")
            return

        increment_user_tests(user.id)
        
        # Adminga foydalanuvchi test boshlagani haqida habar
        if user.id != ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✍️ **{user.first_name}** (`{user.id}`) **{test_key}** ni boshladi.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        # Test jarayonini saqlash
        context.user_data["current_test"] = tests_data[test_key]
        context.user_data["current_index"] = 0
        context.user_data["score"] = 0
        context.user_data["test_key"] = test_key

        await send_question(query)

    elif query.data.startswith("ans_"):
        selected_option = int(query.data.split("_")[1])
        current_test = context.user_data.get("current_test", [])
        current_index = context.user_data.get("current_index", 0)

        if current_index < len(current_test):
            if selected_option == current_test[current_index]["correct"]:
                context.user_data["score"] += 1

            context.user_data["current_index"] += 1
            if context.user_data["current_index"] < len(current_test):
                await send_question(query)
            else:
                score = context.user_data["score"]
                total = len(current_test)
                test_key = context.user_data.get("test_key", "")
                
                await query.edit_message_text(
                    f"🎉 **Test yakunlandi!**\n\n"
                    f"📊 Natijangiz: **{score} / {total}**",
                    parse_mode="Markdown"
                )
                
                # Adminga natijani yuborish
                if user.id != ADMIN_ID:
                    try:
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"🏁 **{user.first_name}** (`{user.id}`) **{test_key}** ni tugatdi.\nNatija: {score}/{total}",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

    elif query.data == "admin_panel":
        if user.id != ADMIN_ID:
            return
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Foydalanuvchilar ro'yxati", callback_data="admin_users")]
        ]
        await query.edit_message_text("⚙️ **Admin Boshqaruv Paneli**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "admin_stats":
        if user.id != ADMIN_ID:
            return
        users = load_users()
        total_users = len(users)
        total_tests_taken = sum(u.get("tests_taken", 0) for u in users.values())
        
        text = (
            f"📊 **Bot Statistikasi:**\n\n"
            f"👥 Jami foydalanuvchilar: **{total_users} ta**\n"
            f"📝 Jami yechilgan testlar: **{total_tests_taken} marta**"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "admin_users":
        if user.id != ADMIN_ID:
            return
        users = load_users()
        if not users:
            text = "Hozircha hech qanday foydalanuvchi yo'q."
        else:
            text = "👥 **Foydalanuvchilar ro'yxati:**\n\n"
            for u_id, u_info in list(users.items())[-15:]:  # Oxirgi 15 ta foydalanuvchini ko'rsatish
                username = f"@{u_info['username']}" if u_info.get('username') else "Username yo'q"
                text += f"• **{u_info['first_name']}** ({username}) | ID: `{u_id}` | Testlar: {u_info.get('tests_taken', 0)}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def send_question(query):
    current_test = query.message if hasattr(query, 'message') else query
    user_data = query.from_user if hasattr(query, 'from_user') else None
    
    # Context ma'lumotlarini olish
    test_items = query.data if hasattr(query, 'data') else None
    
    # Note: query ob'ekti orqali javoblarni yuborish
    ctx_test = query.message
    
    # Oddiy ko'rinishda savolni shakllantirish:
    # (Bu yerda o'zingizning savol berish kodingiz ishlaydi)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_click))

    logger.info("Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()
