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
    entering_promo = State()
    uploading_receipt = State()
    rejecting = State()


def fmt(amount): return f"{amount:,}".replace(",", " ")


@router.message(Command("payment"))
@router.message(F.text == "💳 Limit olish")
async def payment_start(msg: Message, state: FSMContext):
    subscribed, not_joined = await check_subscription(msg.bot, msg.from_user.id)
    if not subscribed:
        await msg.answer("⚠️ Avval kanallarga obuna bo'ling:", reply_markup=sub_keyboard(not_joined))
        return

    tariffs = await get_tariffs()
    if not tariffs:
        await msg.answer("😔 Hozircha tariflar mavjud emas.")
        return

    text = "💳 <b>Limit sotib olish</b>\n\nMavjud tariflar:\n\n"
    buttons = []
    for t in tariffs:
        text += (
            f"📦 <b>{t['name']}</b>\n"
            f"   {t['description']}\n"
            f"   +{t['public_limit']} ommaviy / +{t['private_limit']} shaxsiy\n"
            f"   💰 <b>{fmt(t['price'])} so'm</b>\n\n"
        )
        buttons.append([InlineKeyboardButton(text=f"{t['name']} — {fmt(t['price'])} so'm", callback_data=f"buy:{t['id']}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="pay_cancel")])

    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await state.set_state(PaymentStates.choosing_tariff)


@router.callback_query(F.data.startswith("buy:"))
async def tariff_selected(call: CallbackQuery, state: FSMContext):
    tariff_id = int(call.data.split(":")[1])
    tariff = await get_tariff(tariff_id)
    if not tariff:
        await call.answer("Tarif topilmadi!", show_alert=True)
        return

    await state.update_data(tariff_id=tariff_id, tariff=tariff)
    await state.set_state(PaymentStates.entering_id)

    await call.message.edit_text(
        f"✅ <b>{tariff['name']}</b> tanlandi\n\n"
        f"📝 <b>8 xonali Teacher ID</b> ingizni kiriting:\n\n"
        f"<i>ID ni testifyuz.online saytida dashboard sahifasida topasiz</i>\n\n"
        f"/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(PaymentStates.entering_id)
async def teacher_id_entered(msg: Message, state: FSMContext):
    teacher_id = msg.text.strip()
    if not teacher_id.isdigit() or len(teacher_id) != 8:
        await msg.answer("❌ ID noto'g'ri! 8 ta raqamdan iborat bo'lishi kerak.\n\nQaytadan kiriting:")
        return

    await state.update_data(teacher_id=teacher_id)
    await state.set_state(PaymentStates.entering_promo)

    await msg.answer(
        "🎟 <b>Promokodingiz bormi?</b>\n\n"
        "Promokod egasiga bonus limit beriladi!\n\n"
        "Promokod bo'lsa yozing, bo'lmasa — <b>YO'Q</b> deb yuboring.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Promokod yo'q", callback_data="no_promo")]
        ])
    )


@router.callback_query(F.data == "no_promo")
async def no_promo(call: CallbackQuery, state: FSMContext):
    await state.update_data(promo_code=None)
    await send_payment_info(call.message, state, edit=True)
    await call.answer()


@router.message(PaymentStates.entering_promo)
async def promo_entered(msg: Message, state: FSMContext):
    text = msg.text.strip().upper()

    if text in ['YOQ', "YO'Q", 'NO', '-']:
        await state.update_data(promo_code=None)
        await send_payment_info(msg, state, edit=False)
        return

    # Validate promo
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/bot/promocode/validate",
                json={"code": text, "secret": BOT_SECRET}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await state.update_data(promo_code=text, promo_owner=data.get("teacherName", ""))
                    await msg.answer(f"✅ Promokod tasdiqlandi! (<b>{data.get('teacherName', '')}</b> ning kodi)", parse_mode="HTML")
                    await send_payment_info(msg, state, edit=False)
                else:
                    await msg.answer("❌ Promokod noto'g'ri! Qaytadan kiriting yoki <b>YO'Q</b> deb yuboring.", parse_mode="HTML")
    except Exception:
        await state.update_data(promo_code=None)
        await send_payment_info(msg, state, edit=False)


