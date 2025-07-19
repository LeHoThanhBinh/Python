import tkinter as tk
from tkinter import messagebox
from db import get_db

class HabitScreen:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        tk.Label(root, text="Quản lý thói quen", font=("Arial", 16)).pack(pady=10)
        tk.Button(root, text="Dashboard", command=app.show_dashboard).pack(side=tk.LEFT, padx=5)
        tk.Button(root, text="Nội dung giáo dục", command=app.show_content).pack(side=tk.LEFT, padx=5)
        tk.Button(root, text="Đăng xuất", command=app.show_login).pack(side=tk.RIGHT, padx=5)
        self.habit_entry = tk.Entry(root, width=30)
        self.habit_entry.pack(pady=5)
        tk.Button(root, text="Thêm thói quen", command=self.add_habit).pack(pady=5)
        self.habit_frame = tk.Frame(root)
        self.habit_frame.pack(pady=10)
        self.load_habits()

    def add_habit(self):
        name = self.habit_entry.get().strip()
        if not name:
            messagebox.showwarning("Lỗi", "Nhập tên thói quen.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO habits (user_id, name, goal, frequency) VALUES (?, ?, '', '')", (self.app.current_user[0], name))
        conn.commit()
        conn.close()
        self.habit_entry.delete(0, tk.END)
        self.load_habits()

    def load_habits(self):
        for widget in self.habit_frame.winfo_children():
            widget.destroy()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name FROM habits WHERE user_id=?", (self.app.current_user[0],))
        habits = c.fetchall()
        for habit in habits:
            tk.Label(self.habit_frame, text=habit[1]).pack(anchor="w")
        conn.close()
