import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, ssl="require")
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
            INSERT INTO settings (key, value)
            VALUES ('welcome_text', 'Botga xush kelibsiz! 🎉'), ('welcome_buttons', '[]')
            ON CONFLICT (key) DO NOTHING
        """)


async def add_user(user_id: int, username: str, full_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, username, full_name)


async def get_user_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users")


async def get_today_count() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("""
            SELECT COUNT(*) FROM users
            WHERE joined_at::date = CURRENT_DATE
        """)


async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [r["user_id"] for r in rows]


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
        await conn.execute("""
            INSERT INTO admins (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id)


async def remove_admin(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)


async def get_admins():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM admins")
        return [r["user_id"] for r in rows]


async def add_channel(channel_id: str, channel_name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO channels (channel_id, channel_name)
            VALUES ($1, $2)
            ON CONFLICT (channel_id) DO NOTHING
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
