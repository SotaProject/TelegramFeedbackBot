import logging

from sqlalchemy.sql import insert, select, and_, update
from sqlalchemy.exc import NoResultFound
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter
from aiogram.types.message import ContentType
from aiogram.dispatcher import filters
from aiogram.utils import exceptions
import datetime

import asyncio

from db_utils import session_scope, prepare_db
from config import (
    LOGGING_LEVEL,
    TOKEN,
    COMMANDS,
    FEEDBACK_CHAT,
)
import models
import re

bot = Bot(TOKEN, parse_mode="html")
dp = Dispatcher(bot)

logging.basicConfig(level=LOGGING_LEVEL.upper())


class IsPrivate(BoundFilter):
    async def check(self, message: types.Message):
        return message.from_user and message.chat.type == types.ChatType.PRIVATE


def get_user_title(user) -> str:
    return (
        f'{user.first_name + " " if user.first_name else ""} '
        f'{user.last_name + " " if user.last_name else ""} '
        f'[{user.id}] {" @" + user.username if user.username else ""}'
    )


async def get_message_origin(chat_id: int, message_id: int) -> (int, int):
    async with session_scope() as session:
        q = select(
            models.FeedbackMessage.from_chat_id, models.FeedbackMessage.from_message_id
        ).where(
            and_(
                models.FeedbackMessage.to_chat_id == chat_id,
                models.FeedbackMessage.to_message_id == message_id,
            )
        )
        r = (await session.execute(q)).one()
        return r


async def add_user_to_db_if_not_exists(message: types.Message):
    if message.chat.id == FEEDBACK_CHAT:
        return

    async with session_scope() as session:
        q = (
            select(models.User.tid)
            .where(models.User.tid == message.from_user.id)
            .limit(1)
        )
        r = (await session.execute(q)).one_or_none()
        if not r:
            await session.execute(
                insert(models.User).values(
                    tid=message.from_user.id,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    username=message.from_user.username
                    if message.from_user.username
                    else "",
                    date=datetime.datetime.now(),
                )
            )


@dp.edited_message_handler(
    chat_id=FEEDBACK_CHAT,
    content_types=[
        types.ContentType.TEXT,
        types.ContentType.PHOTO,
        types.ContentType.VIDEO,
        types.ContentType.DOCUMENT,
        types.ContentType.AUDIO,
    ],
)
async def handle_edited_message(message: types.Message):
    async with session_scope() as session:
        q = select(
            models.FeedbackMessage.to_chat_id, models.FeedbackMessage.to_message_id
        ).where(
            and_(
                models.FeedbackMessage.from_chat_id == message.chat.id,
                models.FeedbackMessage.from_message_id == message.message_id,
            )
        )
        to_msg = (await session.execute(q)).one_or_none()

        if not to_msg:
            return

        if message.content_type == types.ContentType.TEXT:
            await bot.edit_message_text(
                chat_id=to_msg.to_chat_id,
                message_id=to_msg.to_message_id,
                text=message.text,
                entities=message.entities,
            )

        else:
            await bot.edit_message_caption(
                chat_id=to_msg.to_chat_id,
                message_id=to_msg.to_message_id,
                caption=message.caption,
                caption_entities=message.caption_entities,
            )


@dp.message_handler(
    filters.RegexpCommandsFilter(regexp_commands=["unban ([0-9]*)"]),
    chat_id=FEEDBACK_CHAT,
    is_chat_admin=FEEDBACK_CHAT,
)
async def unban(message: types.Message, regexp_command):
    user_id = int(regexp_command.group(1))
    async with session_scope() as session:
        await session.execute(
            update(models.User).values(ban=False).where(models.User.tid == user_id)
        )
    await message.reply(f"Я разбанил {user_id}")


