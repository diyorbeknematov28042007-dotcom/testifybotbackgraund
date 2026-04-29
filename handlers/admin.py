import json
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    is_admin, get_user_count, get_today_count, get_all_users,
    add_admin, remove_admin, get_admins,
    add_channel, remove_channel, get_channels,
    get_setting, set_setting
)

router = Router()


class AdminStates(StatesGroup):
    broadcast = State()
    add_channel = State()
    add_admin = State()
    edit_welcome = State()
    edit_buttons = State()


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Ommaviy post", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Kanallar", callback_data="admin_channels")],
        [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_admins")],
        [InlineKeyboardButton(text="✏️ Salomlashuv", callback_data="admin_welcome")],
    ])


async def check_admin(user_id: int, msg_or_call) -> bool:
    if not await is_admin(user_id):
        if isinstance(msg_or_call, Message):
            await msg_or_call.answer("❌ Sizda admin huquqi yo'q!")
        else:
            await msg_or_call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return False
    return True


@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not await check_admin(msg.from_user.id, msg):
        return
    await msg.answer("🛠 Admin panel", reply_markup=admin_menu())


# ── STATISTIKA ──
@router.callback_query(F.data == "admin_stats")
async def stats_handler(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    total = await get_user_count()
    today = await get_today_count()
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"🆕 Bugun qo'shildi: <b>{today}</b>"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")]
    ]), parse_mode="HTML")
    await call.answer()


# ── BROADCAST ──
@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.broadcast)
    await call.message.edit_text(
        "📢 Ommaviy post uchun xabar yuboring:\n\n"
        "<i>Matn, rasm, video yoki hujjat yuborishingiz mumkin</i>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML",
        reply_markup=None
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
        f"✅ Post yuborildi!\n\n"
        f"📨 Yuborildi: {sent}\n"
        f"❌ Xato: {failed}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ])
    )


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
        await msg.answer(f"❌ Kanal topilmadi: {e}\n\nBot kanalda admin bo'lishi kerak!",
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
    channels = await get_channels()
    text = "📋 <b>Kanallar</b>\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch['name']} — <code>{ch['id']}</code>\n"
    if not channels:
        text += "Hali kanal yo'q"
    buttons = [[InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channel_add")]]
    if channels:
        buttons.append([InlineKeyboardButton(text="🗑 Kanal o'chirish", callback_data="channel_remove")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")])
    await call.message.edit_text(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


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


# ── SALOMLASHUV ──
@router.callback_query(F.data == "admin_welcome")
async def welcome_menu(call: CallbackQuery):
    if not await check_admin(call.from_user.id, call):
        return
    text = await get_setting("welcome_text", "Botga xush kelibsiz!")
    await call.message.edit_text(
        f"✏️ <b>Hozirgi salomlashuv matni:</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Matnni tahrirlash", callback_data="edit_welcome_text")],
            [InlineKeyboardButton(text="🔗 Tugmalarni tahrirlash", callback_data="edit_welcome_buttons")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_back")],
        ])
    )
    await call.answer()


@router.callback_query(F.data == "edit_welcome_text")
async def edit_welcome_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_welcome)
    await call.message.edit_text(
        "✏️ Yangi salomlashuv matnini yuboring:\n\n"
        "<i>HTML format ishlatishingiz mumkin: &lt;b&gt;, &lt;i&gt;, &lt;a&gt;</i>\n\n"
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_welcome)
async def edit_welcome_save(msg: Message, state: FSMContext):
    await state.clear()
    await set_setting("welcome_text", msg.text or msg.caption or "Xush kelibsiz!")
    await msg.answer("✅ Salomlashuv matni yangilandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
        ]))


@router.callback_query(F.data == "edit_welcome_buttons")
async def edit_buttons_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, call):
        return
    await state.set_state(AdminStates.edit_buttons)
    await call.message.edit_text(
        "🔗 Tugmalarni JSON formatda yuboring:\n\n"
        '<pre>[{"text": "Kanal", "url": "https://t.me/kanal"}]</pre>\n\n'
        "Bir necha tugma:\n"
        '<pre>[{"text": "1-tugma", "url": "https://..."}, {"text": "2-tugma", "url": "https://..."}]</pre>\n\n'
        "/cancel — bekor qilish",
        parse_mode="HTML", reply_markup=None
    )
    await call.answer()


@router.message(AdminStates.edit_buttons)
async def edit_buttons_save(msg: Message, state: FSMContext):
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
        await msg.answer("❌ JSON format noto'g'ri! Qaytadan urinib ko'ring.")


# ── BACK ──
@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🛠 Admin panel", reply_markup=admin_menu())
    await call.answer()


# ── CANCEL ──
@router.message(Command("cancel"))
async def cancel_handler(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Bekor qilindi", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_back")]
    ]))
