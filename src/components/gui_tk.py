import os
import tkinter as tk
# from tkinter import messagebox
from typing import Any, Dict, Optional
import sys, time
import json
import subprocess
from pathlib import Path

import customtkinter as ctk

import queue

from AppKit import NSImage, NSMakeSize, NSMenu, NSMenuItem, NSObject, NSStatusBar
import objc

from .config_manager import get_config_manager
from .ui_theme import GUIStyles
from ..util.app_logger import AppLogger

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None

from .hotkey import UniversalKeyListener, ShortcutKey, KeyEvent

# ============ 全局解耦队列 ============
# 所有 状态栏动作 都写入此队列，由 Tkinter 主循环轮询处理
_status_queue = queue.Queue()
# 文件下载进度 写入此队列。用于非 UI 线程向 UI 线程发送指令
_progress_queue = queue.Queue()
# _queue_lock = threading.Lock()
# _queue_callbacks = {}  # 存储回调函数，避免在 ObjC 中直接调用


def enqueue_action(action_type, window_id=None, data=None):
    """线程安全的入队函数，供 ObjC 回调调用"""
    try:
        _status_queue.put_nowait({
            'action': action_type,
            'window_id': window_id,
            'data': data
        })
    except:
        pass

def enqueue_action_progress(action_type, window_id=None, data=None):
    """
    发送 UI 动作指令的辅助函数
    :param action_type: 动作类型 (e.g., 'show', 'hide', 'progress_start')
    :param window_id: 相关窗口 ID (可选)
    :param data: 携带的数据 (可选)
    """
    try:
        _progress_queue.put((action_type, window_id, data))
    except Exception as e:
        print(f"❌ Enqueue action failed: {e}")

# ============ 状态栏控制器 ============
class MacStatusBar(NSObject):
    """
    macOS 原生状态栏控制器
    所有回调方法只做一件事：将动作类型写入全局队列
    """

    _instances = {}
    _id_counter = 0

    def init(self):
        """纯 ObjC 风格初始化，不接受任何参数"""
        self = objc.super(MacStatusBar, self).init()
        if self is None:
            return None

        self.window_id = None
        self.status_item = None
        self.menu = None
        self.status_menu_item = None

        return self

    def setupWithWindowId_(self, window_id):
        """设置窗口 ID 并初始化状态栏"""
        self.window_id = window_id

        try:
            # 创建状态栏项
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
            status_image = self._loadStatusBarImage()
            if status_image is not None:
                button = self.status_item.button()
                if button is not None:
                    button.setImage_(status_image)
                    button.setTitle_("")
                else:
                    self.status_item.setImage_(status_image)
            else:
                self.status_item.setTitle_("🔵")
            self.status_item.setHighlightMode_(True)

            # 创建菜单
            self.menu = NSMenu.alloc().init()

            # 菜单项 - 只绑定到简单的入队方法
            show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "打开 VoiceTyping", "onShow:", ""
            )
            show_item.setTarget_(self)
            self.menu.addItem_(show_item)

            hide_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "隐藏 VoiceTyping", "onHide:", ""
            )
            hide_item.setTarget_(self)
            self.menu.addItem_(hide_item)

            self.menu.addItem_(NSMenuItem.separatorItem())

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "退出", "onQuit:", ""
            )
            quit_item.setTarget_(self)
            self.menu.addItem_(quit_item)

            self.status_item.setMenu_(self.menu)

            # 注册实例
            MacStatusBar._instances[window_id] = self

            print(f"✅ 状态栏已创建 (ID: {window_id})")
            return self

        except Exception as e:
            print(f"❌ 状态栏创建失败：{e}")
            return self

    def _loadStatusBarImage(self):
        """加载菜单栏图标，失败时由调用方回退到文本状态图标。"""
        try:
            logo_path = Path(__file__).resolve().parents[2] / "assets" / "icon.png"
            if not logo_path.exists():
                return None
            image = NSImage.alloc().initWithContentsOfFile_(str(logo_path))
            if image is None:
                return None
            image.setSize_(NSMakeSize(18, 18))
            try:
                image.setTemplate_(False)
            except Exception:
                pass
            return image
        except Exception as e:
            print(f"⚠️ 菜单栏 logo 加载失败（将使用默认状态图标）: {e}")
            return None

    # ===== ObjC 回调方法 - 绝对不做任何复杂操作，只入队 =====

    def onShow_(self, sender):
        """显示窗口 - 仅入队"""
        enqueue_action('show', self.window_id)

    def onHide_(self, sender):
        """隐藏窗口 - 仅入队"""
        enqueue_action('hide', self.window_id)

    def onQuit_(self, sender):
        """退出程序 - 仅入队"""
        enqueue_action('quit', self.window_id)

    # ===== 供主线程调用的方法 =====

    def updateStatus_(self, text):
        """更新状态文本（在主线程调用）"""
        if self.status_menu_item:
            self.status_menu_item.setTitle_(f"● 状态：{text}")

    def remove(self):
        """移除状态栏"""
        if self.status_item:
            NSStatusBar.systemStatusBar().removeStatusItem_(self.status_item)
        if self.window_id in MacStatusBar._instances:
            del MacStatusBar._instances[self.window_id]


