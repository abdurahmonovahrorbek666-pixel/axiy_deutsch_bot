import asyncio
import os
import json
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery,
    PollAnswer
)

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID") 

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----------------- MA'LUMOTLAR BAZASI (SQLite) -----------------

DB_FILE = "user_progress.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER PRIMARY KEY,
            a1_day INTEGER DEFAULT 1,
            a2_day INTEGER DEFAULT 1,
            b1_day INTEGER DEFAULT 1,
            b2_day INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def get_user_day(user_id: int, level: str = "a1") -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {level}_day FROM user_progress WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO user_progress (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return 1
    conn.close()
    return row[0]

def update_user_day(user_id: int, level: str, next_day: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE user_progress SET {level}_day = ? WHERE user_id = ?", (next_day, user_id))
    conn.commit()
    conn.close()

init_db()

# ----------------- JSON SO'ZLAR BAZASINI O'QISH -----------------

def load_words_data(level: str, day: int):
    filename = "words_a1.json"  # Fayl nomingiz bilan mos bo'lishi kerak
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            level_data = data.get(level.lower(), {})
            days_data = level_data.get("days", {})
            return days_data.get(f"day_{day}", [])
    return []

# ----------------- FSM NIZOMLARI -----------------

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

class QuizState(StatesGroup):
    level = State()
    day = State()
    current_index = State()
    correct_count = State()
    questions = State()

# ----------------- KLAVIATURALAR -----------------

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Kunlik Lug'at va Test"), KeyboardButton(text="📊 Natijalarim")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Xabar yuborish (Broadcast)")],
        [KeyboardButton(text="⬅️ Bosh menyuga qaytish")]
    ],
    resize_keyboard=True
)

def get_levels_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 A1 Daraja", callback_data="level_a1"), InlineKeyboardButton(text="🟡 A2 Daraja", callback_data="level_a2")],
            [InlineKeyboardButton(text="🟠 B1 Daraja", callback_data="level_b1"), InlineKeyboardButton(text="🔴 B2 Daraja", callback_data="level_b2")]
        ]
    )

# ----------------- BOT HANDLERLARI -----------------

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    await message.answer(
        f"Hallo, <b>{user_name}</b>!\n\nNemis tili kunlik 30 ta so'z va test tizimiga xush kelibsiz!",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "⬅️ Bosh menyuga qaytish")
async def back_to_main_user(message: Message):
    await message.answer("Bosh menyu:", reply_markup=main_keyboard)

@dp.message(F.text == "📊 Natijalarim")
async def show_results(message: Message):
    user_id = message.from_user.id
    a1_day = get_user_day(user_id, "a1")
    a2_day = get_user_day(user_id, "a2")
    b1_day = get_user_day(user_id, "b1")
    b2_day = get_user_day(user_id, "b2")

    a1_pct = min(round(((a1_day - 1) / 20) * 100), 100)
    a2_pct = min(round(((a2_day - 1) / 20) * 100), 100)
    b1_pct = min(round(((b1_day - 1) / 20) * 100), 100)
    b2_pct = min(round(((b2_day - 1) / 20) * 100), 100)

    text = (
        "📊 <b>Sizning umumiy o'zlashtirish ko'rsatkichingiz:</b>\n\n"
        f"🟢 <b>A1 Daraja:</b> {a1_pct}% | Ochiq: {a1_day}-kun/20\n"
        f"🟡 <b>A2 Daraja:</b> {a2_pct}% | Ochiq: {a2_day}-kun/20\n"
        f"🟠 <b>B1 Daraja:</b> {b1_pct}% | Ochiq: {b1_day}-kun/20\n"
        f"🔴 <b>B2 Daraja:</b> {b2_pct}% | Ochiq: {b2_day}-kun/20\n\n"
        "<i>Eslatma: Keyingi kunga o'tish uchun kunlik testdan kamida 80% to'plashingiz lozim.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📚 Kunlik Lug'at va Test")
