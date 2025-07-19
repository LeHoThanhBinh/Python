import tkinter as tk
from tkinter import messagebox
from db import get_db
import hashlib

class RegisterScreen:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        root.title("Đăng ký")

        tk.Label(root, text="Đăng ký", font=("Arial", 16)).pack(pady=10)

        tk.Label(root, text="Tên đăng nhập").pack()
        self.username = tk.Entry(root)
        self.username.pack()

        tk.Label(root, text="Mật khẩu").pack()
        self.password = tk.Entry(root, show="*")
        self.password.pack()

        tk.Label(root, text="Họ tên").pack()
        self.fullname = tk.Entry(root)
        self.fullname.pack()

        tk.Button(root, text="Đăng ký", command=self.register).pack(pady=5)
        tk.Button(root, text="Quay lại đăng nhập", command=self.return_to_login).pack()

    def register(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        fullname = self.fullname.get().strip()

        if not username or not password or not fullname:
            messagebox.showwarning("Lỗi", "Vui lòng nhập đầy đủ thông tin.")
            return

        # Mã hóa mật khẩu
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password, fullname) VALUES (?, ?, ?)",
                (username, hashed_pw, fullname)
            )
            conn.commit()
            messagebox.showinfo("Thành công", "Đăng ký thành công. Vui lòng đăng nhập.")
            self.root.destroy()              # Đóng cửa sổ đăng ký
            self.app.show_login()            # Hiển thị lại đăng nhập
        except Exception:
            messagebox.showerror("Lỗi", "Tên đăng nhập đã tồn tại.")
        finally:
            conn.close()

    def return_to_login(self):
        self.root.destroy()
        self.app.show_login()