class VoiceInputGUI:
    def __init__(self, app: Any, app_name: str):
        print("DEBUG: VoiceInputGUI.__init__ start")
        _perf_t0 = time.perf_counter()
        self.app = app
        self.app_name = app_name
        self.config_manager = get_config_manager()
        try:
            ctk.set_appearance_mode("system")
        except Exception:
            pass


        # self.root = ctk.CTk()
        self.root = self._init_window2center()

        # 生成唯一 ID
        self._window_id = id(self.root)
        self.statusbar = None
        self._closing = False

        self.status_var = tk.StringVar(value="就绪")
        self._status_label: Optional[ctk.CTkLabel] = None

        # 录音浮层（纯 Cocoa）：macOS 下使用 NSPanel 非激活面板，不抢占输入光标
        self._cocoa_recording_overlay = None
        # 录音浮层：音量轮询 job（GUI 主线程）
        self._recording_overlay_volume_job = None
        self._recording_overlay_volume_last_seq = -1
        # 录音浮层：转写进度轮询 job（GUI 主线程）
        self._recording_overlay_progress_job = None
        self._recording_overlay_progress_value = 0.0
        self._recording_overlay_progress_last_ts = 0.0
        self._progress_overlay_requested = False
        self._progress_overlay_close_job = None

        self._nav_buttons: Dict[str, Dict[str, Any]] = {}
        self._nav_icons: Dict[str, ctk.CTkImage] = {}
        # self._nav_font is now provided by GUIStyles.get_nav_font()
        self._sidebar_bg_color = GUIStyles.COLOR_SIDEBAR_BG
        self._card_bg_color = GUIStyles.COLOR_CARD_BG
        self._home_stat_labels: Dict[str, ctk.CTkLabel] = {}
        self._home_history_list_frame: Optional[ctk.CTkFrame] = None
        self._home_empty_history_label: Optional[ctk.CTkLabel] = None
        self._home_recent_textbox: Optional[ctk.CTkTextbox] = None
        self._home_recent_meta_label: Optional[ctk.CTkLabel] = None
        self._home_recent_text_save_job: Any = None
        self._home_recent_text_updating = False
        self._home_history_records: list[dict[str, Any]] = []
        self._home_selected_record: Optional[dict[str, Any]] = None
        self._home_history_cache_signature: tuple[int, int] | None = None
        self._home_history_cache_records: list[dict[str, Any]] = []
        self._home_rendered_history_signature: tuple[int, int] | None = None
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        except Exception:
            pass

        self.pages: Dict[str, ctk.CTkFrame] = {}
        self.current_page: Optional[str] = None

        print("DEBUG: Before _build_ui")
        self._build_ui()
        print("DEBUG: After _build_ui")

        self.show_page("home")

        try:
            self._init_cocoa_recording_overlay()
        except Exception as e:
            print(f"⚠️ 初始化 Cocoa 录音浮层失败（将禁用录音浮层）: {e}")

        try:
            self.root.after(0, self._initial_paint)
        except Exception:
            pass

        ###### 状态栏相关 功能 ######
        self._setup_statusbar()
        # 启动队列轮询 - 这是处理状态栏事件的唯一入口
        self._poll_queue()

    def _init_window2center(self):
        root = ctk.CTk()
        root.withdraw()  # 先隐藏窗口
        root.title("")
        window_width = 1024
        window_height = 720

        root.update_idletasks()  # 确保获取的尺寸是准确的
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        # --- 居中代码结束 ---

        try:
            root.minsize(720, 520)
        except Exception:
            pass

        root.deiconify()  # 最后显示窗口

        return root


    def _post_gui_init(self) -> None:
        """GUI绘制完成后执行的重型初始化任务
        包括：
        1. 通知应用执行其他重型初始化（如STT）
        """
        print("🚀 开始GUI绘制后的重型初始化任务")

        # 2. 通知应用执行其他重型初始化
        try:
            on_gui_ready = getattr(self.app, "on_gui_ready", None)
            if callable(on_gui_ready):
                on_gui_ready()
                print("✅ 通知应用执行后加载初始化完成，仅通知成功")
        except Exception as e:
            print(f"⚠️ 通知应用执行后加载初始化失败: {e}")

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

        t0 = time.perf_counter()
        self._create_sidebar()
        print(f"[perf] gui:build_ui sidebar: {(time.perf_counter() - t0) * 1000:.1f}ms")

        t0 = time.perf_counter()
        self._create_content_area()
        print(f"[perf] gui:build_ui content_area: {(time.perf_counter() - t0) * 1000:.1f}ms")

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

    def _prepare_square_logo_image(
        self,
        image: "Image.Image",
        padding_ratio: float = 0.02,
        source_size: int = 144,
    ) -> "Image.Image":
        image = image.convert("RGBA")
        alpha_bbox = image.getchannel("A").getbbox()
        if not alpha_bbox:
            return image

        left, top, right, bottom = alpha_bbox
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        side = max(right - left, bottom - top)
        side = int(side * (1 + padding_ratio * 2))

        crop_left = int(round(center_x - side / 2))
        crop_top = int(round(center_y - side / 2))
        crop_right = crop_left + side
        crop_bottom = crop_top + side

        pad_left = max(0, -crop_left)
        pad_top = max(0, -crop_top)
        pad_right = max(0, crop_right - image.width)
        pad_bottom = max(0, crop_bottom - image.height)
        if any((pad_left, pad_top, pad_right, pad_bottom)):
            padded = Image.new(
                "RGBA",
                (image.width + pad_left + pad_right, image.height + pad_top + pad_bottom),
                (0, 0, 0, 0),
            )
            padded.paste(image, (pad_left, pad_top))
            image = padded
            crop_left += pad_left
            crop_top += pad_top
            crop_right += pad_left
            crop_bottom += pad_top
        logo = image.crop((crop_left, crop_top, crop_right, crop_bottom))
        logo = logo.resize((source_size, source_size), Image.Resampling.LANCZOS)
        if ImageFilter is not None:
            logo = logo.filter(ImageFilter.UnsharpMask(radius=0.7, percent=120, threshold=2))
        return logo

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
            fg_color=GUIStyles.COLOR_DIVIDER,
        )
        sidebar_border.pack(side="left", fill="y")
        sidebar_border.pack_propagate(False)

        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=18, pady=(20, 18))

        self._app_logo_image = None
        logo_display_size = 36
        if Image is not None:
            try:
                logo_path = Path(__file__).resolve().parents[2] / "assets" / "logo-small.png"
                if logo_path.exists():
                    logo_image = self._prepare_square_logo_image(Image.open(logo_path))
                    self._app_logo_image = ctk.CTkImage(
                        light_image=logo_image,
                        dark_image=logo_image,
                        size=(logo_display_size, logo_display_size),
                    )
            except Exception as e:
                print(f"⚠️ 侧边栏 logo 加载失败（可忽略）: {e}")

        if self._app_logo_image is not None:
            brand_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
            brand_frame.pack(anchor="w")
            ctk.CTkLabel(
                brand_frame,
                text="",
                image=self._app_logo_image,
                width=logo_display_size,
                height=logo_display_size,
            ).pack(side="left")
            ctk.CTkLabel(
                brand_frame,
                text="VoiceTyping",
                font=ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=15, weight="bold"),
                text_color=GUIStyles.COLOR_TEXT_PRIMARY,
            ).pack(side="left", padx=(8, 0))
        else:
            ctk.CTkLabel(
                title_frame,
                text=self.app_name,
                font=GUIStyles.get_title_font(),
                text_color=GUIStyles.COLOR_TEXT_PRIMARY,
            ).pack(anchor="w")

        nav_buttons = [
            ("主页", "home"),
            ("设置", "settings"),
            ("关于", "about"),
            ("退出", "exit"),
        ]
        icon_letters = {"home": "H", "settings": "S", "about": "C", "exit": "E"}

        self._nav_buttons = {}
        for text, page_name in nav_buttons:
            container = ctk.CTkFrame(sidebar, fg_color="transparent")
            pack_args = {"fill": "x", "padx": 10, "pady": 2}
            if page_name == "exit":
                pack_args.update({"side": "bottom", "pady": (2, 18)})
            container.pack(**pack_args)

            container.grid_columnconfigure(0, weight=0, minsize=0)
            container.grid_columnconfigure(1, weight=1)

            indicator = ctk.CTkFrame(
                container, 
                width=0,
                height=0,
                corner_radius=0,
                fg_color="transparent"
            )
            indicator.grid(row=0, column=0, sticky="ns", pady=0, padx=0)

            # Button
            icon = self._nav_icons.get(page_name)
            if icon is None:
                icon = self._create_nav_icon(icon_letters.get(page_name, "•"))
                if icon:
                    self._nav_icons[page_name] = icon
            
            # Special command for exit
            if page_name == "exit":
                cmd = self.exit_application
            else:
                cmd = lambda p=page_name: self.show_page(p)

            btn = ctk.CTkButton(
                container,
                text=text,
                anchor="w",
                font=GUIStyles.get_nav_font(),
                fg_color=GUIStyles.COLOR_NAV_BG_DEFAULT,
                text_color=GUIStyles.COLOR_DESTRUCTIVE if page_name == "exit" else GUIStyles.COLOR_NAV_TEXT_DEFAULT,
                hover_color=GUIStyles.COLOR_NAV_BG_HOVER,
                compound="left",
                height=38,
                corner_radius=10,
                command=cmd,
            )
            btn.grid(row=0, column=1, sticky="ew")
            
            # Store references
            self._nav_buttons[page_name] = {
                "container": container,
                "indicator": indicator,
                "button": btn
            }

    def _create_content_area(self) -> None:
        content_area = ctk.CTkFrame(self.root, corner_radius=0, fg_color=GUIStyles.COLOR_CONTENT_BG)
        content_area.pack(side="left", fill="both", expand=True)
        content_area.grid_rowconfigure(0, weight=1)
        content_area.grid_columnconfigure(0, weight=1)

        self.pages["home"] = self._create_home_page(content_area, "主页")
        # self.pages["dictionary"] = self._create_placeholder_page(content_area, "词典")
        self.pages["about"] = self._create_about_page(content_area)
        self.pages["settings"] = self._create_settings_page(content_area)
        # self.pages["provider"] = self._build_provider_settings_page(content_area)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._create_status_bar(content_area)

    def _create_status_bar(self, parent: ctk.CTkFrame) -> None:
        """
        在右侧内容区的底部创建状态栏。
        """
        status_bar_frame = ctk.CTkFrame(
            parent,
            height=30,
            corner_radius=0,
            fg_color=GUIStyles.COLOR_WINDOW_BG,
            border_width=1,
            border_color=GUIStyles.COLOR_DIVIDER,
        )
        status_bar_frame.grid(row=1, column=0, sticky="sew")
        status_bar_frame.pack_propagate(False)

        self._status_label = ctk.CTkLabel(
            status_bar_frame,
            textvariable=self.status_var,
            text_color=GUIStyles.COLOR_TEXT_MUTED,
            font=GUIStyles.get_note_font(),
        )
        self._status_label.pack(side="right", padx=10)


    # -------------------------
    # Pages
    # -------------------------
    def _create_placeholder_page(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        page = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(page, text=title, font=GUIStyles.get_section_title_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY).pack(
            anchor="w", padx=20, pady=(20, 10)
        )
        ctk.CTkLabel(page, text="开发中…", font=GUIStyles.get_body_font(), text_color=GUIStyles.COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20)
        return page

    def _create_about_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """
        创建关于页面。
        """
        page = ctk.CTkFrame(parent, fg_color=GUIStyles.COLOR_CONTENT_BG)
        page.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(page, fg_color="transparent")
        container.grid(row=0, column=0, padx=40, pady=48, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="关于",
            font=GUIStyles.get_page_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        card = ctk.CTkFrame(container, **GUIStyles.get_card_frame_args())
        card.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="MyVoiceTyping 是一款面向 macOS 的本地语音输入工具。",
            font=GUIStyles.get_section_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 10))

        body_text = (
            "它使用本地语音识别模型和本地文字处理模型完成转写与简单润色，"
            "不依赖云端模型处理你的语音和文本，数据更安全，也更适合隐私敏感的输入场景。\n\n"
            "相比键盘输入，语音更适合快速记录想法、撰写长段内容和在聊天、文档、编程等场景中连续表达。"
            "普通打字往往每分钟几十个字，而自然说话可以更快地输出完整句子；对长文本来说，语音输入通常能显著减少敲击和停顿"
        )
        body_box = ctk.CTkTextbox(
            card,
            height=146,
            font=GUIStyles.get_body_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
            fg_color="transparent",
            border_width=0,
            wrap="word",
        )
        body_box.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 20))
        body_box.insert("1.0", body_text)
        body_box.configure(state="disabled")

        version = "1.0.0"
        try:
            from src import __version__ as package_version
            version = str(package_version or version)
        except Exception:
            pass
        ctk.CTkLabel(
            card,
            text=f"版本 {version}",
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_MUTED,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 18))

        return page

    def _create_home_page(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        """
        创建主页,展示应用的欢迎信息和核心功能。
        """
        page = ctk.CTkScrollableFrame(parent, fg_color=GUIStyles.COLOR_CONTENT_BG)
        page.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="语音输入工作台",
            font=GUIStyles.get_page_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="查看最近录音、转写内容、累计字数和提效统计。",
            font=GUIStyles.get_body_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        ctk.CTkButton(
            header,
            text="刷新",
            width=76,
            command=lambda: self._refresh_home_dashboard(force=True),
            **GUIStyles.get_secondary_button_args(),
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=28, pady=(6, 18))
        for col in range(5):
            stats.grid_columnconfigure(col, weight=1, uniform="home_stats")

        stat_specs = [
            ("today_count", "今日记录", "0"),
            ("today_chars", "今日字数", "0"),
            ("total_count", "历史记录", "0"),
            ("total_chars", "累计字数", "0"),
            ("saved_time", "已节约时间", "0 min"),
        ]
        for col, (key, label, value) in enumerate(stat_specs):
            card = ctk.CTkFrame(stats, **GUIStyles.get_card_frame_args())
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == len(stat_specs) - 1 else 6))
            ctk.CTkLabel(
                card,
                text=label,
                font=GUIStyles.get_stat_label_font(),
                text_color=GUIStyles.COLOR_TEXT_SECONDARY,
            ).pack(anchor="w", padx=16, pady=(14, 4))
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=GUIStyles.get_saved_time_value_font() if key == "saved_time" else GUIStyles.get_stat_value_font(),
                text_color=GUIStyles.COLOR_DESTRUCTIVE if key == "saved_time" else GUIStyles.COLOR_TEXT_PRIMARY,
            )
            value_label.pack(anchor="w", padx=12 if key == "saved_time" else 16, pady=(0, 14))
            self._home_stat_labels[key] = value_label

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 28))
        body.grid_rowconfigure(0, weight=1)
        for col in range(4):
            body.grid_columnconfigure(col, weight=1, uniform="home_body_columns")

        history_card = ctk.CTkFrame(body, **GUIStyles.get_card_frame_args())
        history_card.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=(0, 6))
        history_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            history_card,
            text="历史对话记录",
            font=GUIStyles.get_section_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            history_card,
            text="按时间倒序展示最近 8 条语音输入",
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
        self._home_history_list_frame = ctk.CTkFrame(history_card, fg_color="transparent")
        self._home_history_list_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

        detail_card = ctk.CTkFrame(body, **GUIStyles.get_card_frame_args())
        detail_card.grid(row=0, column=3, sticky="nsew", padx=(6, 0))
        detail_card.grid_columnconfigure(0, weight=1)
        detail_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            detail_card,
            text="最近一次输入",
            font=GUIStyles.get_section_title_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 12))
        self._home_recent_meta_label = None

        self._home_recent_textbox = ctk.CTkTextbox(
            detail_card,
            height=200,
            corner_radius=8,
            border_width=1,
            border_color=GUIStyles.COLOR_CARD_BORDER,
            fg_color=GUIStyles.COLOR_CONTROL_BG,
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
            font=GUIStyles.get_note_font(),
            wrap="word",
        )
        self._home_recent_textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        try:
            self._home_recent_textbox._textbox.bind("<FocusOut>", self._on_home_recent_text_focus_out)
        except Exception:
            self._home_recent_textbox.bind("<FocusOut>", self._on_home_recent_text_focus_out)
        try:
            self.root.bind("<Button-1>", self._on_home_recent_click_outside, add="+")
        except Exception:
            pass

        actions = ctk.CTkFrame(detail_card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 18))
        actions.grid_columnconfigure(0, weight=1)
        action_button_args = {
            **GUIStyles.get_button_args(),
            "width": 180,
            "height": 30,
            "corner_radius": 6,
            "font": ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12, weight="bold"),
        }
        ctk.CTkButton(
            actions,
            text="打开音频目录",
            command=lambda: self._open_path(self.config_manager.get_audio_dir(), create_if_missing=True),
            **action_button_args,
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            actions,
            text="打开转写目录",
            command=lambda: self._open_path(self.config_manager.get_transcripts_dir(), create_if_missing=True),
            **action_button_args,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self._refresh_home_dashboard()

        return page

    @staticmethod
    def _home_char_count(text: str) -> int:
        return len("".join(str(text or "").split()))

    @staticmethod
    def _format_saved_typing_time(total_chars: int) -> str:
        typing_chars_per_minute = 50
        minutes = max(0, round(int(total_chars or 0) / typing_chars_per_minute))
        if minutes < 60:
            return f"{minutes} min"
        hours, remain_minutes = divmod(minutes, 60)
        if remain_minutes <= 0:
            return f"{hours} hr"
        return f"{hours} hr {remain_minutes} min"

    @staticmethod
    def _history_output_text(record: dict[str, Any]) -> str:
        return str(record.get("final_text") or record.get("raw_text") or "")

    @staticmethod
    def _history_input_text(record: dict[str, Any]) -> str:
        return str(record.get("raw_text") or "")

    def _history_file_path(self) -> Path:
        return self.config_manager.get_transcripts_dir() / "voice_history.jsonl"

    def _load_home_history(self, limit: int | None = None, force: bool = False) -> list[dict[str, Any]]:
        history_path = self._history_file_path()
        if not history_path.exists():
            self._home_history_cache_signature = None
            self._home_history_cache_records = []
            return []

        records: list[dict[str, Any]] = []
        try:
            stat = history_path.stat()
            signature = (int(stat.st_mtime_ns), int(stat.st_size))
            if not force and limit is None and self._home_history_cache_signature == signature:
                return list(self._home_history_cache_records)
            lines = history_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            print(f"⚠️ 读取转写历史失败（可忽略）: {e}")
            return []

        source_lines = lines[-limit:] if limit is not None and limit > 0 else lines
        for line in source_lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except Exception:
                continue
        records.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        if limit is None:
            self._home_history_cache_signature = signature
            self._home_history_cache_records = list(records)
        return records

    def _set_home_textbox_text(self, text: str) -> None:
        if self._home_recent_textbox is None:
            return
        try:
            self._home_recent_text_updating = True
            self._home_recent_textbox.configure(state="normal")
            self._home_recent_textbox.delete("1.0", "end")
            self._home_recent_textbox.insert("1.0", text or "暂无转写文本")
            self._home_recent_textbox.edit_modified(False)
        except Exception:
            pass
        finally:
            self._home_recent_text_updating = False

    def _on_home_recent_text_focus_out(self, event: Any = None) -> None:
        if self._home_recent_text_updating or self._home_recent_textbox is None:
            return
        self._save_home_recent_text_edit()

    def _on_home_recent_click_outside(self, event: Any = None) -> None:
        textbox = self._home_recent_textbox
        if self._home_recent_text_updating or textbox is None:
            return
        try:
            inner = getattr(textbox, "_textbox", textbox)
            widget = event.widget if event is not None else None
            if widget is inner or widget is textbox:
                return
        except Exception:
            pass
        self._save_home_recent_text_edit()

    def _save_home_recent_text_edit(self) -> None:
        self._home_recent_text_save_job = None
        record = self._home_selected_record
        textbox = self._home_recent_textbox
        if not record or textbox is None:
            return

        try:
            edited_text = textbox.get("1.0", "end-1c").strip()
        except Exception:
            return

        record_id = str(record.get("id") or "")
        data_id = str(record.get("dataId") or "")
        if not record_id and not data_id:
            return

        current_output = self._history_output_text(record).strip()
        if edited_text == current_output:
            return

        history_path = self._history_file_path()
        if not history_path.exists():
            return

        try:
            lines = history_path.read_text(encoding="utf-8").splitlines()
            rewritten: list[str] = []
            saved = False
            for line in lines:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    rewritten.append(line)
                    continue
                item_id = str(item.get("id") or "")
                item_data_id = str(item.get("dataId") or "")
                if (record_id and item_id == record_id) or (data_id and item_data_id == data_id):
                    item.pop("input", None)
                    item.pop("output", None)
                    item["final_text"] = edited_text
                    item["char_count"] = self._home_char_count(edited_text)
                    record.update(item)
                    saved = True
                rewritten.append(json.dumps(item, ensure_ascii=False))

            if saved:
                history_path.write_text("\n".join(rewritten) + ("\n" if rewritten else ""), encoding="utf-8")
                self._home_history_cache_signature = None
                self._home_rendered_history_signature = None
                self._refresh_home_dashboard(force=True)
                self._select_home_history_record(record)
        except Exception as e:
            print(f"⚠️ 保存手工修正文本失败（可忽略）: {e}")

    def _render_home_history_rows(self, records: list[dict[str, Any]]) -> None:
        frame = self._home_history_list_frame
        if frame is None:
            return

        for child in frame.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        if not records:
            self._home_empty_history_label = ctk.CTkLabel(
                frame,
                text="暂无语音输入记录。完成一次录音转写后，这里会显示转写文字。",
                font=GUIStyles.get_body_font(),
                text_color=GUIStyles.COLOR_TEXT_SECONDARY,
                wraplength=460,
                justify="left",
            )
            self._home_empty_history_label.pack(anchor="w", padx=8, pady=12)
            return

        for index, record in enumerate(records[:8]):
            final_text = self._history_output_text(record)
            created_at = str(record.get("created_at") or "")
            audio_path = str(record.get("audio_path") or "")
            char_count = int(record.get("char_count") or self._home_char_count(final_text))

            row = ctk.CTkFrame(frame, **GUIStyles.get_soft_card_frame_args())
            row.pack(fill="x", padx=4, pady=(0, 8))
            row.grid_columnconfigure(0, weight=1)

            title = final_text[:42] + ("..." if len(final_text) > 42 else "")
            if not title:
                title = "空转写文本"
            title_label = ctk.CTkLabel(
                row,
                text=title,
                font=GUIStyles.get_body_font(),
                text_color=GUIStyles.COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            title_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))

            meta = f"{created_at.replace('T', ' ')} · {char_count} 字"
            if audio_path:
                meta += f" · {Path(audio_path).name}"
            ctk.CTkLabel(
                row,
                text=meta,
                font=GUIStyles.get_note_font(),
                text_color=GUIStyles.COLOR_TEXT_SECONDARY,
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

            ctk.CTkButton(
                row,
                text="查看",
                width=58,
                command=lambda r=record: self._select_home_history_record(r),
                **GUIStyles.get_weak_action_button_args(),
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=10)

            if index == 0:
                self._select_home_history_record(record)

    def _select_home_history_record(self, record: dict[str, Any]) -> None:
        self._home_selected_record = record

        final_text = self._history_output_text(record)
        self._set_home_textbox_text(final_text)

    def _refresh_home_dashboard(self, force: bool = False) -> None:
        records = self._load_home_history(force=force)
        self._home_history_records = records
        history_signature = self._home_history_cache_signature

        today_prefix = time.strftime("%Y-%m-%d")
        today_count = sum(1 for r in records if str(r.get("created_at") or "").startswith(today_prefix))
        total_count = len(records)
        def _record_char_count(record: dict[str, Any]) -> int:
            return int(record.get("char_count") or self._home_char_count(self._history_output_text(record)))

        today_chars = sum(_record_char_count(r) for r in records if str(r.get("created_at") or "").startswith(today_prefix))
        total_chars = sum(_record_char_count(r) for r in records)
        values = {
            "today_count": str(today_count),
            "today_chars": str(today_chars),
            "total_count": str(total_count),
            "total_chars": str(total_chars),
            "saved_time": self._format_saved_typing_time(total_chars),
        }
        for key, value in values.items():
            label = self._home_stat_labels.get(key)
            if label is not None:
                try:
                    label.configure(text=value)
                except Exception:
                    pass

        should_render_history = force or self._home_rendered_history_signature != history_signature

        if not records:
            self._home_selected_record = None
            if self._home_recent_meta_label is not None:
                self._home_recent_meta_label.configure(text="暂无记录")
            self._set_home_textbox_text("完成一次语音输入后，这里会显示转写后的文字。")
            should_render_history = True

        if should_render_history:
            self._render_home_history_rows(records)
            self._home_rendered_history_signature = history_signature

    def notify_transcription_record_added(self, record: dict[str, Any] | None = None) -> None:
        try:
            self.root.after(0, lambda: self._refresh_home_dashboard(force=True))
        except Exception:
            self._refresh_home_dashboard(force=True)

    def _open_path(self, path: str | Path, create_if_missing: bool = False, reveal: bool = False) -> None:
        try:
            p = Path(path).expanduser()
            should_reveal = reveal and p.exists() and p.is_file()
            if not p.exists():
                if create_if_missing:
                    p.mkdir(parents=True, exist_ok=True)
                elif p.parent.exists():
                    p = p.parent
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p = p.parent
            if should_reveal:
                subprocess.run(["open", "-R", str(p)], check=False)
            else:
                subprocess.run(["open", str(p)], check=False)
        except Exception as e:
            print(f"Failed to open path: {e}")

    def _create_section_card(self, parent, title, row):
        """
        创建带有标题和分割线的卡片容器。
        """
        card = ctk.CTkFrame(parent, **GUIStyles.get_card_frame_args())
        card.grid(row=row, column=0, sticky="ew", padx=28, pady=10)
        card.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(card, text=title, font=GUIStyles.get_section_title_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY)
        title_label.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 6))

        # Divider
        divider = ctk.CTkFrame(card, height=1, fg_color=GUIStyles.COLOR_DIVIDER)
        divider.grid(row=1, column=0, sticky="ew", padx=22, pady=(4, 16))

        # Content Container
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 22))
        content.grid_columnconfigure(1, weight=1)

        return content

    def _create_log_row(self, parent, row):
        """
        创建日志目录行。
        """
        # Left side: Title
        left_frame = ctk.CTkFrame(parent, fg_color="transparent")
        left_frame.grid(row=row, column=0, sticky="w", padx=(0, 20))

        ctk.CTkLabel(left_frame, text="日志目录", font=GUIStyles.get_label_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY).pack(anchor="w")

        # Right side: Button
        ctk.CTkButton(
            parent,
            text="打开日志目录",
            command=self._open_log_directory,
            **GUIStyles.get_button_args()
        ).grid(row=row, column=1, sticky="e")

    def _open_log_directory(self):
        """打开日志目录"""
        try:
            log_dir = AppLogger.get_log_dir()
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
                
            subprocess.run(["open", str(log_dir)], check=False)
        except Exception as e:
            print(f"Failed to open log directory: {e}")

    def _create_settings_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        page = ctk.CTkScrollableFrame(parent, fg_color=GUIStyles.COLOR_CONTENT_BG)
        page.grid_columnconfigure(0, weight=1)

        # --- 页面标题 ---
        ctk.CTkLabel(page, text="设置", font=GUIStyles.get_page_title_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w", padx=28, pady=(26, 12)
        )

        # --- 输入快捷键部分 ---
        hotkey_content = self._create_section_card(page, "输入快捷键", 1)
        self._create_hotkey_setting(
            hotkey_content,
            title="语音输入",
            config_key="press_hotkey",
            description="按住快捷键说话，松开后自动转写并输入。",
            row=0,
        )

        # --- 文本处理部分 ---
        rewrite_content = self._create_section_card(page, "文本处理", 2)
        self._create_text_rewrite_setting(rewrite_content, row=0)

        # --- 热词设置部分 ---
        hotword_content = self._create_section_card(page, "热词设置", 3)
        self._create_hotword_setting(hotword_content, row=0)

        # --- 日志部分 ---
        log_content = self._create_section_card(page, "日志", 4)
        self._create_log_row(log_content, 0)

        # Prevent scrolling jitter at the bottom
        ctk.CTkFrame(page, height=20, fg_color="transparent").grid(row=5, column=0)

        return page

    def _create_text_rewrite_setting(self, parent: ctk.CTkFrame, row: int) -> None:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        container.grid_columnconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(container, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=(0, 20))

        ctk.CTkLabel(
            left_frame,
            text="本地纠错和输入润色",
            font=GUIStyles.get_label_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            left_frame,
            text="开启后会在转录完成后进行本地文本纠错和简单润色。",
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))

        enabled_var = tk.BooleanVar(value=bool(self.config_manager.get("format_text", True)))

        def _save() -> None:
            enabled = bool(enabled_var.get())
            self.config_manager.set("format_text", enabled)
            if enabled:
                self.update_status_success("本地纠错和输入润色已开启")
                try:
                    preload = getattr(self.app, "_preload_local_rewriter", None)
                    if callable(preload):
                        preload()
                except Exception as e:
                    print(f"⚠️ 触发本地纠错模型预加载失败（可忽略）: {e}")
            else:
                self.update_status_success("本地纠错和输入润色已关闭")

        ctk.CTkSwitch(
            container,
            text="",
            variable=enabled_var,
            command=_save,
            **GUIStyles.get_switch_args(),
        ).grid(row=0, column=1, sticky="e")

    def _build_provider_settings_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        page = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        if self.config_manager.get("llm_text_provider") != "llama_cpp":
            self.config_manager.set("llm_text_provider", "llama_cpp")

        ctk.CTkLabel(page, text="服务设置", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=18, pady=(18, 12), sticky="w"
        )

        self._create_hotword_setting(page, row=1)

        return page

    def _create_hotword_setting(self, parent: ctk.CTkFrame, row: int) -> None:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, columnspan=2, padx=0, pady=(12, 0), sticky="ew")
        container.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(container, fg_color="transparent")
        body.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        available_frame = ctk.CTkFrame(body, fg_color="transparent")
        available_frame.grid(row=1, column=0, sticky="ew", pady=(8, 14))

        hint_frame = ctk.CTkFrame(body, fg_color="transparent")
        hint_frame.grid(row=2, column=0, sticky="w", pady=(0, 14))

        selected_frame = ctk.CTkFrame(body, fg_color="transparent")
        selected_frame.grid(row=4, column=0, sticky="ew")
        selected_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="可选热词词典",
            font=GUIStyles.get_label_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            body,
            text="已加载词典",
            font=GUIStyles.get_label_font(),
            text_color=GUIStyles.COLOR_TEXT_PRIMARY,
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        ctk.CTkLabel(
            hint_frame,
            text="更多分类词库，可以从搜狗细胞词库",
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_MUTED,
        ).pack(side="left")
        download_link = ctk.CTkLabel(
            hint_frame,
            text="下载",
            font=ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=12, weight="bold"),
            text_color=GUIStyles.COLOR_ACCENT,
            cursor="hand2",
        )
        download_link.pack(side="left", padx=(4, 0))
        download_link.bind(
            "<Button-1>",
            lambda _event: subprocess.run(
                ["open", "https://pinyin.sogou.com/dict/"],
                check=False,
            ),
        )

        selected_paths = self.config_manager.get_selected_hotword_dictionary_paths()

        def _save_selected() -> None:
            self.config_manager.set_selected_hotword_dictionary_paths(selected_paths)
            total = len(self.config_manager.get_funasr_hotwords())
            self.update_status_success(f"热词词典已保存，共加载 {total} 个热词")

        def _render_all() -> None:
            _render_available()
            _render_selected()

        def _dictionary_label(item: dict) -> str:
            return f"{item.get('name')} ({item.get('word_count', 0)})"

        def _dictionary_display_name(dictionary_path: str) -> str:
            for item in self.config_manager.list_hotword_dictionaries():
                if str(item.get("path") or "") == dictionary_path:
                    return str(item.get("name") or Path(dictionary_path).stem)
            return Path(dictionary_path).stem

        def _render_available() -> None:
            for widget in available_frame.winfo_children():
                widget.destroy()
            dictionaries = self.config_manager.list_hotword_dictionaries()
            selected = set(selected_paths)
            if not dictionaries:
                ctk.CTkLabel(
                    available_frame,
                    text="暂无可用词典",
                    font=GUIStyles.get_note_font(),
                    text_color=GUIStyles.COLOR_TEXT_MUTED,
                ).grid(row=0, column=0, sticky="w")
                return
            for index, item in enumerate(dictionaries):
                path = str(item.get("path") or "")
                is_selected = path in selected
                button = ctk.CTkButton(
                    available_frame,
                    text=_dictionary_label(item),
                    width=150,
                    state="disabled" if is_selected else "normal",
                    command=lambda p=path: _add_dictionary(p),
                    **GUIStyles.get_secondary_button_args(),
                )
                button.grid(row=index // 3, column=index % 3, padx=(0, 8), pady=(6, 0), sticky="w")

        def _add_dictionary(path: str) -> None:
            if path and path not in selected_paths:
                selected_paths.append(path)
                _save_selected()
                _render_all()

        def _remove_dictionary(path: str) -> None:
            if path in selected_paths:
                selected_paths.remove(path)
                _save_selected()
                _render_all()

        def _render_selected() -> None:
            for widget in selected_frame.winfo_children():
                widget.destroy()
            if not selected_paths:
                ctk.CTkLabel(
                    selected_frame,
                    text="未加载热词词典",
                    font=GUIStyles.get_note_font(),
                    text_color=GUIStyles.COLOR_TEXT_MUTED,
                ).grid(row=0, column=0, sticky="w")
                return
            for index, path in enumerate(list(selected_paths)):
                _render_dictionary_editor(selected_frame, index, path)

        def _render_dictionary_editor(parent_frame: ctk.CTkFrame, editor_row: int, dictionary_path: str) -> None:
            words = self.config_manager.load_hotword_dictionary(dictionary_path)

            card = ctk.CTkFrame(
                parent_frame,
                **GUIStyles.get_card_frame_args(),
            )
            card.grid(row=editor_row, column=0, sticky="ew", pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
            header.grid_columnconfigure(0, weight=1)

            name = _dictionary_display_name(dictionary_path)
            ctk.CTkLabel(
                header,
                text=f"{name} · {len(words)} 个词",
                font=GUIStyles.get_label_font(),
                text_color=GUIStyles.COLOR_TEXT_PRIMARY,
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(
                header,
                text="移除",
                width=64,
                command=lambda p=dictionary_path: _remove_dictionary(p),
                **GUIStyles.get_secondary_button_args(),
            ).grid(row=0, column=1, sticky="e")

            ctk.CTkLabel(
                card,
                text="一行一个热词。保存后，下次语音转写会重新加载已选词典。",
                font=GUIStyles.get_note_font(),
                text_color=GUIStyles.COLOR_TEXT_MUTED,
            ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

            textbox = ctk.CTkTextbox(
                card,
                height=180,
                corner_radius=8,
                border_width=1,
                border_color=GUIStyles.COLOR_CARD_BORDER,
                fg_color=GUIStyles.COLOR_CONTROL_BG,
                text_color=GUIStyles.COLOR_TEXT_PRIMARY,
                font=GUIStyles.get_body_font(),
            )
            textbox.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")
            textbox.insert("1.0", "\n".join(words))
            self._bind_textbox_local_scroll(textbox)

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
            actions.grid_columnconfigure(0, weight=1)

            def _save_words() -> None:
                raw_text = textbox.get("1.0", "end")
                updated_words = [
                    self.config_manager._normalize_hotword(line)
                    for line in raw_text.splitlines()
                ]
                updated_words = [word for word in updated_words if word]
                self.config_manager.save_hotword_dictionary(dictionary_path, updated_words)
                _save_selected()
                _render_all()

            ctk.CTkButton(
                actions,
                text="保存词典",
                width=96,
                command=_save_words,
                **GUIStyles.get_weak_action_button_args(),
            ).grid(row=0, column=1, sticky="e")

        _render_all()

    # -------------------------
    # Widgets helpers
    # -------------------------

    def _bind_textbox_local_scroll(self, textbox: ctk.CTkTextbox) -> None:
        """Keep mouse-wheel scrolling inside a textbox from bubbling to parent scroll frames."""
        target = getattr(textbox, "_textbox", textbox)

        def _scroll_units(delta: int) -> int:
            if not delta:
                return 0
            if abs(delta) >= 120:
                return -int(delta / 120)
            return -1 if delta > 0 else 1

        def _on_mousewheel(event) -> str:
            units = _scroll_units(getattr(event, "delta", 0))
            if units:
                target.yview_scroll(units, "units")
            return "break"

        def _on_button4(_event) -> str:
            target.yview_scroll(-1, "units")
            return "break"

        def _on_button5(_event) -> str:
            target.yview_scroll(1, "units")
            return "break"

        for widget in {textbox, target}:
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_button4)
            widget.bind("<Button-5>", _on_button5)

    def _auto_save_on_change(self, var: tk.StringVar, key: str) -> None:
        """
        为 StringVar 变量添加跟踪回调，当其内容发生变化时，自动将新值保存到配置中。
        这是一个通用函数，可以用于任何希望在用户输入时自动保存的设置项。

        @param var: 需要跟踪的 tkinter StringVar 对象。
        @param key: 对应于配置管理器中的键名 (config key)。
        """
        def _save(*_args) -> None:
            """
            回调函数，用于将 StringVar 的当前值保存到配置中。
            """
            try:
                value = var.get()
                self.config_manager.set(key, value)
                print(f"配置 '{key}' 已自动更新为 '{value}'")
            except Exception as e:
                error_msg = f"自动保存配置 '{key}' 失败: {e}"
                print(error_msg)
                self.update_status_error(error_msg)

        var.trace_add("write", _save)

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
        ctk.CTkLabel(left_frame, text=title, font=GUIStyles.get_label_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            left_frame,
            text=description,
            font=GUIStyles.get_note_font(),
            text_color=GUIStyles.COLOR_TEXT_SECONDARY,
            wraplength=250,
            justify="left",
        ).pack(
            anchor="w", pady=(4, 0)
        )

        # --- 右侧：动态内容区域 ---
        right_frame = ctk.CTkFrame(parent, fg_color="transparent")
        right_frame.grid(row=row, column=1, sticky="ew", pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)

        # --- State ---
        # 录制状态
        recorder: Optional[UniversalKeyListener] = None
        current_recording_keys: set[str] = set()

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
            **GUIStyles.get_button_args(),
            command=lambda: switch_to_edit_mode(activate_listeners=True)
        )
        record_button.grid(row=0, column=0, sticky="ew", ipady=4)


        entry = ctk.CTkEntry(
            right_frame, 
            placeholder_text="请按下快捷键...",
            **GUIStyles.get_entry_args()
        )

        bubble_container = ctk.CTkFrame(
            right_frame,
            fg_color="transparent",
            corner_radius=8,
        )
        bubble_container.grid_columnconfigure(0, weight=1)
        change_button = ctk.CTkButton(
            bubble_container,
            text="更改快捷键",
            width=100,
            command=lambda: switch_to_edit_mode(activate_listeners=True),
            **GUIStyles.get_secondary_button_args(),
        )


        # --- Helper Functions ---
        def _clear_widgets() -> None:
            """清除 right_frame 中的所有子控件"""
            for widget in right_frame.winfo_children():
                widget.grid_remove()

        def _update_ui_text(keys: set[str]) -> None:
            """更新输入框显示的快捷键文本"""
            if not entry.winfo_exists():
                return

            display_text = ""
            if keys:
                try:
                    # 尝试使用 ShortcutKey 格式化
                    sk = ShortcutKey(*keys)
                    display_text = str(sk).replace("<", "").replace(">", "")
                except ValueError:
                    # 如果无效（如单个非修饰键），显示原始组合用于反馈
                    display_text = "+".join(sorted(keys))
                except Exception:
                    display_text = "+".join(sorted(keys))

            entry.delete(0, "end")
            entry.insert(0, display_text)

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
            # 如果热键还没设置也无需操作
            if not new_hotkey:
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
                fg_color=GUIStyles.COLOR_BUBBLE_FRAME_BG,
                border_color=GUIStyles.COLOR_BUBBLE_BORDER,
                border_width=1,
                corner_radius=8
            )
            display_frame.grid(row=0, column=0, sticky="ew")

            keys = hotkey_str.replace("<", "").replace(">", "").split("+")

            # --- 删除按钮 ---
            # 优先 pack 到右侧，以确保它始终在最右边
            delete_normal_text_color = GUIStyles.COLOR_TEXT_SECONDARY
            delete_hover_text_color = GUIStyles.COLOR_TEXT_PRIMARY
            
            # 气泡背景色
            key_bubble_bg_color = GUIStyles.COLOR_BUBBLE_BG

            delete_button = ctk.CTkLabel(
                display_frame,
                text="✕",
                # cursor="hand2",
                font=ctk.CTkFont(family=GUIStyles.FONT_FAMILY, size=16),
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
                    border_color=GUIStyles.COLOR_BUBBLE_BORDER
                )
                # pack 到左侧，第一个气泡左侧有边距，其他气泡之间有边距
                key_bubble.pack(side="left", padx=(4 if i == 0 else 0, 4), pady=4)

                # 气泡内的 Label
                label = ctk.CTkLabel(
                    key_bubble,
                    text=key.upper(),
                    fg_color="transparent",
                    text_color=GUIStyles.COLOR_BUBBLE_TEXT,
                    font=GUIStyles.get_note_font(),
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
            entry.grid(row=0, column=0, sticky="ew")
            entry.delete(0, "end")
            entry.insert(0, "请按下快捷键...")
            entry.focus_set()

            # 绑定失去焦点事件（取消录制）
            entry.bind("<FocusOut>", _on_focus_out)

            if activate_listeners:
                _start_recording()


        def switch_to_initial_mode() -> None:
            _clear_widgets()
            record_button.grid(row=0, column=0, sticky="ew", ipady=4)
            # 鼠标悬停时改变按钮样式 - 已由 GUIStyles 统一管理，无需手动绑定


        def _stop_recording() -> None:
            """停止录制并清理资源"""
            nonlocal recorder
            if recorder:
                try:
                    recorder.stop()
                except Exception:
                    pass
                recorder = None

            # 解绑事件
            if entry.winfo_exists():
                entry.unbind("<FocusOut>")

        def _on_recording_event(event: KeyEvent) -> None:
            """处理录制过程中的键盘事件"""
            nonlocal current_recording_keys

            # 在主线程更新UI（UniversalKeyListener 在独立线程回调）
            def _ui_update_task():
                if event.event_type == 'press':
                    current_recording_keys.update(event.keys_pressed)
                    _update_ui_text(current_recording_keys)

                elif event.event_type == 'release':
                    # 当所有键释放时，尝试保存
                    # 逻辑：如果当前没有按下的键，且之前记录过按键，则认为输入完成
                    if not event.keys_pressed and current_recording_keys:
                        try:
                            # 使用 ShortcutKey 进行校验和格式化
                            sk = ShortcutKey(*current_recording_keys)
                            hotkey_str = str(sk).replace("<", "").replace(">", "")

                            _stop_recording()
                            _save(hotkey_str)
                        except ValueError as e:
                            # 校验失败（如包含非法键），显示错误并重置
                            self.update_status_error(f"无效快捷键: {e}")
                            current_recording_keys.clear()
                            _update_ui_text(set())
                        except Exception as e:
                            self.update_status_error(f"录制出错: {e}")
                            current_recording_keys.clear()
                            _update_ui_text(set())
                    elif event.keys_pressed:
                        # 部分键释放（如组合键中松开了一个），更新显示
                        _update_ui_text(event.keys_pressed)

            # 调度到主线程执行
            entry.after(0, _ui_update_task)

        def _start_recording() -> None:
            """启动键盘监听"""
            nonlocal recorder, current_recording_keys
            _stop_recording()

            current_recording_keys.clear()
            try:
                recorder = UniversalKeyListener()
                recorder.on_press(_on_recording_event)
                recorder.on_release(_on_recording_event)
                recorder.start()
            except Exception as e:
                self.update_status_error(f"无法启动键盘监听: {e}")

        def _on_focus_out(event) -> None:
            """失去焦点时取消录制，恢复原状"""
            _stop_recording()
            initial_hotkey = self.config_manager.get(config_key, "") or ""
            _update_ui(initial_hotkey)

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

        for name, components in (self._nav_buttons or {}).items():
            try:
                btn = components["button"]
                indicator = components["indicator"]
                
                if name == page_name:
                    # Active State
                    btn.configure(
                        fg_color=GUIStyles.COLOR_NAV_BG_ACTIVE,
                        text_color=GUIStyles.COLOR_NAV_TEXT_ACTIVE,
                        hover_color=GUIStyles.COLOR_NAV_BG_ACTIVE # Keep active color on hover
                    )
                    indicator.configure(fg_color=GUIStyles.COLOR_NAV_INDICATOR_ACTIVE)
                else:
                    # Inactive State
                    btn.configure(
                        fg_color=GUIStyles.COLOR_NAV_BG_DEFAULT,
                        text_color=GUIStyles.COLOR_DESTRUCTIVE if name == "exit" else GUIStyles.COLOR_NAV_TEXT_DEFAULT,
                        hover_color=GUIStyles.COLOR_NAV_BG_HOVER
                    )
                    indicator.configure(fg_color="transparent")
            except Exception:
                pass

    def show_page(self, page_name: str) -> None:
        if page_name not in self.pages:
            return

        page = self.pages[page_name]

        try:
            page.grid(row=0, column=0, sticky="nsew")
        except Exception:
            try:
                page.grid()
            except Exception:
                pass

        try:
            self._raise_page_frame(page)
        except Exception:
            pass

        self.current_page = page_name
        self._set_active_nav_button(page_name)

    def _raise_page_frame(self, page: ctk.CTkFrame) -> None:
        """
        CTkScrollableFrame 的真实 grid 容器是内部 _parent_frame。
        只 raise 页面对象本身会让 tab 层级在多次切换后错乱。
        """
        raised = False
        for attr in ("_parent_frame", "_parent_canvas"):
            try:
                widget = getattr(page, attr, None)
                if widget is not None:
                    widget.lift()
                    raised = True
            except Exception:
                pass
        try:
            page.lift()
            raised = True
        except Exception:
            pass
        if not raised:
            page.tkraise()

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
        self._perform_exit()

    def _perform_exit(self) -> None:
        """执行实际退出逻辑"""
        # 设置关闭状态位
        self._closing = True
        if hasattr(self.app, "exit_application"):
            self.app.exit_application()
            return

        if not self.root:
            return

        def _quit() -> None:
            try:
                if self.statusbar:
                    self.statusbar.remove()
                self.root.quit()
                self.root.destroy()
            finally:
                # 【强制退出】这是解决弹出 3 次最有效的方案
                os._exit(0)

        try:
            self.root.after(10, _quit)
        except Exception:
            _quit()

    def _initial_paint(self) -> None:
        t0 = time.perf_counter()
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

        print(f"[perf] gui:initial_paint: {(time.perf_counter() - t0) * 1000:.1f}ms")

        # 在初始绘制完成后再触发重型初始化
        try:
            self.root.after_idle(self._post_gui_init)
        except Exception:
            try:
                self.root.after(0, self._post_gui_init)
            except Exception:
                pass

    ##### 录音浮层 功能模块---start #####

    def show_recording_overlay(self, text: str = "录音中…") -> None:
        """
        /**
         * 显示录音提示浮层（纯 Cocoa）。
         *
         * 说明：
         * - macOS 下使用 NSPanel 非激活面板：不会抢占当前前台应用的输入光标。
         * - 已移除 Tk/CTk 的 Toplevel 录音浮层实现。
         *
         * @param {string} text - 预留参数：后续可用于显示文案。
         * @returns {void}
         */
        """

        try:
            self._init_cocoa_recording_overlay()
        except Exception:
            pass

        if self._cocoa_recording_overlay is None:
            print("⚠️ 录音浮层不可用：Cocoa overlay 未初始化")
            return

        try:
            self._cocoa_recording_overlay.show()
        except Exception as e:
            print(f"⚠️ 显示 Cocoa 录音浮层失败（可忽略）: {e}")
            return

        # 启动一次轮询即可（update_recording_volume 内部会自我调度）
        try:
            self._recording_overlay_volume_last_seq = -1
            self.update_recording_volume(0)
        except Exception as e:
            print(f"⚠️ 启动录音浮层音量轮询失败（可忽略）: {e}")

    def hide_recording_overlay(self):
        """
        /**
         * 隐藏录音提示浮层（纯 Cocoa）。
         *
         * @returns {void}
         */
        """

        # 停止音量轮询，避免后台持续 after 造成卡顿
        try:
            job = self._recording_overlay_volume_job
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
            self._recording_overlay_volume_job = None
            self._recording_overlay_volume_last_seq = -1
        except Exception as e:
            print(f"⚠️ 停止录音浮层音量轮询失败（可忽略）: {e}")

        # 停止转写进度轮询
        try:
            job = getattr(self, "_recording_overlay_progress_job", None)
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
            self._recording_overlay_progress_job = None
            self._recording_overlay_progress_value = 0.0
            self._recording_overlay_progress_last_ts = 0.0
            # 更新 Cocoa 转写进度，确保浮层可见时进度条可见
            self._cocoa_recording_overlay.set_progress(float(self._recording_overlay_progress_value))
        except Exception as e:
            print(f"⚠️ 停止转写进度轮询失败（可忽略）: {e}")

        try:
            self._init_cocoa_recording_overlay()
        except Exception:
            pass

        if self._cocoa_recording_overlay is None:
            return

        try:
            self._cocoa_recording_overlay.hide()
        except Exception as e:
            print(f"⚠️ 隐藏 Cocoa 录音浮层失败（可忽略）: {e}")

    def update_transcribe_progress(self, byte_len: int = 0):
        """
        /**
         * 录音浮窗：以固定速度轮询方式持续刷新（纯 Cocoa）。
         *
         * 方案说明：
         * - 以固定速度调用 _cocoa_recording_overlay 的 `set_progress` 重绘进度条浮窗。
         * - 进度在 0~1 之间循环（无限动画），直到浮层不可见时自动停止轮询。
         *
         * @param {number} byte_len - 兼容参数：外部传入时可忽略。
         * @returns {void}
         */
        """

        # 若 Cocoa overlay 不可用或不可见：停止轮询
        try:
            if self._cocoa_recording_overlay is None or not self._cocoa_recording_overlay.is_visible():
                self._recording_overlay_progress_job = None
                self._recording_overlay_progress_value = 0.0
                self._recording_overlay_progress_last_ts = 0.0
                return
        except Exception:
            self._recording_overlay_progress_job = None
            self._recording_overlay_progress_value = 0.0
            self._recording_overlay_progress_last_ts = 0.0
            return

        # 转写开始后不再需要音量轮询（避免两个 after 同时跑）
        try:
            job = getattr(self, "_recording_overlay_volume_job", None)
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
            self._recording_overlay_volume_job = None
            self._recording_overlay_volume_last_seq = -1
        except Exception:
            pass

        if self._recording_overlay_progress_last_ts <= 0.0:
            self._recording_overlay_progress_last_ts = time.perf_counter()

        # 先刷新一次
        try:
            self._cocoa_recording_overlay.set_progress(float(self._recording_overlay_progress_value))
        except Exception as e:
            print(f"⚠️ 更新 Cocoa 转写进度失败（可忽略）: {e}")

        # 确保同一时间只有一个 after job
        if self._recording_overlay_progress_job:
            return

        cycle_s = 3  # 进度条从 0->1 走完一圈所需秒数（固定速度）

        def _tick() -> None:
            self._recording_overlay_progress_job = None

            try:
                if self._cocoa_recording_overlay is None or not self._cocoa_recording_overlay.is_visible():
                    self._recording_overlay_progress_value = 0.0
                    self._recording_overlay_progress_last_ts = 0.0
                    return
            except Exception:
                self._recording_overlay_progress_value = 0.0
                self._recording_overlay_progress_last_ts = 0.0
                return

            now = time.perf_counter()
            last_ts = float(self._recording_overlay_progress_last_ts or now)
            dt = max(0.0, now - last_ts)
            self._recording_overlay_progress_last_ts = now

            p = float(self._recording_overlay_progress_value or 0.0)
            p = (p + dt / cycle_s) % 1.0
            self._recording_overlay_progress_value = p

            try:
                self._cocoa_recording_overlay.set_progress(p)
            except Exception as e:
                print(f"⚠️ 更新 Cocoa 转写进度失败（可忽略）: {e}")

            try:
                self._recording_overlay_progress_job = self.root.after(100, _tick)
            except Exception as e:
                print(f"⚠️ 调度转写进度轮询失败（可忽略）: {e}")
                self._recording_overlay_progress_job = None

        try:
            self._recording_overlay_progress_job = self.root.after(100, _tick)
        except Exception as e:
            print(f"⚠️ 调度转写进度轮询失败（可忽略）: {e}")
            self._recording_overlay_progress_job = None

    def update_recording_volume(self, volume_level: int = 0):
        """
        /**
         * 录音浮窗：根据“全局音量数组”更新音波高度，并以 after 轮询方式持续刷新（纯 Cocoa）。
         *
         * 方案说明：
         * - AudioRecorder._record 周期性写入 `GLOBAL_VOLUME_LEVELS` 与 `GLOBAL_VOLUME_SEQ`。
         * - 这里在 GUI 主线程轮询读取最新音量值，并调用 Cocoa overlay 的 `set_volume` 重绘。
         * - 当浮层不可见时，自动停止轮询。
         *
         * @param {number} volume_level - 兼容参数：外部传入时可忽略；默认从全局数组读取。
         * @returns {void}
         */
        """

        # 若 Cocoa overlay 不可用或不可见：停止轮询
        try:
            if self._cocoa_recording_overlay is None or not self._cocoa_recording_overlay.is_visible():
                self._recording_overlay_volume_job = None
                self._recording_overlay_volume_last_seq = -1
                return
        except Exception:
            self._recording_overlay_volume_job = None
            self._recording_overlay_volume_last_seq = -1
            return

        latest_level = int(volume_level) if volume_level is not None else 0
        seq = None

        try:
            from . import audio_recorder as audio_recorder_module

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

        last_seq = self._recording_overlay_volume_last_seq
        if seq is None or seq != last_seq:
            lv = max(0, min(100, latest_level))
            try:
                self._cocoa_recording_overlay.set_volume(lv)
            except Exception as e:
                print(f"⚠️ 更新 Cocoa 音波失败（可忽略）: {e}")

            if seq is not None:
                self._recording_overlay_volume_last_seq = seq

        # 轮询：确保同一时间只有一个 after job
        if self._recording_overlay_volume_job:
            return

        def _tick() -> None:
            self._recording_overlay_volume_job = None
            self.update_recording_volume(0)

        try:
            self._recording_overlay_volume_job = self.root.after(50, _tick)
        except Exception as e:
            print(f"⚠️ 调度音量轮询失败（可忽略）: {e}")
            self._recording_overlay_volume_job = None

    def _init_cocoa_recording_overlay(self) -> None:
        """
        /**
         * 初始化 macOS Cocoa 录音浮层（NSPanel 非激活面板）。
         *
         * 目标：
         * - 纯 Cocoa 实现，不依赖 Tk/CTk 的 Toplevel。
         * - 显示/更新时不抢占输入光标。
         * - 支持 Spaces/全屏（collectionBehavior）。
         *
         * @returns {void}
         */
        """
        # 已初始化则跳过
        if self._cocoa_recording_overlay is not None:
            return

        try:
            from .macos_recording_overlay import CocoaRecordingOverlay

            # 录音浮层尺寸：这里决定“黑色圆角胶囊”整体大小（NSPanel + 内容视图同尺寸）
            overlay = CocoaRecordingOverlay(width=140, height=44, bottom_margin=40)
            if not overlay.is_available():
                print("⚠️ Cocoa 录音浮层不可用（将禁用录音浮层）")
                self._cocoa_recording_overlay = None
                return

            self._cocoa_recording_overlay = overlay
            print("✅ 已启用 Cocoa 录音浮层（纯 Cocoa，不抢占输入光标）")
        except Exception as e:
            self._cocoa_recording_overlay = None
            print(f"⚠️ Cocoa 录音浮层初始化失败（将禁用录音浮层）: {e}")

    ##### 录音浮层 功能模块---end #####

    ##### 下载进度条 功能模块---start #####

    def _show_progress_window(self, data):
        """显示全屏进度条覆盖层"""
        self._progress_overlay_requested = True
        if self._progress_overlay_close_job is not None:
            try:
                self.root.after_cancel(self._progress_overlay_close_job)
            except Exception:
                pass
            self._progress_overlay_close_job = None

        def _do_show():
            try:
                if not self._progress_overlay_requested:
                    return

                # 延迟导入新的 Frame 组件
                from ..core.progress_bar import ProgressBarFrame

                title = data.get('title', '正在准备模型...')
                label = data.get('label', '首次运行需要下载模型，请稍候...')

                # 如果已存在，复用覆盖层，避免连续下载多个模型时销毁/重建造成闪烁
                if hasattr(self, 'progress_overlay') and self.progress_overlay:
                    try:
                        self.progress_overlay.configure_text(title=title, label_text=label)
                        self.progress_overlay.reset_progress()
                    except Exception:
                        pass
                    self.progress_overlay.lift()
                    return

                # 创建全屏覆盖层，直接挂载到 self.root 上
                # 这样它会遮挡所有其他内容（Sidebar + Content）
                self.progress_overlay = ProgressBarFrame(self.root, title=title, label_text=label)
                self.progress_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

                # 强制刷新一次，确保用户立刻看到
                self.root.update()
                print(f"✅ 进度覆盖层已显示: {title}")

            except Exception as e:
                print(f"❌ 显示进度条失败: {e}")

        # 确保在主线程空闲时执行
        self.root.after_idle(_do_show)

    def _update_progress_window(self, data):
        """更新进度条数值"""
        if not hasattr(self, 'progress_overlay') or not self.progress_overlay:
            return

        try:
            progress = data.get('progress', 0)
            desc = data.get('desc', '')
            # 调用组件内部方法
            numeric_progress = float(progress)
            if numeric_progress < 0:
                self.progress_overlay.update_progress(-1, desc)
            else:
                self.progress_overlay.update_progress(numeric_progress / 100.0, desc)
            # 强制刷新界面（重要！否则下载密集时界面会卡死）
            self.root.update_idletasks()
        except Exception as e:
            print(f"❌ 更新进度条失败: {e}")

    def _close_progress_window(self):
        """销毁进度条覆盖层"""
        self._progress_overlay_requested = False

        def _do_close():
            self._progress_overlay_close_job = None
            if self._progress_overlay_requested:
                return
            if not (hasattr(self, 'progress_overlay') and self.progress_overlay):
                return
            try:
                self.progress_overlay.destroy()
            except Exception:
                pass
            self.progress_overlay = None
            print("✅ 进度覆盖层已关闭")

        if self._progress_overlay_close_job is not None:
            try:
                self.root.after_cancel(self._progress_overlay_close_job)
            except Exception:
                pass
        self._progress_overlay_close_job = self.root.after(900, _do_close)

    ##### 下载进度条 功能模块---end #####

    ##### 状态栏相关功能模块---start #####
    def _poll_queue(self):
        """
        轮询全局队列 - 这是唯一处理状态栏事件的地方
        在 Tkinter 主线程中执行，绝对安全
        """
        if self._closing:
            return

        try:
            while True:
                ## 处理状态栏消息 start
                item = _status_queue.get_nowait()
                action = item.get('action')
                window_id = item.get('window_id')
                data = item.get('data')

                # 验证是否是自己的消息
                # if window_id != self._window_id:
                #     continue

                print(f"📥 处理动作: {action}，数据: {data}")

                if action == 'show':
                    self._do_show()
                elif action == 'hide':
                    self._do_hide()
                elif action == 'quit':
                    self.exit_application()
                    # return  # 退出后不再继续轮询 (已移除，以便在取消退出时继续轮询)
                ## 处理进度条消息 start
                elif action == 'progress_start':
                    self._show_progress_window(data)
                elif action == 'progress_update':
                    self._update_progress_window(data)
                elif action == 'progress_end':
                    self._close_progress_window()
                ## 处理进度条消息 end

        except queue.Empty:
            pass
        except Exception as e:
            print(f"❌ 处理队列错误: {e}")

        # 继续轮询
        self.root.after(50, self._poll_queue)  # 50ms 轮询一次

    def _setup_statusbar(self):
        """初始化状态栏"""
        self.statusbar = MacStatusBar.alloc().init()
        self.statusbar.setupWithWindowId_(self._window_id)

    def _do_show(self):
        """实际显示窗口"""
        self.root.deiconify()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def _do_hide(self):
        """实际隐藏窗口"""
        self.root.withdraw()

    ##### 状态栏相关功能模块---end #####
