import os
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

BACKEND_URL = os.getenv("BACKEND_URL", "https://testify-backend-l4um.onrender.com")
BOT_SECRET = os.getenv("BOT_SECRET", "")


class VerifyStates(StatesGroup):
    waiting_code = State()


@router.message(Command("verify"))
@router.message(F.text == "✅ Akkauntni tasdiqlash")
async def verify_start(msg: Message, state: FSMContext):
    await state.set_state(VerifyStates.waiting_code)
    await msg.answer(
        "🔐 <b>Akkauntni tasdiqlash</b>\n\n"
        "Testify saytida ro'yxatdan o'tgandan so'ng sizga <b>6 xonali kod</b> berilgan.\n\n"
        "📝 Shu kodni yuboring:\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML"
    )


@router.message(VerifyStates.waiting_code)
async def verify_code(msg: Message, state: FSMContext):
    code = msg.text.strip() if msg.text else ""

    if not code.isdigit() or len(code) != 6:
        await msg.answer(
            "❌ Kod noto'g'ri! 6 ta raqamdan iborat bo'lishi kerak.\n\nQaytadan kiriting:"
        )
        return

    await state.clear()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/bot/verify",
                json={
                    "telegramId": msg.from_user.id,
                    "verifyCode": code,
                    "secret": BOT_SECRET,
                }
            ) as resp:
                data = await resp.json()

                if resp.status == 200 and data.get("ok"):
                    await msg.answer(
                        f"✅ <b>Akkaunt muvaffaqiyatli tasdiqlandi!</b>\n\n"
                        f"👤 Ism: <b>{data['teacherName']}</b>\n"
                        f"🆔 Teacher ID: <code>{data['teacherId']}</code>\n"
                        f"🔑 Login: <code>{data['login']}</code>\n"
                        f"📦 Tarif: <b>{data['currentTariff']}</b>\n\n"
                        f"🌐 Saytga kiring: testifyuz.online\n\n"
                        f"Endi /meninfo buyrug'i orqali ma'lumotlaringizni ko'rishingiz mumkin!",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
                        ])
                    )
                elif data.get("alreadyLinked"):
                    await msg.answer(
                        f"⚠️ Bu Telegram akkaunt allaqachon <b>{data.get('teacherName', '')}</b> ga bog'langan!\n\n"
                        f"Agar bu siz bo'lmasangiz, adminga murojaat qiling.",
                        parse_mode="HTML"
                    )
                elif "muddati" in data.get("error", ""):
                    await msg.answer(
                        "⏰ <b>Kodning muddati o'tgan!</b>\n\n"
                        "Saytda qayta ro'yxatdan o'ting yoki yangi kod oling.",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🌐 Saytga o'tish", url="https://testifyuz.online")]
                        ])
                    )
                else:
                    await msg.answer(
                        f"❌ <b>Xato:</b> {data.get('error', 'Noma'lumxato')}\n\n"
                        f"Kodni to'g'ri kiritganingizni tekshiring.",
                        parse_mode="HTML"
                    )
    except Exception as e:
        await msg.answer(
            "😔 Serverga ulanishda xato. Keyinroq urinib ko'ring.",
        )
