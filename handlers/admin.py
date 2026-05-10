import json
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    is_admin, get_user_count, get_today_count, get_week_count, get_month_count,
    get_all_users, add_admin, remove_admin, get_admins,
    add_channel, remove_channel, get_channels,
    get_setting, set_setting,
    add_tariff, get_tariffs, delete_tariff, format_price if False else str
)

router = Router()


def fmt(amount): return f"{amount:,}".replace(",", " ")


class AdminStates(StatesGroup):
    broadcast = State()
    add_channel = State()
    add_admin = State()
    edit_welcome_text = State()
    edit_welcome_buttons = State()
    edit_payment_text = State()
    edit_payment_admin = State()
    edit_card = State()
    add_tariff_name = State()
    add_tariff_desc = State()
    add_tariff_price = State()
    add_tariff_public = State()
    add_tariff_private = State()


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Ommaviy post", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Monitoring", callback_data="admin_stats")],
        [InlineKeyboardButton(text="✏️ Salomlashuv postini tahrirlash", callback_data="admin_welcome")],
        [InlineKeyboardButton(text="💳 Karta sozlamalari", callback_data="admin_card")],
        [InlineKeyboardButton(text="📦 Tariflarni boshqarish", callback_data="admin_tariffs")],
        [InlineKeyboardButton(text="📋 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_admins")],
    ])


async def check_admin(user_id: int, obj) -> bool:
    if not await is_admin(user_id):
        if isinstance(obj, Message):
            await obj.answer("❌ Sizda admin huquqi yo'q!")
        else:
            await obj.answer("❌ Ruxsat yo'q!", show_alert=True)
        return False
    return True


@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not await check_admin(msg.from_user.id, msg):
        return
    await msg.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu(), parse_mode="HTML")


# ── STATS ──
@router.callback_query(F.data == "admin_stats")
async def stats_handler(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    total = await get_user_count()
    today = await get_today_count()
    week = await get_week_count()
    month = await get_month_count()
    text = (
        f"📊 <b>Monitoring</b>\n\n"
        f"👥 Jami: <b>{total}</b>\n"
        f"🆕 Bugun: <b>{today}</b>\n"
        f"📅 Hafta: <b>{week}</b>\n"
        f"📆 Oy: <b>{month}</b>"
    )
    await call.message.edit_text(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_stats")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")]
        ]))
    await call.answer()


# ── BROADCAST ──
@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text(
        "📢 <b>Ommaviy post</b>\n\nXabar yuboring:\n\n/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.broadcast)
async def broadcast_send(msg: Message, state: FSMContext):
    await state.clear()
    users = await get_all_users()
    total = len(users)
    sent = 0
    failed = 0
    progress_msg = await msg.answer(f"📤 Yuborilmoqda: 0/{total}")
    for i, user_id in enumerate(users):
        try:
            await msg.copy_to(user_id)
            sent += 1
        except Exception:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await progress_msg.edit_text(f"📤 Yuborilmoqda: {i+1}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await progress_msg.edit_text(
        f"✅ <b>Tayyor!</b>\n📨 Yuborildi: <b>{sent}</b>\n❌ Xato: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))


# ── SALOMLASHUV ──
@router.callback_query(F.data == "admin_welcome")
async def welcome_menu(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    text = await get_setting("welcome_text")
    await call.message.edit_text(
        f"✏️ <b>Salomlashuv</b>\n\n<b>Hozirgi:</b>\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Matnni tahrirlash", callback_data="edit_welcome_text")],
            [InlineKeyboardButton(text="🔗 Tugmalarni tahrirlash", callback_data="edit_welcome_buttons")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ]))
    await call.answer()


