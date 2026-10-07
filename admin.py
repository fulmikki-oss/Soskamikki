from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import is_admin, fetchall, fetchone, execute
from keyboards import kb
from aiogram.types import InlineKeyboardButton

router=Router()

async def guard(c): return await is_admin(c.from_user.id)

class AddCat(StatesGroup): name=State()
class AddSub(StatesGroup): name=State(); cid=State()
class AddProd(StatesGroup): data=State()
class AddKey(StatesGroup): value=State(); pid=State()
class AddAdmin(StatesGroup): uid=State()
class AddChannel(StatesGroup): value=State()
class DocEdit(StatesGroup): body=State()
class PayEdit(StatesGroup): details=State()

def admin_menu():
    return kb([
      [InlineKeyboardButton(text="🛍 Товары",callback_data="a_products")],
      [InlineKeyboardButton(text="👥 Администраторы",callback_data="a_admins"),
       InlineKeyboardButton(text="📢 Каналы",callback_data="a_channels")],
      [InlineKeyboardButton(text="💳 Оплата",callback_data="a_pay"),
       InlineKeyboardButton(text="📄 Документы",callback_data="a_docs")],
      [InlineKeyboardButton(text="⬅️ В магазин",callback_data="home")]
    ])

@router.callback_query(F.data=="admin")
async def admin(c:CallbackQuery):
    if not await guard(c): return await c.answer("Нет доступа",show_alert=True)
    await c.message.edit_text("👑 Админ-панель",reply_markup=admin_menu()); await c.answer()

@router.callback_query(F.data=="a_products")
async def a_products(c:CallbackQuery):
    if not await guard(c): return
    rows=await fetchall("SELECT id,name FROM categories")
    b=[[InlineKeyboardButton(text=f"📁 {r['name']}",callback_data=f"amcat:{r['id']}")] for r in rows]
    b += [[InlineKeyboardButton(text="➕ Категория",callback_data="addcat")],
          [InlineKeyboardButton(text="🗑 Удалить категорию",callback_data="delcat")],
          [InlineKeyboardButton(text="⬅️",callback_data="admin")]]
    await c.message.edit_text("Управление товарами",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data=="addcat")
async def addcat(c:CallbackQuery,state:FSMContext):
    if not await guard(c): return
    await state.set_state(AddCat.name); await c.message.answer("Введите название категории:"); await c.answer()

@router.message(AddCat.name)
async def addcat_save(m:Message,state:FSMContext):
    await execute("INSERT INTO categories(name) VALUES(?)",(m.text,)); await state.clear(); await m.answer("Категория добавлена.")

@router.callback_query(F.data=="delcat")
async def delcat(c:CallbackQuery):
    rows=await fetchall("SELECT id,name FROM categories")
    await c.message.edit_text("Выберите категорию для удаления:",reply_markup=kb([[InlineKeyboardButton(text="🗑 "+r["name"],callback_data=f"delcat:{r['id']}")] for r in rows])); await c.answer()

@router.callback_query(F.data.startswith("delcat:"))
async def delcat_do(c:CallbackQuery):
    await execute("DELETE FROM categories WHERE id=?",(int(c.data.split(":")[1]),)); await c.answer("Удалено"); await a_products(c)

