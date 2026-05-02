import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from sqlalchemy import select
from config import settings
from database.db import init_db, AsyncSessionLocal
from database.models import Business
from handlers.owner import (
    setup_handler, update_handler,
    orders_handler, clear_handler,
    order_callback_handler
)
from handlers.client import handle_message

logging.basicConfig(level=logging.INFO)


async def is_owner(telegram_id: str) -> bool:
    """Проверяет — владелец ли пользователь"""
    # Сначала проверяем .env (суперадмин)
    if settings.OWNER_TELEGRAM_ID and telegram_id == settings.OWNER_TELEGRAM_ID:
        return True
    # Затем проверяем БД
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.owner_telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None


async def start(update: Update, context):
    user_id = str(update.effective_user.id)
    owner = await is_owner(user_id)

    if owner:
        await update.message.reply_text(
            "Привет! Вы в панели управления ботом 🛠\n\n"
            "/update — обновить название, описание, FAQ\n"
            "/orders — все заказы\n"
            "/orders new — только новые\n"
            "/clear — очистить свою историю чата",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "Привет! Чем могу помочь?\n"
            "Задайте любой вопрос или опишите что хотите заказать 👇"
        )


def owner_only(handler):
    """Декоратор — только для владельцев бизнеса"""
    async def wrapper(update: Update, context):
        user_id = str(update.effective_user.id)
        if not await is_owner(user_id):
            await update.message.reply_text(
                "Эта команда доступна только владельцам бизнеса.\n"
                "Используйте /setup для регистрации."
            )
            return
        return await handler(update, context)
    return wrapper


async def post_init(application):
    await init_db()


app = Application.builder()\
    .token(settings.BOT_TOKEN)\
    .post_init(post_init)\
    .build()

app.add_handler(CommandHandler("start", start))
app.add_handler(setup_handler)
app.add_handler(update_handler)
app.add_handler(orders_handler)
app.add_handler(clear_handler)
app.add_handler(order_callback_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен!")
app.run_polling()