async def send_payment_info(msg_or_obj, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    tariff = data["tariff"]
    teacher_id = data["teacher_id"]
    promo_code = data.get("promo_code")

    card = await get_setting("payment_card", "0000000000000000")
    card_owner = await get_setting("payment_card_owner", "Testify")

    await state.set_state(PaymentStates.uploading_receipt)

    promo_text = f"\n🎟 Promokod: <code>{promo_code}</code>" if promo_code else ""

    text = (
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📦 Tarif: <b>{tariff['name']}</b>\n"
        f"💰 Summa: <b>{fmt(tariff['price'])} so'm</b>\n"
        f"🆔 Teacher ID: <code>{teacher_id}</code>"
        f"{promo_text}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💳 Karta:\n<code>{card}</code>\n"
        f"👤 Egasi: <b>{card_owner}</b>\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"1️⃣ Kartaga <b>{fmt(tariff['price'])} so'm</b> o'tkazing\n"
        f"2️⃣ To'lov chekini <b>rasm</b> sifatida yuboring\n\n"
        f"/cancel — bekor qilish"
    )

    if edit and hasattr(msg_or_obj, 'edit_text'):
        await msg_or_obj.edit_text(text, parse_mode="HTML", reply_markup=None)
    else:
        target = msg_or_obj if isinstance(msg_or_obj, Message) else msg_or_obj
        await target.answer(text, parse_mode="HTML")


@router.message(PaymentStates.uploading_receipt, F.photo)
async def receipt_uploaded(msg: Message, state: FSMContext):
    data = await state.get_data()
    tariff = data["tariff"]
    teacher_id = data["teacher_id"]
    promo_code = data.get("promo_code")

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
    promo_text = f"\n🎟 Promokod: <code>{promo_code}</code>" if promo_code else ""

    group_text = (
        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 {username_text}\n"
        f"🆔 Teacher ID: <code>{teacher_id}</code>\n"
        f"📦 Tarif: <b>{tariff['name']}</b>\n"
        f"💰 Summa: <b>{fmt(tariff['price'])} so'm</b>"
        f"{promo_text}\n"
        f"⏰ {msg.date.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔢 To'lov ID: <code>{payment_id}</code>"
    )

    group_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul", callback_data=f"approve:{payment_id}:{promo_code or ''}"),
         InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{payment_id}")]
    ])

    try:
        group_msg = await msg.bot.send_photo(
            chat_id=PAYMENT_GROUP, photo=msg.photo[-1].file_id,
            caption=group_text, reply_markup=group_keyboard, parse_mode="HTML"
        )
        await set_payment_group_msg(payment_id, group_msg.message_id)
    except Exception:
        pass

    await msg.answer(
        f"✅ <b>So'rovingiz yuborildi!</b>\n\n"
        f"🔢 Raqam: <code>{payment_id}</code>\n\n"
        f"Tez orada ko'rib chiqiladi (5-30 daqiqa).",
        parse_mode="HTML"
    )


@router.message(PaymentStates.uploading_receipt)
async def not_photo(msg: Message):
    await msg.answer("📸 Iltimos, to'lov chekining <b>rasmini</b> yuboring!", parse_mode="HTML")


@router.callback_query(F.data.startswith("approve:"))
async def approve_handler(call: CallbackQuery):
    parts = call.data.split(":")
    payment_id = int(parts[1])
    promo_code = parts[2] if len(parts) > 2 and parts[2] else None

    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("To'lov topilmadi!", show_alert=True)
        return
    if payment["status"] != "pending":
        await call.answer("Allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    tariff = await get_tariff(payment["tariff_id"])
    if not tariff:
        await call.answer("Tarif topilmadi!", show_alert=True)
        return

    try:
        async with aiohttp.ClientSession() as session:
            # Add limit to buyer
            async with session.post(
                f"{BACKEND_URL}/api/bot/add-limit",
                json={"teacherId": payment["teacher_id"], "publicLimit": tariff["public_limit"], "privateLimit": tariff["private_limit"], "tariffName": tariff["name"], "secret": BOT_SECRET}
            ) as resp:
                if resp.status != 200:
                    await call.answer("Backend xatosi!", show_alert=True)
                    return

            # Apply promocode if exists
            promo_owner_name = None
            if promo_code:
                async with session.post(
                    f"{BACKEND_URL}/api/bot/promocode/apply",
                    json={"code": promo_code, "secret": BOT_SECRET}
                ) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.json()
                        promo_owner_name = data2.get("ownerName")
    except Exception as e:
        await call.answer(f"Xato: {e}", show_alert=True)
        return

    await approve_payment(payment_id)

    try:
        await call.message.edit_caption(
            caption=call.message.caption + "\n\n✅ <b>QABUL QILINDI</b>",
            reply_markup=None, parse_mode="HTML"
        )
    except Exception:
        pass

    # Notify buyer
    promo_bonus_text = f"\n\n🎟 Promokod (<b>{promo_code}</b>) egasiga ham bonus berildi!" if promo_owner_name else ""
    try:
        await call.bot.send_message(
            chat_id=payment["user_id"],
            text=f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                 f"📦 {payment['tariff_name']}\n"
                 f"➕ +{tariff['public_limit']} ommaviy\n"
                 f"➕ +{tariff['private_limit']} shaxsiy\n\n"
                 f"Limitlar qo'shildi! 🎉{promo_bonus_text}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Notify promo owner
    if promo_owner_name and promo_code:
        try:
            # We need owner user_id — get from backend
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_URL}/api/bot/promocode/validate",
                    json={"code": promo_code, "secret": BOT_SECRET}
                ) as resp3:
                    if resp3.status == 200:
                        pass  # owner notification via teacherId lookup not implemented here
        except Exception:
            pass

    await call.answer("✅ Qabul qilindi!")


@router.callback_query(F.data.startswith("reject:"))
async def reject_start(call: CallbackQuery, state: FSMContext):
    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("Topilmadi!", show_alert=True)
        return
    if payment["status"] != "pending":
        await call.answer("Allaqachon ko'rib chiqilgan!", show_alert=True)
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
        await msg.bot.edit_message_caption(
            chat_id=data["chat_id"], message_id=data["msg_id"],
            caption=(await msg.bot.get_message(data["chat_id"], data["msg_id"])).caption + f"\n\n❌ <b>RAD ETILDI</b>\n📝 {reason}",
            reply_markup=None, parse_mode="HTML"
        )
    except Exception:
        pass

    try:
        await msg.bot.send_message(
            chat_id=payment["user_id"],
            text=f"❌ <b>To'lovingiz rad etildi</b>\n\n📝 Sabab: {reason}\n\nQaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await msg.answer("❌ Rad etildi va foydalanuvchiga xabar yuborildi.")


@router.callback_query(F.data == "pay_cancel")
async def pay_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()
