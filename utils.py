import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import logging
import google.generativeai as genai
from db import get_db
import json
import re

load_dotenv()
logger = logging.getLogger(__name__)


def get_weather(city):
    """Lấy dữ liệu thời tiết từ OpenWeatherMap."""
    if not city:
        logger.error("Thành phố không được cung cấp.")
        return None
        
    if not os.getenv("OPENWEATHER_API_KEY"):
        logger.error("OPENWEATHER_API_KEY không được thiết lập.")
        return None
        
    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": os.getenv("OPENWEATHER_API_KEY"),
        "units": "metric",
        "lang": "vi"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        weather_data = {
            "temp": data["main"]["temp"],
            "desc": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data.get("wind", {}).get("speed", 0)
        }
        logger.info(f"Lấy thời tiết thành công cho {city}: {weather_data['temp']}°C, {weather_data['desc']}")
        return weather_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi khi kết nối OpenWeather: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"Lỗi phân tích dữ liệu thời tiết: {e}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi lấy thời tiết: {e}")
    
    return None


def get_existing_habits(user_id):
    """Lấy danh sách thói quen hiện có của user từ database."""
    existing_habits = []
    conn = None
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT name, description, category FROM habits WHERE user_id = ?", (user_id,))
        habits = c.fetchall()
        existing_habits = [f"{habit[0]} ({habit[2]})" for habit in habits]
        logger.info(f"Lấy được {len(existing_habits)} thói quen hiện có cho user {user_id}")
        
    except Exception as e:
        logger.error(f"Lỗi khi truy vấn thói quen từ DB: {e}")
        
    finally:
        if conn:
            conn.close()
            
    return existing_habits


def extract_json_from_response(response_text):
    """Trích xuất JSON từ response của Gemini, xử lý các trường hợp response không chuẩn."""
    try:
        # Thử parse trực tiếp JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Tìm JSON trong markdown code block
    json_pattern = r'```json\s*(.*?)\s*```'
    match = re.search(json_pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Tìm JSON bằng cách tìm dấu ngoặc nhọn
    start = response_text.find('{')
    end = response_text.rfind('}')
    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(response_text[start:end+1])
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"Không thể trích xuất JSON từ response: {response_text[:200]}...")
    return None


def create_fallback_habit(weather_desc, current_hour):
    """Tạo thói quen dự phòng khi AI API thất bại."""
    fallback_habits = [
        {
            "name": "Thiền thư giãn",
            "description": "Thực hiện thiền thư giãn để tĩnh tâm và giảm stress",
            "duration": 15,
            "advice": "Tìm một không gian yên tĩnh, ngồi thoải mái và tập trung vào hơi thở"
        },
        {
            "name": "Đọc sách",
            "description": "Dành thời gian đọc sách để nâng cao kiến thức",
            "duration": 30,
            "advice": "Chọn một cuốn sách yêu thích và tạo không gian đọc thoải mái"
        },
        {
            "name": "Viết nhật ký",
            "description": "Ghi lại những suy nghĩ và trải nghiệm trong ngày",
            "duration": 10,
            "advice": "Viết một cách tự nhiên, không cần lo lắng về ngữ pháp"
        }
    ]
    
    habit = random.choice(fallback_habits)
    
    # Tính toán thời gian phù hợp
    if 6 <= current_hour < 12:
        time_slot = f"{current_hour + 1}:00"
        completion_time = f"{current_hour + 1}:{habit['duration']:02d}"
    elif 12 <= current_hour < 18:
        time_slot = f"{current_hour}:30"
        completion_time = f"{current_hour + 1}:{(30 + habit['duration']) % 60:02d}"
    else:
        time_slot = f"{max(7, current_hour)}:00"
        completion_time = f"{max(7, current_hour)}:{habit['duration']:02d}"
    
    return {
        "name": habit["name"],
        "description": habit["description"],
        "time_of_day": time_slot,
        "target_duration": habit["duration"],
        "expected_completion": completion_time,
        "weather_condition": weather_desc,
        "evaluation": "Thói quen dự phòng được tạo tự động",
        "advice": habit["advice"]
    }


