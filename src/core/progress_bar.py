import customtkinter as ctk

class ProgressBarWindow(ctk.CTkToplevel):
    def __init__(self, title="下载中...", label_text="正在下载模型...", parent=None):
        super().__init__(parent)

        # 先隐藏窗口，计算位置后再显示，避免左上角闪烁
        self.withdraw()

        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)

        # 尝试置顶
        self.attributes("-topmost", True)

        # 居中显示
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        # 避免负坐标
        x = max(0, x)
        y = max(0, y)
        self.geometry(f"+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.label = ctk.CTkLabel(self, text=label_text, font=("Arial", 14))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal")
        self.progress_bar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="准备中...", font=("Arial", 12), text_color="gray")
        self.status_label.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        # 显示窗口
        self.deiconify()
        # 强制聚焦
        self.focus_force()
