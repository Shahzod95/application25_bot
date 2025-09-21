from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_IDS, BOT_TOKEN
from database import SessionLocal
from models import Notification, Response, Channel
from database import Base, engine
from utils.keyboards import notification_button, admin_menu
from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import pandas as pd
from aiogram.types import FSInputFile
import os
import openpyxl

router = Router()
user_states = {}

Base.metadata.create_all(bind=engine)

class CreateNotif(StatesGroup):
    waiting_for_data = State()

class CreateNotification(StatesGroup):
    title = State()
    description = State()
    fields = State()


# START
@router.message(F.from_user.id.in_(ADMIN_IDS), F.text == "/start")
async def admin_start(message: Message):
    await message.answer(
        "🔐 Admin panelga xush kelibsiz!\nQuyidagilardan birini tanlang:",
        reply_markup=admin_menu()
    )


# CREATE
@router.callback_query(F.data == "create")
async def cb_create(call: CallbackQuery, state: FSMContext):
    await state.set_state(CreateNotification.title)
    await call.message.answer("📌 Yangi xabarnoma yaratish!\n\nIltimos, avval *Title* yuboring:")
    await call.answer()

# --- STEP 1: TITLE ---
@router.message(F.from_user.id.in_(ADMIN_IDS), CreateNotification.title)
async def step_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateNotification.description)
    await message.answer("📝 Endi *Description* yuboring:")


# --- STEP 2: DESCRIPTION ---
@router.message(F.from_user.id.in_(ADMIN_IDS), CreateNotification.description)
async def step_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(CreateNotification.fields)
    await message.answer("📋 Endi *Fieldlarni* yuboring (vergul bilan):\n\nMasalan: Ism, Telefon, Email")

# --- STEP 3: FIELDS ---
@router.message(F.from_user.id.in_(ADMIN_IDS), CreateNotification.fields)
async def step_fields(message: Message, state: FSMContext):
    fields = [f.strip() for f in message.text.split(",")]
    await state.update_data(fields=fields)

    data = await state.get_data()
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data="confirm_create")
    kb.button(text="❌ Bekor qilish", callback_data="cancel_create")
    kb.adjust(2)

    await message.answer(
        f"📌 Xabarnoma tayyor:\n\n"
        f"📍 Title: {data['title']}\n"
        f"📝 Description: {data['description']}\n"
        f"📋 Fields: {', '.join(fields)}\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=kb.as_markup()
    )

