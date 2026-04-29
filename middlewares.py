from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Any, Callable, Awaitable
from database import add_user, get_channels, is_admin
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def check_subscription(bot, user_id: int) -> tuple[bool, list]:
    channels = await get_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return len(not_joined) == 0, not_joined


def sub_keyboard(not_joined: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in not_joined:
        name = ch.get("name") or "Kanal"
        cid = ch["id"]
        if str(cid).startswith("-100"):
            link = f"https://t.me/c/{str(cid)[4:]}"
        elif str(cid).startswith("@"):
            link = f"https://t.me/{str(cid)[1:]}"
        else:
            link = f"https://t.me/{cid}"
        buttons.append([InlineKeyboardButton(text=f"📢 {name}", url=link)])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


class RegisterMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Any, data: dict) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            await add_user(
                user_id=user.id,
                username=user.username or "",
                full_name=user.full_name or ""
            )
        return await handler(event, data)
