import os
import json
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from database import get_setting, get_channels
from middlewares import check_subscription, sub_keyboard

router = Router()

BACKEND_URL = os.getenv("BACKEND_URL", "https://testify-backend-l4um.onrender.com")
BOT_SECRET = os.getenv("BOT_SECRET", "")


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Test Platformasi"), KeyboardButton(text="💳 Limit olish")],
            [KeyboardButton(text="👤 Men haqimda"), KeyboardButton(text="🎟 Promokodlarim")],
            [KeyboardButton(text="✅ Akkauntni tasdiqlash"), KeyboardButton(text="📞 Yordam")],
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
    await bot.send_message(chat_id, welcome_text, reply_markup=keyboard, parse_mode="HTML")


async def get_teacher_info(telegram_id: int) -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/bot/teacher-info",
                json={"telegramId": telegram_id, "secret": BOT_SECRET}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
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

    await send_welcome(msg.bot, msg.chat.id)
    await msg.answer("👇 Quyidagi bo'limlardan birini tanlang:", reply_markup=main_keyboard())


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    subscribed, not_joined = await check_subscription(call.bot, call.from_user.id)
    if not subscribed:
        await call.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=sub_keyboard(not_joined))
        return
    await call.message.delete()
    await send_welcome(call.bot, call.message.chat.id)
    await call.bot.send_message(call.message.chat.id, "👇 Bo'limlardan birini tanlang:", reply_markup=main_keyboard())
    await call.answer("✅ Obuna tasdiqlandi!")


# ── TEST PLATFORMASI ──
@router.message(F.text == "🌐 Test Platformasi")
async def test_platform(msg: Message):
    await msg.answer(
        "🌐 <b>Test Platformasi</b>\n\n"
        "Testify — o'qituvchilar uchun test yaratish va talabalar uchun ishlash platformasi.\n\n"
        "👇 Saytga kirish uchun quyidagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
        ])
    )


# ── MEN HAQIMDA ──
@router.message(F.text == "👤 Men haqimda")
@router.message(Command("meninfo"))
async def my_info(msg: Message):
    info = await get_teacher_info(msg.from_user.id)

    if not info or not info.get("ok"):
        await msg.answer(
            "❌ <b>Sayt akkauntingiz topilmadi</b>\n\n"
            "Testify saytida ro'yxatdan o'ting va botda tasdiqlang:\n\n"
            "1️⃣ testifyuz.online ga o'ting\n"
            "2️⃣ Ro'yxatdan o'ting\n"
            "3️⃣ Berилган 6 raqamli kodni botga yuboring\n\n"
            "Yoki '✅ Akkauntni tasdiqlash' tugmasini bosing",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
            ])
        )
        return

    tariff_emoji = {
        'Testify Ufq': '🌅',
        'Testify Nihol': '🌱',
        'Testify Cho\'qqi': '🏔',
        'Testify Dargoh': '🏛',
        'Testify Samo': '🌌',
    }.get(info.get('currentTariff', ''), '📦')

    await msg.answer(
        f"👤 <b>Sizning ma'lumotlaringiz</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 Ism: <b>{info['name']}</b>\n"
        f"🆔 Teacher ID: <code>{info['teacherId']}</code>\n"
        f"🔑 Login: <code>{info['login']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{tariff_emoji} Tarif: <b>{info['currentTariff']}</b>\n"
        f"📢 Ommaviy limit: <b>{info['publicTestLimit']} ta</b>\n"
        f"🔒 Shaxsiy limit: <b>{info['privateTestLimit']} ta</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Holat: <b>Tasdiqlangan</b>\n",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online/teacher/dashboard")]
        ])
    )


# ── PROMOKODLARIM ──
@router.message(F.text == "🎟 Promokodlarim")
@router.message(Command("promo"))
async def my_promo(msg: Message):
    info = await get_teacher_info(msg.from_user.id)

    if not info or not info.get("ok"):
        await msg.answer(
            "❌ Sayt akkauntingiz topilmadi.\n\n"
            "Avval '✅ Akkauntni tasdiqlash' tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    promo = info.get("promo")

    if not promo:
        await msg.answer(
            "🎟 <b>Promokodlarim</b>\n\n"
            "Sizda hali promokod yo'q.\n\n"
            "Promokod yaratish uchun saytga o'ting:\n"
            "Dashboard → Promokod tugmasi",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Promokod yaratish", url="https://testifyuz.online/teacher/dashboard")]
            ])
        )
        return

    await msg.answer(
        f"🎟 <b>Promokodlarim</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Kod: <code>{promo['code']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Ishlatildi: <b>{promo['usageCount']} marta</b>\n"
        f"📢 Ommaviy limit ishlandi: <b>+{promo['publicLimitEarned']} ta</b>\n"
        f"🔒 Shaxsiy limit ishlandi: <b>+{promo['privateLimitEarned']} ta</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Promokodingizni tarqating!\n"
        f"Kimdir ishlatsa sizga <b>+1 ommaviy +1 shaxsiy</b> test beriladi!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Kodni nusxalash", callback_data=f"copy_promo:{promo['code']}")]
        ])
    )


@router.callback_query(F.data.startswith("copy_promo:"))
async def copy_promo(call: CallbackQuery):
    code = call.data.split(":")[1]
    await call.answer(f"Kod: {code} — Nusxalab oling!", show_alert=True)


# ── YORDAM ──
@router.message(F.text == "📞 Yordam")
async def support_handler(msg: Message):
    support = await get_setting("support_username", "@testifyN3_bot")
    await msg.answer(
        "📞 <b>Yordam</b>\n\n"
        "Savol yoki muammolaringiz uchun:\n\n"
        f"👤 {support}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Adminga yozish", url=f"https://t.me/{support.lstrip('@')}")]
        ])
    )


# ── HAQIMIZDA ──
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
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
        ])
    )
