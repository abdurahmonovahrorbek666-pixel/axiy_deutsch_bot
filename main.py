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

# Foydalanuvchilar va aktiv testlar xotirasi
users_db = {}
active_polls = {}

# Render Web Service uchun ping nuqtasi
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly!")

# Lug'at faylini (words.json) yuklash
def load_words():
    try:
        if os.path.exists("words.json"):
            with open("words.json", "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logging.error("Xatolik: words.json fayli topilmadi!")
            return {}
    except Exception as e:
        logging.error(f"words.json faylini o'qishda xatolik: {e}")
        return {}

words_data = load_words()

def get_user_data(user_id, username):
    if user_id not in users_db:
        users_db[user_id] = {
            "username": username or "Foydalanuvchi",
            "a1": 1,
            "a2": 1,
            "b1": 1,
            "b2": 1,
            "scores": {}
        }
    return users_db[user_id]

# Asosiy menyu
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Kunlik Lug'at va Test"), KeyboardButton(text="📊 Natijalarim")],
            [KeyboardButton(text="📖 Nemis tili Kitoblari (PDF)"), KeyboardButton(text="ℹ️ Bot haqida")]
        ],
        resize_keyboard=True
    )

# /start buyrug'i
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    get_user_data(user_id, username)
    
    welcome_text = (
        f"Hallo, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"<b>Deutsch mit Ahrorbek</b> botiga xush kelibsiz!\n"
        f"Bu bot orqali nemis tili so'z boyligingizni kunlik bosqichma-bosqich va testlar orqali oshirib borishingiz mumkin."
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_keyboard())

# Admin buyruqlari
@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID and ADMIN_ID != 0:
        count = len(users_db)
        await message.answer(f"📊 <b>Bot statistikasi:</b>\n\nJamlangan foydalanuvchilar soni: <b>{count}</b> ta", parse_mode="HTML")
    else:
        await message.answer("⚠️ Bu buyruq faqat bot admini uchun!")

@dp.message(Command("users"))
async def users_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID and ADMIN_ID != 0:
        if not users_db:
            await message.answer("Hozircha foydalanuvchilar yo'q.")
            return
        text = "👥 <b>Foydalanuvchilar ro'yxati:</b>\n\n"
        for uid, data in users_db.items():
            text += f"• ID: {uid} | @{data['username']} | A1: {data['a1']}-kun\n"
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer("⚠️ Bu buyruq faqat bot admini uchun!")

# Natijalarim bo'limi
@dp.message(F.text == "📊 Natijalarim")
async def my_stats(message: types.Message):
    user = get_user_data(message.from_user.id, message.from_user.username)
    text = (
        f"📊 <b>Sizning umumiy o'zlashtirish ko'rsatkichingiz:</b>\n\n"
        f"🟢 <b>A1 Daraja:</b> Ochiq: {user['a1']}-kun\n"
        f"🟡 <b>A2 Daraja:</b> Ochiq: {user['a2']}-kun\n"
        f"🟠 <b>B1 Daraja:</b> Ochiq: {user['b1']}-kun\n"
        f"🔴 <b>B2 Daraja:</b> Ochiq: {user['b2']}-kun\n\n"
        f"💡 <i>Eslatma: Keyingi kunga o'tish uchun testlarda kamida 80% natija ko'rsatishingiz kerak.</i>"
    )
    await message.answer(text, parse_mode="HTML")

# Bot haqida
@dp.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: types.Message):
    await message.answer(
        "🇩🇪 <b>Deutsch mit Ahrorbek</b> — Nemis tilini oson va samarali o'rganish loyihasi.\n\n"
        "Botingiz orqali har kuni yangi so'zlarni yodlab, testlar orqali bilimlaringizni mustahkamlab borasiz.",
        parse_mode="HTML"
    )

# Kitoblar bo'limi
@dp.message(F.text == "📖 Nemis tili Kitoblari (PDF)")
async def pdf_books(message: types.Message):
    await message.answer("📚 Tez orada ushbu bo'limga saralangan nemis tili kitoblari joylanadi!")

# Darajalar menyusi
@dp.message(F.text == "📚 Kunlik Lug'at va Test")
async def show_levels(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja (Anfänger)", callback_data="showdays_a1")],
            [InlineKeyboardButton(text="🟡 A2 Daraja (Grundlegend)", callback_data="showdays_a2")],
            [InlineKeyboardButton(text="🟠 B1 Daraja (Fortgeschritten)", callback_data="showdays_b1")],
            [InlineKeyboardButton(text="🔴 B2 Daraja (Selbstständig)", callback_data="showdays_b2")]
        ]
    )
    await message.answer("🎯 O'zingizga mos bo'lgan til darajasini tanlang:", reply_markup=kb)

# Kunlar menyusi
@dp.callback_query(F.data.startswith("showdays_"))
async def show_days(callback: CallbackQuery):
    await callback.answer()
    level = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user = get_user_data(user_id, callback.from_user.username)
    
    unlocked_day = user.get(level, 1)
    level_days = words_data.get(level, {}).get("days", {})
    
    buttons = []
    row = []
    
    total_days = max(len(level_days), 5)
    for day_num in range(1, total_days + 1):
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
    if row:
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_levels")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    title = words_data.get(level, {}).get("title", level.upper())
    await callback.message.edit_text(
        f"<b>{title}</b>\n\nDavom etish uchun ochiq kunni tanlang:",
        parse_mode="HTML",
        reply_markup=kb
    )

