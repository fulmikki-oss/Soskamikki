from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(rows): return InlineKeyboardMarkup(inline_keyboard=rows)

def main_kb(admin=False):
    rows=[[InlineKeyboardButton(text="🛍 Товары",callback_data="cats"),
           InlineKeyboardButton(text="👤 Профиль",callback_data="profile")]]
    if admin: rows.append([InlineKeyboardButton(text="👑 Админ",callback_data="admin")])
    return kb(rows)

def back(): return kb([[InlineKeyboardButton(text="⬅️ Назад",callback_data="home")]])
