import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)

TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Lug'at ma'lumotlari
VOCABULARY = {
    "a1": [
        {"word": "der Tag", "meaning": "kun"},
        {"word": "die Zeit", "meaning": "vaqt"},
        {"word": "das Haus", "meaning": "uy"},
        {"word": "lernen", "meaning": "o'rganmoq"},
        {"word": "verstehen", "meaning": "tushunmoq"}
    ],
    "a2": [
        {"word": "die Erfahrung", "meaning": "tajriba"},
        {"word": "entscheiden", "meaning": "qaror qilmoq"},
        {"word": "die Ausbildung", "meaning": "kasbiy ta'lim"},
        {"word": "pünktlich", "meaning": "o'z vaqtida"}
    ],
    "b1": [
        {"word": "die Voraussetzung", "meaning": "talab / shart"},
        {"word": "beeinflussen", "meaning": "ta'sir o'tkazmoq"},
        {"word": "selbstständig", "meaning": "mustaqil"},
        {"word": "verantwortlich", "meaning": "mas'uliyatli"}
    ],
    "b2": [
        {"word": "die Anforderung", "meaning": "talab"},
        {"word": "berücksichtigen", "meaning": "hisobga olmoq"},
        {"word": "der Zwang", "meaning": "majburiyat"},
        {"word": "angemessen", "meaning": "mos / muvofiq"}
    ]
}

# Test ma'lumotlari
TESTS = {
    "a1": [
        {"question": "Nemis tilida 'der Apfel' nimani anglatadi?", "options": ["Olma", "Banan", "Olmori", "Uzum"], "correct": 0},
        {"question": "'Guten Tag' iborasining ma'nosi nima?", "options": ["Xayrli tun", "Xayrli kun", "Xayrli tong", "Rahmat"], "correct": 1}
    ],
    "a2": [
        {"question": "'entscheiden' fe'lining ma'nosi nima?", "options": ["Tushunmoq", "Qaror qilmoq", "O'rganmoq", "Yozmoq"], "correct": 1}
    ],
    "b1": [
        {"question": "'die Voraussetzung' so'zining tarjimasi qaysi?", "options": ["Talab / shart", "Tajriba", "Munosabat", "Natija"], "correct": 0}
    ],
    "b2": [
        {"question": "'berücksichtigen' fe'li nimani anglatadi?", "options": ["Hisobga olmoq", "Rad etmoq", "Taklif qilmoq", "Boshlamoq"], "correct": 0}
    ]
}

# Menyular
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Lug'at (Wortschatz)"), KeyboardButton(text="📝 Testlar")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

vocab_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 Daraja", callback_data="vocab_a1"), InlineKeyboardButton(text="🟡 A2 Daraja", callback_data="vocab_a2")],
        [InlineKeyboardButton(text="🟠 B1 Daraja", callback_data="vocab_b1"), InlineKeyboardButton(text="🔴 B2 Daraja", callback_data="vocab_b2")]
    ]
)

test_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 Testi", callback_data="test_a1"), InlineKeyboardButton(text="🟡 A2 Testi", callback_data="test_a2")],
        [InlineKeyboardButton(text="🟠 B1 Testi", callback_data="test_b1"), InlineKeyboardButton(text="🔴 B2 Testi", callback_data="test_b2")]
    ]
)

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    await message.answer(
        f"Hallo, <b>{user_name}</b>!\n\nNemis tili botiga xush kelibsiz! Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "📚 Lug'at (Wortschatz)")
async def dictionary_handler(message: Message) -> None:
    await message.answer(
        "📚 <b>Qaysi darajadagi lug'atni o'rganmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=vocab_inline_kb
    )

@dp.callback_query(F.data.startswith("vocab_"))
async def send_vocab(callback: CallbackQuery):
    level = callback.data.split("_")[1]
    words = VOCABULARY.get(level, [])
    if not words:
        await callback.message.answer("Ushbu daraja uchun lug'at hali qo'shilmadi.")
    else:
        text = f"📌 <b>{level.upper()} Darajasi Lug'ati:</b>\n\n"
        for item in words:
            text += f"• <b>{item['word']}</b> — {item['meaning']}\n"
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.message(F.text == "📝 Testlar")
async def test_handler(message: Message) -> None:
    await message.answer(
        "🧠 <b>Bilimingizni sinash uchun darajani tanlang:</b>",
        parse_mode="HTML",
        reply_markup=test_inline_kb
    )

@dp.callback_query(F.data.startswith("test_"))
async def run_test(callback: CallbackQuery):
    level = callback.data.split("_")[1]
    questions = TESTS.get(level, [])
    if not questions:
        await callback.message.answer("Ushbu daraja uchun testlar topilmadi.")
    else:
        q = questions[0]
        await callback.message.answer_poll(
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["correct"],
            is_anonymous=False
        )
    await callback.answer()

@dp.message(F.text == "ℹ️ Bot haqida")
async def about_handler(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Deutsch mit Ahrorbek</b> botida A1-B2 darajalar bo'yicha lug'atlar va interaktiv testlar mavjud.",
        parse_mode="HTML"
    )

async def handle_web(request):
    return web.Response(text="Bot active")

async def main():
    # Eski to'sqinlik qilayotgan ulanish va webhooklarni o'chirish
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

if name == "__main__":
    asyncio.run(main())
