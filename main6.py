import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus

logging.basicConfig(level=logging.INFO)

TOKEN = "8556280255:AAG60JAZc-6K7aV60btZYHrBPyP9hgsGGtU"
DATA_FILE = "group_users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

group_data = load_data()

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ─── Специфические команды (регистрируем ПЕРВЫМИ) ───

@dp.message(CommandStart())
async def cmd_start(message: Message):
    print("DEBUG: /start сработал")  # для отладки — потом можно убрать
    await message.answer(
        "Привет! Я бот для управления дополнительными никами в группе Psycho Band.\n\n"
        "Команды:\n"
        "• /clan_members — список известных участников и их доп. имен\n"
        "• /add_nick [ник] — присвоить доп. имя\n"
        "• /show_nick — посмотреть доп. имя \n\n"
        
    )


@dp.message(Command("clan_members"))
async def list_members(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Эта команда работает только в группах.")
        return

    chat_id = str(message.chat.id)
    if chat_id not in group_data or not group_data[chat_id]:
        await message.reply("Пока никто не писал в чат после запуска бота.")
        return

    lines = []
    for uid, info in group_data[chat_id].items():
        nick = info.get("nick")
        nick_part = f" → {nick}" if nick else ""
        lines.append(f"@{info['name']} (id: {uid}){nick_part}")

    await message.reply("Известные участники:\n" + "\n".join(lines))


@dp.message(Command("add_nick"))
async def set_nick(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Работает только в группах.")
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.reply("Только администраторы группы могут присваивать ники.")
        return

    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение человека → /add_nick НовыйНик")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Укажите ник после команды, например: /add_nick Котик")
        return

    nick = parts[1].strip()
    target = message.reply_to_message.from_user
    chat_id = str(message.chat.id)
    user_id = str(target.id)

    if chat_id not in group_data:
        group_data[chat_id] = {}

    username = target.username or target.first_name
    group_data[chat_id][user_id] = {"name": username, "nick": nick}
    save_data(group_data)

    await message.reply(f"Доп. ник **{nick}** установлен для @{username}")


@dp.message(Command("show_nick"))
async def get_nick(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Работает только в группах.")
        return

    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение участника.")
        return

    target = message.reply_to_message.from_user
    chat_id = str(message.chat.id)
    user_id = str(target.id)

    if chat_id not in group_data or user_id not in group_data[chat_id]:
        await message.reply("Этот пользователь пока неизвестен боту.")
        return

    nick = group_data[chat_id][user_id].get("nick")
    if not nick:
        await message.reply(f"У @{target.username or target.first_name} нет доп. ника.")
        return

    await message.reply(f"Доп. ник: **{nick}**")


# ─── Общий хендлер для сбора участников (самый последний!) ───

@dp.message()
async def collect_user(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return  # в личке ничего не собираем

    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name

    print(f"[COLLECT] сообщение от {user_id} @{username} в чате {chat_id}")

    if chat_id not in group_data:
        group_data[chat_id] = {}
        print(f"[COLLECT] создан новый чат {chat_id}")

    entry = group_data[chat_id].setdefault(user_id, {"name": username, "nick": None})

    if entry["name"] != username:
        print(f"[COLLECT] обновлено имя: {entry['name']} → {username}")
        entry["name"] = username

    # Принудительное сохранение после каждого
    try:
        save_data(group_data)
        print(f"[COLLECT] данные сохранены в {DATA_FILE}")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить JSON: {e}")


async def main():
    print("=== Бот запущен ===")
    await dp.start_polling(
        bot,
        drop_pending_updates=True,
        allowed_updates=["message"]
    )


if __name__ == "__main__":
    asyncio.run(main())