@dp.message_handler(
    lambda msg: msg.reply_to_message,
    commands=["unban"],
    chat_id=FEEDBACK_CHAT,
    is_chat_admin=FEEDBACK_CHAT,
)
async def unban_by_reply(message: types.Message):
    try:
        chat_id, _ = await get_message_origin(
            message.chat.id, message.reply_to_message.message_id
        )
    except NoResultFound:
        return
    async with session_scope() as session:
        await session.execute(
            update(models.User).values(ban=False).where(models.User.tid == chat_id)
        )
        await message.reply(f"Я разбанил {chat_id}")


@dp.message_handler(
    filters.RegexpCommandsFilter(regexp_commands=["ban ([0-9]*)"]),
    chat_id=FEEDBACK_CHAT,
    is_chat_admin=FEEDBACK_CHAT,
)
async def ban_by_id(message: types.Message, regexp_command):
    user_id = int(regexp_command.group(1))
    async with session_scope() as session:
        await session.execute(
            update(models.User).values(ban=True).where(models.User.tid == user_id)
        )
        await message.reply(f"Я забанил {user_id}, для разбана исплользуйте /unban")


@dp.message_handler(
    lambda msg: msg.reply_to_message,
    commands=["ban"],
    chat_id=FEEDBACK_CHAT,
    is_chat_admin=FEEDBACK_CHAT,
)
async def ban_by_reply(message: types.Message):
    try:
        chat_id, _ = await get_message_origin(
            message.chat.id, message.reply_to_message.message_id
        )
    except NoResultFound:
        return
    async with session_scope() as session:
        await session.execute(
            update(models.User).values(ban=True).where(models.User.tid == chat_id)
        )
        await message.reply(f"Я забанил {chat_id}, для разбана исплользуйте /unban")


@dp.message_handler(commands="chat_id")
async def cmd_chat_id(message: types.Message):
    await message.reply(message.chat.id)


@dp.message_handler(
    lambda msg: msg.reply_to_message, commands=["id", "get_id"], chat_id=FEEDBACK_CHAT
)
async def get_id(message: types.Message):
    try:
        chat_id, _ = await get_message_origin(
            message.chat.id, message.reply_to_message.message_id
        )
    except NoResultFound:
        return
    await message.answer(chat_id)


async def send_copy_message(user_id: int, message: types.Message) -> bool:
    """
    Safe messages sender
    :param user_id:
    :param message:
    :return:
    """

    try:
        await message.send_copy(user_id)
    except exceptions.BotBlocked:
        logging.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        logging.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logging.error(
            f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds."
        )
        await asyncio.sleep(e.timeout)
        return await send_copy_message(user_id, message)  # Recursive call
    except exceptions.UserDeactivated:
        logging.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return True
    return False


@dp.message_handler(
    lambda msg: msg.reply_to_message,
    chat_id=FEEDBACK_CHAT,
    commands=["broadcast"],
    is_chat_admin=FEEDBACK_CHAT,
)
async def broadcast_message(message: types.Message):
    reply_msg = await message.answer("Начинаю рассылку")
    async with session_scope() as session:
        q = select(models.User.tid)
        users = (await session.execute(q)).all()
        for i, user in enumerate(users):
            try:
                await reply_msg.edit_text(f"Рассылка {i + 1}/{len(users)}")
            except exceptions.RetryAfter as e:
                logging.error(f"edit_text: Flood limit")
            await send_copy_message(user[0], message.reply_to_message)
            await asyncio.sleep(0.1)


@dp.message_handler(
    lambda msg: msg.text[0] != "/" if msg.text else True,
    chat_id=FEEDBACK_CHAT,
    content_types=(
        ContentType.TEXT,
        ContentType.DOCUMENT,
        ContentType.STICKER,
        ContentType.PHOTO,
        ContentType.VOICE,
        ContentType.VIDEO,
        ContentType.VIDEO_NOTE,
        ContentType.AUDIO,
    ),
)
async def feedback_answer(message: types.Message):
    if not message.reply_to_message:
        return
    async with session_scope() as session:
        q = select(
            models.FeedbackMessage.from_chat_id, models.FeedbackMessage.from_message_id
        ).where(
            and_(
                models.FeedbackMessage.to_chat_id == message.chat.id,
                models.FeedbackMessage.to_message_id
                == message.reply_to_message.message_id,
            )
        )
        r = (await session.execute(q)).one_or_none()
        if not r:
            return
        copy = await message.send_copy(chat_id=r[0], reply_to_message_id=r[1])
        await session.execute(
            insert(models.FeedbackMessage).values(
                from_chat_id=message.chat.id,
                from_message_id=message.message_id,
                to_chat_id=copy.chat.id,
                to_message_id=copy.message_id,
                type="response",
            )
        )


