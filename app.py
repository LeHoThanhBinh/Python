from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from db import get_db, init_db
from utils import get_weather, evaluate_habit_with_weather, ai_api_suggest_habit
from datetime import date, datetime
import os
from dotenv import load_dotenv
import logging

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "f6f8e1800dee43aeb1882a1e637b1297")

@app.before_request
def setup():
    if not hasattr(app, 'db_initialized'):
        init_db()
        app.db_initialized = True

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, fullname FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user and len(user) >= 2:  # Đảm bảo user có đủ dữ liệu
            user_id = user[0]
            logger.debug(f"User {username} logged in successfully.")
            return redirect(url_for("dashboard", user_id=user_id))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu")
            logger.warning(f"Failed login attempt for username: {username}")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        fullname = request.form["fullname"]
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, fullname) VALUES (?, ?, ?)",
                      (username, password, fullname))
            conn.commit()
            flash("Đăng ký thành công. Vui lòng đăng nhập.")
            logger.info(f"User {username} registered successfully.")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Tên đăng nhập đã tồn tại.")
            logger.error(f"Registration failed for {username}: {str(e)}")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/dashboard/<int:user_id>", methods=["GET"])
def dashboard(user_id):
    today = date.today().isoformat()
    conn = get_db()
    c = conn.cursor()

    # Lấy fullname và id an toàn
    c.execute("SELECT fullname, id FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user or len(user) < 2:
        logger.error(f"User with ID {user_id} not found or data invalid.")
        flash("Người dùng không tồn tại hoặc dữ liệu không hợp lệ.")
        return redirect(url_for("login"))

    # Lấy thông tin thời tiết nếu có city
    weather_city = request.args.get("city")
    suggestion = request.args.get("suggestion")
    weather = get_weather(weather_city) if weather_city else None
    logger.debug(f"Weather for {weather_city}: {weather}")

    # Thói quen chưa hoàn thành
    c.execute("""
        SELECT h.id, h.name, h.description, h.category, h.frequency, h.target_duration,
               h.city, h.time_of_day, h.created_date, h.weather_condition, h.evaluation, h.advice
        FROM habits h
        WHERE h.user_id = ? AND h.id NOT IN (
            SELECT habit_id FROM habit_tracking 
            WHERE date = ? AND completed = 1
        )
    """, (user_id, today))
    columns = [desc[0] for desc in c.description]
    pending_habits = [dict(zip(columns, row)) for row in c.fetchall()]
    logger.debug(f"Pending habits for user {user_id}: {pending_habits}")

    # Thói quen đã hoàn thành
    c.execute("""
        SELECT h.name, h.time_of_day, h.description, h.target_duration, ht.timestamp
        FROM habits h
        JOIN habit_tracking ht ON h.id = ht.habit_id
        WHERE h.user_id = ? AND ht.date = ? AND ht.completed = 1
    """, (user_id, today))
    columns = [desc[0] for desc in c.description]
    completed_habits = [dict(zip(columns, row)) for row in c.fetchall()]
    logger.debug(f"Completed habits for user {user_id}: {completed_habits}")

    # Nội dung tĩnh từ bảng content
    c.execute("SELECT title, body FROM content")
    contents = c.fetchall()
    logger.debug(f"Contents: {contents}")

    conn.close()

    return render_template("dashboard.html",
                           fullname=user[0],
                           user_id=user[1],
                           pending_habits=pending_habits,
                           completed_habits=completed_habits,
                           contents=contents,
                           weather=weather,
                           weather_city=weather_city,
                           suggestion=suggestion)

@app.route("/create_habit/<int:user_id>", methods=["GET", "POST"])
def create_habit(user_id):
    weather_city = request.args.get("city")
    weather = get_weather(weather_city) if weather_city else None
    logger.debug(f"Creating habit for user {user_id}, city: {weather_city}, weather: {weather}")

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        category = request.form["category"]
        frequency = request.form["frequency"]
        time_of_day = request.form["time_of_day"]

        try:
            target_duration = int(request.form["target_duration"])
            if target_duration < 1 or target_duration > 240:
                flash("Thời gian mục tiêu phải từ 1 đến 240 phút.")
                logger.warning(f"Invalid target duration: {target_duration}")
                return render_template("habits.html", user_id=user_id, weather=weather, city=weather_city)
        except ValueError:
            flash("Thời gian mục tiêu không hợp lệ.")
            logger.error("Invalid target duration format.")
            return render_template("habits.html", user_id=user_id, weather=weather, city=weather_city)

        valid, message = evaluate_habit_with_weather(weather, time_of_day)
        if not valid:
            flash(message)
            logger.warning(f"Habit evaluation failed: {message}")
            return render_template("habits.html", user_id=user_id, weather=weather, city=weather_city)

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO habits (user_id, name, description, category, frequency, target_duration, city, time_of_day)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, description, category, frequency, target_duration, weather_city, time_of_day))
        conn.commit()
        conn.close()

        flash("Tạo thói quen thành công!")
        logger.info(f"Habit created for user {user_id}: {name}")
        return redirect(url_for("dashboard", user_id=user_id, city=weather_city))

    return render_template("habits.html", user_id=user_id, weather=weather, weather_city=weather_city)

