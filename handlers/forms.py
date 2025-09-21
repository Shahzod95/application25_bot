from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import Notification, Response
from utils.keyboards import edit_button

router = Router()


class FillForm(StatesGroup):
    notif_id = State()
    current_field = State()
    answers = State()
    edit_id = State()
    edit_field = State()


# /start notif_xxx orqali boshlash
@router.message(F.text.startswith("/start notif_"))
async def start_notif(message: Message, state: FSMContext):
    notif_id = int(message.text.split("_")[1])

    db = SessionLocal()
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    db.close()

    if not notif:
        await message.answer("❌ Xabarnoma topilmadi.")
        return

    # eski response bormi?
    db = SessionLocal()
    resp = db.query(Response).filter(
        Response.notification_id == notif_id,
        Response.user_id == str(message.from_user.id)
    ).first()
    db.close()

    if resp:
        await message.answer(
            "⚠️ Siz allaqachon ariza topshirgansiz.\n"
            "Hoziroq qayta kiritilayotgan ma’lumotlar eski arizangizni yangilaydi ✅"
        )
        old_answers = resp.data
    else:
        old_answers = []

    await state.update_data(
        notif_id=notif_id,
        fields=notif.fields,
        answers=old_answers,
        edit_id=None
    )
    await state.set_state(FillForm.current_field)

    # qaysi fielddan boshlash kerak?
    next_index = len(old_answers)
    if next_index < len(notif.fields):
        await state.set_state(FillForm.current_field)
        await message.answer(f"✍️ Iltimos, {notif.fields[next_index]} ni kiriting:")
    else:
        # barcha maydonlar to‘ldirilgan
        kb = InlineKeyboardBuilder()
        kb.button(text="✏️ Tahrirlash", callback_data=f"edit_{resp.id}")
        kb.button(text="❌ Bekor qilish", callback_data="cancel")
        kb.adjust(1)

        await message.answer(
            "✅ Siz barcha maydonlarni to‘ldirgansiz.\n"
            "Xohlaysizmi, arizani tahrirlash?",
            reply_markup=kb.as_markup()
        )


# Ketma-ket fieldlarni olish
@router.message(FillForm.current_field)
async def fill_fields(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data["fields"]
    answers = data.get("answers", [])
    answers.append(message.text.strip())
    await state.update_data(answers=answers)

    if len(answers) < len(fields):
        next_field = fields[len(answers)]
        await message.answer(f"✍️ Endi {next_field} ni kiriting:")
        return

    # Hammasi to‘ldirildi
    notif_id = data["notif_id"]
    user_id = str(message.from_user.id)

    db = SessionLocal()
    try:
        resp = db.query(Response).filter(
            Response.notification_id == notif_id,
            Response.user_id == user_id
        ).first()

        if resp:
            resp.data = answers
            db.commit()
            await message.answer(
                "✅ Arizangiz yangilandi!", 
                # reply_markup=edit_button(resp.id)
                )
        else:
            resp = Response(
                notification_id=notif_id,
                user_id=user_id,
                data=answers
            )
            db.add(resp)
            db.commit()
            db.refresh(resp)
            await message.answer(
                "✅ Arizangiz muvaffaqiyatli saqlandi!",
                reply_markup=edit_button(resp.id)
            )
    except IntegrityError:
        db.rollback()
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko‘ring.")
    finally:
        db.close()
        await state.clear()



@router.callback_query(F.data.startswith("edit_"))
async def edit_response(call: CallbackQuery, state: FSMContext):
    resp_id = int(call.data.split("_")[1])
    db = SessionLocal()
    resp = db.query(Response).filter(Response.id == resp_id).first()
    notif = resp.notification if resp else None
    db.close()

    if not resp or not notif:
        await call.message.answer("❌ Ariza topilmadi.")
        return

    await state.update_data(
        notif_id=notif.id,
        fields=notif.fields,
        answers=[],   # bo‘shatamiz
        edit_id=resp.id
    )
    await state.set_state(FillForm.current_field)

    await call.message.answer(
        f"✏️ Arizani qayta to‘ldirishni boshlaymiz.\n"
        f"Oldingi ma'lumotlar: {resp.data}\n\n"
        f"Endi {notif.fields[0]} ni kiriting:"
    )


@router.callback_query(F.data.startswith("edit_field_"))
async def edit_field(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
    resp_id = int(parts[2])
    field_name = parts[3]

    await state.update_data(edit_id=resp_id, edit_field=field_name)
    await call.message.answer(f"✏️ Yangi {field_name} ni kiriting:")
    await state.set_state(FillForm.edit_field)


@router.message(FillForm.edit_field)
async def save_field_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    resp_id = data["edit_id"]
    field_name = data["edit_field"]

    db = SessionLocal()
    resp = db.query(Response).filter(Response.id == resp_id).first()
    if resp:
        resp.data[field_name] = message.text.strip()
        db.commit()
        await message.answer(f"✅ {field_name} muvaffaqiyatli yangilandi!")
    db.close()

    await state.clear()

@router.callback_query(F.data == "cancel")
async def cancel_action(call: CallbackQuery, state: FSMContext):
    # FSM holatini tozalaymiz
    await state.clear()
    
    # Foydalanuvchiga xabar yuboramiz
    await call.message.answer("❌ Ariza bekor qilindi. Sizning ma'lumotlaringiz saqlanmadi.")
    
    # Callbackni javobsiz qoldirmaymiz
    await call.answer()
