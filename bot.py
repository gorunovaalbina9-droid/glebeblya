import asyncio
from collections import defaultdict
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand
from dotenv import load_dotenv
import os

# Токен берётся из .env (файл не попадает в git)
load_dotenv(Path(__file__).resolve().parent / ".env")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Создай файл .env и запиши в него: BOT_TOKEN=твой_токен")

# Хранилище: для каждого чата – список ID сообщений с медиа
# { chat_id: [message_id1, message_id2, ...] }
media_storage: dict[int, list[int]] = defaultdict(list)

# Отдельное хранилище только для фотографий
photo_storage: dict[int, list[int]] = defaultdict(list)

router = Router()
dp = Dispatcher()
dp.include_router(router)


@router.message(
    F.content_type.in_(
        {
            "photo",
            "video",
            "document",
            "audio",
            "voice",
            "video_note",
            "animation",
        }
    )
)
async def save_media(message: Message) -> None:
    chat_id = message.chat.id
    media_storage[chat_id].append(message.message_id)

    # Если это фотография — сохраняем отдельно в список фотографий
    if message.photo:
        photo_storage[chat_id].append(message.message_id)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот, который запоминает медиа в чатах.\n"
        "Добавь меня в группу, отключи режим приватности (privacy) у бота в BotFather,\n"
        "отправь в чат медиа и напиши /resend_media — я перешлю все сохранённые медиа.\n\n"
        "Команды:\n"
        "/resend_media - переслать все сохранённые медиа\n"
        "/resend_photos - переслать только сохранённые фотографии\n"
        "/clear_media - очистить список сохранённых медиа для этого чата\n"
        "/help - показать это меню"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Показывает меню доступных команд.
    """
    await message.answer(
        "Меню команд бота:\n"
        "/start - информация о боте\n"
        "/resend_media - переслать все сохранённые медиа\n"
        "/resend_photos - переслать только сохранённые фотографии\n"
        "/clear_media - очистить список сохранённых медиа для этого чата\n"
    )


@router.message(Command("resend_media"))
async def cmd_resend_media(message: Message, bot: Bot) -> None:
    chat_id = message.chat.id
    messages_ids = media_storage.get(chat_id, [])

    if not messages_ids:
        await message.answer("В этом чате пока нет сохранённых медиасообщений.")
        return

    await message.answer(
        f"Пересылаю {len(messages_ids)} медиасообщений, это может занять некоторое время..."
    )

    for msg_id in messages_ids:
        try:
            await bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Не удалось переслать сообщение {msg_id}: {e}")

    await message.answer("Готово! Все сохранённые медиа пересланы.")


@router.message(Command("resend_photos"))
async def cmd_resend_photos(message: Message, bot: Bot) -> None:
    """
    Пересылает только сохранённые фотографии для этого чата.
    """
    chat_id = message.chat.id
    photo_ids = photo_storage.get(chat_id, [])

    if not photo_ids:
        await message.answer("В этом чате пока нет сохранённых фотографий.")
        return

    await message.answer(
        f"Пересылаю {len(photo_ids)} фотографий, это может занять некоторое время..."
    )

    for msg_id in photo_ids:
        try:
            await bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Не удалось переслать фото {msg_id}: {e}")

    await message.answer("Готово! Все сохранённые фотографии пересланы.")


@router.message(Command("clear_media"))
async def cmd_clear_media(message: Message) -> None:
    chat_id = message.chat.id
    count = len(media_storage.get(chat_id, []))
    media_storage[chat_id].clear()
    await message.answer(f"Очистил список медиа для этого чата (удалено {count}).")


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    # Настраиваем список команд, который будет виден в меню Telegram
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Информация о боте"),
            BotCommand(command="help", description="Показать меню команд"),
            BotCommand(command="resend_media", description="Переслать все сохранённые медиа"),
            BotCommand(command="resend_photos", description="Переслать только сохранённые фото"),
            BotCommand(command="clear_media", description="Очистить сохранённые медиа в чате"),
        ]
    )
    print("Бот запускается. Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
