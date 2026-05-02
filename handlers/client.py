from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from datetime import datetime
from database.db import AsyncSessionLocal
from database.models import Business, ChatSession, Order
from services.ai_service import get_ai_response
from services.order_service import create_order
from services.notification_service import notify_owner


async def get_business_for_chat(chat_id: str) -> Business | None:
    """
    Находит бизнес по chat_id.
    Логика: если у пользователя есть свой бизнес — он владелец,
    иначе ищем бизнес у которого этот chat привязан к сессии,
    иначе берём первый активный (для демо/одного бизнеса).
    """
    async with AsyncSessionLocal() as session:
        # Сначала проверяем — может сам владелец пишет
        result = await session.execute(
            select(Business).where(
                Business.owner_telegram_id == chat_id,
                Business.is_active == True
            )
        )
        owned = result.scalar_one_or_none()
        if owned:
            return owned

        # Ищем бизнес с которым у клиента уже есть сессия
        session_result = await session.execute(
            select(ChatSession).where(
                ChatSession.client_telegram_id == chat_id
            ).order_by(ChatSession.updated_at.desc()).limit(1)
        )
        existing_session = session_result.scalar_one_or_none()

        if existing_session:
            biz_result = await session.execute(
                select(Business).where(
                    Business.id == existing_session.business_id,
                    Business.is_active == True
                )
            )
            return biz_result.scalar_one_or_none()

        # Fallback — первый активный бизнес
        fallback = await session.execute(
            select(Business).where(Business.is_active == True).limit(1)
        )
        return fallback.scalar_one_or_none()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client_id = str(update.effective_user.id)
    client_name = update.effective_user.full_name
    user_text = update.message.text

    business = await get_business_for_chat(client_id)

    if not business:
        await update.message.reply_text("Бот ещё не настроен.")
        return

    async with AsyncSessionLocal() as session:
        session_result = await session.execute(
            select(ChatSession).where(
                ChatSession.business_id == business.id,
                ChatSession.client_telegram_id == client_id
            )
        )
        chat_session = session_result.scalar_one_or_none()

        if not chat_session:
            chat_session = ChatSession(
                business_id=business.id,
                client_telegram_id=client_id,
                messages=[]
            )
            session.add(chat_session)
            await session.flush()

        await update.message.chat.send_action("typing")

        ai_reply, is_order = await get_ai_response(
            business_name=business.name,
            business_description=business.description or "",
            faq=business.faq or "",
            chat_history=chat_session.messages,
            user_message=user_text,
            business_id=business.id
        )

        # Лимит истории — храним последние 50 сообщений
        new_messages = chat_session.messages + [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": ai_reply}
        ]
        chat_session.messages = new_messages[-50:]
        chat_session.updated_at = datetime.utcnow()
        await session.commit()

    if is_order:
        order = await create_order(
            business_id=business.id,
            client_telegram_id=client_id,
            client_name=client_name,
            details=user_text
        )
        await notify_owner(
            owner_telegram_id=business.owner_telegram_id,
            order_id=order.id,
            client_name=client_name,
            client_telegram_id=client_id,
            business_name=business.name,
            order_details=user_text
        )

    await update.message.reply_text(ai_reply)