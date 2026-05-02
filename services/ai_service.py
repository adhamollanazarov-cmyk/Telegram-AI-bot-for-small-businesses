from groq import AsyncGroq
from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def get_ai_response(
    business_name: str,
    business_description: str,
    faq: str,
    chat_history: list,
    user_message: str,
    business_id: int          # <-- добавили для multi-tenant
) -> tuple[str, bool]:

    system_prompt = f"""Ты — вежливый AI-помощник компании "{business_name}".

О компании:
{business_description}

FAQ:
{faq}

Правила:
- Отвечай только на основе информации о компании
- Если не знаешь ответа — скажи "Уточню у менеджера"
- Отвечай кратко, максимум 3-4 предложения
- Пиши на том же языке что клиент

В конце ответа обязательно добавь одну из меток:
- [STATUS:ORDER] — если клиент описал конкретный заказ с деталями
- [STATUS:INFO] — если это просто вопрос или разговор"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        reply = response.choices[0].message.content

        # Надёжный парсинг статуса
        is_order = "[STATUS:ORDER]" in reply
        clean_reply = reply.replace("[STATUS:ORDER]", "").replace("[STATUS:INFO]", "").strip()

        return clean_reply, is_order

    except Exception as e:
        return "Извините, произошла техническая ошибка. Попробуйте чуть позже.", False