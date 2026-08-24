import asyncio
import os
import json
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

TOKEN = "8912605806:AAEshu0Br0OVKsT1QXSg43Yy9NBJzOzW2Z8"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# JSON fayllardan ma'lumotlarni yuklash
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

vocab_data = load_json("words.json")
test_data = load_json("tests.json")

# Asosiy menyu
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Lug'at (Wortschatz)"), KeyboardButton(text="📝 Testlar")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

# Lug'at inline tugmalari
vocab_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 Daraja", callback_data="vocab_a1"), InlineKeyboardButton(text="🟡 A2 Daraja", callback_data="vocab_a2")],
        [InlineKeyboardButton(text="🟠 B1 Daraja", callback_data="vocab_b1"), InlineKeyboardButton(text="🔴 B2 Daraja", callback_data="vocab_b2")]
    ]
)

# Test inline tugmalari
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

# --- LUG'AT BO'LIMI ---
@dp.message(F.text == "📚 Lug'at (Wortschatz)")
async def dictionary_handler(message: Message) -> None:
    await message.answer(
        "📚 <b>Qaysi darajadagi lug'atni o'rganmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=vocab_inline_kb
    )

@dp.callback_query(F.data.startswith("vocab_"))
async def send_vocab(callback: CallbackQuery):
    level = callback.data.split("_")[1] # a1, a2, b1, b2
    words = vocab_data.get(level, [])
    
    if not words:
        await callback.message.answer(f"{level.upper()} darajasi uchun lug'at hali qo'shilmadi.")
    else:
        text = f"📌 <b>{level.upper()} Darajasi Lug'ati:</b>\n\n"
        for item in words[:20]: # Dastlabki 20 ta so'zni ko'rsatadi
            text += f"• <b>{item['word']}</b> — {item['meaning']}\n"
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# --- TESTLAR BO'LIMI ---
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
    questions = test_data.get(level, [])
    
    if not questions:
        await callback.message.answer(f"{level.upper()} darajasi uchun testlar topilmadi.")
    else:
        # Darajadagi birinchi testni yuboradi
        q = questions[0]
        await callback.message.answer_poll(
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["correct"],
            is_anonymous=False
        )
    await callback.answer()

# --- BOT HAQIDA ---
@dp.message(F.text == "ℹ️ Bot haqida")
async def about_handler(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Deutsch mit Ahrorbek</b> botida A1-B2 darajalar bo'yicha minglab so'zlar va interaktiv testlar mavjud.",
        parse_mode="HTML"
    )

# Render uchun Veb-server
async def handle_web(request):
    return web.Response(text="Bot active")

async def main():
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
