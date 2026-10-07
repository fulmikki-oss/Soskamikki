import aiosqlite
from pathlib import Path

DB = Path("shop.db")

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS subcategories(id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, name TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, subcategory_id INTEGER NOT NULL,
            name TEXT NOT NULL, description TEXT DEFAULT '', price REAL NOT NULL,
            FOREIGN KEY(subcategory_id) REFERENCES subcategories(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS keys(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
            value TEXT NOT NULL, sold INTEGER DEFAULT 0,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, title TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS payment_methods(
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
            enabled INTEGER DEFAULT 0, details TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS documents(
            code TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            price REAL NOT NULL, payment_code TEXT NOT NULL, status TEXT DEFAULT 'waiting_payment',
            proof TEXT DEFAULT '', key_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(key_id) REFERENCES keys(id));
        """)
        await db.execute("INSERT OR IGNORE INTO admins(user_id) VALUES (?)", (int(__import__("os").getenv("ADMIN_ID")),))
        for code,title in [("crypto","₿ Крипта"),("cryptobot","🤖 Crypto Bot"),("yookassa","💰 ЮKassa"),("pay","💳 Платёжная система"),("manual","📝 Полуавтомат")]:
            await db.execute("INSERT OR IGNORE INTO payment_methods(code,title) VALUES(?,?)",(code,title))
        await db.execute("INSERT OR IGNORE INTO documents(code,title,body) VALUES('privacy','Политика конфиденциальности','Текст политики пока не задан.')")
        await db.execute("INSERT OR IGNORE INTO documents(code,title,body) VALUES('terms','Пользовательское соглашение','Текст соглашения пока не задан.')")
        await db.commit()

async def fetchall(sql, args=()):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql,args)
        return await cur.fetchall()

async def fetchone(sql,args=()):
    rows=await fetchall(sql,args)
    return rows[0] if rows else None

async def execute(sql,args=()):
    async with aiosqlite.connect(DB) as db:
        cur=await db.execute(sql,args); await db.commit()
        return cur.lastrowid

async def is_admin(uid:int)->bool:
    return bool(await fetchone("SELECT 1 FROM admins WHERE user_id=?", (uid,)))

async def add_user(uid, username):
    await execute("INSERT OR IGNORE INTO users(id,username) VALUES(?,?)",(uid,username))
