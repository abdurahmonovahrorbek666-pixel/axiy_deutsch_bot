import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message

# Tokeningizni qo'shtirnoq ichiga yozing:
TOKEN = "8912605806:AAEshu0BrOOVKsT1QXSg43Yy9NBJzOZw2Z8"

dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(f"Hallo, {html.bold(message.from_user.full_name)}! Nemis tili botiga xush kelibsiz!")

async def main() -> None:
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())