def ai_api_suggest_habit(weather, user_id, user_habits=None):
    """Sử dụng Gemini API để tạo gợi ý thói quen ngẫu nhiên dựa trên thời tiết và DB."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY không được thiết lập")
        return create_fallback_habit("không rõ", datetime.now().hour)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        existing_habits = get_existing_habits(user_id) if user_habits is None else user_habits

        temp = weather.get("temp", 25) if weather else 25
        desc = weather.get("desc", "không rõ") if weather else "không rõ"
        humidity = weather.get("humidity", 50) if weather else 50
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute

        # Đảm bảo thời gian gợi ý hợp lý dựa trên giờ hiện tại
        if 0 <= current_hour < 5 or current_hour >= 22:  # Giờ nghỉ ngơi
            suggested_hour = 7  # Gợi ý buổi sáng
        else:
            suggested_hour = current_hour + 1 if current_hour < 23 else 0

        prompt = f"""
        Hãy gợi ý MỘT thói quen mới phù hợp với điều kiện sau:
        - Nhiệt độ: {temp}°C
        - Mô tả: {desc}
        - Độ ẩm: {humidity}%
        - Giờ hiện tại: {current_hour}:{current_minute:02d}
        - Thói quen đã có: {', '.join(existing_habits) if existing_habits else 'Chưa có thói quen nào'}
        YÊU CẦU:
        - KHÁC danh sách hiện có
        - Phù hợp với thời tiết và giờ hiện tại (gợi ý giờ thực hiện gần với {suggested_hour}:00)
        - Thực tế, thời lượng 10-60 phút
        ĐỊNH DẠNG JSON:
        {{
            "ten_thoi_quen": "Tên",
            "mo_ta": "Mô tả",
            "thoi_luong_phut": 30,
            "gio_thuc_hien": "HH:MM",
            "gio_hoan_thanh": "HH:MM",
            "loi_khuyen": "Lời khuyên"
        }}
        """

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    top_p=0.8,
                    top_k=40
                )
            )
        except Exception as api_error:
            logger.warning(f"Lỗi với model chính, dùng model dự phòng: {api_error}")
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)

        if not response or not response.text:
            return create_fallback_habit(desc, current_hour)

        data = extract_json_from_response(response.text)
        if not data:
            return create_fallback_habit(desc, current_hour)

        duration = int(str(data.get("thoi_luong_phut", 30)).split()[0])
        duration = max(10, min(duration, 120))

        # Đảm bảo gio_thuc_hien hợp lý dựa trên giờ hiện tại
        time_of_day = data.get("gio_thuc_hien", f"{suggested_hour}:00")
        if not re.match(r'^\d{1,2}:\d{2}$', time_of_day):
            time_of_day = f"{suggested_hour}:00"
        try:
            start_hour, start_min = map(int, time_of_day.split(':'))
            if start_hour < current_hour or (start_hour == current_hour and start_min < current_minute):
                start_hour = suggested_hour
            if start_hour > 23:
                start_hour = 0
            time_of_day = f"{start_hour:02d}:{start_min:02d}"
        except (ValueError, IndexError):
            time_of_day = f"{suggested_hour}:00"

        # Tính toán gio_hoan_thanh
        try:
            start_hour, start_min = map(int, time_of_day.split(':'))
            total_minutes = start_hour * 60 + start_min + duration
            end_hour = total_minutes // 60 % 24
            end_min = total_minutes % 60
            completion_time = f"{end_hour:02d}:{end_min:02d}"
        except Exception as e:
            logger.warning(f"Lỗi tính giờ hoàn thành: {e}")
            completion_time = f"{(start_hour + 1) % 24:02d}:{(start_min + duration) % 60:02d}"

        return {
            "name": data.get("ten_thoi_quen", "Thói quen mới")[:50],
            "description": data.get("mo_ta", "Mô tả thói quen")[:200],
            "time_of_day": time_of_day,
            "target_duration": duration,
            "expected_completion": completion_time,
            "weather_condition": desc,
            "evaluation": f"Được tạo bởi AI dựa trên thời tiết {temp}°C, {desc}",
            "advice": data.get("loi_khuyen", "Thực hiện đều đặn để đạt kết quả tốt")[:150]
        }

    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {e}")
        return create_fallback_habit(desc, current_hour)

def evaluate_habit_with_weather(weather, time_of_day):
    """Đánh giá xem thời gian thực hiện có phù hợp với thời tiết không."""
    if not weather:
        return False, "Không thể kiểm tra thời tiết. Vui lòng thử lại sau."

    if not time_of_day:
        return False, "Thời gian thực hiện không hợp lệ."

    try:
        hour = int(time_of_day.split(":")[0])
        if hour < 0 or hour > 23:
            return False, "Giờ thực hiện không hợp lệ (0-23)."
    except (ValueError, IndexError):
        return False, "Định dạng thời gian không hợp lệ. Sử dụng định dạng HH:MM."

    desc = weather.get("desc", "").lower()
    temp = weather.get("temp", 25)
    humidity = weather.get("humidity", 50)

    # Kiểm tra điều kiện thời tiết
    weather_warnings = []
    
    if "mưa" in desc or "rain" in desc:
        if 6 <= hour <= 8 or 17 <= hour <= 19:
            weather_warnings.append("Có mưa vào giờ này, không nên tập ngoài trời")
    
    if temp > 35:
        if 11 <= hour <= 15:
            weather_warnings.append("Nắng quá gay gắt giữa trưa, nên chọn thời điểm mát hơn")
    
    if temp < 10:
        if hour < 6 or hour > 22:
            weather_warnings.append("Trời quá lạnh vào giờ này, nên tập vào thời điểm ấm hơn")
    
    if temp > 30 and humidity > 80:
        if 10 <= hour <= 16:
            weather_warnings.append("Thời tiết oi bức, nên tập vào buổi sáng sớm hoặc tối")
    
    # Trả về kết quả
    if weather_warnings:
        return False, ". ".join(weather_warnings)
    
    return True, f"Thời gian phù hợp với điều kiện thời tiết ({temp}°C, {desc})"


def validate_habit_data(habit_data):
    """Validate dữ liệu thói quen trước khi lưu vào database."""
    required_fields = ['name', 'description', 'time_of_day', 'target_duration']
    
    for field in required_fields:
        if not habit_data.get(field):
            return False, f"Thiếu trường bắt buộc: {field}"
    
    # Validate target_duration
    try:
        duration = int(habit_data['target_duration'])
        if duration < 1 or duration > 240:
            return False, "Thời gian mục tiêu phải từ 1 đến 240 phút"
    except (ValueError, TypeError):
        return False, "Thời gian mục tiêu không hợp lệ"
    
    # Validate time format
    time_pattern = r'^\d{1,2}:\d{2}$'
    if not re.match(time_pattern, habit_data['time_of_day']):
        return False, "Định dạng thời gian không hợp lệ (HH:MM)"
    
    return True, "Dữ liệu hợp lệ"


def get_available_models():
    """Lấy danh sách các model Gemini khả dụng."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return []
        
        genai.configure(api_key=api_key)
        models = genai.list_models()
        available_models = [model.name.split('/')[-1] for model in models 
                          if 'generateContent' in model.supported_generation_methods]
        logger.info(f"Các model Gemini khả dụng: {available_models}")
        return available_models
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách model: {e}")
        return []


def test_gemini_connection():
    """Test kết nối và khả năng sử dụng Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False, "GEMINI_API_KEY không được thiết lập"
    
    try:
        genai.configure(api_key=api_key)
        
        # Thử với model mới nhất
        preferred_models = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash', 
            'gemini-1.5-flash-8b'
        ]
        
        for model_name in preferred_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Hello", 
                    generation_config=genai.types.GenerationConfig(max_output_tokens=10))
                if response and response.text:
                    logger.info(f"Model {model_name} hoạt động bình thường")
                    return True, f"Kết nối thành công với {model_name}"
            except Exception as model_error:
                logger.warning(f"Model {model_name} không khả dụng: {model_error}")
                continue
        
        return False, "Không có model nào khả dụng"
        
    except Exception as e:
        logger.error(f"Lỗi khi test Gemini connection: {e}")
        return False, f"Lỗi kết nối: {str(e)}"