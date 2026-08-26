import asyncio
import os
import json
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
    CallbackQuery
)

TOKEN = os.environ.get("BOT_TOKEN")
# Admin Telegram ID sini Render Environment Variables'dan oladi
ADMIN_ID = os.environ.get("ADMIN_ID") 

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Admin holatini saqlash uchun (FSM)
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()

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

VOCABULARY, tests = load_data()

# Asosiy klaviatura
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Lug'at (Wortschatz)"), KeyboardButton(text="📝 Testlar")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

# Admin klaviaturasi
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Xabar yuborish (Broadcast)")],
        [KeyboardButton(text="⬅️ Bosh menyuga qaytish")]
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

# ----------------- ADMIN PANEL BO'LIMI -----------------

@dp.message(Command("admin"))
async def admin_start(message: Message):
    # Tekshirish: foydalanuvchi Admin yoki yo'qligini aniqlaydi
    if str(message.from_user.id) == str(ADMIN_ID):
        await message.answer(
            "👨‍💻 <b>Admin paneliga xush kelibsiz!</b>\n\nQuyidagi tugmalardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=admin_keyboard
        )
    else:
        await message.answer("⚠️ Sizga admin paneldan foydalanish uchun ruxsat berilmagan.")

@dp.message(F.text == "📢 Xabar yuborish (Broadcast)")
async def broadcast_prompt(message: Message, state: FSMContext):
    if str(message.from_user.id) == str(ADMIN_ID):
        await state.set_state(AdminStates.waiting_for_broadcast_text)
        await message.answer("Barchaga yubormoqchi bo'lgan xabaringizni matn yoki rasm ko'rinishida yuboring:")

@dp.message(AdminStates.waiting_for_broadcast_text)
async def send_broadcast(message: Message, state: FSMContext):
    if str(message.from_user.id) == str(ADMIN_ID):
        await message.answer("✅ Xabaringiz qabul qilindi va barchaga yuborish uchun tayyorlandi!")
        await state.clear()

@dp.message(F.text == "⬅️ Bosh menyuga qaytish")
async def back_to_main_user(message: Message):
    await message.answer("Bosh menyuga qaytdingiz:", reply_markup=main_keyboard)

# --------------------------------------------------------

@dp.message(F.text == "📚 Lug'at (Wortschatz)")
async def dictionary_handler(message: Message) -> None:
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

if __name__ == "__main__":
    asyncio.run(main())
