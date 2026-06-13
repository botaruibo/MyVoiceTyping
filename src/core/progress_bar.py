import customtkinter as ctk

from ..components.ui_theme import GUIStyles


class ProgressBarFrame(ctk.CTkFrame):
    """
    全屏覆盖的进度条组件（替代原本的 Toplevel 弹窗）
    """

    def __init__(self, master, title="下载中...", label_text="正在下载模型..."):
        super().__init__(master, fg_color=GUIStyles.COLOR_WINDOW_BG)

        # 让自身填充整个父容器
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 居中布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self, width=440, **GUIStyles.get_card_frame_args())
        self.container.grid(row=0, column=0)
        self.container.grid_columnconfigure(0, weight=1)

        # 标题
        self.title_label = ctk.CTkLabel(
            self.container,
            text=title,
            font=GUIStyles.get_section_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        )
        self.title_label.pack(padx=28, pady=(26, 10))

        # 描述文本
        self.desc_label = ctk.CTkLabel(
            self.container,
            text=label_text,
            font=GUIStyles.get_body_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
        )
        self.desc_label.pack(padx=28, pady=(0, 16))

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            self.container,
            orientation="horizontal",
            width=360,
            progress_color=GUIStyles.COLOR_ACCENT,
        )
        self.progress_bar.pack(padx=28, pady=8)
        self.progress_bar.set(0)
        self._indeterminate_value = 0.0
        self._determinate_started = False
        self._last_progress = 0.0

        # 状态文本（如百分比）
        self.status_label = ctk.CTkLabel(
            self.container,
            text="准备中...",
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_MUTED,
        )
        self.status_label.pack(padx=28, pady=(4, 26))

    def configure_text(self, title: str = "", label_text: str = ""):
        if title:
            self.title_label.configure(text=title)
        if label_text:
            self.desc_label.configure(text=label_text)

    def reset_progress(self):
        self._indeterminate_value = 0.0
        self._determinate_started = False
        self._last_progress = 0.0
        self.progress_bar.set(0)
        self.status_label.configure(text="准备中...")

    def update_progress(self, progress: float | None, desc: str):
        if progress is None:
            if desc:
                self.status_label.configure(text=desc)
            self.update_idletasks()
            return
        if progress < 0:
            if not self._determinate_started:
                self._indeterminate_value = (self._indeterminate_value + 0.035) % 1.0
                self.progress_bar.set(self._indeterminate_value)
        else:
            value = max(0.0, min(1.0, progress))
            if value + 0.001 >= self._last_progress:
                self._determinate_started = True
                self._last_progress = value
                self.progress_bar.set(value)
        if desc:
            self.status_label.configure(text=desc)
        # 强制刷新界面
        self.update_idletasks()

    def close(self):
        self.destroy()
