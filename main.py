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

# Bazani ishga tushirish
init_db()

# ----------------- FSM NIZOMLARI -----------------

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

class QuizState(StatesGroup):
    level = State()
    day = State()
    current_index = State()
    correct_count = State()
    questions = State()

# ----------------- SO'ZLAR MA'LUMOTI (KUNLAR BO'YICHA) -----------------

A1_WORDS_DATA = {
    "day_1": [
        {"word": "hallo", "meaning": "salom", "options": ["salom", "xayr", "rahmat", "ha"], "correct": 0},
        {"word": "danke", "meaning": "rahmat", "options": ["yo'q", "rahmat", "marhamat", "bugun"], "correct": 1},
        {"word": "bitte", "meaning": "marhamat", "options": ["xayr", "salom", "marhamat", "kechirasiz"], "correct": 2},
        {"word": "ja", "meaning": "ha", "options": ["ha", "yo'q", "balki", "albatta"], "correct": 0},
        {"word": "nein", "meaning": "yo'q", "options": ["ha", "yo'q", "yaxshi", "yomon"], "correct": 1},
        {"word": "Guten Morgen", "meaning": "Xayrli tong", "options": ["Xayrli kech", "Xayrli tong", "Xayrli kun", "Xayr"], "correct": 1},
        {"word": "Guten Tag", "meaning": "Xayrli kun", "options": ["Xayrli kun", "Tungi salom", "Ertagacha", "Rahmat"], "correct": 0},
        {"word": "Guten Abend", "meaning": "Xayrli kech", "options": ["Xayrli tong", "Xayrli kun", "Xayrli kech", "Xayr"], "correct": 2},
        {"word": "Gute Nacht", "meaning": "Xayrli tun", "options": ["Xayrli tun", "Kun xayrli bo'lsin", "Salom", "Afsus"], "correct": 0},
        {"word": "Tschüss", "meaning": "Xayr", "options": ["Salom", "Xayr", "Rahmat", "Iltimos"], "correct": 1},
        {"word": "Auf Wiedersehen", "meaning": "Ko'rishguncha", "options": ["Salom", "Ko'rishguncha", "Xush kelibsiz", "Rahmat"], "correct": 1},
        {"word": "der Mann", "meaning": "erkak", "options": ["ayol", "erkak", "boshliq", "bola"], "correct": 1},
        {"word": "die Frau", "meaning": "ayol / xotin", "options": ["qiz", "ayol / xotin", "ona", "opa"], "correct": 1},
        {"word": "das Kind", "meaning": "bola", "options": ["o'g'il", "qiz", "bola", "talaba"], "correct": 2},
        {"word": "der Junge", "meaning": "o'g'il bola", "options": ["qiz bola", "o'g'il bola", "aka", "uka"], "correct": 1},
        {"word": "das Mädchen", "meaning": "qiz bola", "options": ["qiz bola", "onasi", "opa", "singil"], "correct": 0},
        {"word": "der Freund", "meaning": "do'st (o'g'il)", "options": ["dushman", "do'st", "qo'shni", "talaba"], "correct": 1},
        {"word": "die Freundin", "meaning": "do'st (qiz)", "options": ["qiz do'st", "singil", "shifokor", "o'qituvchi"], "correct": 0},
        {"word": "der Name", "meaning": "ism", "options": ["familiya", "ism", "shahar", "yosh"], "correct": 1},
        {"word": "das Land", "meaning": "mamlakat", "options": ["shahar", "kenglik", "mamlakat", "qishloq"], "correct": 2},
        {"word": "die Stadt", "meaning": "shahar", "options": ["shahar", "qishloq", "davlat", "uy"], "correct": 0},
        {"word": "die Sprache", "meaning": "til", "options": ["so'z", "til", "gap", "harf"], "correct": 1},
        {"word": "lernen", "meaning": "o'rganmoq", "options": ["yozmoq", "o'qimoq", "o'rganmoq", "gapirmoq"], "correct": 2},
        {"word": "sprechen", "meaning": "gapirmoq", "options": ["eshitmoq", "gapirmoq", "ko'rmoq", "yozmoq"], "correct": 1},
        {"word": "verstehen", "meaning": "tushunmoq", "options": ["tushunmoq", "so'ramoq", "bilmoq", "o'ylamoq"], "correct": 0},
        {"word": "schreiben", "meaning": "yozmoq", "options": ["chizmoq", "yozmoq", "o'qimoq", "tinglamoq"], "correct": 1},
        {"word": "lesen", "meaning": "o'qimoq", "options": ["yozmoq", "o'qimoq", "gapirmoq", "tinglamoq"], "correct": 1},
        {"word": "hören", "meaning": "eshitmoq", "options": ["eshitmoq", "ko'rmoq", "sezmoq", "aytmoq"], "correct": 0},
        {"word": "fragen", "meaning": "so'ramoq", "options": ["javob bermoq", "so'ramoq", "aytmoq", "chaqirmoq"], "correct": 1},
        {"word": "antworten", "meaning": "javob bermoq", "options": ["so'ramoq", "javob bermoq", "yozmoq", "o'qimoq"], "correct": 1}
    ],
    "day_2": [
        {"word": "der Vater", "meaning": "ota", "options": ["ona", "ota", "aka", "bobo"], "correct": 1},
        {"word": "die Mutter", "meaning": "ona", "options": ["ona", "opa", "bobi", "xola"], "correct": 0},
        {"word": "der Sohn", "meaning": "o'g'il", "options": ["qiz", "o'g'il", "noma'lum", "aka"], "correct": 1},
        {"word": "die Tochter", "meaning": "qiz perzent", "options": ["ona", "singil", "qiz perzent", "amaki"], "correct": 2},
        {"word": "der Bruder", "meaning": "aka/uka", "options": ["aka/uka", "dada", "do'st", "o'qituvchi"], "correct": 0},
        {"word": "die Schwester", "meaning": "opa/singil", "options": ["xola", "opa/singil", "qo'shni", "ona"], "correct": 1},
        {"word": "die Familie", "meaning": "oila", "options": ["uy", "oila", "shahar", "do'stlar"], "correct": 1},
        {"word": "das Haus", "meaning": "uy", "options": ["xona", "uy", "bino", "eshik"], "correct": 1},
        {"word": "die Wohnung", "meaning": "xonadon (kvartira)", "options": ["xonadon (kvartira)", "hovli", "ko'cha", "shahar"], "correct": 0},
        {"word": "das Zimmer", "meaning": "xona", "options": ["oshxona", "deraza", "xona", "stul"], "correct": 2},
        {"word": "die Küche", "meaning": "oshxona", "options": ["oshxona", "yotoqxona", "burchak", "uy"], "correct": 0},
        {"word": "das Bad", "meaning": "vanna xonasi", "options": ["vanna xonasi", "tualet", "zal", "balkon"], "correct": 0},
        {"word": "der Tisch", "meaning": "stol", "options": ["stul", "stol", "shkaf", "krovat"], "correct": 1},
        {"word": "der Stuhl", "meaning": "stul", "options": ["stol", "stul", "gilam", "deraza"], "correct": 1},
        {"word": "das Bett", "meaning": "krovat", "options": ["yastik", "krovat", "xona", "stol"], "correct": 1},
        {"word": "die Tür", "meaning": "eshik", "options": ["deraza", "eshik", "devor", "tom"], "correct": 1},
        {"word": "das Fenster", "meaning": "deraza", "options": ["deraza", "eshik", "parda", "ko'cha"], "correct": 0},
        {"word": "wohnen", "meaning": "yashamoq", "options": ["ishlamoq", "yashamoq", "uxlamoq", "o'tirmoq"], "correct": 1},
        {"word": "arbeiten", "meaning": "ishlamoq", "options": ["o'ynamoq", "ishlamoq", "dam olmoq", "yozmoq"], "correct": 1},
        {"word": "schlafen", "meaning": "uxlamoq", "options": ["yurmoq", "uxlamoq", "turmoq", "yemoq"], "correct": 1},
        {"word": "essen", "meaning": "yemoq", "options": ["ichmoq", "yemoq", "pishirmoq", "olmoq"], "correct": 1},
        {"word": "trinken", "meaning": "ichmoq", "options": ["yemoq", "ichmoq", "quyish", "sotib olmoq"], "correct": 1},
        {"word": "kochen", "meaning": "ovqat pishirmoq", "options": ["yemoq", "yuvmoq", "ovqat pishirmoq", "tozalamoq"], "correct": 2},
        {"word": "groß", "meaning": "katta", "options": ["kichik", "katta", "uzun", "keng"], "correct": 1},
        {"word": "klein", "meaning": "kichik", "options": ["katta", "baland", "kichik", "past"], "correct": 2},
        {"word": "schön", "meaning": "chiroyli", "options": ["xunuk", "chiroyli", "yaxshi", "yangi"], "correct": 1},
        {"word": "alt", "meaning": "eski / qari", "options": ["yangi", "eski / qari", "yosh", "katta"], "correct": 1},
        {"word": "neu", "meaning": "yangi", "options": ["eski", "yangi", "zamonaviy", "chiroyli"], "correct": 1},
        {"word": "gut", "meaning": "yaxshi", "options": ["yomon", "yaxshi", "to'g'ri", "tayyor"], "correct": 1},
        {"word": "schlecht", "meaning": "yomon", "options": ["yaxshi", "yomon", "qiyin", "oson"], "correct": 1}
    ]
}

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