async def dictionary_handler(message: Message):
    await message.answer(
        "📚 <b>O'rganmoqchi bo'lgan darajangizni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_levels_keyboard()
    )

@dp.callback_query(F.data.startswith("level_"))
async def choose_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split("_")[1]
    user_id = callback.from_user.id
    current_day = get_user_day(user_id, level)

    questions = load_words_data(level, current_day)

    if not questions:
        await callback.answer(f"⚠️ {level.upper()} darajasi {current_day}-kun uchun lug'at topilmadi.", show_alert=True)
        return

    vocab_text = f"📚 <b>{level.upper()} Daraja - {current_day}-kun lug'ati ({len(questions)} ta so'z):</b>\n\n"
    for idx, item in enumerate(questions, 1):
        vocab_text += f"{idx}. <b>{item['word']}</b> — {item['meaning']}\n"

    start_quiz_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📝 {current_day}-kun testini boshlash", callback_data=f"startquiz_{level}_{current_day}")]
        ]
    )

    await callback.message.edit_text(vocab_text, parse_mode="HTML", reply_markup=start_quiz_kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("startquiz_"))
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    _, level, day = callback.data.split("_")
    day = int(day)
    
    questions = load_words_data(level, day)

    await state.set_state(QuizState.current_index)
    await state.update_data(
        level=level,
        day=day,
        current_index=0,
        correct_count=0,
        questions=questions
    )

    await callback.message.answer(f"🚀 <b>{level.upper()} - {day}-kun testi boshlandi!</b>\nOmad!", parse_mode="HTML")
    await send_next_question_by_id(callback.from_user.id, state)
    await callback.answer()

@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer, state: FSMContext):
    data = await state.get_data()
    if not data:
        return

    idx = data.get("current_index", 0)
    questions = data.get("questions", [])
    correct_count = data.get("correct_count", 0)

    if idx < len(questions):
        correct_option = questions[idx]["correct"]
        if poll_answer.option_ids[0] == correct_option:
            correct_count += 1

        await state.update_data(current_index=idx + 1, correct_count=correct_count)
        await send_next_question_by_id(poll_answer.user.id, state)

async def send_next_question_by_id(user_id: int, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_index", 0)
    questions = data.get("questions", [])

    if idx < len(questions):
        q = questions[idx]
        await bot.send_poll(
            chat_id=user_id,
            question=f"[{idx+1}/{len(questions)}] '{q['word']}' so'zining ma'nosi nima?",
            options=q["options"],
            type="quiz",
            correct_option_id=q["correct"],
            is_anonymous=False
        )
    else:
        correct = data.get("correct_count", 0)
        total = len(questions)
        percentage = round((correct / total) * 100) if total > 0 else 0
        level = data.get("level")
        day = data.get("day")

        result_text = (
            f"🏁 <b>Test yakunlandi!</b>\n\n"
            f"Natijangiz: <b>{correct}/{total}</b> ({percentage}%)\n"
        )

        next_kb = None
        if percentage >= 80:
            next_day = day + 1
            update_user_day(user_id, level, next_day)
            result_text += f"\n🎉 <b>Tabriklaymiz! 80% dan yuqori ball to'pladingiz. {next_day}-kun ochildi!</b>"
            
            next_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"➡️ {next_day}-kun lug'atiga o'tish", callback_data=f"level_{level}")]
                ]
            )
        else:
            result_text += "\n⚠️ <b>80% to'play olmadingiz. {day}-kunda qolasiz. Qayta urinib ko'ring.</b>"
            next_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"🔄 {day}-kun testini qayta topshirish", callback_data=f"startquiz_{level}_{day}")]
                ]
            )

        await bot.send_message(chat_id=user_id, text=result_text, parse_mode="HTML", reply_markup=next_kb)
        await state.clear()

@dp.message(F.text == "ℹ️ Bot haqida")
async def about_handler(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Deutsch mit Ahrorbek</b> botida har kuni nemischa so'zlarni o'rganasiz va test topshirasiz.",
        parse_mode="HTML"
    )

async def handle_web(request):
    return web.Response(text="Bot active")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
