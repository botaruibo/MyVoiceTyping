import tkinter as tk
from typing import Any, Dict, Optional
import random, sys

import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None

from .utils.config_manager import ConfigManager


class VoiceInputGUI:
    def __init__(self, app: Any, app_name: str):
        self.app = app
        self.app_name = app_name
        self.config_manager = ConfigManager()

        try:
            ctk.set_appearance_mode("system")
        except Exception:
            pass

        self.root = ctk.CTk()
        self.root.title(self.app_name)
        self.root.geometry("800x600")

        # --- 将窗口居中 ---
        self.root.update_idletasks()  # 确保获取的尺寸是准确的
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # --- 居中代码结束 ---

        try:
            self.root.minsize(720, 520)
        except Exception:
            pass

        self.status_var = tk.StringVar(value="就绪")
        self._status_label: Optional[ctk.CTkLabel] = None

        self._recording_overlay: Optional[ctk.CTkToplevel] = None
        self._recording_overlay_label: Optional[ctk.CTkLabel] = None
        self._recording_overlay_progress: Optional[ctk.CTkProgressBar] = None
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._nav_icons: Dict[str, ctk.CTkImage] = {}
        self._nav_font = ctk.CTkFont(size=16)
        self._nav_default_color = "transparent"
        self._nav_hover_color = ("#E2E2E2", "#2A2A2A")
        self._nav_active_color = ("#D2D2D2", "#333333")
        self._nav_text_color = ("#303030", "#E6E6E6")
        self._sidebar_bg_color = ("#F4F4F4", "#141414")
        self._card_bg_color = ("#F0F0F0", "#242424")
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        except Exception:
            pass

        self.pages: Dict[str, ctk.CTkFrame] = {}
        self.current_page: Optional[str] = "home"

        self._build_ui()
        self.show_page("home")

        # 让窗口尽快渲染：放到主循环启动后执行，避免 `update()` 在某些环境下卡死。
        try:
            self.root.after(0, self._initial_paint)
        except Exception:
            pass

    # -------------------------
    # UI
    # -------------------------

    def _build_ui(self) -> None:
        """
        构建主 UI 界面。
        - 左侧为导航侧边栏。
        - 右侧为内容区域，包含页面和底部状态栏。
        """
        # 主窗口布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=0, minsize=200)
        self.root.grid_columnconfigure(1, weight=0, minsize=1)
        self.root.grid_columnconfigure(2, weight=1)

        self._create_sidebar()
        self._create_content_area()

    def _create_nav_icon(self, letter: str) -> Optional[ctk.CTkImage]:
        if Image is None or ImageDraw is None or ImageFont is None:
            return None

        canvas_size = 32

        def _make(color: tuple[int, int, int, int]) -> "Image.Image":
            img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([2, 2, canvas_size - 2, canvas_size - 2], radius=7, outline=color, width=2)

            font = ImageFont.load_default()
            try:
                bbox = draw.textbbox((0, 0), letter, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except Exception:
                text_w, text_h = 10, 10

            draw.text(
                ((canvas_size - text_w) / 2, (canvas_size - text_h) / 2 - 1),
                letter,
                fill=color,
                font=font,
            )
            return img

        light_img = _make((80, 80, 80, 255))
        dark_img = _make((230, 230, 230, 255))
        return ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=(16, 16))

    def _create_sidebar(self) -> None:
        """
        创建左侧的导航侧边栏。
        """
        sidebar = ctk.CTkFrame(
            self.root,
            width=200,
            corner_radius=0,
            fg_color=self._sidebar_bg_color,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        sidebar_border = ctk.CTkFrame(
            self.root,
            width=1,
            corner_radius=0,
            fg_color=("gray70", "gray25"),
        )
        sidebar_border.pack(side="left", fill="y")
        sidebar_border.pack_propagate(False)

        ctk.CTkLabel(sidebar, text=self.app_name, font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        nav_buttons = [
            ("主页", "home"),
            ("设置", "settings"),
            ("关于", "about"),
        ]
        icon_letters = {"home": "H", "settings": "S", "about": "I"}

        self._nav_buttons = {}
        for text, page_name in nav_buttons:
            icon = self._nav_icons.get(page_name)
            if icon is None:
                icon = self._create_nav_icon(icon_letters.get(page_name, "•"))
                if icon:
                    self._nav_icons[page_name] = icon

            btn = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                font=self._nav_font,
                fg_color=self._nav_default_color,
                text_color=self._nav_text_color,
                hover_color=self._nav_hover_color,
                image=icon,
                compound="left",
                command=lambda p=page_name: self.show_page(p),
            )
            btn.pack(fill="x", padx=10, pady=5)
            self._nav_buttons[page_name] = btn

        # --- 底部退出按钮 ---
        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=10, pady=10)


        ctk.CTkButton(footer, text="退出", command=self.exit_application).pack(fill="x", pady=(8, 0))

    def _create_content_area(self) -> None:
        content_area = ctk.CTkFrame(self.root, corner_radius=0, fg_color=("#FBFBFB", "#1E1E1E"))
        content_area.pack(side="left", fill="both", expand=True)
        content_area.grid_rowconfigure(0, weight=1)
        content_area.grid_columnconfigure(0, weight=1)

        self.pages["home"] = self._create_home_page(content_area, "主页")
        # self.pages["dictionary"] = self._create_placeholder_page(content_area, "词典")
        self.pages["about"] = self._create_placeholder_page(content_area, "关于")
        self.pages["settings"] = self._create_settings_page(content_area)
        # self.pages["provider"] = self._build_provider_settings_page(content_area)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

        self._create_status_bar(content_area)

    def _create_status_bar(self, parent: ctk.CTkFrame) -> None:
        """
        在右侧内容区的底部创建状态栏。
        """
        status_bar_frame = ctk.CTkFrame(
            parent,
            height=30,
            corner_radius=0,
            fg_color=self._sidebar_bg_color,
            border_width=1,
            border_color=("gray85", "gray20"),
        )
        status_bar_frame.grid(row=1, column=0, sticky="sew")
        status_bar_frame.pack_propagate(False)

        self._status_label = ctk.CTkLabel(
            status_bar_frame,
            textvariable=self.status_var,
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self._status_label.pack(side="right", padx=10)


    # -------------------------
    # Pages
    # -------------------------

    def _create_placeholder_page(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        page = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(page, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10)
        )
        ctk.CTkLabel(page, text="开发中…", text_color="gray").pack(anchor="w", padx=20)
        return page

    def _create_home_page(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        """
                创建主页,展示应用的欢迎信息和核心功能。
                """
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        # --- 内容居中容器 ---
        content_frame = ctk.CTkFrame(page, fg_color="transparent")
        content_frame.grid(row=0, column=0)

        # --- 主标题 ---
        main_headline_text = f"告别打字, 用 AI 语音输入 \n  速度快 4 倍"
        main_headline = ctk.CTkLabel(
            content_frame,
            text=main_headline_text,
            font=ctk.CTkFont(size=40, weight="bold"),
            justify="center",
        )
        main_headline.pack(pady=(0, 20), padx=20)

        # --- 副标题 ---
        sub_headline_text = "使用场景：AI 聊天 、AI 编程、文档写作、聊天回复...支持所有应用"
        sub_headline = ctk.CTkLabel(
            content_frame,
            text=sub_headline_text,
            font=ctk.CTkFont(size=16),
            text_color="gray",
            wraplength=550,
            justify="center",
        )
        sub_headline.pack(pady=10, padx=20)

        # --- 试用提示 ---
        trial_label = ctk.CTkLabel(
            content_frame,
            text="按住快捷键，立刻试用",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        trial_label.pack(pady=(40, 10), padx=20)

        # --- 试用输入框 ---
        self.home_trial_textbox = ctk.CTkTextbox(
            content_frame,
            height=100,
            corner_radius=8,
            border_width=1,
            font=ctk.CTkFont(size=14),
        )
        self.home_trial_textbox.pack(fill="x", expand=True, padx=40, pady=(0, 20))

        placeholder_text = "请按住快捷键，说一段文字"

        # --- Placeholder Logic ---
        def _add_placeholder(event=None):
            if self.home_trial_textbox and not self.home_trial_textbox.get("1.0", "end-1c"):
                self.home_trial_textbox.insert("1.0", placeholder_text)
                self.home_trial_textbox.configure(text_color="gray")

        def _remove_placeholder(event=None):
            if self.home_trial_textbox and self.home_trial_textbox.get("1.0", "end-1c") == placeholder_text:
                self.home_trial_textbox.delete("1.0", "end")
                default_text_color = ctk.ThemeManager.theme["CTkTextbox"]["text_color"]
                self.home_trial_textbox.configure(text_color=default_text_color)

        if self.home_trial_textbox:
            self.home_trial_textbox.bind("<FocusIn>", _remove_placeholder)
            self.home_trial_textbox.bind("<FocusOut>", _add_placeholder)
            _add_placeholder()

        return page


    def _create_settings_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)

        # --- 标题 ---
        header_frame = ctk.CTkFrame(page, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="设置", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        # --- 键盘快捷键 ---
        hotkey_header_frame = ctk.CTkFrame(page, fg_color="transparent")
        hotkey_header_frame.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="ew")
        hotkey_header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hotkey_header_frame, text="键盘快捷键", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        # --- 分割线 ---
        ctk.CTkFrame(page, height=1, fg_color=("#E0E0E0", "#303030")).grid(
            row=2, column=0, padx=20, pady=(5, 15), sticky="ew"
        )

        # --- 热键设置容器 ---
        hotkey_settings_container = ctk.CTkFrame(page, fg_color="transparent")
        hotkey_settings_container.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        hotkey_settings_container.grid_columnconfigure(1, weight=1)  # 输入框列占满剩余空间
        # --- 热键设置项 ---
        self._create_hotkey_setting(
            hotkey_settings_container,
            title="语音输入",
            config_key="press_hotkey",
            description="按住说话。双击进入免提模式。",
            row=0,
        )

        self._create_hotkey_setting(
            hotkey_settings_container,
            title="免提模式",
            config_key="toggle_hotkey",
            description="按一次开始说话,无需按住。再次按下将文本粘贴到任何文本框中。",
            row=1,
        )

        # self._create_hotkey_setting(
        #     hotkey_settings_container,
        #     title="翻译模式",
        #     config_key="translate_hotkey",
        #     description="按一下开始语音翻译。再按一下将翻译文本粘贴到任何文本框中。",
        #     row=2,
        # )

        return page

    def _build_provider_settings_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        page = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(page, text="服务设置", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(18, 12), sticky="w"
        )

        def _save_var_on_event(entry: ctk.CTkEntry, var: tk.StringVar, key: str) -> None:
            def _save(_evt=None) -> None:
                self.config_manager.set(key, (var.get() or "").strip())
                self.update_status_success("已保存配置（部分配置需重启生效）")

            entry.bind("<Return>", _save)
            entry.bind("<FocusOut>", _save)

        # STT Provider
        stt_provider_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        stt_provider_row.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")
        stt_provider_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(stt_provider_row, text="STT 提供者", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )

        stt_provider_default = self.config_manager.get("stt_provider", "funasr") or "funasr"

        def _on_stt_provider_change(v: str) -> None:
            self.config_manager.set("stt_provider", v)
            self.update_status_success("已保存配置（切换 STT 提供者需重启生效）")

        stt_provider_menu = ctk.CTkOptionMenu(
            stt_provider_row,
            values=["funasr", "openai_api"],
            dynamic_resizing=False,
            fg_color=self._card_bg_color,
            button_color=self._card_bg_color,
            button_hover_color=self._nav_hover_color,
            dropdown_fg_color=("#FCFCFC", "#2B2B2B"),
            dropdown_hover_color=self._nav_hover_color,
            text_color=self._nav_text_color,
            dropdown_text_color=self._nav_text_color,
            command=_on_stt_provider_change,
        )
        stt_provider_menu.set(stt_provider_default)
        stt_provider_menu.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        try:
            dropdown_menu = getattr(stt_provider_menu, "_dropdown_menu", None)
            if dropdown_menu is not None:
                dropdown_menu.configure(relief="solid", borderwidth=1)
        except Exception:
            pass

        # （已移除）OpenAI STT API Key

        ctk.CTkLabel(page, text="远程 LLM（用于 AI 纠正等能力）", text_color="gray").grid(
            row=2, column=0, padx=18, pady=(8, 8), sticky="w"
        )

        # Remote LLM API Key
        api_key_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        api_key_row.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="ew")
        api_key_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(api_key_row, text="API Key", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        api_key_var = tk.StringVar(value=self.config_manager.get("api_key", "") or "")
        api_key_entry = ctk.CTkEntry(api_key_row, textvariable=api_key_var)
        api_key_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(api_key_entry, api_key_var, "api_key")

        # Base URL
        base_url_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        base_url_row.grid(row=4, column=0, padx=18, pady=(0, 12), sticky="ew")
        base_url_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(base_url_row, text="Base URL", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        base_url_var = tk.StringVar(value=self.config_manager.get("base_url", "") or "")
        base_url_entry = ctk.CTkEntry(base_url_row, textvariable=base_url_var)
        base_url_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(base_url_entry, base_url_var, "base_url")

        # Model Name
        model_name_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        model_name_row.grid(row=5, column=0, padx=18, pady=(0, 18), sticky="ew")
        model_name_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(model_name_row, text="Model Name", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        model_name_var = tk.StringVar(value=self.config_manager.get("model_name", "") or "")
        model_name_entry = ctk.CTkEntry(model_name_row, textvariable=model_name_var)
        model_name_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(model_name_entry, model_name_var, "model_name")

        return page

    # -------------------------
    # Widgets helpers
    # -------------------------

    def _create_hotkey_setting(
        self,
        parent: ctk.CTkFrame,
        title: str,
        config_key: str,
        description: str,
        row: int,
    ) -> None:
        """
        创建符合新设计的热键设置项。

        - **初始状态**：未设置热键时，显示“录制快捷键”按钮。
        - **录制模式**：点击按钮或“更改”后，显示输入框并监听按键。
        - **显示状态**：设置后，显示包含按键的气泡，气泡右侧有删除按钮。
        - **悬停效果**：鼠标悬停在已设置的热键上时，显示“更改快捷键”按钮。
        - **统一布局**：确保所有设置项宽度一致。
        - **灵活保存**：支持普通组合键、纯修饰键组合的录制。
        """
        # --- 左侧：标题和描述 ---
        left_frame = ctk.CTkFrame(parent, fg_color="transparent")
        left_frame.grid(row=row, column=0, padx=(0, 20), sticky="w", pady=10)
        ctk.CTkLabel(left_frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left_frame, text=description, text_color="gray", wraplength=250, justify="left").pack(
            anchor="w", pady=(4, 0)
        )

        # --- 右侧：动态内容区域 ---
        right_frame = ctk.CTkFrame(parent, fg_color="transparent")
        right_frame.grid(row=row, column=1, sticky="ew", pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)

        # --- State ---
        # --- State ---
        # pressed_keys：本次录制窗口内“出现过”的所有键（用于最终保存）
        pressed_keys: set[str] = set()
        # down_keys：当前仍处于按下状态的键（用于过滤长按自动重复触发）
        down_keys: set[str] = set()
        # first_key：进入录制窗口后用户按下的第一个键（其释放时触发保存）
        first_key: Optional[str] = None
        MODIFIER_KEYS = {
            "control", "shift", "alt", "option", "command", "cmd",
            "control_l", "control_r", "shift_l", "shift_r",
            "alt_l", "alt_r", "super_l", "super_r", "darwin",
            "cmd_l", "cmd_r" # pynput names
        }

        # 按键名称映射表：tkinter -> pynput（尽量映射为通用 token，避免只匹配左/右修饰键）
        KEY_MAP = {
            "darwin": "cmd",
            "command": "cmd",
            "meta_l": "cmd_l",
            "meta_r": "cmd_r",
            "super_l": "cmd_l",
            "super_r": "cmd_r",
            "cmd_l": "cmd_l",
            "cmd_r": "cmd_r",
            "option": "alt",
            "alt_l": "alt_l",
            "alt_r": "alt_r",
            "control": "ctrl",
            "control_l": "ctrl_l",
            "control_r": "ctrl_r",
            "shift_l": "shift_l",
            "shift_r": "shift_r",
        }


        # --- Widgets ---
        # 将所有动态控件都放置在 right_frame 中
        record_button = ctk.CTkButton(
            right_frame,
            text="录制快捷键",
            fg_color=self._card_bg_color,
            border_color=("#C0C0C0", "#404040"),
            border_width=1,
            text_color=self._nav_text_color,
            hover_color=self._nav_hover_color,
            command=lambda: switch_to_edit_mode(activate_listeners=True)
        )
        record_button.grid(row=0, column=0, sticky="ew", ipady=4)


        entry = ctk.CTkEntry(right_frame, corner_radius=8, placeholder_text="请按下快捷键...")

        bubble_container = ctk.CTkFrame(
            right_frame,
            fg_color="transparent",
            corner_radius=8,
        )
        bubble_container.grid_columnconfigure(0, weight=1)
        change_button = ctk.CTkButton(
            bubble_container,
            text="更改快捷键",
            fg_color=("#000000", "#FFFFFF"),
            text_color=("#FFFFFF", "#000000"),
            hover=False,
            width=100,
            height=28,
            command=lambda: switch_to_edit_mode(activate_listeners=True)
        )


        # --- Helper Functions ---
        def _clear_widgets() -> None:
            """清除 right_frame 中的所有子控件"""
            for widget in right_frame.winfo_children():
                widget.grid_remove()


        def _get_key_name(raw_key: str) -> str:
            return KEY_MAP.get(raw_key, raw_key)

        def _format_hotkey_for_save(keys: Optional[set[str]]) -> str:
            """
            格式化并排序录制到的按键，准备写入配置。
            - 过滤空值和 "return"
            - 修饰键在前，字母数字键在后
            """
            normalized = [k for k in (keys or set()) if k and k != "return"]
            if not normalized:
                return ""

            ordered = sorted(set(normalized), key=lambda k: (k not in MODIFIER_KEYS, k))
            return "+".join(ordered)

        def _validate_hotkey(keys: set[str]) -> bool:
            """
            验证快捷键组合是否有效。
            """
            FORBIDDEN_KEYS = {"tab", "esc", "enter", "capslock", "delete", "backspace"}

            if not keys:
                return True # 空快捷键是有效的（表示清除）

            # 规则 4: 任何情况下都不支持的键
            if any(k in FORBIDDEN_KEYS for k in keys):
                self.update_status_error("无效按键: Tab/Esc/Enter等不可用")
                return False

            has_modifier = any(k in MODIFIER_KEYS for k in keys)

            # 规则 1: 单个键必须是修饰键
            if len(keys) == 1 and not has_modifier:
                self.update_status_error("无效快捷键: 单个按键必须是修饰键")
                return False

            # 规则 2: 组合键必须包含修饰键
            if len(keys) > 1 and not has_modifier:
                self.update_status_error("无效快捷键: 组合键必须包含修饰键")
                return False

            return True

        def _update_entry_text() -> None:
            sorted_keys = sorted(list(pressed_keys), key=lambda k: (k not in MODIFIER_KEYS, k))
            entry.delete(0, "end")
            entry.insert(0, "+".join(sorted_keys))

        def _reset_capture_state() -> None:
            nonlocal first_key
            pressed_keys.clear()
            down_keys.clear()
            first_key = None

        # --- Event Handlers ---
        def _on_key_press(event):
            """处理按键按下事件：从第一个键开始录制，到第一个键释放时保存。"""
            nonlocal first_key

            event_keysym = getattr(event, "keysym", "")
            raw_key = (event_keysym or "").lower()

            # Return 键不可作为快捷键组成部分；行为保持“用于确认/保存”的语义
            if raw_key == "return":
                hotkey_str = _format_hotkey_for_save(pressed_keys)
                if hotkey_str:
                    entry.unbind("<KeyPress>")
                    entry.unbind("<KeyRelease>")
                    entry.unbind("<FocusOut>")
                    _reset_capture_state()
                    _save(hotkey_str)
                return "break"

            key_name = _get_key_name(raw_key)
            if not key_name:
                return "break"

            # 过滤长按导致的重复 KeyPress
            if key_name in down_keys:
                return "break"

            down_keys.add(key_name)

            # 第一个键：打开录制窗口
            if first_key is None:
                first_key = key_name

            # 在第一个键释放前，所有按下过的键都计入组合
            pressed_keys.add(key_name)
            _update_entry_text()
            return "break"

        def _on_key_release(event) -> None:
            """处理按键释放事件：当第一个键释放时，直接保存所有录制到的键。"""
            nonlocal first_key

            event_keysym = getattr(event, "keysym", "")
            raw_key = (event_keysym or "").lower()
            if raw_key == "return":
                return

            key_name = _get_key_name(raw_key)
            if not key_name:
                return

            down_keys.discard(key_name)

            # 只有当“第一个键”释放时才触发保存
            if first_key is None or key_name != first_key:
                return

            # 在保存前验证快捷键
            if not _validate_hotkey(pressed_keys):
                # --- 显示错误状态 ---
                error_color = ("#D32F2F", "#FF5252")  # 深/浅色模式下的红色
                original_border_color = entry.cget("border_color")

                entry.configure(border_color=error_color)

                def _revert_error_state():
                    if entry.winfo_exists():
                        entry.configure(border_color=original_border_color)

                entry.after(3000, _revert_error_state)

                # --- 重置捕获状态并恢复UI ---
                _reset_capture_state()
                initial_hotkey = self.config_manager.get(config_key, "") or ""
                _update_ui(initial_hotkey)
                # 短暂显示错误后清除
                entry.after(3000, lambda: self.update_status_info("就绪"))
                return

            hotkey_str = _format_hotkey_for_save(pressed_keys)

            entry.unbind("<KeyPress>")
            entry.unbind("<KeyRelease>")
            entry.unbind("<FocusOut>")

            _reset_capture_state()
            _save(hotkey_str)

        def _on_focus_out(event) -> None:
            """失去焦点时取消本次录制，恢复到当前已保存的热键显示。"""
            entry.unbind("<KeyPress>")
            entry.unbind("<KeyRelease>")
            entry.unbind("<FocusOut>")

            _reset_capture_state()

            initial_hotkey = self.config_manager.get(config_key, "") or ""
            _update_ui(initial_hotkey)


        def _on_bubble_enter(event) -> None:
            change_button.place(relx=0.5, rely=0.5, anchor="center")

        def _on_bubble_leave(event) -> None:
            change_button.place_forget()
# --- Core Logic ---
        def _save(new_hotkey: str) -> None:
            """
            保存热键，并强制重新加载所有热键配置以确保监听生效。
            """
            new_hotkey = new_hotkey.strip()
            current_hotkey = self.config_manager.get(config_key, "") or ""

            # 如果热键没有变化，则无需执行任何操作
            if new_hotkey == current_hotkey:
                _update_ui(new_hotkey)
                return

            print(f"准备将热键 '{config_key}' 从 '{current_hotkey}' 更新为 '{new_hotkey}'。")
            self.config_manager.set(config_key, new_hotkey)
            self.update_status_success("配置已保存，正在重新加载热键...")

            if hasattr(self.app, "reload_hotkeys"):
                try:
                    # 关键步骤：强制从文件重新加载配置，以确保热键管理器获得最新值
                    self.config_manager.load_config()
                    print("配置已从文件重新加载。")

                    # 调用主应用的重载方法
                    self.app.reload_hotkeys()

                    self.update_status_success("热键已生效")
                    print(f"热键 '{config_key}' 已成功重载。")
                except Exception as e:
                    self.update_status_error(f"热键重载失败: {e}")
                    print(f"热键重载失败: {e}")
            else:
                print("警告: app 对象上未找到 reload_hotkeys 方法。")

            # 更新UI显示
            _update_ui(new_hotkey)

        def _clear(event=None) -> None:
            _save("")

        # --- UI State Changers ---
        def _render_bubbles(hotkey_str: str) -> None:
            for widget in bubble_container.winfo_children():
                if widget != change_button:  # 不要销毁“更改”按钮
                    widget.destroy()

            # --- 单层气泡容器 ---
            # 使用一个 Frame 同时作为边框和内部所有组件的容器
            display_frame = ctk.CTkFrame(
                bubble_container,
                fg_color=self._card_bg_color,
                border_color=("#C0C0C0", "#404040"),
                border_width=1,
                corner_radius=8
            )
            display_frame.grid(row=0, column=0, sticky="ew")

            keys = hotkey_str.replace("<", "").replace(">", "").split("+")

            # --- 删除按钮 ---
            # 优先 pack 到右侧，以确保它始终在最右边
            delete_normal_text_color = ("gray25", "gray75")
            delete_hover_text_color = ("#000000", "#FFFFFF")
            key_bubble_bg_color = ("#C0C0C0", "#404040")  # 气泡背景色

            delete_button = ctk.CTkLabel(
                display_frame,
                text="✕",
                # cursor="hand2",
                font=ctk.CTkFont(size=16),
                text_color=delete_normal_text_color,
                fg_color="transparent",
                width=28,
                height=28,
                corner_radius=8,
            )
            delete_button.pack(side="right", padx=(4, 8), pady=4)
            delete_button.bind("<Button-1>", _clear)
            delete_button.bind(
                "<Enter>",
                lambda e: delete_button.configure(
                    text_color=delete_hover_text_color,
                    fg_color=key_bubble_bg_color
                )
            )
            delete_button.bind(
                "<Leave>",
                lambda e: delete_button.configure(
                    text_color=delete_normal_text_color,
                    fg_color="transparent"
                )
            )
            delete_button.bind("<Enter>", _on_bubble_enter, add="+")
            delete_button.bind("<Leave>", _on_bubble_leave, add="+")

            # --- 按键气泡 ---
            for i, key in enumerate(keys):
                # 使用一个 Frame 作为气泡
                key_bubble = ctk.CTkFrame(
                    display_frame,
                    fg_color=key_bubble_bg_color,
                    corner_radius=6,
                    border_width=1,
                    border_color=("#C0C0C0", "#404040")
                )
                # pack 到左侧，第一个气泡左侧有边距，其他气泡之间有边距
                key_bubble.pack(side="left", padx=(4 if i == 0 else 0, 4), pady=4)

                # 气泡内的 Label
                label = ctk.CTkLabel(
                    key_bubble,
                    text=key.upper(),
                    fg_color="transparent",
                    text_color=("#000000", "#FFFFFF")
                )
                label.pack(padx=8, pady=2)

                # 绑定悬停事件
                key_bubble.bind("<Enter>", _on_bubble_enter)
                key_bubble.bind("<Leave>", _on_bubble_leave)
                label.bind("<Enter>", _on_bubble_enter)
                label.bind("<Leave>", _on_bubble_leave)

            # --- 容器的悬停事件 ---
            # 将事件绑定到新的单层容器上
            bubble_container.bind("<Enter>", _on_bubble_enter)
            bubble_container.bind("<Leave>", _on_bubble_leave)
            display_frame.bind("<Enter>", _on_bubble_enter)
            display_frame.bind("<Leave>", _on_bubble_leave)

        def switch_to_display_mode(hotkey_str: str) -> None:
            _clear_widgets()
            bubble_container.grid(row=0, column=0, sticky="ew")
            _render_bubbles(hotkey_str)


        def switch_to_edit_mode(activate_listeners: bool) -> None:
            _clear_widgets()
            entry.grid(row=0, column=0, sticky="ew", ipady=4)
            entry.focus_set()
            if activate_listeners:
                pressed_keys.clear()
                _update_entry_text()
                entry.bind("<KeyPress>", _on_key_press)
                entry.bind("<KeyRelease>", _on_key_release)
                entry.bind("<FocusOut>", _on_focus_out)


        def switch_to_initial_mode() -> None:
            _clear_widgets()
            record_button.grid(row=0, column=0, sticky="ew", ipady=4)
            # 鼠标悬停时改变按钮样式
            record_button.bind("<Enter>", lambda e: record_button.configure(fg_color=self._nav_hover_color))
            record_button.bind("<Leave>", lambda e: record_button.configure(fg_color=self._card_bg_color))


        def _update_ui(hotkey_str: Optional[str]) -> None:
            """根据热键字符串更新UI显示"""
            if hotkey_str:
                switch_to_display_mode(hotkey_str)
            else:
                switch_to_initial_mode()

        # --- Initial State ---
        initial_hotkey = self.config_manager.get(config_key, "") or ""
        _update_ui(initial_hotkey)

    # -------------------------
    # Navigation
    # -------------------------

    def _set_active_nav_button(self, page_name: Optional[str]) -> None:
        if not page_name:
            return

        for name, btn in (self._nav_buttons or {}).items():
            try:
                if name == page_name:
                    btn.configure(fg_color=self._nav_active_color, hover_color=self._nav_active_color)
                else:
                    btn.configure(fg_color=self._nav_default_color, hover_color=self._nav_hover_color)
            except Exception:
                pass

    def show_page(self, page_name: str) -> None:
        if page_name not in self.pages:
            return

        if self.current_page and self.current_page in self.pages:
            try:
                self.pages[self.current_page].grid_remove()
            except Exception:
                pass

        self.current_page = page_name
        page = self.pages[self.current_page]

        try:
            page.grid(row=0, column=0, sticky="nsew")
        except Exception:
            try:
                page.grid()
            except Exception:
                pass

        try:
            page.tkraise()
        except Exception:
            pass

        self._set_active_nav_button(self.current_page)

    # -------------------------
    # Status / lifecycle
    # -------------------------

    def update_status(self, text: str) -> None:
        if not self.root:
            return

        def _update() -> None:
            self.status_var.set(text)
            if self._status_label is not None:
                try:
                    self._status_label.configure(text=text)
                except Exception:
                    pass

        try:
            self.root.after(0, _update)
        except Exception:
            _update()

    def update_status_info(self, text: str) -> None:
        """
        以“信息”状态更新状态栏。
        - 文本为灰色。
        - 无图标。
        """
        if self._status_label:
            self.status_var.set(text)
            self._status_label.configure(text_color="gray")

    def update_status_success(self, text: str) -> None:
        """
        以“成功”状态更新状态栏。
        - 文本为绿色。
        - 前缀为 ✅。
        """
        if self._status_label:
            self.status_var.set(f"✅ {text}")
            self._status_label.configure(text_color=("#007A00", "#00C500"))  # Dark/Light green

    def update_status_error(self, text: str) -> None:
        """
        以“错误”状态更新状态栏。
        - 文本为红色。
        - 前缀为 ⚠️。
        """
        if self._status_label:
            self.status_var.set(f"⚠️ {text}")
            self._status_label.configure(text_color=("#C40000", "#FF5555"))  # Dark/Light red

    def run(self) -> None:
        self.root.mainloop()

    # -------------------------
    # Window control
    # -------------------------

    def _minimize_to_tray_with_animation(self) -> None:
        if not self.root:
            return

        def _hide_to_tray() -> None:
            if hasattr(self.app, "minimize_to_tray"):
                try:
                    self.app.minimize_to_tray()
                    return
                except Exception:
                    pass

            try:
                self.root.withdraw()
            except Exception:
                pass

        try:
            if self.root.state() != "withdrawn":
                self.root.iconify()
            self.root.after(220, _hide_to_tray)
        except Exception:
            _hide_to_tray()

    def _on_window_close(self) -> None:
        self._minimize_to_tray_with_animation()

    def minimize_to_tray(self, sender: Any = None, app_data: Any = None) -> None:
        if not self.root:
            return
        self.root.withdraw()

    def restore_from_tray(self) -> None:
        if not self.root:
            return

        def _restore() -> None:
            try:
                self.root.deiconify()
            except Exception:
                pass

            try:
                self.root.state("normal")
            except Exception:
                pass

            try:
                self.root.update_idletasks()
            except Exception:
                pass

            try:
                self.root.lift()
            except Exception:
                pass

            try:
                self.root.attributes("-topmost", True)
                self.root.after(250, lambda: self.root.attributes("-topmost", False))
            except Exception:
                pass

            try:
                self.root.focus_force()
            except Exception:
                pass


    def exit_application(self, sender: Any = None, app_data: Any = None) -> None:
        if hasattr(self.app, "exit_application"):
            self.app.exit_application()
            return

        if not self.root:
            return

        def _quit() -> None:
            try:
                self.root.quit()
            finally:
                try:
                    self.root.destroy()
                except Exception:
                    pass

        try:
            self.root.after(0, _quit)
        except Exception:
            _quit()

    def _initial_paint(self) -> None:
        try:
            self.root.update_idletasks()
        except Exception:
            pass

        try:
            self.root.lift()
        except Exception:
            pass

        try:
            self.root.attributes("-topmost", True)
            self.root.after(250, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

        try:
            self.root.focus_force()
        except Exception:
            pass

    def _ensure_recording_overlay(self) -> None:
        """
        /**
         * 确保“录音提示框浮层”已创建。
         *
         * 视觉效果：
         * - 屏幕底部居中
         * - 小卡片 + 文案 + 动画（不确定进度条）
         *
         * 说明：
         * - 该浮层是独立 Toplevel，不依赖主窗口是否在当前页面。
         * - 用于按下快捷键开始录音时的即时反馈。
         *
         * @returns {void}
         */
        """

        if self.root is None:
            return
        if self._recording_overlay and self._recording_overlay.winfo_exists():
            return

        # 使用原生 Toplevel：在 macOS 上更稳定地支持透明窗口背景
        overlay = tk.Toplevel(self.root)

        # 尽早让窗口“不可见”，避免系统在默认位置/默认背景短暂绘制
        try:
            overlay.wm_attributes("-alpha", 0.0)
        except Exception as e:
            print(f"⚠️ 设置录音浮层 alpha=0 失败（可忽略）: {e}")

        try:
            overlay.geometry("1x1+0+0")
        except Exception:
            pass

        try:
            overlay.withdraw()
        except Exception:
            pass

        try:
            overlay.overrideredirect(True)
        except Exception as e:
            print(f"⚠️ 设置录音浮层无边框失败（可忽略）: {e}")

        try:
            overlay.wm_attributes("-topmost", True)
        except Exception as e:
            print(f"⚠️ 设置录音浮层置顶失败（可忽略）: {e}")

        width = 100
        height = 40
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = screen_height - height - 100

        # 透明背景策略：
        # - macOS：-transparent + systemTransparent
        # - Windows：-transparentcolor + 颜色键
        # - Linux：通常不支持形状透明，这里尽量不报错
        if sys.platform == "darwin":
            try:
                overlay.wm_attributes("-transparent", True)
            except Exception as e:
                print(f"⚠️ macOS 设置 -transparent 失败（可能导致白底）: {e}")

            try:
                overlay.configure(bg="systemTransparent")
            except Exception as e:
                print(f"⚠️ macOS 设置 systemTransparent 失败（可能导致白底）: {e}")

            transparent_key_color: Optional[str] = None
        else:
            transparent_key_color = "#ff00ff"  # 选一个不常用的“色键”
            try:
                overlay.configure(bg=transparent_key_color)
                overlay.wm_attributes("-transparentcolor", transparent_key_color)
            except Exception as e:
                print(f"⚠️ 设置透明色键失败（可忽略，可能导致方形背景）: {e}")

        try:
            overlay.geometry(f"{width}x{height}+{x}+{y}")
        except Exception as e:
            print(f"⚠️ 设置录音浮层尺寸/位置失败（可忽略）: {e}")

        # 容器：圆角胶囊
        # 关键：bg_color 设为 transparent（或透明色键），否则圆角外侧可能露出白底
        container_bg_color = "transparent" if transparent_key_color is None else transparent_key_color
        container_frame = ctk.CTkFrame(
            overlay,
            fg_color="black",
            bg_color=container_bg_color,
            corner_radius=height // 2,
            border_width=1,
            border_color="white",
        )
        container_frame.pack(fill="both", expand=True)

        self._recording_overlay_animation = SoundWaveAnimation(
            container_frame, width=width - 20, height=height - 10
        )
        self._recording_overlay_animation.pack(pady=5, padx=10)

        self._recording_overlay = overlay

    def show_recording_overlay(self, text: str = "录音中…") -> None:
        """
        /**
         * 显示录音提示浮层并开始动画。
         *
         * 关键：
         * - _ensure_recording_overlay 里会把窗口 alpha 设为 0（完全透明）来避免闪白。
         * - 所以这里必须在 deiconify 后恢复 alpha=1，否则你会“看不到浮窗”。
         *
         * @param {string} text - 预留参数：后续可用于显示文案。
         * @returns {void}
         */
        """
        self._ensure_recording_overlay()
        if not self._recording_overlay:
            return
    
        overlay = self._recording_overlay
    
        try:
            overlay.deiconify()
            overlay.lift()
        except Exception as e:
            print(f"⚠️ 显示录音浮层失败（可忽略）: {e}")
            return
    
        # macOS：部分环境下需要在窗口映射后重新设置透明属性才更稳定
        if sys.platform == "darwin":
            try:
                overlay.wm_attributes("-transparent", True)
            except Exception as e:
                print(f"⚠️ macOS 重新设置 -transparent 失败（可能导致白底）: {e}")
    
            try:
                overlay.configure(bg="systemTransparent")
            except Exception as e:
                print(f"⚠️ macOS 重新设置 systemTransparent 失败（可能导致白底）: {e}")
    
        try:
            overlay.update_idletasks()
        except Exception:
            pass
    
        # 恢复可见
        try:
            overlay.wm_attributes("-alpha", 1.0)
        except Exception as e:
            # 如果这里失败，而 ensure 里 alpha=0 成功了，就会导致整窗不可见
            print(f"⚠️ 恢复录音浮层 alpha=1 失败（可能导致看不见）: {e}")
    
        if self._recording_overlay_animation:
            try:
                # 改为“全局音量数组 + GUI 轮询”驱动：不再启动随机动画
                # 启动一次轮询即可（update_recording_volume 内部会自我调度）
                self.update_recording_volume(0)
            except Exception as e:
                print(f"⚠️ 启动录音浮层音量轮询失败（可忽略）: {e}")
    
    def hide_recording_overlay(self):
        """
        /**
         * 隐藏录音提示浮层并停止动画。
         *
         * @returns {void}
         */
        """
        if not self._recording_overlay:
            return
    
        try:
            # 先设为透明，进一步减少 withdraw 的闪烁概率
            try:
                self._recording_overlay.wm_attributes("-alpha", 0.0)
            except Exception:
                pass
    
            self._recording_overlay.withdraw()
        except Exception as e:
            print(f"⚠️ 隐藏录音浮层失败（可忽略）: {e}")
    
        if self._recording_overlay_animation and self._recording_overlay_animation._animation_job:
            try:
                self._recording_overlay_animation.after_cancel(self._recording_overlay_animation._animation_job)
            except Exception as e:
                print(f"⚠️ 停止录音浮层动画失败（可忽略）: {e}")
            finally:
                self._recording_overlay_animation._animation_job = None

    def update_recording_volume(self, volume_level: int = 0):
        """
        /**
         * 录音浮窗：根据“全局音量数组”更新音波高度，并以 after 轮询方式持续刷新。
         *
         * 方案说明（最小改动实现）：
         * - AudioRecorder._record 会周期性写入 `GLOBAL_VOLUME_LEVELS` 与 `GLOBAL_VOLUME_SEQ`。
         * - 这里在 GUI 主线程轮询读取最新音量值，并驱动 `SoundWaveAnimation.update_animation`。
         * - 当浮窗不可见时，自动停止轮询（不再继续 after）。
         *
         * @param {number} volume_level - 兼容参数：外部传入时可忽略；默认从全局数组读取。
         * @returns {void}
         */
        """

        # 若浮窗不可见：停止轮询
        try:
            if not (self._recording_overlay and self._recording_overlay.winfo_viewable()):
                setattr(self, "_recording_overlay_volume_job", None)
                setattr(self, "_recording_overlay_volume_last_seq", -1)
                return
        except Exception:
            setattr(self, "_recording_overlay_volume_job", None)
            setattr(self, "_recording_overlay_volume_last_seq", -1)
            return

        if not self._recording_overlay_animation:
            return

        latest_level = int(volume_level) if volume_level is not None else 0
        seq = None

        try:
            from .components import audio_recorder as audio_recorder_module

            try:
                with audio_recorder_module.GLOBAL_VOLUME_LOCK:
                    seq = int(audio_recorder_module.GLOBAL_VOLUME_SEQ)
                    if audio_recorder_module.GLOBAL_VOLUME_LEVELS:
                        latest_level = int(audio_recorder_module.GLOBAL_VOLUME_LEVELS[-1])
                    else:
                        latest_level = 0
            except Exception as e:
                print(f"⚠️ 读取全局音量缓存失败（可忽略）: {e}")
        except Exception as e:
            print(f"⚠️ 导入 audio_recorder 失败（可忽略）: {e}")

        last_seq = getattr(self, "_recording_overlay_volume_last_seq", -1)
        if seq is None or seq != last_seq:
            try:
                self._recording_overlay_animation.update_animation(max(0, min(100, latest_level)))
            except Exception as e:
                print(f"⚠️ 更新音波动画失败（可忽略）: {e}")

            if seq is not None:
                setattr(self, "_recording_overlay_volume_last_seq", seq)

        # 轮询：确保同一时间只有一个 after job
        if getattr(self, "_recording_overlay_volume_job", None):
            return

        def _tick() -> None:
            setattr(self, "_recording_overlay_volume_job", None)
            self.update_recording_volume(0)

        try:
            job = self.root.after(50, _tick)
            setattr(self, "_recording_overlay_volume_job", job)
        except Exception as e:
            print(f"⚠️ 调度音量轮询失败（可忽略）: {e}")
            setattr(self, "_recording_overlay_volume_job", None)


class SoundWaveAnimation(ctk.CTkCanvas):

        """
        一个用 Canvas 实现的音波动画小组件。
        """

        def __init__(self, master, width=50, height=5, **kwargs):
            super().__init__(master, width=width, height=height, **kwargs)
            self.configure(bg="black", highlightthickness=0)
            self._width = width
            self._height = height
            self._animation_job = None
            self._num_bars = 15
            self._bar_width = 2
            self._gap = 2
            self._min_bar_height = 0
            self._max_bar_height = height - 5

            total_width = self._num_bars * (self._bar_width + self._gap) - self._gap
            self._start_x = (width - total_width) / 2

        def _draw_sound_wave(self, volume_level=None):
            """
            根据音量级别绘制一帧音波图像。
            volume_level: 0-100 的整数。如果为 None，则使用随机高度。
            """
            self.delete("all")
            for i in range(self._num_bars):
                if volume_level is not None:
                    # 基于音量，中间的音波高，两边的低
                    distance_from_center = abs(i - self._num_bars // 2)
                    dampening = 1 - (distance_from_center / (self._num_bars / 2)) ** 2
                    max_h = self._min_bar_height + (self._max_bar_height - self._min_bar_height) * (
                                volume_level / 100.0)
                    bar_height = max(self._min_bar_height, int(max_h * dampening * random.uniform(0.8, 1.2)))
                else:
                    bar_height = random.randint(self._min_bar_height, self._max_bar_height)

                x0 = self._start_x + i * (self._bar_width + self._gap)
                y0 = (self._height - bar_height) / 2
                x1 = x0 + self._bar_width
                y1 = y0 + bar_height
                self.create_rectangle(x0, y0, x1, y1, fill="white", outline="")

        def update_animation(self, volume_level: int):
            """
            由外部调用，传入实时音量来更新动画。
            """
            self._draw_sound_wave(volume_level)

        def start_random_animation(self):
            self._animate()

        def _animate(self):
            self._draw_sound_wave()
            self._animation_job = self.after(100, self._animate)