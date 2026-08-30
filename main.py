import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    CallbackQuery, 
    PollAnswer
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Render Environment'dan Token va Admin ID ni olish
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8912605806:AAGL2tn2d_g7yXFewWrxjkLFMvU80uHEz6k")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Fayl nomlari
WORDS_FILE = "words.json"
USERS_DB_FILE = "users_db.json"
GRAMMAR_A1_FILE = "grammar_a1.json"

# Aktiv testlar xotirasi
active_polls = {}

# --- BAZA BILAN ISHLASH ---

def load_users_db() -> dict:
    """Foydalanuvchilar progressini fayldan o'qish"""
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            logging.error(f"{USERS_DB_FILE} ni o'qishda xatolik: {e}")
            return {}
    return {}

def save_users_db(users_data: dict):
    """Foydalanuvchilar progressini faylga saqlash"""
    try:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"{USERS_DB_FILE} ga saqlashda xatolik: {e}")

users_db = load_users_db()

def load_words():
    try:
        if os.path.exists(WORDS_FILE):
            with open(WORDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"{WORDS_FILE} faylini o'qishda xatolik: {e}")
        return {}

words_data = load_words()

def load_grammar_a1():
    try:
        if os.path.exists(GRAMMAR_A1_FILE):
            with open(GRAMMAR_A1_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"{GRAMMAR_A1_FILE} faylini o'qishda xatolik: {e}")
        return {}

grammar_a1_data = load_grammar_a1()

def get_user_data(user_id: int, username: str) -> dict:
    if user_id not in users_db:
        users_db[user_id] = {
            "username": username or "Foydalanuvchi",
            "a1": 1, "a2": 1, "b1": 1, "b2": 1,
            "grammar_a1": 1,
            "scores": {}
        }
        save_users_db(users_db)
    else:
        if username and users_db[user_id].get("username") != username:
            users_db[user_id]["username"] = username
            save_users_db(users_db)
            
    return users_db[user_id]

