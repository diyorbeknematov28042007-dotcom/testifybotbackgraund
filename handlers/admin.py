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
    get_setting, set_setting
)

router = Router()


class AdminStates(StatesGroup):
    broadcast = State()
    add_channel = State()
    add_admin = State()
    edit_welcome_text = State()
    edit_welcome_buttons = State()
    edit_payment_text = State()
    edit_payment_admin = State()


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Ommaviy post", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Monitoring", callback_data="admin_stats")],
        [InlineKeyboardButton(text="✏️ Salomlashuv postini tahrirlash", callback_data="admin_welcome")],
        [InlineKeyboardButton(text="💳 To'lov funksiyasini tahrirlash", callback_data="admin_payment")],
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


# ── MONITORING ──
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
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"🆕 Bugun: <b>{today}</b>\n"
        f"📅 Hafta ichida: <b>{week}</b>\n"
        f"📆 Oy ichida: <b>{month}</b>"
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
        "📢 <b>Ommaviy post</b>\n\n"
        "Xabar, rasm, video yoki hujjat yuboring:\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
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
        f"✅ <b>Post yuborildi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ])
    )


# ── SALOMLASHUV ──
@router.callback_query(F.data == "admin_welcome")
async def welcome_menu(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    text = await get_setting("welcome_text")
    await call.message.edit_text(
        f"✏️ <b>Salomlashuv postini tahrirlash</b>\n\n"
        f"<b>Hozirgi matn:</b>\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Matnni tahrirlash", callback_data="edit_welcome_text")],
            [InlineKeyboardButton(text="🔗 Tugmalarni tahrirlash", callback_data="edit_welcome_buttons")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ])
    )
    await call.answer()


@router.callback_query(F.data == "edit_welcome_text")
async def edit_welcome_text_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_welcome_text)
    await call.message.edit_text(
        "✏️ Yangi salomlashuv matnini yuboring:\n\n"
        "<i>HTML format: &lt;b&gt;bold&lt;/b&gt;, &lt;i&gt;italic&lt;/i&gt;, &lt;a href='url'&gt;link&lt;/a&gt;</i>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_welcome_text)
async def edit_welcome_text_save(msg: Message, state: FSMContext):
    await state.clear()
    await set_setting("welcome_text", msg.text or msg.caption or "Xush kelibsiz!")
    await msg.answer("✅ Salomlashuv matni yangilandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))


@router.callback_query(F.data == "edit_welcome_buttons")
async def edit_welcome_buttons_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_welcome_buttons)
    current = await get_setting("welcome_buttons", "[]")
    await call.message.edit_text(
        "🔗 <b>Tugmalarni tahrirlash</b>\n\n"
        "JSON formatda yuboring:\n"
        '<pre>[{"text": "Sayt", "url": "https://testfyedu.online"}, {"text": "Bot", "url": "https://t.me/bot"}]</pre>\n\n'
        f"<b>Hozirgi:</b>\n<code>{current}</code>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_welcome_buttons)
async def edit_welcome_buttons_save(msg: Message, state: FSMContext):
    await state.clear()
    try:
        data = json.loads(msg.text)
        if not isinstance(data, list):
            raise ValueError
        await set_setting("welcome_buttons", msg.text)
        await msg.answer("✅ Tugmalar yangilandi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
            ]))
    except Exception:
        await msg.answer(
            "❌ JSON format noto'g'ri!\n\n"
            "Misol:\n"
            '<code>[{"text": "Sayt", "url": "https://testfyedu.online"}]</code>',
            parse_mode="HTML"
        )


# ── TO'LOV FUNKSIYASI ──
@router.callback_query(F.data == "admin_payment")
async def payment_menu(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    payment_text = await get_setting("payment_text")
    payment_admin = await get_setting("payment_admin", "@admin")
    await call.message.edit_text(
        f"💳 <b>To'lov funksiyasini tahrirlash</b>\n\n"
        f"<b>Admin username:</b> {payment_admin}\n\n"
        f"<b>Hozirgi matn:</b>\n{payment_text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Matnni tahrirlash", callback_data="edit_payment_text")],
            [InlineKeyboardButton(text="👤 Admin username", callback_data="edit_payment_admin")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ])
    )
    await call.answer()


@router.callback_query(F.data == "edit_payment_text")
async def edit_payment_text_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_payment_text)
    await call.message.edit_text(
        "💳 Yangi to'lov matnini yuboring:\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_payment_text)
async def edit_payment_text_save(msg: Message, state: FSMContext):
    await state.clear()
    await set_setting("payment_text", msg.text or "")
    await msg.answer("✅ To'lov matni yangilandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))


@router.callback_query(F.data == "edit_payment_admin")
async def edit_payment_admin_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_payment_admin)
    await call.message.edit_text(
        "👤 Admin Telegram username yuboring:\n\n"
        "Misol: <code>@username</code>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_payment_admin)
async def edit_payment_admin_save(msg: Message, state: FSMContext):
    await state.clear()
    username = msg.text.strip()
    await set_setting("payment_admin", username)
    await msg.answer(f"✅ Admin username yangilandi: {username}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))


# ── KANALLAR ──
@router.callback_query(F.data == "admin_channels")
async def channels_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    channels = await get_channels()
    text = "📋 <b>Majburiy obuna kanallari</b>\n\n"
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']} — <code>{ch['id']}</code>\n"
    else:
        text += "Hali kanal qo'shilmagan"

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
        "📢 Kanal ID yoki username yuboring:\n\n"
        "Misol: <code>@kanalim</code> yoki <code>-1001234567890</code>\n\n"
        "⚠️ Bot kanalda admin bo'lishi kerak!\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.add_channel)
async def channel_add_save(msg: Message, state: FSMContext):
    await state.clear()
    channel_id = msg.text.strip()
    try:
        chat = await msg.bot.get_chat(channel_id)
        name = chat.title or channel_id
        await add_channel(str(chat.id), name)
        await msg.answer(f"✅ Kanal qo'shildi: <b>{name}</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
            ]))
    except Exception as e:
        await msg.answer(f"❌ Kanal topilmadi!\n\nBot kanalda admin bo'lishi kerak.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
            ]))


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
    channel_id = call.data.split(":", 1)[1]
    await remove_channel(channel_id)
    await call.answer("✅ Kanal o'chirildi!", show_alert=True)
    await channels_list(call)


# ── ADMINLAR ──
@router.callback_query(F.data == "admin_admins")
async def admins_list(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    admins = await get_admins()
    text = "👥 <b>Adminlar ro'yxati</b>\n\n"
    if admins:
        for i, a in enumerate(admins, 1):
            text += f"{i}. <code>{a}</code>\n"
    else:
        text += "Qo'shimcha admin yo'q"

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
    await call.message.edit_text(
        "👤 Yangi admin Telegram ID sini yuboring:\n\n"
        "Misol: <code>123456789</code>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.add_admin)
async def admin_add_save(msg: Message, state: FSMContext):
    await state.clear()
    try:
        new_admin_id = int(msg.text.strip())
        await add_admin(new_admin_id)
        await msg.answer(f"✅ Admin qo'shildi: <code>{new_admin_id}</code>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
            ]))
    except ValueError:
        await msg.answer("❌ Noto'g'ri ID format! Faqat raqam kiriting.")


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
    admin_id = int(call.data.split(":", 1)[1])
    await remove_admin(admin_id)
    await call.answer(f"✅ Admin o'chirildi!", show_alert=True)
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
    await msg.answer("❌ Bekor qilindi",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))
