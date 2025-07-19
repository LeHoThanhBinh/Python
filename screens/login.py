import tkinter as tk
from tkinter import messagebox
from db import get_db
import hashlib

class LoginScreen:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        root.title("Đăng nhập")

        tk.Label(root, text="Đăng nhập", font=("Arial", 16)).pack(pady=10)

        tk.Label(root, text="Tên đăng nhập").pack()
        self.username = tk.Entry(root)
        self.username.pack()
        self.username.focus()

        tk.Label(root, text="Mật khẩu").pack()
        self.password = tk.Entry(root, show="*")
        self.password.pack()

        tk.Button(root, text="Đăng nhập", command=self.login).pack(pady=5)
        tk.Button(root, text="Đăng ký", command=app.show_register).pack()

    def login(self):
        username = self.username.get().strip()
        password = self.password.get().strip()

        if not username or not password:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đầy đủ.")
            return

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
        user = c.fetchone()
        conn.close()

        if user:
            self.root.destroy()
            self.app.login_success(user)
        else:
            messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu")