@router.callback_query(F.data == "edit_welcome_text")
async def edit_welcome_text_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_welcome_text)
    await call.message.edit_text(
        "✏️ Yangi salomlashuv matnini yuboring:\n\n/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.edit_welcome_text)
async def edit_welcome_text_save(msg: Message, state: FSMContext):
    await state.clear()
    await set_setting("welcome_text", msg.text or "Xush kelibsiz!")
    await msg.answer("✅ Yangilandi!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))


@router.callback_query(F.data == "edit_welcome_buttons")
async def edit_welcome_buttons_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_welcome_buttons)
    current = await get_setting("welcome_buttons", "[]")
    await call.message.edit_text(
        f"🔗 JSON formatda tugmalar:\n"
        f'<pre>[{{"text": "Sayt", "url": "https://testifyuz.online"}}]</pre>\n\n'
        f"<b>Hozirgi:</b>\n<code>{current}</code>\n\n/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.edit_welcome_buttons)
async def edit_welcome_buttons_save(msg: Message, state: FSMContext):
    await state.clear()
    try:
        json.loads(msg.text)
        await set_setting("welcome_buttons", msg.text)
        await msg.answer("✅ Tugmalar yangilandi!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))
    except Exception:
        await msg.answer("❌ JSON format noto'g'ri!")


# ── KARTA ──
@router.callback_query(F.data == "admin_card")
async def card_menu(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    card = await get_setting("payment_card", "")
    owner = await get_setting("payment_card_owner", "")
    await call.message.edit_text(
        f"💳 <b>Karta sozlamalari</b>\n\n"
        f"Karta: <code>{card}</code>\n"
        f"Egasi: <b>{owner}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Karta raqamini o'zgartirish", callback_data="edit_card_number")],
            [InlineKeyboardButton(text="✏️ Egasini o'zgartirish", callback_data="edit_card_owner")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ]))
    await call.answer()


@router.callback_query(F.data == "edit_card_number")
async def edit_card_number(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_card)
    await state.update_data(card_field="payment_card")
    await call.message.edit_text("💳 Yangi karta raqamini yuboring:\n\nMisol: <code>9860123456789012</code>\n\n/cancel",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.callback_query(F.data == "edit_card_owner")
async def edit_card_owner(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_card)
    await state.update_data(card_field="payment_card_owner")
    await call.message.edit_text("👤 Karta egasining ismini yuboring:\n\n/cancel",
        reply_markup=None)
    await call.answer()


@router.message(AdminStates.edit_card)
async def edit_card_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await set_setting(data["card_field"], msg.text.strip())
    await msg.answer("✅ Yangilandi!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))


# ── TARIFLAR ──
@router.callback_query(F.data == "admin_tariffs")
async def tariffs_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    tariffs = await get_tariffs(only_active=False)
    text = "📦 <b>Tariflar</b>\n\n"
    if tariffs:
        for t in tariffs:
            status = "✅" if t["is_active"] else "❌"
            text += (f"{status} <b>{t['name']}</b> — {fmt(t['price'])} so'm\n"
                     f"   +{t['public_limit']} ommaviy / +{t['private_limit']} shaxsiy\n\n")
    else:
        text += "Hali tarif yo'q"

    buttons = [[InlineKeyboardButton(text="➕ Tarif qo'shish", callback_data="tariff_add")]]
    if tariffs:
        buttons.append([InlineKeyboardButton(text="🗑 Tarif o'chirish", callback_data="tariff_delete")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")])

    await call.message.edit_text(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data == "tariff_add")
async def tariff_add_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.add_tariff_name)
    await call.message.edit_text("📦 Tarif nomini yuboring:\n\nMisol: <b>Pro</b>\n\n/cancel",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.add_tariff_name)
async def tariff_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(AdminStates.add_tariff_desc)
    await msg.answer("📝 Tavsifini yuboring:\n\nMisol: <b>5 ta ommaviy test</b>\n\n/cancel", parse_mode="HTML")


@router.message(AdminStates.add_tariff_desc)
async def tariff_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text.strip())
    await state.set_state(AdminStates.add_tariff_price)
    await msg.answer("💰 Narxini so'mda yuboring:\n\nMisol: <b>50000</b>\n\n/cancel", parse_mode="HTML")


@router.message(AdminStates.add_tariff_price)
async def tariff_price(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.strip().replace(" ", ""))
        await state.update_data(price=price)
        await state.set_state(AdminStates.add_tariff_public)
        await msg.answer("📊 Nechta <b>ommaviy</b> test limiti qo'shilsin?\n\nMisol: <b>5</b>\n\n/cancel", parse_mode="HTML")
    except ValueError:
        await msg.answer("❌ Faqat raqam kiriting!")


@router.message(AdminStates.add_tariff_public)
async def tariff_public(msg: Message, state: FSMContext):
    try:
        public = int(msg.text.strip())
        await state.update_data(public_limit=public)
        await state.set_state(AdminStates.add_tariff_private)
        await msg.answer("📊 Nechta <b>shaxsiy</b> test limiti qo'shilsin?\n\nMisol: <b>2</b>\n\n/cancel", parse_mode="HTML")
    except ValueError:
        await msg.answer("❌ Faqat raqam kiriting!")


@router.message(AdminStates.add_tariff_private)
async def tariff_private(msg: Message, state: FSMContext):
    try:
        private = int(msg.text.strip())
        data = await state.get_data()
        await state.clear()
        tariff = await add_tariff(
            name=data["name"],
            description=data["description"],
            price=data["price"],
            public_limit=data["public_limit"],
            private_limit=private
        )
        await msg.answer(
            f"✅ <b>Tarif qo'shildi!</b>\n\n"
            f"📦 Nom: <b>{tariff['name']}</b>\n"
            f"💰 Narx: <b>{fmt(tariff['price'])} so'm</b>\n"
            f"📊 +{tariff['public_limit']} ommaviy / +{tariff['private_limit']} shaxsiy",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))
    except ValueError:
        await msg.answer("❌ Faqat raqam kiriting!")


@router.callback_query(F.data == "tariff_delete")
async def tariff_delete_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    tariffs = await get_tariffs(only_active=True)
    buttons = [[InlineKeyboardButton(
        text=f"🗑 {t['name']} — {fmt(t['price'])} so'm",
        callback_data=f"del_tariff:{t['id']}")] for t in tariffs]
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_tariffs")])
    await call.message.edit_text("O'chirmoqchi bo'lgan tarifni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data.startswith("del_tariff:"))
async def tariff_delete(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    tariff_id = int(call.data.split(":")[1])
    await delete_tariff(tariff_id)
    await call.answer("✅ Tarif o'chirildi!", show_alert=True)
    await tariffs_list(call)


# ── KANALLAR ──
@router.callback_query(F.data == "admin_channels")
async def channels_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    channels = await get_channels()
    text = "📋 <b>Kanallar</b>\n\n"
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']} — <code>{ch['id']}</code>\n"
    else:
        text += "Kanal yo'q"
    buttons = [[InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channel_add")]]
    if channels:
        buttons.append([InlineKeyboardButton(text="🗑 Kanal o'chirish", callback_data="channel_remove")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")])
    await call.message.edit_text(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data == "channel_add")
async def channel_add_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.add_channel)
    await call.message.edit_text(
        "📢 Kanal ID yoki username:\n\nMisol: <code>@kanal</code>\n\n⚠️ Bot admin bo'lishi kerak!\n\n/cancel",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.add_channel)
async def channel_add_save(msg: Message, state: FSMContext):
    await state.clear()
    try:
        chat = await msg.bot.get_chat(msg.text.strip())
        await add_channel(str(chat.id), chat.title or msg.text)
        await msg.answer(f"✅ <b>{chat.title}</b> qo'shildi!", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))
    except Exception:
        await msg.answer("❌ Kanal topilmadi!")


@router.callback_query(F.data == "channel_remove")
async def channel_remove_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    channels = await get_channels()
    buttons = [[InlineKeyboardButton(text=f"🗑 {ch['name']}", callback_data=f"del_ch:{ch['id']}")] for ch in channels]
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_channels")])
    await call.message.edit_text("O'chirmoqchi bo'lgan kanalni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data.startswith("del_ch:"))
async def channel_delete(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    await remove_channel(call.data.split(":", 1)[1])
    await call.answer("✅ O'chirildi!", show_alert=True)
    await channels_list(call)


# ── ADMINLAR ──
@router.callback_query(F.data == "admin_admins")
async def admins_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    admins = await get_admins()
    text = "👥 <b>Adminlar</b>\n\n"
    text += "\n".join(f"{i}. <code>{a}</code>" for i, a in enumerate(admins, 1)) if admins else "Admin yo'q"
    await call.message.edit_text(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add")],
            [InlineKeyboardButton(text="🗑 Admin o'chirish", callback_data="admin_remove")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ]))
    await call.answer()


@router.callback_query(F.data == "admin_add")
async def admin_add_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.add_admin)
    await call.message.edit_text("👤 Yangi admin ID:\n\nMisol: <code>123456789</code>\n\n/cancel",
        parse_mode="HTML", reply_markup=None)
    await call.answer()


@router.message(AdminStates.add_admin)
async def admin_add_save(msg: Message, state: FSMContext):
    await state.clear()
    try:
        await add_admin(int(msg.text.strip()))
        await msg.answer(f"✅ Admin qo'shildi: <code>{msg.text.strip()}</code>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))
    except ValueError:
        await msg.answer("❌ Noto'g'ri ID!")


@router.callback_query(F.data == "admin_remove")
async def admin_remove_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    admins = await get_admins()
    if not admins:
        await call.answer("Admin yo'q!", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(text=f"🗑 {a}", callback_data=f"del_admin:{a}")] for a in admins]
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_admins")])
    await call.message.edit_text("O'chirmoqchi bo'lgan adminni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@router.callback_query(F.data.startswith("del_admin:"))
async def admin_delete(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    await remove_admin(int(call.data.split(":", 1)[1]))
    await call.answer("✅ O'chirildi!", show_alert=True)
    await admins_list(call)


# ── BACK & CANCEL ──
@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🛠 <b>Admin panel</b>", reply_markup=admin_menu(), parse_mode="HTML")
    await call.answer()


@router.message(Command("cancel"))
async def cancel_handler(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Bekor qilindi", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]]))
