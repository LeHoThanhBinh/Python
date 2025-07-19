import tkinter as tk

class ContentScreen:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        tk.Label(root, text="Nội dung giáo dục", font=("Arial", 16)).pack(pady=10)
        tk.Button(root, text="Quay lại thói quen", command=app.show_habit).pack()
        # ...hiển thị danh sách bài viết, video, tips...
        tk.Label(root, text="(Chức năng đang phát triển)").pack(pady=20)