async def handle_ping(request):
    return web.Response(text="Bot is running smoothly!")

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Kunlik Lug'at"), KeyboardButton(text="📝 Grammatik testlar")],
            [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="📖 Nemis tili Kitoblari (PDF)")],
            [KeyboardButton(text="ℹ️ Bot haqida")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    get_user_data(user_id, username)
    
    welcome_text = (
        f"Hallo, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"<b>Deutsch mit Ahrorbek</b> botiga xush kelibsiz!\n"
        f"Bu bot orqali nemis tili so'z boyligingizni oshirishingiz va grammatik testlar orqali bilimlaringizni test qilishingiz mumkin."
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_keyboard())

@dp.message(F.text == "📊 Natijalarim")
async def my_stats(message: types.Message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    text = (
        f"📊 <b>Sizning umumiy o'zlashtirish ko'rsatkichingiz:</b>\n\n"
        f"🟢 <b>A1 Lug'at:</b> {user.get('a1', 1)}-kun\n"
        f"📝 <b>A1 Grammatika:</b> {user.get('grammar_a1', 1)}-test ko'rib chiqilmoqda\n\n"
        f"💡 <i>Eslatma: Keyingi bosqichga o'tish uchun testda kamida 80% to'plashingiz kerak.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: types.Message):
    await message.answer(
        "🇩🇪 <b>Deutsch mit Ahrorbek</b> — Nemis tilini oson va samarali o'rganish loyihasi.",
        parse_mode="HTML"
    )

@dp.message(F.text == "📖 Nemis tili Kitoblari (PDF)")
async def pdf_books(message: types.Message):
    await message.answer("📚 Tez orada ushbu bo'limga saralangan nemis tili kitoblari joylanadi!")

@dp.message(F.text == "📚 Kunlik Lug'at")
async def show_vocab_levels(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja (Anfänger)", callback_data="showdays_a1_1")],
            [InlineKeyboardButton(text="🟡 A2 Daraja (Grundlegend)", callback_data="showdays_a2_1")],
            [InlineKeyboardButton(text="🟠 B1 Daraja (Fortgeschritten)", callback_data="showdays_b1_1")],
            [InlineKeyboardButton(text="🔴 B2 Daraja (Selbstständig)", callback_data="showdays_b2_1")]
        ]
    )
    await message.answer("📚 <b>Kunlik Lug'at</b> bo'limi. O'zingizga mos til darajasini tanlang:", parse_mode="HTML", reply_markup=kb)

# GRAMMATIK TESTLAR BO'LIMI
@dp.message(F.text == "📝 Grammatik testlar")
async def show_grammar_levels(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Grammatika Testlari (20 ta Test)", callback_data="showgrammartests_a1_1")],
            [InlineKeyboardButton(text="🟡 A2 Grammatika Testlari", callback_data="grammartest_a2")],
            [InlineKeyboardButton(text="🟠 B1 Grammatika Testlari", callback_data="grammartest_b1")],
            [InlineKeyboardButton(text="🔴 B2 Grammatika Testlari", callback_data="grammartest_b2")]
        ]
    )
    await message.answer("📝 <b>Grammatik testlar</b> bo'limi. Bilimingizni sinash uchun darajani tanlang:", parse_mode="HTML", reply_markup=kb)

# A1 Grammatika testlari ro'yxati (1-20 test)
@dp.callback_query(F.data.startswith("showgrammartests_a1_"))
async def show_grammar_a1_tests(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[2])
    user = get_user_data(callback.from_user.id, callback.from_user.username)
    unlocked_test = user.get("grammar_a1", 1)

    total_tests = 20
    per_page = 10
    start_t = (page - 1) * per_page + 1
    end_t = min(start_t + per_page - 1, total_tests)

    buttons = []
    row = []
    for t_num in range(start_t, end_t + 1):
        test_key = f"test_{t_num}"
        if t_num <= unlocked_test:
            icon = "✅" if t_num < unlocked_test else "📝"
            btn_text = f"{icon} {t_num}-test"
            cb_data = f"startgtest_a1_{test_key}_0_0"
        else:
            btn_text = f"🔒 {t_num}-test"
            cb_data = f"glocked_{t_num}"
            
        row.append(InlineKeyboardButton(text=btn_text, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Avvalgisi", callback_data=f"showgrammartests_a1_{page - 1}"))
    if end_t < total_tests:
        nav_buttons.append(InlineKeyboardButton(text="Keyingisi ➡️", callback_data=f"showgrammartests_a1_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_glevels")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        f"🟢 <b>A1 Grammatika Testlari</b> (Har bir test 25 ta savol)\nSahifa {page}:\n\nTopshirmoqchi bo'lgan testingizni tanlang:",
        parse_mode="HTML",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("glocked_"))
async def glocked_handler(callback: CallbackQuery):
    t_num = callback.data.split("_")[1]
    await callback.answer(f"⛔️ {t_num}-test yopiq! Keyingi testni ochish uchun oldingisini kamida 80% ga topshiring.", show_alert=True)

@dp.callback_query(F.data == "back_to_glevels")
async def back_to_glevels(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Grammatika Testlari (20 ta Test)", callback_data="showgrammartests_a1_1")],
            [InlineKeyboardButton(text="🟡 A2 Grammatika Testlari", callback_data="grammartest_a2")],
            [InlineKeyboardButton(text="🟠 B1 Grammatika Testlari", callback_data="grammartest_b1")],
            [InlineKeyboardButton(text="🔴 B2 Grammatika Testlari", callback_data="grammartest_b2")]
        ]
    )
    await callback.message.edit_text("📝 <b>Grammatik testlar</b> bo'limi. Darajani tanlang:", parse_mode="HTML", reply_markup=kb)

# Grammatika testlarini yuborish mantiqi
async def send_next_gquestion(user_id: int, level: str, test_key: str, q_idx: int, correct_count: int):
    global grammar_a1_data
    if not grammar_a1_data:
        grammar_a1_data = load_grammar_a1()

    questions = grammar_a1_data.get("tests", {}).get(test_key, [])

    if not questions:
        await bot.send_message(user_id, f"⚠️ Ushbu {test_key} uchun savollar json faylda topilmadi!")
        return

    if q_idx >= len(questions):
        total = len(questions)
        percentage = int((correct_count / total) * 100) if total > 0 else 0
        user = get_user_data(user_id, "")
        current_t_num = int(test_key.split("_")[1])

        result_text = f"🏁 <b>A1 Grammatika - {current_t_num}-test yakunlandi!</b>\n\nNatijangiz: <b>{correct_count}/{total}</b> ({percentage}%)\n\n"

        if percentage >= 80:
            if user.get("grammar_a1", 1) == current_t_num:
                user["grammar_a1"] = current_t_num + 1
                save_users_db(users_db)
            result_text += f"🎉 <b>Ajoyib! 80% dan yuqori ball to'pladingiz. {current_t_num + 1}-test ochildi!</b>"
        else:
            result_text += f"⚠️ <i>Keyingi testni ochish uchun kamida 80% to'plashingiz kerak. Qayta urinib ko'ring!</i>"

        next_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Qayta topshirish", callback_data=f"startgtest_a1_{test_key}_0_0")],
                [InlineKeyboardButton(text="📝 Grammatika testlariga qaytish", callback_data="showgrammartests_a1_1")]
            ]
        )
        await bot.send_message(chat_id=user_id, text=result_text, parse_mode="HTML", reply_markup=next_kb)
        return

    item = questions[q_idx]
    poll_msg = await bot.send_poll(
        chat_id=user_id,
        question=f"[{q_idx + 1}/{len(questions)}] {item['question']}",
        options=item["options"],
        correct_option_id=item["correct"],
        type="quiz",
        is_anonymous=False
    )

    active_polls[poll_msg.poll.id] = {
        "user_id": user_id,
        "is_grammar": True,
        "level": level,
        "test_key": test_key,
        "q_idx": q_idx,
        "correct_count": correct_count,
        "correct_option": item["correct"]
    }

