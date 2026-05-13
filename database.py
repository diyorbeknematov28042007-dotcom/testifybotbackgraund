import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, ssl="require", statement_cache_size=0)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id SERIAL PRIMARY KEY,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                added_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tariffs (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                public_limit INTEGER DEFAULT 0,
                private_limit INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT,
                teacher_id TEXT NOT NULL,
                tariff_id INTEGER REFERENCES tariffs(id),
                tariff_name TEXT,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                reject_reason TEXT,
                group_message_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        defaults = [
            ('welcome_text', "Assalamu alaykum! 👋\nEndi ta'lim — oson va qulay! 📚✨\n\nBizning loyihalarimizdan foydalanish uchun:\n👇 Quyidagi tugmalardan birini tanlang"),
            ('welcome_buttons', '[{"text": "Test Platformasi", "url": "https://testifyuz.online"}]'),
            ('payment_card', '9860123456789012'),
            ('payment_card_owner', 'Testify Platform'),
        ]
        for key, value in defaults:
            await conn.execute("""
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO NOTHING
            """, key, value)


# ── USERS ──
async def add_user(user_id: int, username: str, full_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING
        """, user_id, username, full_name)


async def get_user_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users")


async def get_today_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at::date = CURRENT_DATE")


async def get_week_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= NOW() - INTERVAL '7 days'")


async def get_month_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= NOW() - INTERVAL '30 days'")


async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [r["user_id"] for r in rows]


# ── ADMINS ──
async def is_admin(user_id: int) -> bool:
    main_admin = int(os.getenv("ADMIN_ID", "0"))
    if user_id == main_admin:
        return True
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM admins WHERE user_id = $1", user_id)
        return row is not None


async def add_admin(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", user_id)


async def remove_admin(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)


async def get_admins():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM admins")
        return [r["user_id"] for r in rows]


# ── CHANNELS ──
async def add_channel(channel_id: str, channel_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO channels (channel_id, channel_name)
            VALUES ($1, $2) ON CONFLICT (channel_id) DO NOTHING
        """, channel_id, channel_name)


async def remove_channel(channel_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM channels WHERE channel_id = $1", channel_id)


async def get_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT channel_id, channel_name FROM channels")
        return [{"id": r["channel_id"], "name": r["channel_name"]} for r in rows]


# ── SETTINGS ──
async def set_setting(key: str, value: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO settings (key, value) VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = $2
        """, key, value)


async def get_setting(key: str, default: str = "") -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM settings WHERE key = $1", key)
        return row["value"] if row else default


# ── TARIFFS ──
async def add_tariff(name: str, description: str, price: int, public_limit: int, private_limit: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO tariffs (name, description, price, public_limit, private_limit)
            VALUES ($1, $2, $3, $4, $5) RETURNING *
        """, name, description, price, public_limit, private_limit)
        return dict(row)


async def get_tariffs(only_active: bool = True):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if only_active:
            rows = await conn.fetch("SELECT * FROM tariffs WHERE is_active = TRUE ORDER BY price")
        else:
            rows = await conn.fetch("SELECT * FROM tariffs ORDER BY price")
        return [dict(r) for r in rows]


async def get_tariff(tariff_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tariffs WHERE id = $1", tariff_id)
        return dict(row) if row else None


async def delete_tariff(tariff_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE tariffs SET is_active = FALSE WHERE id = $1", tariff_id)


# ── PAYMENTS ──
async def create_payment(user_id: int, username: str, teacher_id: str, tariff_id: int, tariff_name: str, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO payments (user_id, username, teacher_id, tariff_id, tariff_name, amount)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
        """, user_id, username, teacher_id, tariff_id, tariff_name, amount)
        return row["id"]


async def set_payment_group_msg(payment_id: int, group_message_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE payments SET group_message_id = $1 WHERE id = $2", group_message_id, payment_id)


async def get_payment(payment_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM payments WHERE id = $1", payment_id)
        return dict(row) if row else None


async def approve_payment(payment_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE payments SET status = 'approved' WHERE id = $1", payment_id)


async def reject_payment(payment_id: int, reason: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE payments SET status = 'rejected', reject_reason = $1 WHERE id = $2", reason, payment_id)
