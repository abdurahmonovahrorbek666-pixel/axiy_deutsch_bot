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

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# JSON fayllardan ma'lumotlarni o'qish
def load_data():
    try:
        with open("words.json", "r", encoding="utf-8") as f:
            words = json.load(f)
    except Exception:
        words = {}

    try:
        with open("tests.json", "r", encoding="utf-8") as f:
            tests = json.load(f)
    except Exception:
        tests = {}
        
    return words, tests

VOCABULARY, TESTS = load_data()

# Asosiy klaviatura
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Lug'at (Wortschatz)"), KeyboardButton(text="📝 Testlar")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    await message.answer(
        f"Hallo, <b>{user_name}</b>!\n\nNemis tili botiga xush kelibsiz! Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

# Siz so'ragan DINAMIK LUG'AT BO'LIMI
@dp.message(F.text == "📚 Lug'at (Wortschatz)")
async def dictionary_handler(message: Message) -> None:
    # words.json har safar yangilanganda ma'lumotni qayta o'qiydi
    global VOCABULARY, TESTS
    VOCABULARY, TESTS = load_data()

    keyboard_buttons = []
    for key, data in VOCABULARY.items():
        title = data.get("title", key)
        keyboard_buttons.append([InlineKeyboardButton(text=title, callback_data=f"topic_{key}")])
    
    topics_inline_kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "📚 <b>O'rganmoqchi bo'lgan mavzuyingizni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=topics_inline_kb
    )

@dp.callback_query(F.data.startswith("topic_"))
async def send_topic_words(callback: CallbackQuery):
    topic_key = callback.data.split("_")[1]
    topic_data = VOCABULARY.get(topic_key)
    
    if not topic_data:
        await callback.message.answer("Mavzu topilmadi.")
    else:
        text = f"<b>{topic_data.get('title', '')}</b>:\n\n"
        for item in topic_data.get("words", []):
            text += f"• <b>{item['word']}</b> — {item['meaning']}\n"
            
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Boshqa mavzular", callback_data="back_to_topics")]]
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_topics")
async def back_to_topics_handler(callback: CallbackQuery):
    keyboard_buttons = []
    for key, data in VOCABULARY.items():
        title = data.get("title", key)
        keyboard_buttons.append([InlineKeyboardButton(text=title, callback_data=f"topic_{key}")])
    
    topics_inline_kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "📚 <b>O'rganmoqchi bo'lgan mavzuyingizni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=topics_inline_kb
    )
    await callback.answer()

@dp.message(F.text == "📝 Testlar")
async def test_handler(message: Message) -> None:
    test_buttons = []
    for key in TESTS.keys():
        test_buttons.append([InlineKeyboardButton(text=f"📝 {key.capitalize()} Testi", callback_data=f"test_{key}")])
    
    test_kb = InlineKeyboardMarkup(inline_keyboard=test_buttons)
    await message.answer(
        "🧠 <b>Bilimingizni sinash uchun testni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=test_kb
    )

@dp.callback_query(F.data.startswith("test_"))
async def run_test(callback: CallbackQuery):
    level = callback.data.split("_")[1]
    questions = TESTS.get(level, [])
    if not questions:
        await callback.message.answer("Testlar topilmadi.")
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
        "ℹ️ <b>Deutsch mit Ahrorbek</b> botida mavzulashtirilgan lug'at va testlar mavjud.",
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

if name == "__main__":
    asyncio.run(main())