@dp.callback_query(F.data.startswith("startgtest_"))
async def start_gtest(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    level = parts[1]
    test_key = f"{parts[2]}_{parts[3]}"
    q_idx = int(parts[4])
    correct_count = int(parts[5])

    await send_next_gquestion(callback.from_user.id, level, test_key, q_idx, correct_count)

# LUG'AT BO'LIMI FUNKSIYALARI (ESKI DASTUR)
@dp.callback_query(F.data.startswith("showdays_"))
async def show_days(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    level = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1
    
    user_id = callback.from_user.id
    user = get_user_data(user_id, callback.from_user.username)
    unlocked_day = user.get(level, 1)
    level_days = words_data.get(level, {}).get("days", {})

    json_max_day = 0
    for day_k in level_days.keys():
        if day_k.startswith("day_"):
            try:
                num = int(day_k.split("_")[1])
                if num > json_max_day: json_max_day = num
            except ValueError: pass
    total_days = max(json_max_day, 30)

    per_page = 10
    start_day = (page - 1) * per_page + 1
    end_day = min(start_day + per_page - 1, total_days)

    buttons, row = [], []
    for day_num in range(start_day, end_day + 1):
        day_key = f"day_{day_num}"
        if day_num <= unlocked_day:
            icon = "✅" if day_num < unlocked_day else "📅"
            btn_text = f"{icon} {day_num}-kun"
            cb_data = f"viewday_{level}_{day_key}"
        else:
            btn_text = f"🔒 {day_num}-kun"
            cb_data = f"locked_{day_num}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)

    nav_buttons = []
    if page > 1: nav_buttons.append(InlineKeyboardButton(text="⬅️ Avvalgisi", callback_data=f"showdays_{level}_{page - 1}"))
    if end_day < total_days: nav_buttons.append(InlineKeyboardButton(text="Keyingisi ➡️", callback_data=f"showdays_{level}_{page + 1}"))
    if nav_buttons: buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_levels")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    title = words_data.get(level, {}).get("title", level.upper())
    await callback.message.edit_text(f"<b>{title} Lug'atlari</b> (Sahifa {page})\n\nOchiq kunni tanlang:", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("locked_"))
async def locked_day_handler(callback: CallbackQuery):
    await callback.answer(f"⛔️ Bu kun yopiq! Oldingi kun testini kamida 80% ga topshiring.", show_alert=True)

@dp.callback_query(F.data == "back_to_levels")
async def back_to_levels(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja (Anfänger)", callback_data="showdays_a1_1")],
            [InlineKeyboardButton(text="🟡 A2 Daraja (Grundlegend)", callback_data="showdays_a2_1")],
            [InlineKeyboardButton(text="🟠 B1 Daraja (Fortgeschritten)", callback_data="showdays_b1_1")],
            [InlineKeyboardButton(text="🔴 B2 Daraja (Selbstständig)", callback_data="showdays_b2_1")]
        ]
    )
    await callback.message.edit_text("🎯 Til darajasini tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("viewday_"))
async def view_day_words(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    level, day_key, day_num = parts[1], f"{parts[2]}_{parts[3]}", parts[3]
    questions = words_data.get(level, {}).get("days", {}).get(day_key, [])

    if not questions:
        await callback.message.answer(f"⚠️ {day_num}-kun uchun lug'at hali tayyorlanmagan.")
        return

    vocab_text = f"✨ <b>{level.upper()} DARAJA — {day_num}-KUN LUG'ATI</b> ✨\n───────────────\n"
    for idx, item in enumerate(questions, 1):
        word, meaning = item['word'], item['meaning']
        styled = f"🔹 <b>{word}</b>" if word.startswith("der ") else f"🔸 <b>{word}</b>" if word.startswith("die ") else f"🟢 <b>{word}</b>" if word.startswith("das ") else f"▫️ <b>{word}</b>"
        vocab_text += f"{idx:02d}. {styled} ➔ <i>{meaning}</i>\n"

    vocab_text += f"\n───────────────\n💡 <i>Bilimingizni sinash uchun pastdagi tugmani bosing!</i>"
    start_quiz_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🚀 {day_num}-kun lug'at testini boshlash", callback_data=f"startquiz_{level}_{day_key}_0_0")],
            [InlineKeyboardButton(text="⬅️ Kunlar ro'yxatiga qaytish", callback_data=f"showdays_{level}_1")]
        ]
    )
    await callback.message.edit_text(vocab_text, parse_mode="HTML", reply_markup=start_quiz_kb)

async def send_next_question(user_id: int, level: str, day_key: str, q_idx: int, correct_count: int):
    questions = words_data.get(level, {}).get("days", {}).get(day_key, [])
    if q_idx >= len(questions):
        total = len(questions)
        percentage = int((correct_count / total) * 100) if total > 0 else 0
        user = get_user_data(user_id, "")
        current_day_num = int(day_key.split("_")[1])

        result_text = f"🏁 <b>Test yakunlandi!</b>\n\nNatijangiz: <b>{correct_count}/{total}</b> ({percentage}%)\n\n"
        if percentage >= 80:
            if user.get(level, 1) == current_day_num:
                user[level] = current_day_num + 1
                save_users_db(users_db)
            result_text += f"🎉 <b>Tabriklaymiz! {current_day_num + 1}-kun ochildi!</b>"
        else:
            result_text += f"⚠️ <i>Keyingi kunni ochish uchun kamida 80% to'plashingiz kerak.</i>"

        next_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Qayta topshirish", callback_data=f"viewday_{level}_{day_key}")],
                [InlineKeyboardButton(text="📚 Kunlar ro'yxatiga o'tish", callback_data=f"showdays_{level}_1")]
            ]
        )
        await bot.send_message(chat_id=user_id, text=result_text, parse_mode="HTML", reply_markup=next_kb)
        return

    item = questions[q_idx]
    poll_msg = await bot.send_poll(
        chat_id=user_id,
        question=f"[{q_idx + 1}/{len(questions)}] '{item['word']}' so'zining ma'nosi nima?",
        options=item["options"],
        correct_option_id=item["correct"],
        type="quiz",
        is_anonymous=False
    )
    active_polls[poll_msg.poll.id] = {
        "user_id": user_id, "is_grammar": False, "level": level,
        "day_key": day_key, "q_idx": q_idx, "correct_count": correct_count, "correct_option": item["correct"]
    }

@dp.callback_query(F.data.startswith("startquiz_"))
async def start_quiz(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    await send_next_question(callback.from_user.id, parts[1], f"{parts[2]}_{parts[3]}", int(parts[4]), int(parts[5]))

# Barcha test javoblarini umumiy handle qilish
@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    poll_id = poll_answer.poll_id
    if poll_id in active_polls:
        data = active_polls.pop(poll_id)
        selected_option = poll_answer.option_ids[0]
        correct_count = data["correct_count"] + (1 if selected_option == data["correct_option"] else 0)
        next_idx = data["q_idx"] + 1

        if data.get("is_grammar"):
            await send_next_gquestion(poll_answer.user.id, data["level"], data["test_key"], next_idx, correct_count)
        else:
            await send_next_question(poll_answer.user.id, data["level"], data["day_key"], next_idx, correct_count)

async def main():
    logging.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
