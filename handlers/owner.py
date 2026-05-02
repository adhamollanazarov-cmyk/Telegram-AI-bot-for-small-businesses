from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Business, Order, ChatSession
from services.order_service import update_order_status

# Состояния разговора
NAME, DESCRIPTION, FAQ = range(3)
UPDATE_NAME, UPDATE_DESC, UPDATE_FAQ = range(3, 6)

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Владелец начинает настройку своего бизнеса"""
    user_id = str(update.effective_user.id)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.owner_telegram_id == user_id)
        )
        existing = result.scalar_one_or_none()
    
    if existing:
        await update.message.reply_text(
            f"У вас уже есть бизнес: *{existing.name}*\n"
            f"Используйте /update для обновления данных.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Привет! Настроим вашего AI-помощника.\n\n"
        "Как называется ваш бизнес?"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Отлично! Теперь напишите описание компании:\n"
        "_(чем занимаетесь, адрес, режим работы)_",
        parse_mode="Markdown"
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "Теперь добавьте FAQ — частые вопросы и ответы.\n\n"
        "Формат:\n"
        "*Вопрос: Как сделать заказ?*\n"
        "*Ответ: Напишите нам в боте...*\n\n"
        "Можно в свободной форме.",
        parse_mode="Markdown"
    )
    return FAQ

async def get_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = str(update.effective_user.id)
    
    async with AsyncSessionLocal() as session:
        business = Business(
            owner_telegram_id=owner_id,
            name=context.user_data["name"],
            description=context.user_data["description"],
            faq=update.message.text,
        )
        session.add(business)
        await session.commit()
    
    await update.message.reply_text(
        f"Бизнес *{context.user_data['name']}* создан!\n\n"
        f"Ваш бот готов к работе. Клиенты могут писать сюда 24/7.\n"
        f"Вы будете получать уведомления о заказах.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Собираем ConversationHandler
setup_handler = ConversationHandler(
    entry_points=[CommandHandler("setup", setup_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        FAQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faq)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)

async def handle_order_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    action = parts[1]
    order_id = int(parts[2])
    
    if action == "confirm":
        await update_order_status(order_id, "confirmed")
        await query.edit_message_text(
            query.message.text + "\n\n✅ *Заказ принят!*",
            parse_mode="Markdown"
        )
    elif action == "reject":
        await update_order_status(order_id, "rejected")
        await query.edit_message_text(
            query.message.text + "\n\n❌ *Заказ отклонён*",
            parse_mode="Markdown"
        )

order_callback_handler = CallbackQueryHandler(
    handle_order_callback,
    pattern="^order_"
)



# ===== /update — обновление данных бизнеса =====

UPDATE_NAME, UPDATE_DESC, UPDATE_FAQ = range(3, 6)  # 3,4,5 чтобы не пересекаться с setup

async def update_start(update, context):
    user_id = str(update.effective_user.id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.owner_telegram_id == user_id)
        )
        business = result.scalar_one_or_none()

    if not business:
        await update.message.reply_text(
            "Эта команда только для владельцев.\n/setup — зарегистрировать бизнес."
        )
        return ConversationHandler.END
    
    context.user_data["business_id"] = business.id
    await update.message.reply_text(
        f"Обновляем *{business.name}*\n\n"
        f"Текущее название: `{business.name}`\n\n"
        f"Введите новое название (или /skip чтобы оставить):",
        parse_mode="Markdown"
    )
    return UPDATE_NAME

async def update_name(update, context):
    if update.message.text != "/skip":
        context.user_data["new_name"] = update.message.text
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.id == context.user_data["business_id"])
        )
        business = result.scalar_one_or_none()
    
    await update.message.reply_text(
        f"Текущее описание:\n`{business.description}`\n\n"
        f"Введите новое описание (или /skip):",
        parse_mode="Markdown"
    )
    return UPDATE_DESC

async def update_desc(update, context):
    if update.message.text != "/skip":
        context.user_data["new_desc"] = update.message.text
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.id == context.user_data["business_id"])
        )
        business = result.scalar_one_or_none()
    
    await update.message.reply_text(
        f"Текущий FAQ:\n`{business.faq}`\n\n"
        f"Введите новый FAQ (или /skip):",
        parse_mode="Markdown"
    )
    return UPDATE_FAQ

async def update_faq(update, context):
    if update.message.text != "/skip":
        context.user_data["new_faq"] = update.message.text
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business).where(Business.id == context.user_data["business_id"])
        )
        business = result.scalar_one_or_none()
        
        if "new_name" in context.user_data:
            business.name = context.user_data["new_name"]
        if "new_desc" in context.user_data:
            business.description = context.user_data["new_desc"]
        if "new_faq" in context.user_data:
            business.faq = context.user_data["new_faq"]
        
        await session.commit()
        updated_name = business.name
    
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Бизнес *{updated_name}* обновлён!\n"
        f"Бот уже использует новые данные.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

update_handler = ConversationHandler(
    entry_points=[CommandHandler("update", update_start)],
    states={
        UPDATE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, update_name),
            CommandHandler("skip", update_name),
        ],
        UPDATE_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, update_desc),
            CommandHandler("skip", update_desc),
        ],
        UPDATE_FAQ: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, update_faq),
            CommandHandler("skip", update_faq),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


# ===== /orders — список заказов для владельца =====

async def owner_orders(update, context):
    user_id = str(update.effective_user.id)
    
    async with AsyncSessionLocal() as session:
        # Находим бизнес владельца
        biz_result = await session.execute(
            select(Business).where(Business.owner_telegram_id == user_id)
        )
        business = biz_result.scalar_one_or_none()
        
        if not business:
            await update.message.reply_text("У вас нет бизнеса. Используйте /setup")
            return
        
        # Берём последние 10 заказов
        orders_result = await session.execute(
            select(Order)
            .where(Order.business_id == business.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        orders = orders_result.scalars().all()
    
    if not orders:
        await update.message.reply_text("📭 Заказов пока нет.")
        return
    
    # Иконки статусов
    status_icons = {
        "new": "🆕",
        "confirmed": "✅",
        "rejected": "❌",
        "done": "🏁"
    }
    
    text = f"📦 *Последние заказы — {business.name}*\n\n"
    
    for order in orders:
        icon = status_icons.get(order.status, "❓")
        date = order.created_at.strftime("%d.%m %H:%M")
        # Обрезаем детали если длинные
        details = order.details[:60] + "..." if len(order.details) > 60 else order.details
        text += (
            f"{icon} *Заказ #{order.id}* — {date}\n"
            f"👤 {order.client_name}\n"
            f"💬 {details}\n\n"
        )
    
    text += "_/orders new — только новые_"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def owner_orders_filtered(update, context):
    """/orders new — только новые заказы"""
    user_id = str(update.effective_user.id)
    filter_status = context.args[0] if context.args else None
    
    async with AsyncSessionLocal() as session:
        biz_result = await session.execute(
            select(Business).where(Business.owner_telegram_id == user_id)
        )
        business = biz_result.scalar_one_or_none()
        
        if not business:
            await update.message.reply_text("У вас нет бизнеса.")
            return
        
        query = select(Order).where(Order.business_id == business.id)
        if filter_status:
            query = query.where(Order.status == filter_status)
        query = query.order_by(Order.created_at.desc()).limit(10)
        
        orders_result = await session.execute(query)
        orders = orders_result.scalars().all()
    
    if not orders:
        status_text = f"со статусом '{filter_status}'" if filter_status else ""
        await update.message.reply_text(f"📭 Заказов {status_text} нет.")
        return
    
    status_icons = {"new": "🆕", "confirmed": "✅", "rejected": "❌", "done": "🏁"}
    text = f"📦 *Заказы{' — ' + filter_status if filter_status else ''}*\n\n"
    
    for order in orders:
        icon = status_icons.get(order.status, "❓")
        date = order.created_at.strftime("%d.%m %H:%M")
        details = order.details[:60] + "..." if len(order.details) > 60 else order.details
        text += f"{icon} *#{order.id}* {date}\n👤 {order.client_name}\n💬 {details}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

orders_handler = CommandHandler("orders", owner_orders_filtered)


# ===== /clear — очистка истории чата =====

async def clear_history(update, context):
    client_id = str(update.effective_user.id)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.client_telegram_id == client_id
            )
        )
        sessions = result.scalars().all()
        
        if not sessions:
            await update.message.reply_text("История чата уже пуста.")
            return
        
        for chat_session in sessions:
            chat_session.messages = []
        
        await session.commit()
    
    await update.message.reply_text(
        "🗑 История диалога очищена.\n"
        "Бот начнёт разговор заново!"
    )

clear_handler = CommandHandler("clear", clear_history)