@dp.message(Command("admin"))
async def admin_start(message: Message):
    if str(message.from_user.id) == str(ADMIN_ID):
        await message.answer("👨‍💻 <b>Admin paneli:</b>", parse_mode="HTML", reply_markup=admin_keyboard)
    else:
        await message.answer("⚠️ Admin emassiz.")

@dp.message(F.text == "📢 Xabar yuborish (Broadcast)")
async def broadcast_prompt(message: Message, state: FSMContext):
    if str(message.from_user.id) == str(ADMIN_ID):
        await state.set_state(AdminStates.waiting_for_broadcast_text)
        await message.answer("Barchaga yubormoqchi bo'lgan xabaringizni yuboring:")

@dp.message(AdminStates.waiting_for_broadcast_text)
async def send_broadcast(message: Message, state: FSMContext):
    if str(message.from_user.id) == str(ADMIN_ID):
        await message.answer("✅ Xabar yuborildi!")
        await state.clear()

@dp.message(F.text == "⬅️ Bosh menyuga qaytish")
async def back_to_main_user(message: Message):
    await message.answer("Bosh menyu:", reply_markup=main_keyboard)

# ----------------- NATIJALAR BO'LIMI -----------------

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
        "<i>Eslatma: Keyingi kunga o'tish uchun kunlik testdan kamida 80% (24/30) to'plashingiz lozim.</i>"
    )
    await message.answer(text, parse_mode="HTML")

