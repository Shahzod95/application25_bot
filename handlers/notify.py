from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from database import SessionLocal
from models import Channel

router = Router()

@router.my_chat_member()
async def track_channels(event: ChatMemberUpdated):
    if event.new_chat_member.status in ["administrator", "member"]:
        db = SessionLocal()
        channel = db.query(Channel).filter(Channel.chat_id == str(event.chat.id)).first()
        if not channel:
            channel = Channel(chat_id=str(event.chat.id), title=event.chat.title or "NoName")
            db.add(channel)
        else:
            channel.title = event.chat.title
        db.commit()
        db.close()

    elif event.new_chat_member.status == "left":
        db = SessionLocal()
        channel = db.query(Channel).filter(Channel.chat_id == str(event.chat.id)).first()
        if channel:
            db.delete(channel)
            db.commit()
        db.close()
