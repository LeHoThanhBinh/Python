import tkinter as tk
from screens.login import LoginScreen
from screens.register import RegisterScreen
from screens.habit import HabitScreen
from screens.dashboard import DashboardScreen
from screens.content import ContentScreen

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sustainable Lifestyle App")
        self.current_user = None
        self.show_login()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_screen()
        LoginScreen(self.root, self)

    def show_register(self):
        self.clear_screen()
        RegisterScreen(self.root, self)

    def login_success(self, user):
        self.current_user = user
        self.show_habit()

    def show_habit(self):
        self.clear_screen()
        HabitScreen(self.root, self)

    def show_dashboard(self):
        self.clear_screen()
        DashboardScreen(self.root, self)

    def show_content(self):
        self.clear_screen()
        ContentScreen(self.root, self)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
