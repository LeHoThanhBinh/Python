import sqlite3

def get_db():
    return sqlite3.connect("d:\\SCIS1\\app.db")

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Bảng người dùng
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL
    )''')

    # Bảng thói quen
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        frequency TEXT,
        target_duration INTEGER,
        city TEXT,
        time_of_day TEXT,
        created_date TEXT DEFAULT (datetime('now', 'localtime')),
        weather_condition TEXT,
        evaluation TEXT,
        advice TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Bảng theo dõi hoàn thành thói quen
    c.execute('''CREATE TABLE IF NOT EXISTS habit_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        timestamp TEXT,
        FOREIGN KEY (habit_id) REFERENCES habits(id)
    )''')

    # Thêm cột timestamp nếu chưa có (chống lỗi khi đã tồn tại bảng cũ)
    try:
        c.execute("SELECT timestamp FROM habit_tracking LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE habit_tracking ADD COLUMN timestamp TEXT")

    # Bảng nội dung tin tức, bài viết
    c.execute('''CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        type TEXT CHECK(type IN ('Môi trường', 'Sức khỏe', 'Lối sống', 'Khác')) NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )''')

    conn.commit()
    conn.close()