@router.callback_query(F.data.startswith("amcat:"))
async def amcat(c:CallbackQuery):
    cid=int(c.data.split(":")[1]); rows=await fetchall("SELECT id,name FROM subcategories WHERE category_id=?",(cid,))
    b=[[InlineKeyboardButton(text=r["name"],callback_data=f"amsub:{r['id']}")] for r in rows]
    b += [[InlineKeyboardButton(text="➕ Подкатегория",callback_data=f"addsub:{cid}")],
          [InlineKeyboardButton(text="⬅️",callback_data="a_products")]]
    await c.message.edit_text("Подкатегории:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("addsub:"))
async def addsub(c:CallbackQuery,state:FSMContext):
    await state.update_data(cid=int(c.data.split(":")[1])); await state.set_state(AddSub.name); await c.message.answer("Название подкатегории:"); await c.answer()

@router.message(AddSub.name)
async def addsub_save(m:Message,state:FSMContext):
    d=await state.get_data(); await execute("INSERT INTO subcategories(category_id,name) VALUES(?,?)",(d["cid"],m.text)); await state.clear(); await m.answer("Подкатегория добавлена.")

@router.callback_query(F.data.startswith("amsub:"))
async def amsub(c:CallbackQuery):
    sid=int(c.data.split(":")[1]); rows=await fetchall("SELECT id,name,price FROM products WHERE subcategory_id=?",(sid,))
    b=[[InlineKeyboardButton(text=f"{r['name']} {r['price']}",callback_data=f"amprod:{r['id']}")] for r in rows]
    b += [[InlineKeyboardButton(text="➕ Товар",callback_data=f"addprod:{sid}")],[InlineKeyboardButton(text="⬅️",callback_data="a_products")]]
    await c.message.edit_text("Товары:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("addprod:"))
async def addprod(c:CallbackQuery,state:FSMContext):
    await state.update_data(sid=int(c.data.split(":")[1])); await state.set_state(AddProd.data)
    await c.message.answer("Введите: название | цена | описание"); await c.answer()

@router.message(AddProd.data)
async def addprod_save(m:Message,state:FSMContext):
    try:
        name,price,desc=[x.strip() for x in m.text.split("|",2)]
        d=await state.get_data(); pid=await execute("INSERT INTO products(subcategory_id,name,price,description) VALUES(?,?,?,?)",(d["sid"],name,float(price),desc))
        await state.clear(); await m.answer(f"Товар #{pid} добавлен.")
    except Exception: await m.answer("Формат: название | цена | описание")

@router.callback_query(F.data.startswith("amprod:"))
async def amprod(c:CallbackQuery):
    pid=int(c.data.split(":")[1]); p=await fetchone("SELECT * FROM products WHERE id=?",(pid,))
    b=[[InlineKeyboardButton(text="➕ Добавить ключ",callback_data=f"addkey:{pid}")],
       [InlineKeyboardButton(text="🗑 Удалить товар",callback_data=f"delprod:{pid}")],
       [InlineKeyboardButton(text="⬅️",callback_data="a_products")]]
    await c.message.edit_text(f"#{pid} {p['name']}\nЦена: {p['price']}\n{p['description']}",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("addkey:"))
async def addkey(c:CallbackQuery,state:FSMContext):
    await state.update_data(pid=int(c.data.split(":")[1])); await state.set_state(AddKey.value); await c.message.answer("Отправьте ключ:"); await c.answer()

@router.message(AddKey.value)
async def addkey_save(m:Message,state:FSMContext):
    d=await state.get_data(); await execute("INSERT INTO keys(product_id,value) VALUES(?,?)",(d["pid"],m.text)); await state.clear(); await m.answer("Ключ добавлен.")

@router.callback_query(F.data.startswith("delprod:"))
async def delprod(c:CallbackQuery):
    await execute("DELETE FROM products WHERE id=?",(int(c.data.split(":")[1]),)); await c.answer("Товар удалён")

@router.callback_query(F.data=="a_admins")
async def admins(c:CallbackQuery):
    rows=await fetchall("SELECT user_id FROM admins")
    b=[[InlineKeyboardButton(text=f"🗑 {r['user_id']}",callback_data=f"deladmin:{r['user_id']}")] for r in rows]
    b += [[InlineKeyboardButton(text="➕ Добавить",callback_data="addadmin")],[InlineKeyboardButton(text="⬅️",callback_data="admin")]]
    await c.message.edit_text("Администраторы:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data=="addadmin")
async def addadmin(c:CallbackQuery,state:FSMContext):
    await state.set_state(AddAdmin.uid); await c.message.answer("Telegram ID нового администратора:"); await c.answer()

@router.message(AddAdmin.uid)
async def addadmin_save(m:Message,state:FSMContext):
    await execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)",(int(m.text),)); await state.clear(); await m.answer("Администратор добавлен.")

@router.callback_query(F.data.startswith("deladmin:"))
async def deladmin(c:CallbackQuery):
    uid=int(c.data.split(":")[1])
    from config import settings
    if uid==settings.owner_id: return await c.answer("Владельца удалить нельзя",show_alert=True)
    await execute("DELETE FROM admins WHERE user_id=?",(uid,)); await c.answer("Удалено")

@router.callback_query(F.data=="a_channels")
async def channels(c:CallbackQuery):
    rows=await fetchall("SELECT id,chat_id,title FROM channels")
    b=[[InlineKeyboardButton(text=f"🗑 {r['title'] or r['chat_id']}",callback_data=f"delch:{r['id']}")] for r in rows]
    b += [[InlineKeyboardButton(text="➕ Добавить",callback_data="addch")],[InlineKeyboardButton(text="⬅️",callback_data="admin")]]
    await c.message.edit_text("Каналы:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data=="addch")
async def addch(c:CallbackQuery,state:FSMContext):
    await state.set_state(AddChannel.value); await c.message.answer("Введите chat_id канала | название"); await c.answer()

@router.message(AddChannel.value)
async def addch_save(m:Message,state:FSMContext):
    x=[z.strip() for z in m.text.split("|",1)]
    await execute("INSERT INTO channels(chat_id,title) VALUES(?,?)",(x[0],x[1] if len(x)>1 else "")); await state.clear(); await m.answer("Канал добавлен.")

@router.callback_query(F.data.startswith("delch:"))
async def delch(c:CallbackQuery):
    await execute("DELETE FROM channels WHERE id=?",(int(c.data.split(":")[1]),)); await c.answer("Удалено")

@router.callback_query(F.data=="a_pay")
async def pays(c:CallbackQuery):
    rows=await fetchall("SELECT * FROM payment_methods")
    b=[[InlineKeyboardButton(text=("✅ " if r["enabled"] else "❌ ")+r["title"],callback_data=f"togglepay:{r['code']}"),
        InlineKeyboardButton(text="⚙️",callback_data=f"payset:{r['code']}")] for r in rows]
    b.append([InlineKeyboardButton(text="⬅️",callback_data="admin")])
    await c.message.edit_text("Способы оплаты:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("togglepay:"))
async def togglepay(c:CallbackQuery):
    code=c.data.split(":")[1]; await execute("UPDATE payment_methods SET enabled=1-enabled WHERE code=?",(code,)); await pays(c)

@router.callback_query(F.data.startswith("payset:"))
async def payset(c:CallbackQuery,state:FSMContext):
    code=c.data.split(":")[1]; await state.update_data(code=code); await state.set_state(PayEdit.details)
    r=await fetchone("SELECT details FROM payment_methods WHERE code=?",(code,))
    await c.message.answer(f"Введите реквизиты/инструкцию для {code}:\nТекущие: {r['details'] or '—'}"); await c.answer()

@router.message(PayEdit.details)
async def payset_save(m:Message,state:FSMContext):
    d=await state.get_data(); await execute("UPDATE payment_methods SET details=? WHERE code=?",(m.text,d["code"])); await state.clear(); await m.answer("Сохранено.")

@router.callback_query(F.data=="a_docs")
async def docs(c:CallbackQuery):
    rows=await fetchall("SELECT code,title FROM documents")
    b=[[InlineKeyboardButton(text=r["title"],callback_data=f"editdoc:{r['code']}")] for r in rows]
    b.append([InlineKeyboardButton(text="⬅️",callback_data="admin")])
    await c.message.edit_text("Документы:",reply_markup=kb(b)); await c.answer()

@router.callback_query(F.data.startswith("editdoc:"))
async def editdoc(c:CallbackQuery,state:FSMContext):
    code=c.data.split(":")[1]; await state.update_data(code=code); await state.set_state(DocEdit.body); await c.message.answer("Отправьте новый текст документа:"); await c.answer()

@router.message(DocEdit.body)
async def editdoc_save(m:Message,state:FSMContext):
    d=await state.get_data(); await execute("UPDATE documents SET body=? WHERE code=?",(m.text,d["code"])); await state.clear(); await m.answer("Документ обновлён.")

@router.callback_query(F.data.startswith(("approve:","reject:")))
async def order_decision(c:CallbackQuery):
    if not await guard(c): return
    action,oid=c.data.split(":"); oid=int(oid)
    order=await fetchone("SELECT * FROM orders WHERE id=?",(oid,))
    if not order: return await c.answer("Заказ не найден",show_alert=True)
    if action=="approve":
        key=await fetchone("SELECT * FROM keys WHERE product_id=? AND sold=0 ORDER BY id LIMIT 1",(order["product_id"],))
        if not key: return await c.answer("Нет свободного ключа",show_alert=True)
        await execute("UPDATE keys SET sold=1 WHERE id=?",(key["id"],))
        await execute("UPDATE orders SET status='paid',key_id=? WHERE id=?",(key["id"],oid))
        await c.bot.send_message(order["user_id"],f"✅ Оплата подтверждена.\nВаш ключ:\n<code>{key['value']}</code>")
        await c.message.edit_text(c.message.text+"\n\n✅ ПОДТВЕРЖДЕНО")
    else:
        await execute("UPDATE orders SET status='rejected' WHERE id=?",(oid,))
        await c.bot.send_message(order["user_id"],f"❌ Оплата по заказу #{oid} отклонена.")
        await c.message.edit_text(c.message.text+"\n\n❌ ОТКЛОНЕНО")
    await c.answer()
