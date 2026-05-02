from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import settings

bot = Bot(token=settings.BOT_TOKEN)

async def notify_owner(
    owner_telegram_id: str,
    order_id: int,
    client_name: str,
    client_telegram_id: str,
    business_name: str,
    order_details: str
):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"order_confirm_{order_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"order_reject_{order_id}"),
        ]
    ])
    
    text = (
        f"🛎 *Новый заказ #{order_id}*\n\n"
        f"🏢 Бизнес: {business_name}\n"
        f"👤 Клиент: {client_name}\n"
        f"💬 Детали:\n{order_details}"
    )
    
    await bot.send_message(
        chat_id=owner_telegram_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )