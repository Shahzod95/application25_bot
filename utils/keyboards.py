from aiogram.utils.keyboard import InlineKeyboardBuilder

def notification_button(notif_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✍️ Ariza qoldirish",
        url=f"https://t.me/application25_bot?start=notif_{notif_id}"
    )
    return kb.as_markup()

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 Yangi xabarnoma yaratish", callback_data="create")
    kb.button(text="📊 Statistika ko‘rish", callback_data="stats")
    kb.adjust(1)
    return kb.as_markup()

def edit_button(resp_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Arizani tahrirlash", callback_data=f"edit_{resp_id}")
    return kb.as_markup()

def field_edit_buttons(resp_id: int, fields: list):
    kb = InlineKeyboardBuilder()
    for f in fields:
        kb.button(text=f"✏️ {f}", callback_data=f"edit_field_{resp_id}_{f}")
    kb.adjust(1)
    return kb.as_markup()