@dp.message_handler(
    lambda msg: msg.text[0] != "/" if msg.text else True,
    content_types=(
        ContentType.TEXT,
        ContentType.DOCUMENT,
        ContentType.STICKER,
        ContentType.PHOTO,
        ContentType.VOICE,
        ContentType.VIDEO,
        ContentType.VIDEO_NOTE,
        ContentType.AUDIO,
    ),
)
async def feedback_request(message: types.Message):
    await add_user_to_db_if_not_exists(message)

    async with session_scope() as session:
        user = message.from_user

        q = select(models.User.ban).where(models.User.tid == user.id)
        user_is_banned = (await session.execute(q)).one_or_none().ban

        logging.info(
            f'{message.from_user.id}{"-BANNED" if user_is_banned else ""}:{message.text}'
        )

        if user_is_banned:
            return

        r = None
        if message.reply_to_message:
            q = select(
                models.FeedbackMessage.from_chat_id,
                models.FeedbackMessage.from_message_id,
            ).where(
                and_(
                    models.FeedbackMessage.to_chat_id == message.chat.id,
                    models.FeedbackMessage.to_message_id
                    == message.reply_to_message.message_id,
                )
            )
            r = (await session.execute(q)).one_or_none()
        if message.reply_to_message and not r:
            q = select(
                models.FeedbackMessage.to_chat_id, models.FeedbackMessage.to_message_id
            ).where(
                and_(
                    models.FeedbackMessage.from_chat_id == message.chat.id,
                    models.FeedbackMessage.from_message_id
                    == message.reply_to_message.message_id,
                )
            )
            r = (await session.execute(q)).one_or_none()

        await dp.bot.send_message(
            FEEDBACK_CHAT,
            f"Новое сообщение от {get_user_title(message.from_user)}",
            reply_to_message_id=r[1] if r else None,
        )

        forwarded = await message.forward(FEEDBACK_CHAT)
        await session.execute(
            insert(models.FeedbackMessage).values(
                from_chat_id=message.chat.id,
                from_message_id=message.message_id,
                to_chat_id=forwarded.chat.id,
                to_message_id=forwarded.message_id,
                type="request",
            )
        )


@dp.message_handler(
    IsPrivate(), filters.RegexpCommandsFilter(regexp_commands=["^/[a-zA-Z0-9_]+$"])
)
async def handle_command(message: types.Message):
    await add_user_to_db_if_not_exists(message)

    command = message.text[1:]

    if command not in COMMANDS.keys():
        await message.answer("Не известная команда")
        return

    await message.reply(
        COMMANDS[command]["text"],
        disable_web_page_preview=COMMANDS[command].get(
            "disable_web_page_preview", False
        ),
        parse_mode=COMMANDS[command].get("parse_mode", "MARKDOWN"),
    )

    await bot.send_message(
        FEEDBACK_CHAT,
        f"Пользователь отправил команду /{command}\n\n"
        f"{get_user_title(message.from_user)}",
    )


async def set_commands():
    commands = []
    for k, v in COMMANDS.items():
        if v.get("set_command", True):
            commands.append(types.BotCommand(k, v["description"]))
    await dp.bot.set_my_commands(commands)


async def on_startup(_: Dispatcher):
    await prepare_db()
    await set_commands()


if __name__ == "__main__":
    dp.bind_filter(IsPrivate)
    executor.start_polling(dp, on_startup=on_startup)