@app.route("/track_habit/<int:habit_id>", methods=["POST"])
def track_habit(habit_id):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    completed = 1 if "complete" in request.form else 0
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO habit_tracking (habit_id, date, completed, timestamp) VALUES (?, ?, ?, ?)",
              (habit_id, date_str, completed, timestamp_str))
    conn.commit()
    conn.close()
    flash("Đã ghi nhận hoạt động.")
    logger.info(f"Habit {habit_id} tracked, completed: {completed}")
    return redirect(request.referrer or url_for("dashboard", user_id=1))

@app.route("/suggest_habit/<int:user_id>", methods=["POST"])
def suggest_habit(user_id):
    city = request.form.get("city")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not city:
        message = "Vui lòng chọn thành phố trước khi gợi ý thói quen."
        logger.warning("No city provided for habit suggestion.")
        if is_ajax:
            return jsonify(success=False, error=message), 400
        flash(message)
        return redirect(url_for("dashboard", user_id=user_id))

    weather = get_weather(city)
    if not weather:
        message = "Không thể lấy dữ liệu thời tiết."
        logger.error(f"Failed to get weather data for {city}.")
        if is_ajax:
            return jsonify(success=False, error=message), 500
        flash(message)
        return redirect(url_for("dashboard", user_id=user_id, city=city))

    conn = get_db()
    c = conn.cursor()

    try:
        suggestion = ai_api_suggest_habit(weather, user_id)
        if not suggestion:
            message = "Không thể tạo thói quen từ AI."
            logger.warning(message)
            if is_ajax:
                return jsonify(success=False, error=message), 500
            flash(message)
            return redirect(url_for("dashboard", user_id=user_id, city=city))

        name = suggestion.get("name", "Thói quen mới")[:50]
        description = suggestion.get("description", "Mô tả mới")
        time_of_day = suggestion.get("time_of_day", "09:00")
        target_duration = suggestion.get("target_duration", 30)
        weather_condition = suggestion.get("weather_condition", weather.get("desc", "Không rõ"))
        evaluation = suggestion.get("evaluation", "Phù hợp")
        advice = suggestion.get("advice", "Chuẩn bị đầy đủ")

        c.execute("""
            INSERT INTO habits (
                user_id, name, description, category, frequency,
                target_duration, city, time_of_day, created_date,
                weather_condition, evaluation, advice
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?, ?)
        """, (
            user_id, name, description, "Tự tạo", "Hằng ngày",
            target_duration, city, time_of_day,
            weather_condition, evaluation, advice
        ))
        conn.commit()
        logger.info(f"Suggested habit created for user {user_id}: {name}")
    except Exception as e:
        conn.rollback()
        message = f"Lỗi khi tạo thói quen: {str(e)}"
        logger.error(message)
        if is_ajax:
            return jsonify(success=False, error=message), 500
        flash(message)
        return redirect(url_for("dashboard", user_id=user_id, city=city))
    finally:
        conn.close()

    message = "Đã tạo một thói quen dựa trên thời tiết."
    if is_ajax:
        return jsonify(success=True, num_activities=1)
    flash(message)
    return redirect(url_for("dashboard", user_id=user_id, city=city))

@app.route("/logout")
def logout():
    logger.info("User logged out.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)