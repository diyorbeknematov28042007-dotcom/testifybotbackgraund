import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from database import get_setting, get_channels
from middlewares import check_subscription, sub_keyboard

router = Router()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🌐 Test Platformasi"),
                KeyboardButton(text="💳 Limit olish"),
            ],
            [
                KeyboardButton(text="📞 Yordam"),
                KeyboardButton(text="ℹ️ Haqimizda"),
            ],
        ],
        resize_keyboard=True,
        persistent=True
    )


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
    await bot.send_message(
        chat_id,
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


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

    await msg.answer(
        "👇 Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_keyboard()
    )


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    subscribed, not_joined = await check_subscription(call.bot, call.from_user.id)

    if not subscribed:
        await call.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=sub_keyboard(not_joined))
        return

    await call.message.delete()
    await send_welcome(call.bot, call.message.chat.id)
    await call.bot.send_message(
        call.message.chat.id,
        "👇 Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_keyboard()
    )
    await call.answer("✅ Obuna tasdiqlandi!")


@router.message(F.text == "🌐 Test Platformasi")
async def test_platform(msg: Message):
    await msg.answer(
        "🌐 <b>Test Platformasi</b>\n\n"
        "Testify — o'qituvchilar uchun test yaratish va talabalar uchun ishlash platformasi.\n\n"
        "👇 Saytga kirish uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
        ]),
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Yordam")
async def support_handler(msg: Message):
    support = await get_setting("support_username", "@testifyN3_bot")
    await msg.answer(
        "📞 <b>Yordam</b>\n\n"
        "Savol yoki muammolaringiz bo'lsa, quyidagi manzilga murojaat qiling:\n\n"
        f"👤 {support}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Adminga yozish", url=f"https://t.me/{support.lstrip('@')}")]
        ]),
        parse_mode="HTML"
    )


@router.message(F.text == "ℹ️ Haqimizda")
async def about_handler(msg: Message):
    await msg.answer(
        "ℹ️ <b>Testify haqida</b>\n\n"
        "📚 O'zbek ta'limining zamonaviy platformasi\n\n"
        "✅ O'qituvchilar uchun:\n"
        "— Test yaratish (DTM va oddiy)\n"
        "— Natijalarni real vaqtda kuzatish\n"
        "— DOCX formatida yuklab olish\n\n"
        "✅ Talabalar uchun:\n"
        "— Kod orqali test ishlash\n"
        "— Natijani darhol ko'rish\n\n"
        "🌐 testifyuz.online",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
        ]),
        parse_mode="HTML"
    )
