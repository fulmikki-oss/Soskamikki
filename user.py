from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from db import add_user, fetchall, fetchone
from config import settings
from keyboards import main_kb, kb, back
from aiogram.types import InlineKeyboardButton

router=Router()

@router.message(CommandStart())
async def start(m:Message):
    await add_user(m.from_user.id,m.from_user.username)
    admin=bool(await fetchone("SELECT 1 FROM admins WHERE user_id=?",(m.from_user.id,)))
    await m.answer("Добро пожаловать в магазин.",reply_markup=main_kb(admin))

@router.callback_query(F.data=="home")
async def home(c:CallbackQuery):
    admin=bool(await fetchone("SELECT 1 FROM admins WHERE user_id=?",(c.from_user.id,)))
    await c.message.edit_text("Главное меню",reply_markup=main_kb(admin)); await c.answer()

@router.callback_query(F.data=="cats")
async def cats(c:CallbackQuery):
    rows=await fetchall("SELECT id,name FROM categories ORDER BY id")
    buttons=[[InlineKeyboardButton(text=r["name"],callback_data=f"cat:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="home")])
    await c.message.edit_text("🛍 Категории:",reply_markup=kb(buttons)); await c.answer()

@router.callback_query(F.data.startswith("cat:"))
async def subs(c:CallbackQuery):
    cid=int(c.data.split(":")[1])
    rows=await fetchall("SELECT id,name FROM subcategories WHERE category_id=? ORDER BY id",(cid,))
    buttons=[[InlineKeyboardButton(text=r["name"],callback_data=f"sub:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="cats")])
    await c.message.edit_text("Выберите подкатегорию:",reply_markup=kb(buttons)); await c.answer()

@router.callback_query(F.data.startswith("sub:"))
async def products(c:CallbackQuery):
    sid=int(c.data.split(":")[1])
    rows=await fetchall("SELECT id,name,price FROM products WHERE subcategory_id=? ORDER BY id",(sid,))
    buttons=[[InlineKeyboardButton(text=f"{r['name']} — {r['price']:.2f}",callback_data=f"prod:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="cats")])
    await c.message.edit_text("Товары:",reply_markup=kb(buttons)); await c.answer()

@router.callback_query(F.data.startswith("prod:"))
async def product(c:CallbackQuery):
    pid=int(c.data.split(":")[1])
    p=await fetchone("SELECT * FROM products WHERE id=?",(pid,))
    stock=await fetchone("SELECT COUNT(*) n FROM keys WHERE product_id=? AND sold=0",(pid,))
    if not p: return await c.answer("Товар не найден",show_alert=True)
    b=kb([[InlineKeyboardButton(text=f"Купить за {p['price']:.2f}",callback_data=f"buy:{pid}")],
          [InlineKeyboardButton(text="⬅️ Назад",callback_data="cats")]])
    await c.message.edit_text(f"<b>{p['name']}</b>\n{p['description']}\n\nВ наличии: {stock['n']}",reply_markup=b); await c.answer()

@router.callback_query(F.data.startswith("buy:"))
async def buy(c:CallbackQuery):
    pid=int(c.data.split(":")[1]); p=await fetchone("SELECT * FROM products WHERE id=?",(pid,))
    methods=await fetchall("SELECT code,title FROM payment_methods WHERE enabled=1 ORDER BY id")
    if not methods: return await c.answer("Способы оплаты пока не настроены",show_alert=True)
    buttons=[[InlineKeyboardButton(text=r["title"],callback_data=f"pay:{pid}:{r['code']}")] for r in methods]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад",callback_data=f"prod:{pid}")])
    await c.message.edit_text(f"Цена: <b>{p['price']:.2f}</b>\nВыберите способ оплаты:",reply_markup=kb(buttons)); await c.answer()

@router.callback_query(F.data.startswith("pay:"))
async def payment(c:CallbackQuery):
    _,pid,code=c.data.split(":")
    p=await fetchone("SELECT * FROM products WHERE id=?",(int(pid),))
    method=await fetchone("SELECT * FROM payment_methods WHERE code=?",(code,))
    oid=await __import__("db").execute("INSERT INTO orders(user_id,product_id,price,payment_code) VALUES(?,?,?,?)",(c.from_user.id,int(pid),p["price"],code))
    if code=="manual":
        text=(f"Заказ <b>#{oid}</b>\nСумма: <b>{p['price']:.2f}</b>\n\n{method['details'] or 'Реквизиты оплаты задайте в админке.'}\n\n"
              "После оплаты нажмите кнопку ниже и отправьте подтверждение.")
        b=kb([[InlineKeyboardButton(text="📎 Я оплатил",callback_data=f"proof:{oid}")]])
    else:
        text=f"Заказ <b>#{oid}</b> создан.\nИнтеграцию {method['title']} нужно настроить в соответствующем модуле."
        b=back()
    await c.message.edit_text(text,reply_markup=b); await c.answer()

@router.callback_query(F.data.startswith("proof:"))
async def proof(c:CallbackQuery):
    oid=int(c.data.split(":")[1])
    await __import__("db").execute("UPDATE orders SET status='waiting_proof' WHERE id=? AND user_id=?",(oid,c.from_user.id))
    await c.message.edit_text(f"Заказ #{oid}: отправьте следующим сообщением чек, скриншот или текст подтверждения оплаты.")
    await c.answer()

@router.message()
async def catch_proof(m:Message):
    order=await fetchone("SELECT * FROM orders WHERE user_id=? AND status='waiting_proof' ORDER BY id DESC LIMIT 1",(m.from_user.id,))
    if not order: return
    proof=m.caption or m.text or (m.document.file_id if m.document else None) or (m.photo[-1].file_id if m.photo else "")
    await __import__("db").execute("UPDATE orders SET proof=? WHERE id=?",(proof,order["id"]))
    await m.answer("Подтверждение получено. Ожидайте решения администратора.")
    await m.bot.send_message(settings.owner_id,f"🧾 <b>Заказ #{order['id']}</b>\nПользователь: <code>{m.from_user.id}</code>\nСумма: {order['price']}\n\nПодтверждение: {proof}",reply_markup=kb([
        [InlineKeyboardButton(text="✅ Подтвердить",callback_data=f"approve:{order['id']}"),
         InlineKeyboardButton(text="❌ Отклонить",callback_data=f"reject:{order['id']}")]
    ]))

@router.callback_query(F.data=="profile")
async def profile(c:CallbackQuery):
    orders=await fetchall("SELECT id,price,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 20",(c.from_user.id,))
    history="\n".join(f"#{x['id']} — {x['price']:.2f} — {x['status']}" for x in orders) or "Покупок нет."
    docs=await fetchall("SELECT code,title FROM documents")
    b=[[InlineKeyboardButton(text=x["title"],callback_data=f"doc:{x['code']}")] for x in docs]
    b.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="home")])
    await c.message.edit_text(f"👤 ID: <code>{c.from_user.id}</code>\n\n<b>Покупки:</b>\n{history}",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("doc:"))
async def doc(c:CallbackQuery):
    d=await fetchone("SELECT title,body FROM documents WHERE code=?",(c.data.split(":")[1],))
    await c.message.edit_text(f"<b>{d['title']}</b>\n\n{d['body']}",reply_markup=back()); await c.answer()
