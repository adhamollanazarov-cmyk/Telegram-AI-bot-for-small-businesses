from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Order, Business

async def create_order(
    business_id: int,
    client_telegram_id: str,
    client_name: str,
    details: str
) -> Order:
    async with AsyncSessionLocal() as session:
        order = Order(
            business_id=business_id,
            client_telegram_id=client_telegram_id,
            client_name=client_name,
            details=details,
            status="new"
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

async def update_order_status(order_id: int, status: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            order.status = status
            await session.commit()
        return order