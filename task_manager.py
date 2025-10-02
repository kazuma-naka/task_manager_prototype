import sqlite3
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox
# FIXED: Import Querybox instead of the base Dialog class
from ttkbootstrap.dialogs.dialogs import Querybox
from ttkbootstrap.constants import *
import os


class DatabaseManager:
    """Handles all database operations for the Task Manager."""

    def __init__(self, db_name="task_manager.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS USER (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS COURSE (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT NOT NULL, description TEXT,
            FOREIGN KEY (user_id) REFERENCES USER (id) ON DELETE CASCADE
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS TASK (
            id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, name TEXT NOT NULL, description TEXT, due_date TEXT,
            FOREIGN KEY (course_id) REFERENCES COURSE (id) ON DELETE CASCADE
        )""")
        self.conn.commit()

    def execute_query(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch_query(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()


class App(ttk.Window):
    """The main application window that controls frame switching and session management."""
    SESSION_FILE = "session.txt"

    def __init__(self, db_manager):
        super().__init__(themename="superhero")
        self.db = db_manager
        self.title("Task Manager")
        self.geometry("900x600")
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (LoginFrame, TaskManagerFrame):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.check_session()

    def check_session(self):
        if os.path.exists(self.SESSION_FILE):
            with open(self.SESSION_FILE, 'r') as f:
                user_id = f.read()
                if user_id:
                    self.login_successful(int(user_id))
                    return
        self.show_frame(LoginFrame)

    def login_successful(self, user_id):
        with open(self.SESSION_FILE, 'w') as f:
            f.write(str(user_id))
        task_manager_frame = self.frames[TaskManagerFrame]
        task_manager_frame.set_user(user_id)
        self.show_frame(TaskManagerFrame)

    def logout(self):
        if os.path.exists(self.SESSION_FILE):
            os.remove(self.SESSION_FILE)
        self.title("Task Manager")
        self.show_frame(LoginFrame)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()


class LoginFrame(ttk.Frame):
    """The initial frame for user login or registration."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = controller.db
        login_container = ttk.Frame(self, padding=30)
        login_container.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(login_container, text="Welcome!",
                  font="-family Barlow -size 24 -weight bold").pack(pady=20)
        ttk.Label(login_container, text="Name:").pack(
            fill='x', padx=5, pady=(5, 0))
        self.name_entry = ttk.Entry(login_container, width=40)
        self.name_entry.pack(pady=5, ipady=4)
        ttk.Label(login_container, text="Email:").pack(
            fill='x', padx=5, pady=(5, 0))
        self.email_entry = ttk.Entry(login_container, width=40)
        self.email_entry.pack(pady=5, ipady=4)
        ttk.Button(login_container, text="Login / Register", command=self.handle_login,
                   bootstyle="success").pack(pady=20, ipady=8, fill='x')

    def handle_login(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        if not name or not email:
            Messagebox.show_error(
                "Name and Email cannot be empty.", "Input Error")
            return
        user = self.db.fetch_query(
            "SELECT id FROM USER WHERE email = ?", (email,))
        if user:
            user_id = user[0][0]
        else:
            user_id = self.db.execute_query(
                "INSERT INTO USER (name, email) VALUES (?, ?)", (name, email))
            Messagebox.show_info(
                f"User '{name}' registered successfully.", "Welcome!")
        self.controller.login_successful(user_id)


class TaskManagerFrame(ttk.Frame):
    """The main application screen for managing tasks and courses."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = controller.db
        self.current_user_id = None
        top_bar = ttk.Frame(self, padding=(10, 10, 10, 0))
        top_bar.pack(fill=tk.X)
        self.user_label = ttk.Label(
            top_bar, text="Welcome, User!", font=("-size 12"))
        self.user_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        logout_button = ttk.Button(
            top_bar, text="Logout", command=self.controller.logout, bootstyle="danger")
        logout_button.pack(side=tk.RIGHT)
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        courses_frame = ttk.LabelFrame(
            paned_window, text="Courses", padding="10")
        self.courses_listbox = tk.Listbox(
            courses_frame, exportselection=False, height=15)
        self.courses_listbox.pack(fill=tk.BOTH, expand=True)
        self.courses_listbox.bind('<<ListboxSelect>>', self.on_course_select)
        paned_window.add(courses_frame, weight=1)
        tasks_frame = ttk.LabelFrame(paned_window, text="Tasks", padding="10")
        self.tasks_listbox = tk.Listbox(
            tasks_frame, exportselection=False, height=15)
        self.tasks_listbox.pack(fill=tk.BOTH, expand=True)
        self.tasks_listbox.bind('<<ListboxSelect>>', self.on_task_select)
        paned_window.add(tasks_frame, weight=2)
        details_frame = ttk.LabelFrame(
            paned_window, text="Details", padding="10")
        paned_window.add(details_frame, weight=2)
        course_btn_frame = ttk.Frame(courses_frame)
        course_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(course_btn_frame, text="Add Course", command=self.add_course,
                   bootstyle="primary-outline").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(course_btn_frame, text="Delete Course", command=self.delete_course,
                   bootstyle="danger-outline").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        task_btn_frame = ttk.Frame(tasks_frame)
        task_btn_frame.pack(fill=tk.X, pady=(5, 0))
        self.add_task_btn = ttk.Button(
            task_btn_frame, text="Add Task", command=self.add_task, state="disabled", bootstyle="primary-outline")
        self.add_task_btn.pack(side=tk.LEFT, expand=True,
                               fill=tk.X, padx=(0, 2))
        self.delete_task_btn = ttk.Button(
            task_btn_frame, text="Delete Task", command=self.delete_task, state="disabled", bootstyle="danger-outline")
        self.delete_task_btn.pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        ttk.Label(details_frame, text="Name:").pack(anchor='w', pady=(0, 5))
        self.detail_name = ttk.Entry(details_frame)
        self.detail_name.pack(fill=tk.X, pady=5)
        ttk.Label(details_frame, text="Description:").pack(
            anchor='w', pady=(0, 5))
        self.detail_desc = tk.Text(details_frame, height=8)
        self.detail_desc.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(details_frame,
                  text="Due Date (YYYY-MM-DD):").pack(anchor='w', pady=(0, 5))
        self.detail_due_date = ttk.Entry(details_frame)
        self.detail_due_date.pack(fill=tk.X, pady=5)
        self.detail_due_date.configure(state="disabled")
        self.save_btn = ttk.Button(details_frame, text="Save Changes",
                                   command=self.save_changes, state="disabled", bootstyle="success")
        self.save_btn.pack(fill=tk.X, pady=(10, 0), ipady=5)

    def set_user(self, user_id):
        self.current_user_id = user_id
        user_data = self.db.fetch_query(
            "SELECT name FROM USER WHERE id=?", (user_id,))
        user_name = user_data[0][0]
        self.user_label.config(text=f"Welcome, {user_name}!")
        self.controller.title(f"Task Manager - {user_name}")
        self.refresh_ui()

    def refresh_ui(self):
        self.load_courses()
        self.tasks_listbox.delete(0, tk.END)
        self.clear_details()
        self.add_task_btn.config(state="disabled")
        self.delete_task_btn.config(state="disabled")

    def load_courses(self):
        self.courses_listbox.delete(0, tk.END)
        self.courses_data = {}
        courses = self.db.fetch_query(
            "SELECT id, name FROM COURSE WHERE user_id = ?", (self.current_user_id,))
        for i, (course_id, name) in enumerate(courses):
            self.courses_listbox.insert(tk.END, name)
            self.courses_data[i] = course_id

    def add_course(self):
        # FIXED: Use Querybox for simple user input
        name = Querybox.get_string(
            prompt="Enter course name:", title="Add Course")
        if name:
            desc = Querybox.get_string(
                prompt="Enter course description (optional):", title="Add Course Description")
            self.db.execute_query("INSERT INTO COURSE (user_id, name, description) VALUES (?, ?, ?)",
                                  (self.current_user_id, name, desc if desc else ""))
            self.load_courses()

    def delete_course(self):
        selected_index = self.courses_listbox.curselection()
        if not selected_index:
            return
        course_id = self.courses_data.get(selected_index[0])
        if Messagebox.askyesno("Are you sure you want to delete this course and all its tasks?", "Confirm Delete", parent=self):
            self.db.execute_query(
                "DELETE FROM COURSE WHERE id = ?", (course_id,))
            self.refresh_ui()

    def load_tasks(self, course_id):
        self.tasks_listbox.delete(0, tk.END)
        self.tasks_data = {}
        tasks = self.db.fetch_query(
            "SELECT id, name FROM TASK WHERE course_id = ?", (course_id,))
        for i, (task_id, name) in enumerate(tasks):
            self.tasks_listbox.insert(tk.END, name)
            self.tasks_data[i] = task_id

    def add_task(self):
        selected_course_index = self.courses_listbox.curselection()
        if not selected_course_index:
            return
        course_id = self.courses_data.get(selected_course_index[0])
        # FIXED: Use Querybox for simple user input
        name = Querybox.get_string(prompt="Enter task name:", title="Add Task")
        if name:
            desc = Querybox.get_string(
                prompt="Enter task description (optional):", title="Add Task Description")
            due_date = Querybox.get_string(
                prompt="Enter due date (e.g., YYYY-MM-DD):", title="Add Task Due Date")
            self.db.execute_query("INSERT INTO TASK (course_id, name, description, due_date) VALUES (?, ?, ?, ?)",
                                  (course_id, name, desc if desc else "", due_date if due_date else ""))
            self.load_tasks(course_id)

    def delete_task(self):
        selected_index = self.tasks_listbox.curselection()
        if not selected_index:
            return
        task_id = self.tasks_data.get(selected_index[0])
        if Messagebox.askyesno("Are you sure you want to delete this task?", "Confirm Delete", parent=self):
            self.db.execute_query("DELETE FROM TASK WHERE id = ?", (task_id,))
            self.on_course_select(None)

    def on_course_select(self, event):
        selected_indices = self.courses_listbox.curselection()
        if not selected_indices:
            return
        self.clear_details()
        self.add_task_btn.config(state="normal")
        self.delete_task_btn.config(state="disabled")
        course_id = self.courses_data.get(selected_indices[0])
        course_details = self.db.fetch_query(
            "SELECT name, description FROM COURSE WHERE id = ?", (course_id,))[0]
        self.detail_name.delete(0, tk.END)
        self.detail_name.insert(0, course_details[0])
        self.detail_desc.delete("1.0", tk.END)
        self.detail_desc.insert("1.0", course_details[1] or "")
        self.detail_due_date.config(state="disabled")
        self.save_btn.config(state="normal")
        self.load_tasks(course_id)

    def on_task_select(self, event):
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices:
            return
        self.delete_task_btn.config(state="normal")
        task_id = self.tasks_data.get(selected_indices[0])
        task_details = self.db.fetch_query(
            "SELECT name, description, due_date FROM TASK WHERE id = ?", (task_id,))[0]
        self.detail_name.delete(0, tk.END)
        self.detail_name.insert(0, task_details[0])
        self.detail_desc.delete("1.0", tk.END)
        self.detail_desc.insert("1.0", task_details[1] or "")
        self.detail_due_date.config(state="normal")
        self.detail_due_date.delete(0, tk.END)
        self.detail_due_date.insert(0, task_details[2] or "")
        self.save_btn.config(state="normal")

    def save_changes(self):
        course_sel = self.courses_listbox.curselection()
        task_sel = self.tasks_listbox.curselection()
        name = self.detail_name.get()
        desc = self.detail_desc.get("1.0", tk.END).strip()
        due_date = self.detail_due_date.get()
        if not name:
            Messagebox.show_error("Name cannot be empty.", "Error")
            return
        if task_sel:
            task_id = self.tasks_data.get(task_sel[0])
            self.db.execute_query("UPDATE TASK SET name=?, description=?, due_date=? WHERE id=?",
                                  (name, desc, due_date, task_id))
            self.on_course_select(None)
        elif course_sel:
            course_id = self.courses_data.get(course_sel[0])
            self.db.execute_query("UPDATE COURSE SET name=?, description=? WHERE id=?",
                                  (name, desc, course_id))
            self.load_courses()
            self.courses_listbox.selection_set(course_sel[0])
            self.on_course_select(None)

    def clear_details(self):
        self.detail_name.delete(0, tk.END)
        self.detail_desc.delete("1.0", tk.END)
        self.detail_due_date.delete(0, tk.END)
        self.detail_due_date.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.tasks_listbox.selection_clear(0, tk.END)


if __name__ == "__main__":
    db = DatabaseManager()
    app = App(db)
    app.mainloop()
