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

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Render Environment'dan Token va Admin ID ni olish
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

if not BOT_TOKEN:
    logging.error("CRITICAL: BOT_TOKEN Environment variable topilmadi! Render'da Environment bo'limini tekshiring.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Foydalanuvchilar ma'lumotlari xotirasi
# Structure: users_db[user_id] = {"username": str, "a1": current_unlocked_day, ...}
users_db = {}
active_polls = {}

# Lug'at faylini (words.json) yuklash
def load_words():
    try:
        with open("words.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"words.json yuklashda xatolik: {e}")
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

# Asosiy menyu tugmalari
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Kunlik Lug'at va Test"), KeyboardButton(text="📊 Natijalarim")],
            [KeyboardButton(text="📖 Nemis tili Kitoblari (PDF)"), KeyboardButton(text="ℹ️ Bot haqida")]
        ],
        resize_keyboard=True
    )

# /start komandasi
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
        f"🟢 <b>A1 Daraja:</b> Ochiq: {user['a1']}-kun/20\n"
        f"🟡 <b>A2 Daraja:</b> Ochiq: {user['a2']}-kun/20\n"
        f"🟠 <b>B1 Daraja:</b> Ochiq: {user['b1']}-kun/20\n"
        f"🔴 <b>B2 Daraja:</b> Ochiq: {user['b2']}-kun/20\n\n"
        f"💡 <i>Eslatma: Keyingi kunga o'tish uchun testlardan kamida 80% natija ko'rsatishingiz kerak.</i>"
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
    await message.answer("📚 Tez orada ushbu bo'limga B1 va A2 darajadagi eng saralangan nemis tili kitoblari joylanadi!")

# Darajalar menyusini ko'rsatish
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

# Kunlar menyusi (Bosqichma-bosqich / Unlock Tizimi)
@dp.callback_query(F.data.startswith("showdays_"))
async def show_days(callback: CallbackQuery):
    level = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user = get_user_data(user_id, callback.from_user.username)
    
    unlocked_day = user.get(level, 1)
    level_days = words_data.get(level, {}).get("days", {})
    
    buttons = []
    row = []
    
    # words.json ichidagi barcha kunlarni dinamik chiqarish
    total_days = max(len(level_days), 5) # kamida 5 kunni ko'rsatadi
    for day_num in range(1, total_days + 1):
        day_key = f"day_{day_num}"
        
        if day_num <= unlocked_day:
            # Ochiq kunlar (topshirilgan va hozirgi ochilgan kun)
            icon = "✅" if day_num < unlocked_day else "📅"
            btn_text = f"{icon} {day_num}-kun"
            cb_data = f"viewday_{level}_{day_key}"
        else:
            # Qulflangan yopiq kunlar
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
    await callback.answer()

# Qulflangan kun bosilganda pop-up xabari
@dp.callback_query(F.data.startswith("locked_"))
async def locked_day_handler(callback: CallbackQuery):
    day_num = callback.data.split("_")[1]
    await callback.answer(f"⛔️ {day_num}-kun yopiq! Davom etish uchun oldingi kun testini muvaffaqiyatli topshiring.", show_alert=True)

# Orqaga qaytish
@dp.callback_query(F.data == "back_to_levels")
async def back_to_levels(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja (Anfänger)", callback_data="showdays_a1")],
            [InlineKeyboardButton(text="🟡 A2 Daraja (Grundlegend)", callback_data="showdays_a2")],
            [InlineKeyboardButton(text="🟠 B1 Daraja (Fortgeschritten)", callback_data="showdays_b1")],
            [InlineKeyboardButton(text="🔴 B2 Daraja (Selbstständig)", callback_data="showdays_b2")]
        ]
    )
    await callback.message.edit_text("🎯 O'zingizga mos bo'lgan til darajasini tanlang:", reply_markup=kb)
    await callback.answer()

# Kunlik lug'atni ko'rsatish
@dp.callback_query(F.data.startswith("viewday_"))
async def view_day_words(callback: CallbackQuery):
    _, level, day_key = callback.data.split("_")
    day_num = day_key.split("_")[1]
    
    questions = words_data.get(level, {}).get("days", {}).get(day_key, [])
    
    if not questions:
        await callback.answer(f"⚠️ {day_num}-kun uchun lug'at hali kiritilmagan.", show_alert=True)
        return

    # Chiroyli lug'at ko'rinishi
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
    await callback.answer()

# Test/Viktorina yuborish
@dp.callback_query(F.data.startswith("startquiz_"))
async def start_quiz(callback: CallbackQuery):
    _, level, day_key, q_idx, correct_count = callback.data.split("_")
    q_idx = int(q_idx)
    correct_count = int(correct_count)
    
    questions = words_data.get(level, {}).get("days", {}).get(day_key, [])
    
    # Test tugaganda natijani hisoblash
    if q_idx >= len(questions):
        total = len(questions)
        percentage = int((correct_count / total) * 100) if total > 0 else 0
        user_id = callback.from_user.id
        user = get_user_data(user_id, callback.from_user.username)
        current_day_num = int(day_key.split("_")[1])
        
        result_text = f"🏁 <b>Test yakunlandi!</b>\n\nNatijangiz: <b>{correct_count}/{total}</b> ({percentage}%)\n\n"
        
        # 80% to'plansa keyingi kun ochiladi
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
        await callback.message.answer(result_text, parse_mode="HTML", reply_markup=next_kb)
        await callback.answer()
        return

    item = questions[q_idx]
    poll_msg = await callback.message.answer_poll(
        question=f"[{q_idx + 1}/{len(questions)}] '{item['word']}' so'zining ma'nosi nima?",
        options=item["options"],
        correct_option_id=item["correct"],
        type="quiz",
        is_anonymous=False
    )
    
    active_polls[poll_msg.poll.id] = {
        "user_id": callback.from_user.id,
        "level": level,
        "day_key": day_key,
        "q_idx": q_idx,
        "correct_count": correct_count,
        "correct_option": item["correct"]
    }
    await callback.answer()

# Viktorina javoblarini qabul qilish
@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    poll_id = poll_answer.poll_id
    if poll_id in active_polls:
        data = active_polls.pop(poll_id)
        selected_option = poll_answer.option_ids[0]
        
        if selected_option == data["correct_option"]:
            data["correct_count"] += 1
            
        next_idx = data["q_idx"] + 1
        
        fake_callback = types.CallbackQuery(
            id="",
            from_user=poll_answer.user,
            chat_instance="",
            message=types.Message(
                message_id=0,
                date=None,
                chat=types.Chat(id=poll_answer.user.id, type="private")
            ),
            data=f"startquiz_{data['level']}_{data['day_key']}_{next_idx}_{data['correct_count']}"
        )
        await start_quiz(fake_callback)

# Asosiy ishga tushirish funksiyasi
async def main():
    logging.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
