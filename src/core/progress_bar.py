import customtkinter as ctk


class ProgressBarFrame(ctk.CTkFrame):
    """
    全屏覆盖的进度条组件（替代原本的 Toplevel 弹窗）
    """

    def __init__(self, master, title="下载中...", label_text="正在下载模型..."):
        # 使用半透明或深色背景作为蒙层
        super().__init__(master, fg_color=("gray95", "gray10"))

        # 让自身填充整个父容器
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 居中布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 内容容器
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0)

        # 标题
        self.title_label = ctk.CTkLabel(
            self.container,
            text=title,
            font=("Arial", 20, "bold")
        )
        self.title_label.pack(pady=(0, 20))

        # 描述文本
        self.desc_label = ctk.CTkLabel(
            self.container,
            text=label_text,
            font=("Arial", 14),
            text_color="gray"
        )
        self.desc_label.pack(pady=(0, 15))

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(self.container, orientation="horizontal", width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # 状态文本（如百分比）
        self.status_label = ctk.CTkLabel(
            self.container,
            text="准备中...",
            font=("Arial", 12),
            text_color="gray"
        )
        self.status_label.pack(pady=(5, 0))

    def update_progress(self, progress: float, desc: str):
        self.progress_bar.set(progress)
        if desc:
            self.status_label.configure(text=desc)
        # 强制刷新界面
        self.update_idletasks()

    def close(self):
        self.destroy()