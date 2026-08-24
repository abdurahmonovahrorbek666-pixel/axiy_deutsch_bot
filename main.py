import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8912605806:AAEshu0Br0OVKsT1QXSg43Yy9NBJzOzW2Z8"

bot = Bot(token=TOKEN)
dp = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Lug'at (Wortschatz)"), KeyboardButton(text="📝 Testlar")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        f"Hallo, {html.bold(message.from_user.full_name)}!\n\nNemis tili botiga xush kelibsiz! Bo'limni tanlang:",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "📚 Lug'at (Wortschatz)")
async def dictionary_handler(message: Message) -> None:
    await message.answer("📌 **A1-B1 Lug'at bo'limi:**\n\n- Guten Tag — Xayrli kun\n- Auf Wiedersehen — Xayr\n- Danke — Rahmat\n- Wie geht's? — Ishlar qanday?")

@dp.message(F.text == "📝 Testlar")
async def test_handler(message: Message) -> None:
    await message.answer("🧠 Testlar bo'limi tez orada ishga tushadi!")

@dp.message(F.text == "ℹ️ Bot haqida")
async def about_handler(message: Message) -> None:
    await message.answer("Ushbu bot Nemis tilini o'rganuvchilar uchun maxsus yaratilgan.")

async def handle_web(request):
    return web.Response(text="Bot active")

async def main():
    # Web server yaratish
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    # Bir vaqtda ham portni tinglash, ham pollingni ishlatish
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if name == "__main__":
    asyncio.run(main())
