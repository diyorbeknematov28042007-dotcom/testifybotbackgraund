import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from database import get_setting, get_channels
from middlewares import check_subscription, sub_keyboard

router = Router()


def parse_buttons(buttons_json: str) -> InlineKeyboardMarkup | None:
    try:
        buttons_data = json.loads(buttons_json)
        if not buttons_data:
            return None
        keyboard = []
        row = []
        for btn in buttons_data:
            row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    except Exception:
        return None


async def send_welcome(bot, chat_id: int):
    welcome_text = await get_setting("welcome_text")
    buttons_json = await get_setting("welcome_buttons", "[]")
    keyboard = parse_buttons(buttons_json)
    await bot.send_message(chat_id, welcome_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(CommandStart())
async def start_handler(msg: Message):
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)

    if not subscribed:
        await msg.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    await send_welcome(msg.bot, msg.chat.id)


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    subscribed, not_joined = await check_subscription(call.bot, call.from_user.id)

    if not subscribed:
        await call.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=sub_keyboard(not_joined))
        return

    await call.message.delete()
    await send_welcome(call.bot, call.message.chat.id)
    await call.answer("✅ Obuna tasdiqlandi!")


@router.message(Command("test"))
async def test_handler(msg: Message):
    """Test ishlash — /start dek salomlashuv yuboradi"""
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)

    if not subscribed:
        await msg.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    await send_welcome(msg.bot, msg.chat.id)


@router.message(Command("payment"))
async def payment_handler(msg: Message):
    """To'lov funksiyasi"""
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)

    if not subscribed:
        await msg.answer(
            "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=sub_keyboard(not_joined)
        )
        return

    payment_text = await get_setting("payment_text", "💳 To'lov funksiyasi hali ishga tushmagan.\n\nLimit olish bo'yicha adminga murojaat qiling.")
    payment_admin = await get_setting("payment_admin", "@admin")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Adminga murojaat", url=f"https://t.me/{payment_admin.lstrip('@')}")]
    ])

    await msg.answer(payment_text, reply_markup=keyboard, parse_mode="HTML")