# ----------------- KUNLIK LUG'AT VA TEST TIZIMI -----------------

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

    day_key = f"day_{current_day}"
    # Agar so'ralgan kun bazada bo'lmasa, tayyor bo'lgan oxirgi kunni oladi
    questions = A1_WORDS_DATA.get(day_key, A1_WORDS_DATA.get("day_1"))

    vocab_text = f"📚 <b>{level.upper()} Daraja - {current_day}-kun lug'ati (30 ta so'z):</b>\n\n"
    for idx, item in enumerate(questions, 1):
        vocab_text += f"{idx}. <b>{item['word']}</b> — {item['meaning']}\n"

    start_quiz_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Testni boshlash (30 ta quiz)", callback_data=f"startquiz_{level}_{current_day}")]
        ]
    )

    await callback.message.edit_text(vocab_text, parse_mode="HTML", reply_markup=start_quiz_kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("startquiz_"))
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    _, level, day = callback.data.split("_")
    day = int(day)
    
    day_key = f"day_{day}"
    questions = A1_WORDS_DATA.get(day_key, A1_WORDS_DATA.get("day_1"))

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
            question=f"[{idx+1}/30] '{q['word']}' so'zining ma'nosi nima?",
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
            result_text += f"\n🎉 <b>Tabriklaymiz! 80% dan yuqori ball to'pladingiz. {next_day}-kun testi ochildi!</b>"
            
            next_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"➡️ {next_day}-kun lug'ati va testini boshlash", callback_data=f"level_{level}")]
                ]
            )
        else:
            result_text += "\n⚠️ <b>Afsus, 80% dan kam ball to'pladingiz. Keyingi kun ochilmadi. Qaytadan urinib ko'ring.</b>"
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
        "ℹ️ <b>Deutsch mit Ahrorbek</b> botida har kuni 30 ta so'z o'rganasiz va test topshirasiz.",
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
