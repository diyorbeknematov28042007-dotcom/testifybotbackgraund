import os
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_tariffs, get_tariff, get_setting,
    create_payment, set_payment_group_msg,
    get_payment, approve_payment, reject_payment
)
from middlewares import check_subscription, sub_keyboard

router = Router()

PAYMENT_GROUP = os.getenv("PAYMENT_GROUP_ID")
BACKEND_URL = os.getenv("BACKEND_URL", "https://testify-backend-l4um.onrender.com")
BOT_SECRET = os.getenv("BOT_SECRET", "")


class PaymentStates(StatesGroup):
    choosing_tariff = State()
    entering_id = State()
    uploading_receipt = State()
    rejecting = State()


def format_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


@router.message(Command("payment"))
@router.message(F.text == "💳 Limit olish")
async def payment_start(msg: Message, state: FSMContext):
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)
    if not subscribed:
        await msg.answer("⚠️ Avval kanallarga obuna bo'ling:", reply_markup=sub_keyboard(not_joined))
        return

    tariffs = await get_tariffs()
    if not tariffs:
        await msg.answer("😔 Hozircha tariflar mavjud emas. Keyinroq urinib ko'ring.")
        return

    text = "💳 <b>Limit sotib olish</b>\n\nMavjud tariflar:\n\n"
    buttons = []
    for t in tariffs:
        text += (
            f"📦 <b>{t['name']}</b>\n"
            f"   {t['description']}\n"
            f"   +{t['public_limit']} ommaviy / +{t['private_limit']} shaxsiy test\n"
            f"   💰 <b>{format_price(t['price'])} so'm</b>\n\n"
        )
        buttons.append([InlineKeyboardButton(
            text=f"{t['name']} — {format_price(t['price'])} so'm",
            callback_data=f"buy_tariff:{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="payment_cancel")])

    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await state.set_state(PaymentStates.choosing_tariff)


@router.callback_query(F.data.startswith("buy_tariff:"))
async def tariff_selected(call: CallbackQuery, state: FSMContext):
    tariff_id = int(call.data.split(":")[1])
    tariff = await get_tariff(tariff_id)
    if not tariff:
        await call.answer("Tarif topilmadi!", show_alert=True)
        return

    await state.update_data(tariff_id=tariff_id, tariff=tariff)
    await state.set_state(PaymentStates.entering_id)

    await call.message.edit_text(
        f"✅ <b>{tariff['name']}</b> tarifi tanlandi\n\n"
        f"📝 Endi saytdagi <b>8 xonali Teacher ID</b> ingizni kiriting:\n\n"
        f"<i>ID ni testifyuz.online/teacher/dashboard sahifasida topasiz</i>\n\n"
        f"/cancel — bekor qilish",
        parse_mode="HTML",
        reply_markup=None
    )
    await call.answer()


@router.message(PaymentStates.entering_id)
async def teacher_id_entered(msg: Message, state: FSMContext):
    teacher_id = msg.text.strip()

    if not teacher_id.isdigit() or len(teacher_id) != 8:
        await msg.answer("❌ ID noto'g'ri! 8 ta raqamdan iborat bo'lishi kerak.\n\nQaytadan kiriting:")
        return

    data = await state.get_data()
    tariff = data["tariff"]
    card = await get_setting("payment_card", "0000000000000000")
    card_owner = await get_setting("payment_card_owner", "Testify")

    await state.update_data(teacher_id=teacher_id)
    await state.set_state(PaymentStates.uploading_receipt)

    await msg.answer(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📦 Tarif: <b>{tariff['name']}</b>\n"
        f"💰 Summa: <b>{format_price(tariff['price'])} so'm</b>\n"
        f"🆔 Teacher ID: <code>{teacher_id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 Karta raqami:\n"
        f"<code>{card}</code>\n"
        f"👤 Egasi: <b>{card_owner}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ Yuqoridagi kartaga <b>{format_price(tariff['price'])} so'm</b> o'tkazing\n"
        f"2️⃣ To'lov chekining <b>skrinshot</b>ini yuboring\n\n"
        f"/cancel — bekor qilish",
        parse_mode="HTML"
    )


@router.message(PaymentStates.uploading_receipt, F.photo)
async def receipt_uploaded(msg: Message, state: FSMContext):
    data = await state.get_data()
    tariff = data["tariff"]
    teacher_id = data["teacher_id"]

    payment_id = await create_payment(
        user_id=msg.from_user.id,
        username=msg.from_user.username or "",
        teacher_id=teacher_id,
        tariff_id=tariff["id"],
        tariff_name=tariff["name"],
        amount=tariff["price"]
    )

    await state.clear()

    username_text = f"@{msg.from_user.username}" if msg.from_user.username else f"ID: {msg.from_user.id}"

    group_text = (
        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {username_text}\n"
        f"🆔 Teacher ID: <code>{teacher_id}</code>\n"
        f"📦 Tarif: <b>{tariff['name']}</b>\n"
        f"💰 Summa: <b>{format_price(tariff['price'])} so'm</b>\n"
        f"⏰ Vaqt: {msg.date.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔢 To'lov ID: <code>{payment_id}</code>"
    )

    group_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul", callback_data=f"pay_approve:{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject:{payment_id}")
        ]
    ])

    try:
        group_msg = await msg.bot.send_photo(
            chat_id=PAYMENT_GROUP,
            photo=msg.photo[-1].file_id,
            caption=group_text,
            reply_markup=group_keyboard,
            parse_mode="HTML"
        )
        await set_payment_group_msg(payment_id, group_msg.message_id)
    except Exception as e:
        pass

    await msg.answer(
        f"✅ <b>So'rovingiz yuborildi!</b>\n\n"
        f"🔢 So'rov raqami: <code>{payment_id}</code>\n\n"
        f"Admin tekshirib, tez orada natija yuboriladi.\n"
        f"Odatda 5-30 daqiqa ichida ko'rib chiqiladi.",
        parse_mode="HTML"
    )


@router.message(PaymentStates.uploading_receipt)
async def receipt_not_photo(msg: Message):
    await msg.answer("📸 Iltimos, to'lov chekining <b>rasmini</b> yuboring!", parse_mode="HTML")


@router.callback_query(F.data.startswith("pay_approve:"))
async def approve_handler(call: CallbackQuery):
    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)

    if not payment:
        await call.answer("To'lov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    tariff = await get_tariff(payment["tariff_id"])
    if not tariff:
        await call.answer("Tarif topilmadi!", show_alert=True)
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/bot/add-limit",
                json={
                    "teacherId": payment["teacher_id"],
                    "publicLimit": tariff["public_limit"],
                    "privateLimit": tariff["private_limit"],
                    "secret": BOT_SECRET
                }
            ) as resp:
                if resp.status != 200:
                    await call.answer("Backend xatosi! Qaytadan urinib ko'ring.", show_alert=True)
                    return
    except Exception as e:
        await call.answer(f"Ulanish xatosi: {e}", show_alert=True)
        return

    await approve_payment(payment_id)

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n✅ <b>QABUL QILINDI</b>",
        reply_markup=None,
        parse_mode="HTML"
    )

    try:
        await call.bot.send_message(
            chat_id=payment["user_id"],
            text=f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                 f"📦 Tarif: <b>{payment['tariff_name']}</b>\n"
                 f"➕ +{tariff['public_limit']} ommaviy test\n"
                 f"➕ +{tariff['private_limit']} shaxsiy test\n\n"
                 f"Limitlar hisobingizga qo'shildi! 🎉",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer("✅ Qabul qilindi va limit qo'shildi!")


@router.callback_query(F.data.startswith("pay_reject:"))
async def reject_start(call: CallbackQuery, state: FSMContext):
    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)

    if not payment:
        await call.answer("To'lov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await state.set_state(PaymentStates.rejecting)
    await state.update_data(payment_id=payment_id, chat_id=call.message.chat.id, msg_id=call.message.message_id)
    await call.message.reply("❌ Rad etish sababini yozing:")
    await call.answer()


@router.message(PaymentStates.rejecting)
async def reject_reason(msg: Message, state: FSMContext):
    data = await state.get_data()
    payment_id = data["payment_id"]
    payment = await get_payment(payment_id)
    reason = msg.text.strip()

    await reject_payment(payment_id, reason)
    await state.clear()

    try:
        original = await msg.bot.edit_message_caption(
            chat_id=data["chat_id"],
            message_id=data["msg_id"],
            caption=(await msg.bot.get_message(data["chat_id"], data["msg_id"])).caption +
                    f"\n\n❌ <b>RAD ETILDI</b>\n📝 Sabab: {reason}",
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await msg.bot.send_message(
            chat_id=payment["user_id"],
            text=f"❌ <b>To'lovingiz rad etildi</b>\n\n"
                 f"📝 Sabab: {reason}\n\n"
                 f"Savol bo'lsa /payment orqali qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await msg.answer("❌ Rad etildi va foydalanuvchiga xabar yuborildi.")


@router.callback_query(F.data == "payment_cancel")
async def payment_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()


@router.message(Command("cancel"))
async def cancel_payment(msg: Message, state: FSMContext):
    current = await state.get_state()
    if current and "PaymentStates" in str(current):
        await state.clear()
        await msg.answer("❌ Bekor qilindi.")
