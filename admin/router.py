from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Business, Order

app = FastAPI(title="Business Bot Admin")

# --- Pydantic схемы ---
class BusinessUpdate(BaseModel):
    name: str
    description: str
    faq: str

class BusinessCreate(BaseModel):
    owner_telegram_id: str
    name: str
    description: str
    faq: str

# --- Dependency ---
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# --- Эндпоинты ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <html>
    <head>
        <title>Bot Admin Panel</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 40px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 10px 0; }
            a { color: #3498db; text-decoration: none; margin-right: 15px; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🤖 Business Bot Admin</h1>
        <div class="card">
            <h3>API Endpoints:</h3>
            <a href="/docs">📖 Swagger UI</a>
            <a href="/businesses">🏢 Все бизнесы</a>
            <a href="/orders">📦 Все заказы</a>
        </div>
    </body>
    </html>
    """

@app.get("/businesses")
async def get_businesses(db=Depends(get_db)):
    result = await db.execute(select(Business))
    businesses = result.scalars().all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "owner_telegram_id": b.owner_telegram_id,
            "description": b.description,
            "faq": b.faq,
            "is_active": b.is_active,
            "created_at": b.created_at,
        }
        for b in businesses
    ]

@app.get("/businesses/{business_id}")
async def get_business(business_id: int, db=Depends(get_db)):
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Бизнес не найден")
    return {
        "id": business.id,
        "name": business.name,
        "owner_telegram_id": business.owner_telegram_id,
        "description": business.description,
        "faq": business.faq,
        "is_active": business.is_active,
    }

@app.put("/businesses/{business_id}")
async def update_business(
    business_id: int,
    data: BusinessUpdate,
    db=Depends(get_db)
):
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Бизнес не найден")
    
    business.name = data.name
    business.description = data.description
    business.faq = data.faq
    await db.commit()
    
    return {"status": "ok", "message": f"Бизнес '{data.name}' обновлён"}

@app.post("/businesses/{business_id}/toggle")
async def toggle_business(business_id: int, db=Depends(get_db)):
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Бизнес не найден")
    
    business.is_active = not business.is_active
    await db.commit()
    
    status = "активирован" if business.is_active else "деактивирован"
    return {"status": "ok", "message": f"Бизнес {status}"}

@app.get("/orders")
async def get_orders(status: str = None, db=Depends(get_db)):
    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    result = await db.execute(query.order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return [
        {
            "id": o.id,
            "business_id": o.business_id,
            "client_name": o.client_name,
            "client_telegram_id": o.client_telegram_id,
            "details": o.details,
            "status": o.status,
            "created_at": o.created_at,
        }
        for o in orders
    ]

@app.get("/orders/{order_id}")
async def get_order(order_id: int, db=Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order

@app.put("/orders/{order_id}/status")
async def update_order(
    order_id: int,
    status: str,
    db=Depends(get_db)
):
    if status not in ["new", "confirmed", "rejected", "done"]:
        raise HTTPException(status_code=400, detail="Неверный статус")
    
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    order.status = status
    await db.commit()
    return {"status": "ok", "message": f"Заказ #{order_id} → {status}"}