# Qulflangan kun
@dp.callback_query(F.data.startswith("locked_"))
async def locked_day_handler(callback: CallbackQuery):
    day_num = callback.data.split("_")[1]
    await callback.answer(f"⛔️ {day_num}-kun yopiq! Oldingi kun testini kamida 80% ga topshiring.", show_alert=True)

# Orqaga qaytish
@dp.callback_query(F.data == "back_to_levels")
async def back_to_levels(callback: CallbackQuery):
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja (Anfänger)", callback_data="showdays_a1")],
            [InlineKeyboardButton(text="🟡 A2 Daraja (Grundlegend)", callback_data="showdays_a2")],
            [InlineKeyboardButton(text="🟠 B1 Daraja (Fortgeschritten)", callback_data="showdays_b1")],
            [InlineKeyboardButton(text="🔴 B2 Daraja (Selbstständig)", callback_data="showdays_b2")]
        ]
    )
    await callback.message.edit_text("🎯 O'zingizga mos bo'lgan til darajasini tanlang:", reply_markup=kb)

# Lug'atni ko'rsatish (Tuzatilgan qism)
@dp.callback_query(F.data.startswith("viewday_"))
async def view_day_words(callback: CallbackQuery):
    await callback.answer()
    
    parts = callback.data.split("_")
    level = parts[1]                     # masalan: 'a1'
    day_key = f"{parts[2]}_{parts[3]}"   # masalan: 'day_1'
    day_num = parts[3]                   # masalan: '1'
    
    questions = words_data.get(level, {}).get("days", {}).get(day_key, [])
    
    if not questions:
        await callback.message.answer(f"⚠️ {day_num}-kun uchun lug'at topilmadi yoki words.json faylida xatolik bor.")
        return

    vocab_text = (
        f"✨ <b>{level.upper()} DARAJA — {day_num}-KUN LUG'ATI</b> ✨\n"
        f"───────────────\n"
        f"🎯 <i>Bugungi maqsadingiz: {len(questions)} ta yangi so'z!</i>\n\n"
    )

    for idx, item in enumerate(questions, 1):
        word = item['word']
        meaning = item['meaning']

        if word.startswith("der "):
            styled_word = f"🔹 <b>{word}</b>"
        elif word.startswith("die "):
            styled_word = f"🔸 <b>{word}</b>"
        elif word.startswith("das "):
            styled_word = f"🟢 <b>{word}</b>"
        else:
            styled_word = f"▫️ <b>{word}</b>"

        vocab_text += f"{idx:02d}. {styled_word} ➔ <i>{meaning}</i>\n"

        if idx % 10 == 0 and idx != len(questions):
            vocab_text += "───────────────\n"

    vocab_text += (
        f"\n───────────────\n"
        f"💡 <i>Lug'atni yodlab bo'lgach, bilimingizni sinash uchun pastdagi tugmani bosing!</i>"
    )

    start_quiz_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🚀 {day_num}-kun testini boshlash ({len(questions)} savol)", 
                callback_data=f"startquiz_{level}_{day_key}_0_0"
            )],
            [InlineKeyboardButton(text="⬅️ Kunlar ro'yxatiga qaytish", callback_data=f"showdays_{level}")]
        ]
    )

    await callback.message.edit_text(vocab_text, parse_mode="HTML", reply_markup=start_quiz_kb)

# Keyingi savolni yuborish
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
            result_text += f"🎉 <b>Tabriklaymiz! 80% dan yuqori ball to'pladingiz. {current_day_num + 1}-kun ochildi!</b>"
        else:
            result_text += f"⚠️ <i>Keyingi kunni ochish uchun kamida 80% to'plashingiz kerak. Qayta urinib ko'ring!</i>"

        next_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Qayta topshirish", callback_data=f"viewday_{level}_{day_key}")],
                [InlineKeyboardButton(text="📚 Kunlar ro'yxatiga o'tish", callback_data=f"showdays_{level}")]
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
        "user_id": user_id,
        "level": level,
        "day_key": day_key,
        "q_idx": q_idx,
        "correct_count": correct_count,
        "correct_option": item["correct"]
    }

# Testni boshlash (Tuzatilgan qism)
@dp.callback_query(F.data.startswith("startquiz_"))
async def start_quiz(callback: CallbackQuery):
    await callback.answer()
    
    parts = callback.data.split("_")
    level = parts[1]
    day_key = f"{parts[2]}_{parts[3]}"
    q_idx = int(parts[4])
    correct_count = int(parts[5])
    
    user_id = callback.from_user.id
    await send_next_question(user_id, level, day_key, q_idx, correct_count)

# Test javobini qabul qilish
@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    poll_id = poll_answer.poll_id
    if poll_id in active_polls:
        data = active_polls.pop(poll_id)
        selected_option = poll_answer.option_ids[0]
        
        correct_count = data["correct_count"]
        if selected_option == data["correct_option"]:
            correct_count += 1
            
        next_idx = data["q_idx"] + 1
        
        await send_next_question(
            user_id=poll_answer.user.id,
            level=data["level"],
            day_key=data["day_key"],
            q_idx=next_idx,
            correct_count=correct_count
        )

# Main runner
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
    logging.info(f"Dummy Web Server {port}-portda ishga tushdi.")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