# --- CONFIRM ---
@router.callback_query(F.data == "confirm_create")
async def confirm_create(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    db = SessionLocal()
    notif = Notification(
        title=data["title"],
        description=data["description"],
        fields=data["fields"],
        chat_id=str(call.message.chat.id)
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # 🔹 Kanallar/guruhlar ro‘yxatini chiqaramiz
    channels = db.query(Channel).all()
    db.close()

    if not channels:
        await call.message.answer(
            f"✅ Xabarnoma saqlandi!\n\n📌 {notif.title}\n{notif.description}\n\n"
            "❌ Bot hali hech qanday guruh/kanalda admin emas."
        )
        await state.clear()
        await call.answer()
        return

    kb = InlineKeyboardBuilder()
    for c in channels:
        kb.button(text=c.title, callback_data=f"sendto_{notif.id}_{c.chat_id}")
    kb.adjust(1)

    await call.message.answer(
        f"✅ Xabarnoma saqlandi!\n\n📌 {notif.title}\n{notif.description}\n\n"
        "📥 Endi qaysi guruh/kanalga yuborishni tanlang:",
        reply_markup=kb.as_markup()
    )
    await state.clear()
    await call.answer()



# --- CANCEL ---
@router.callback_query(F.data == "cancel_create")
async def cancel_create(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Xabarnoma yaratish bekor qilindi.")
    await call.answer()



# SEND
@router.message(F.from_user.id.in_(ADMIN_IDS), F.text == "/send")
async def choose_notification(message: Message):
    db = SessionLocal()
    notifs = db.query(Notification).all()
    db.close()

    if not notifs:
        await message.answer("❌ Hali hech qanday xabarnoma yaratilmagan")
        return

    kb = InlineKeyboardBuilder()
    for n in notifs:
        kb.button(text=n.title, callback_data=f"sendnotif_{n.id}")
    kb.adjust(1)

    await message.answer("📌 Qaysi xabarnomani yubormoqchisiz?", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("sendnotif_"))
async def choose_channel(call: CallbackQuery):
    notif_id = int(call.data.split("_")[1])

    db = SessionLocal()
    channels = db.query(Channel).all()
    db.close()

    if not channels:
        await call.message.answer("❌ Bot hali hech qanday guruh/kanalda admin emas")
        return

    kb = InlineKeyboardBuilder()
    for c in channels:
        kb.button(text=c.title, callback_data=f"sendto_{notif_id}_{c.chat_id}")
    kb.adjust(1)

    await call.message.answer(
        "📥 Qaysi guruh/kanalga yuborishni tanlang:",
        reply_markup=kb.as_markup()
    )
    await call.answer()


@router.callback_query(F.data.startswith("sendto_"))
async def send_to_channel(call: CallbackQuery):
    _, notif_id, chat_id = call.data.split("_")

    db = SessionLocal()
    notif = db.query(Notification).filter(Notification.id == int(notif_id)).first()
    db.close()

    if not notif:
        await call.message.answer("❌ Xabarnoma topilmadi")
        return

    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id,
            f"📢 <b>{notif.title}</b>\n\n{notif.description}",
            reply_markup=notification_button(notif.id),
            parse_mode="HTML"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Ortga", callback_data="back_to_menu")
        await call.message.answer("✅ Xabarnoma yuborildi!", reply_markup=kb.as_markup())
    except Exception as e:
        await call.message.answer(f"❌ Xato: {e}")

@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery):
    db = SessionLocal()
    notifs = db.query(Notification).all()

    if notifs:
        kb = InlineKeyboardBuilder()
        text = "📊 Xabarnomalar statistikasi:\n\n"
        for notif in notifs:
            resp_count = db.query(Response).filter(Response.notification_id == notif.id).count()
            # text += f"📌 {notif.title} ➝ {resp_count} ta ariza\n\n"
            kb.button(text=f"📌 {notif.title} ➝ {resp_count} ta ariza", callback_data=f"export_{notif.id}")
        kb.adjust(1)

        # Ortga tugmasini qo‘shamiz
        kb.row()
        kb.button(text="⬅️ Ortga", callback_data="back_to_menu")
        kb.adjust(1)

        await call.message.edit_text(text, reply_markup=kb.as_markup())
    else:
        await call.message.edit_text("📊 Hozircha hech qanday xabarnoma yaratilmagan.\n\n⬅️ Ortga qaytish uchun tugmadan foydalaning.",
                                     reply_markup=InlineKeyboardBuilder()
                                     .button(text="⬅️ Ortga", callback_data="back_to_menu")
                                     .as_markup()
                                     )

    await call.answer()


# Ortga callback handler
@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Yangi xabarnoma yaratish", callback_data="create")
    kb.button(text="📊 Statistikani ko‘rish", callback_data="stats")
    kb.adjust(1)

    await call.message.edit_text(
        "🔐 Admin panelga xush kelibsiz!\nQuyidagilardan birini tanlang:",
        reply_markup=kb.as_markup()
    )
    await call.answer()


@router.callback_query(F.data.startswith("export_"))
async def export_responses(call: CallbackQuery):
    notif_id = int(call.data.split("_")[1])
    db = SessionLocal()

    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    responses = db.query(Response).filter(Response.notification_id == notif_id).all()
    db.close()

    if not notif or not responses:
        await call.message.answer("❌ Bu xabarnoma uchun hali arizalar yo‘q.")
        return

    # Arizalarni dataframe ga aylantiramiz
    data = []
    for r in responses:
        row = {}
        for field_name, value in zip(notif.fields, r.data):
            row[field_name] = value
        data.append(row)

    df = pd.DataFrame(data)

    # Fayl nomi
    file_path = f"export_notif_{notif_id}.xlsx"
    df.to_excel(file_path, index=False, engine="openpyxl")

    # --- Column width sozlash ---
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter  # ustun nomi (A, B, C...)
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)) + 10 )
            except:
                pass
        # +2 buffer beramiz
        adjusted_width = max_length + 2
        ws.column_dimensions[col_letter].width = adjusted_width

    wb.save(file_path)

    # Admin ga fayl yuborish
    await call.message.answer_document(
        FSInputFile(file_path),
        caption=f"📥 {notif.title} arizalari"
    )

    # Faylni o‘chirib tashlash
    os.remove(file_path)



