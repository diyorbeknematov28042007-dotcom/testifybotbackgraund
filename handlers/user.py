import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from database import get_setting, get_channels
from middlewares import check_subscription, sub_keyboard

router = Router()


def parse_buttons(buttons_json: str) -> InlineKeyboardMarkup | None:
    try:
        buttons_data = json.loads(buttons_json)
        if not buttons_data:
            return None
        keyboard = []
        for row in buttons_data:
            if isinstance(row, list):
                keyboard.append([InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row])
            elif isinstance(row, dict):
                keyboard.append([InlineKeyboardButton(text=row["text"], url=row["url"])])
        return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    except Exception:
        return None


@router.message(CommandStart())
async def start_handler(msg: Message):
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)

    if not subscribed:
        await msg.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    welcome_text = await get_setting("welcome_text", "Botga xush kelibsiz! 🎉")
    buttons_json = await get_setting("welcome_buttons", "[]")
    keyboard = parse_buttons(buttons_json)

    await msg.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    subscribed, not_joined = await check_subscription(call.bot, call.from_user.id)

    if not subscribed:
        await call.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=sub_keyboard(not_joined))
        return

    await call.message.delete()

    welcome_text = await get_setting("welcome_text", "Botga xush kelibsiz! 🎉")
    buttons_json = await get_setting("welcome_buttons", "[]")
    keyboard = parse_buttons(buttons_json)

    await call.message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer("✅ Obuna tasdiqlandi!")
