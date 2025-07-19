from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_api_suggest_habit(weather, user_habits):
    desc = weather["desc"]
    temp = weather["temp"]
    existing = ", ".join(user_habits) if user_habits else "chưa có"

    prompt = f"""
    Dựa trên thời tiết hiện tại là "{desc}" với nhiệt độ khoảng {temp}°C,
    và các thói quen người dùng đã có là: {existing}.
    Hãy gợi ý một thói quen mới, đơn giản, phù hợp với sức khỏe thể chất hoặc tinh thần, ngắn gọn trong một câu.
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=60
    )

    return response.choices[0].message.content.strip()
