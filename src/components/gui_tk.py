import os
import tkinter as tk
# from tkinter import messagebox
from typing import Any, Dict, Optional
import sys, time
from pathlib import Path

import customtkinter as ctk
import platform

import queue

if platform.system() == "Darwin":
    from AppKit import NSStatusBar, NSMenu, NSMenuItem, NSObject
    import objc

from .config_manager import get_config_manager
from ..util.app_logger import AppLogger

class GUIStyles:
    # Colors
    COLOR_CARD_BG = ("#FFFFFF", "#2B2B2B")
    COLOR_BG = ("#FBFBFB", "#1E1E1E")
    COLOR_BORDER = ("#E5E5E5", "#333333")
    COLOR_TEXT_PRIMARY = ("#000000", "#FFFFFF")
    COLOR_TEXT_SECONDARY = ("#888888", "#AAAAAA")
    COLOR_BUTTON_FG = ("#FFFFFF", "#3A3A3A")
    COLOR_BUTTON_HOVER = ("#F0F0F0", "#404040")

    @staticmethod
    def get_card_frame_args():
        return {
            "fg_color": GUIStyles.COLOR_CARD_BG,
            "corner_radius": 10,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_BORDER
        }

    @staticmethod
    def get_title_font():
        return ctk.CTkFont(family="Arial", size=16, weight="bold")

    @staticmethod
    def get_label_font():
        return ctk.CTkFont(family="Arial", size=14)

    @staticmethod
    def get_note_font():
        return ctk.CTkFont(family="Arial", size=12)

    @staticmethod
    def get_button_args():
        return {
            "fg_color": GUIStyles.COLOR_BUTTON_FG,
            "text_color": GUIStyles.COLOR_TEXT_PRIMARY,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_BORDER,
            "hover_color": GUIStyles.COLOR_BUTTON_HOVER,
            "corner_radius": 6,
            "height": 32,
            "font": GUIStyles.get_label_font()
        }

    @staticmethod
    def get_switch_args():
        return {
            "progress_color": ("#000000", "#FFFFFF"),
        }

    @staticmethod
    def get_entry_args():
        return {
            "corner_radius": 6,
            "border_width": 1,
            "border_color": GUIStyles.COLOR_BORDER,
            "fg_color": GUIStyles.COLOR_BG,
            "text_color": GUIStyles.COLOR_TEXT_PRIMARY,
            "height": 36,
            "font": GUIStyles.get_label_font()
        }

    # Navigation Styles
    COLOR_NAV_BG_DEFAULT = "transparent"
    COLOR_NAV_BG_HOVER = ("#F0F0F0", "#2A2A2A")
    COLOR_NAV_BG_ACTIVE = ("#E8E8E8", "#333333") 
    COLOR_NAV_TEXT_DEFAULT = ("#5A5A5A", "#A0A0A0") 
    COLOR_NAV_TEXT_ACTIVE = ("#000000", "#FFFFFF")
    COLOR_NAV_INDICATOR_ACTIVE = ("#000000", "#FFFFFF")

    @staticmethod
    def get_nav_font():
        # Slightly larger and bolder than default
        return ctk.CTkFont(family="Arial", size=15, weight="bold")

    # Hotkey Bubble Styles
    COLOR_BUBBLE_FRAME_BG = COLOR_BG # Same as input background
    COLOR_BUBBLE_BG = ("#E8E8E8", "#454545") # Very light gray for light mode, lighter dark for dark mode
    COLOR_BUBBLE_BORDER = ("#D0D0D0", "#5A5A5A")
    COLOR_BUBBLE_TEXT = ("#000000", "#FFFFFF")

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
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
            self.status_item.setTitle_("◎")
            self.status_item.setHighlightMode_(True)

            # 创建菜单
            self.menu = NSMenu.alloc().init()

            # 菜单项 - 只绑定到简单的入队方法
            show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"打开闪电输入", "onShow:", ""
            )
            show_item.setTarget_(self)
            self.menu.addItem_(show_item)

            hide_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"隐藏闪电输入", "onHide:", ""
            )
            hide_item.setTarget_(self)
            self.menu.addItem_(hide_item)

            self.menu.addItem_(NSMenuItem.separatorItem())

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "⏻ 退出", "onQuit:", ""
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

        self._nav_buttons: Dict[str, Dict[str, Any]] = {}
        self._nav_icons: Dict[str, ctk.CTkImage] = {}
        # self._nav_font is now provided by GUIStyles.get_nav_font()
        self._sidebar_bg_color = ("#F4F4F4", "#141414")
        self._card_bg_color = ("#F0F0F0", "#242424")
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        except Exception:
            pass

        self.pages: Dict[str, ctk.CTkFrame] = {}
        self.current_page: Optional[str] = "home"

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
        root.title(self.app_name)
        window_width = 1024
        window_height = 800

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
            ("联系作者", "about"),
            ("退出", "exit"),
        ]
        icon_letters = {"home": "H", "settings": "S", "about": "C", "exit": "E"}

        self._nav_buttons = {}
        for text, page_name in nav_buttons:
            # Container Frame for each nav item
            container = ctk.CTkFrame(sidebar, fg_color="transparent")
            container.pack(fill="x", padx=10, pady=2)
            
            # Use Grid layout within the container
            container.grid_columnconfigure(0, weight=0) # Indicator column
            container.grid_columnconfigure(1, weight=1) # Button column

            # Indicator (Left bar)
            indicator = ctk.CTkFrame(
                container, 
                width=4, 
                height=16, 
                corner_radius=2, 
                fg_color="transparent" # Initial state
            )
            indicator.grid(row=0, column=0, sticky="ns", pady=8, padx=(0, 4))

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
                text_color=GUIStyles.COLOR_NAV_TEXT_DEFAULT,
                hover_color=GUIStyles.COLOR_NAV_BG_HOVER,
                # image=icon,
                compound="left",
                height=40,
                corner_radius=8,
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
        content_area = ctk.CTkFrame(self.root, corner_radius=0, fg_color=("#FBFBFB", "#1E1E1E"))
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

    def _create_about_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """
        创建关于/联系我们页面。
        包含二维码图片和说明文字。
        """
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        
        # 居中容器
        container = ctk.CTkFrame(page, fg_color="transparent")
        container.grid(row=0, column=0, pady=40, sticky="n")
        
        # 标题
        ctk.CTkLabel(
            container, 
            text="联系我们", 
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 20))
        
        # 白色卡片背景 (模拟截图中的卡片效果)
        card = ctk.CTkFrame(
            container, 
            fg_color=("white", "#333333"), 
            corner_radius=12,
            border_width=1,
            border_color=("gray90", "gray40")
        )
        card.pack(pady=10, ipadx=30, ipady=30)
        
        # 二维码图片加载
        try:
            # src/components/gui_tk.py -> src/assets/qr_code.png
            assets_dir = Path(__file__).parent.parent / "assets"
            if not assets_dir.exists():
                try:
                    assets_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                
            qr_path = assets_dir / "qr_code.png"
            
            if qr_path.exists() and Image:
                pil_img = Image.open(qr_path)
                # 调整大小，例如 200x200
                qr_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(200, 200))
                ctk.CTkLabel(card, text="", image=qr_image).pack()
            else:
                # 占位符
                placeholder = ctk.CTkFrame(card, width=200, height=200, fg_color=("gray90", "gray20"))
                placeholder.pack()
                placeholder.pack_propagate(False)
                ctk.CTkLabel(
                    placeholder, 
                    text="请放入二维码图片:\nsrc/assets/qr_code.png", 
                    text_color="gray",
                    justify="center"
                ).place(relx=0.5, rely=0.5, anchor="center")
                
        except Exception as e:
            ctk.CTkLabel(card, text=f"图片加载错误: {e}", text_color="red").pack()

        # 底部提示
        ctk.CTkLabel(
            card, 
            text="扫描二维码，直接反馈问题", 
            font=ctk.CTkFont(size=12), 
            text_color="gray"
        ).pack(pady=(15, 0))

        # 额外说明文字 (50字以内)
        desc_text = "欢迎加入用户交流群！扫描上方二维码，直接反馈问题或提出建议，让我们一起打造更好的语音输入体验。"
        ctk.CTkLabel(
            container, 
            text=desc_text, 
            font=ctk.CTkFont(size=14), 
            wraplength=360, 
            justify="center",
            text_color=("gray30", "gray70")
        ).pack(pady=(30, 0))

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

    def _create_section_card(self, parent, title, row):
        """
        创建带有标题和分割线的卡片容器。
        """
        card = ctk.CTkFrame(parent, **GUIStyles.get_card_frame_args())
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(card, text=title, font=GUIStyles.get_title_font(), text_color=GUIStyles.COLOR_TEXT_PRIMARY)
        title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))

        # Divider
        divider = ctk.CTkFrame(card, height=1, fg_color=GUIStyles.COLOR_BORDER)
        divider.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 15))

        # Content Container
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
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
                
            if platform.system() == "Darwin":
                os.system(f"open '{log_dir}'")
            elif platform.system() == "Windows":
                os.startfile(log_dir)
            else:
                os.system(f"xdg-open '{log_dir}'")
        except Exception as e:
            print(f"Failed to open log directory: {e}")

    def _create_settings_page(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        page = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)

        # --- 页面标题 ---
        ctk.CTkLabel(page, text="设置", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 10)
        )

        # --- 键盘快捷键部分 ---
        hotkey_content = self._create_section_card(page, "键盘快捷键", 1)
        self._create_hotkey_setting(
            hotkey_content,
            title="语音输入",
            config_key="press_hotkey",
            description="按住说话。双击进入免提模式。",
            row=0,
        )

        self._create_hotkey_setting(
            hotkey_content,
            title="免提模式",
            config_key="toggle_hotkey",
            description="按一次开始说话,无需按住。再次按下将文本粘贴到任何文本框中。",
            row=1,
        )

        # --- 模型设置部分 ---
        model_content = self._create_section_card(page, "模型设置", 2)
        
        # API Key 设置
        api_key_frame = ctk.CTkFrame(model_content, fg_color="transparent")
        api_key_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        api_key_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(api_key_frame, text="模型密钥", font=ctk.CTkFont(size=16)).grid(
            row=0, column=0, padx=(0, 20), sticky="w"
        )

        api_key_var = tk.StringVar(value=self.config_manager.get("api_key", ""))
        self._auto_save_on_change(api_key_var, "api_key")
        api_key_entry = ctk.CTkEntry(
            api_key_frame, 
            textvariable=api_key_var,
            **GUIStyles.get_entry_args()
        )
        api_key_entry.grid(row=0, column=1, sticky="ew")

        def _save_api_key(event=None):
            self.config_manager.set("api_key", api_key_var.get())

        api_key_entry.bind("<FocusOut>", _save_api_key)

        test_button = ctk.CTkButton(
            api_key_frame, 
            text="测试", 
            width=60, 
            command=self._test_api_key,
            **GUIStyles.get_button_args()
        )
        test_button.grid(row=0, column=2, padx=(10, 0))

        self._create_hotword_setting(model_content, row=1)

        # --- 日志部分 ---
        log_content = self._create_section_card(page, "日志", 3)
        self._create_log_row(log_content, 0)

        # Prevent scrolling jitter at the bottom
        ctk.CTkFrame(page, height=20, fg_color="transparent").grid(row=4, column=0)

        return page

    def _test_api_key(self):
        """
        测试当前文本改写模型是否可用。
        """
        provider = self.config_manager.get("llm_text_provider", "cloud_llm")
        api_key = self.config_manager.get("api_key")
        if provider == "cloud_llm" and not api_key:
            self.update_status_error("模型密钥为空")
            return

        try:
            rewriter = getattr(self.app, "rewriter", None)
            if rewriter is None:
                get_rewriter = getattr(self.app, "_get_rewriter_safe", None)
                rewriter = get_rewriter() if callable(get_rewriter) else None
            if rewriter is None:
                self.update_status_error("文本改写模型未初始化")
                return

            test_llm = getattr(rewriter, "test_llm", None)
            result = test_llm() if callable(test_llm) else rewriter.test_remote_llm()
            if(result is None):
                self.update_status_success("文本改写模型测试成功")
            else:
                self.update_status_error(result)
        except Exception as e:
            self.update_status_error(f"文本改写模型测试失败: {e}")

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

        self._create_hotword_setting(page, row=2)

        # （已移除）OpenAI STT API Key
        ctk.CTkLabel(page, text="远程 LLM（用于 AI 纠正等能力）", text_color="gray").grid(
            row=3, column=0, padx=18, pady=(8, 8), sticky="w"
        )
        llm_provider_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        llm_provider_row.grid(row=4, column=0, padx=18, pady=(0, 12), sticky="ew")
        llm_provider_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(llm_provider_row, text="文本优化引擎", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )

        llm_provider_default = self.config_manager.get("llm_text_provider", "cloud_llm") or "cloud_llm"

        def _on_llm_provider_change(v: str) -> None:
            self.config_manager.set("llm_text_provider", v)
            self.update_status_success("已保存配置")

        llm_provider_menu = ctk.CTkOptionMenu(
            llm_provider_row,
            values=["cloud_llm", "ollama"],
            dynamic_resizing=False,
            fg_color=self._card_bg_color,
            button_color=self._card_bg_color,
            button_hover_color=self._nav_hover_color,
            dropdown_fg_color=("#FCFCFC", "#2B2B2B"),
            dropdown_hover_color=self._nav_hover_color,
            text_color=self._nav_text_color,
            dropdown_text_color=self._nav_text_color,
            command=_on_llm_provider_change,
        )
        llm_provider_menu.set(llm_provider_default)
        llm_provider_menu.grid(row=0, column=1, padx=12, pady=12, sticky="ew")

        # Remote LLM API Key
        api_key_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        api_key_row.grid(row=5, column=0, padx=18, pady=(0, 12), sticky="ew")
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
        base_url_row.grid(row=6, column=0, padx=18, pady=(0, 12), sticky="ew")
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
        model_name_row.grid(row=7, column=0, padx=18, pady=(0, 12), sticky="ew")
        model_name_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(model_name_row, text="Model Name", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        model_name_var = tk.StringVar(value=self.config_manager.get("model_name", "") or "")
        model_name_entry = ctk.CTkEntry(model_name_row, textvariable=model_name_var)
        model_name_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(model_name_entry, model_name_var, "model_name")

        ctk.CTkLabel(page, text="本地 Ollama", text_color="gray").grid(
            row=8, column=0, padx=18, pady=(8, 8), sticky="w"
        )

        ollama_base_url_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        ollama_base_url_row.grid(row=9, column=0, padx=18, pady=(0, 12), sticky="ew")
        ollama_base_url_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ollama_base_url_row, text="Ollama URL", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        ollama_base_url_var = tk.StringVar(value=self.config_manager.get("ollama_base_url", "") or "")
        ollama_base_url_entry = ctk.CTkEntry(ollama_base_url_row, textvariable=ollama_base_url_var)
        ollama_base_url_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(ollama_base_url_entry, ollama_base_url_var, "ollama_base_url")

        ollama_model_row = ctk.CTkFrame(page, fg_color=self._card_bg_color)
        ollama_model_row.grid(row=10, column=0, padx=18, pady=(0, 18), sticky="ew")
        ollama_model_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ollama_model_row, text="Ollama Model", width=120).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        ollama_model_var = tk.StringVar(value=self.config_manager.get("ollama_model", "") or "")
        ollama_model_entry = ctk.CTkEntry(ollama_model_row, textvariable=ollama_model_var)
        ollama_model_entry.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        _save_var_on_event(ollama_model_entry, ollama_model_var, "ollama_model")

        return page

    def _create_hotword_setting(self, parent: ctk.CTkFrame, row: int) -> None:
        container = ctk.CTkFrame(parent, fg_color=self._card_bg_color)
        container.grid(row=row, column=0, columnspan=2, padx=0, pady=(12, 0), sticky="ew")
        container.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(container, fg_color="transparent")
        left.grid(row=0, column=0, padx=12, pady=12, sticky="nw")
        ctk.CTkLabel(left, text="FunASR 热词", width=120, anchor="w").pack(anchor="w")
        ctk.CTkLabel(left, text="回车添加", text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(4, 0))

        right = ctk.CTkFrame(container, fg_color="transparent")
        right.grid(row=0, column=1, padx=12, pady=12, sticky="ew")
        right.grid_columnconfigure(0, weight=1)

        entry_var = tk.StringVar(value="")
        entry = ctk.CTkEntry(right, textvariable=entry_var, placeholder_text="输入产品名、人名、专有名词后回车")
        entry.grid(row=0, column=0, sticky="ew")

        tags_frame = ctk.CTkFrame(right, fg_color="transparent")
        tags_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        def _load_hotwords() -> list[str]:
            raw = self.config_manager.get("funasr_hotwords", [])
            if isinstance(raw, list):
                words = raw
            elif isinstance(raw, str):
                words = [p for p in raw.replace("，", ",").split(",")]
            else:
                words = []
            result: list[str] = []
            seen: set[str] = set()
            for item in words:
                word = str(item or "").strip()
                if word and word not in seen:
                    seen.add(word)
                    result.append(word)
            return result

        hotwords = _load_hotwords()
        editing_word: list[str | None] = [None]

        def _save_hotwords() -> None:
            self.config_manager.set("funasr_hotwords", hotwords)
            self.update_status_success("热词已保存，下次转写生效")

        def _start_edit(word: str) -> None:
            editing_word[0] = word
            entry_var.set(word)
            entry.focus_set()
            entry.select_range(0, "end")
            self.update_status_success("编辑热词后回车保存")

        def _render_tags() -> None:
            for widget in tags_frame.winfo_children():
                widget.destroy()

            if not hotwords:
                ctk.CTkLabel(tags_frame, text="暂无热词", text_color="gray").pack(anchor="w")
                return

            for word in hotwords:
                tag = ctk.CTkFrame(
                    tags_frame,
                    fg_color=("#EEF4FF", "#263247"),
                    border_color=("#BFD4FF", "#415678"),
                    border_width=1,
                    corner_radius=14,
                )
                tag.pack(side="left", padx=(0, 8), pady=(0, 8))

                label = ctk.CTkLabel(
                    tag,
                    text=word,
                    text_color=("#163B73", "#D8E7FF"),
                    font=ctk.CTkFont(size=13),
                )
                label.pack(side="left", padx=(10, 4), pady=4)
                try:
                    label.configure(cursor="hand2")
                    tag.configure(cursor="hand2")
                except Exception:
                    pass

                delete = ctk.CTkLabel(
                    tag,
                    text="✕",
                    width=20,
                    height=20,
                    corner_radius=10,
                    text_color=("#456A9F", "#AFC7E8"),
                    fg_color="transparent",
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                delete.pack(side="left", padx=(0, 6), pady=4)

                def _remove(_event=None, w=word) -> None:
                    if w in hotwords:
                        hotwords.remove(w)
                        if editing_word[0] == w:
                            editing_word[0] = None
                            entry_var.set("")
                        _save_hotwords()
                        _render_tags()

                tag.bind("<Button-1>", lambda _event, w=word: _start_edit(w))
                label.bind("<Button-1>", lambda _event, w=word: _start_edit(w))
                delete.bind("<Button-1>", _remove)
                delete.bind("<Enter>", lambda _e, d=delete: d.configure(fg_color=("#DCEAFF", "#354966")))
                delete.bind("<Leave>", lambda _e, d=delete: d.configure(fg_color="transparent"))

        def _add_hotword(_event=None) -> None:
            word = (entry_var.get() or "").strip()
            if not word:
                editing_word[0] = None
                return
            old_word = editing_word[0]
            if old_word and old_word in hotwords:
                old_index = hotwords.index(old_word)
                if word == old_word:
                    pass
                elif word in hotwords:
                    hotwords.pop(old_index)
                else:
                    hotwords[old_index] = word
                editing_word[0] = None
                _save_hotwords()
                _render_tags()
            elif word not in hotwords:
                hotwords.append(word)
                _save_hotwords()
                _render_tags()
            else:
                editing_word[0] = None
            entry_var.set("")

        entry.bind("<Return>", _add_hotword)
        _render_tags()

    # -------------------------
    # Widgets helpers
    # -------------------------

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
            delete_normal_text_color = ("gray25", "gray75")
            delete_hover_text_color = ("#000000", "#FFFFFF")
            
            # 气泡背景色
            key_bubble_bg_color = GUIStyles.COLOR_BUBBLE_BG

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
                    border_color=GUIStyles.COLOR_BUBBLE_BORDER
                )
                # pack 到左侧，第一个气泡左侧有边距，其他气泡之间有边距
                key_bubble.pack(side="left", padx=(4 if i == 0 else 0, 4), pady=4)

                # 气泡内的 Label
                label = ctk.CTkLabel(
                    key_bubble,
                    text=key.upper(),
                    fg_color="transparent",
                    text_color=GUIStyles.COLOR_BUBBLE_TEXT
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
                        text_color=GUIStyles.COLOR_NAV_TEXT_DEFAULT,
                        hover_color=GUIStyles.COLOR_NAV_BG_HOVER
                    )
                    indicator.configure(fg_color="transparent")
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
        # 检查是否已有弹窗
        if getattr(self, "_is_exiting_prompt_active", False):
            for widget in self.root.winfo_children():
                if isinstance(widget, ctk.CTkToplevel) and getattr(widget, "_is_exit_dialog", False):
                    try:
                        widget.lift()
                        widget.focus_force()
                    except Exception:
                        pass
                    return
            self._is_exiting_prompt_active = False
        
        self._is_exiting_prompt_active = True
        
        try:
            # --- 自定义退出弹窗 (替代 messagebox) ---
            # 只有自定义弹窗才能实现：1. 无图标 2. 自定义按钮文字("确认退出")
            
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("退出确认")
            setattr(dialog, "_is_exit_dialog", True)
            
            # 窗口大小与位置居中
            w, h = 300, 160
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - w) // 2
            y = (screen_h - h) // 2
            dialog.geometry(f"{w}x{h}+{x}+{y}")
            dialog.resizable(False, False)
            
            # 模态与置顶
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.attributes("-topmost", True)
            
            # 关闭回调
            def on_close():
                self._is_exiting_prompt_active = False
                dialog.destroy()
            dialog.protocol("WM_DELETE_WINDOW", on_close)

            # --- 内容布局 ---
            # 1. 提示文本 (无图标)
            content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            content_frame.pack(expand=True, fill="both", padx=20, pady=20)
            
            ctk.CTkLabel(
                content_frame, 
                text="确定要退出吗？\n退出后将无法使用语音输入功能。", 
                font=ctk.CTkFont(size=14),
                justify="center",
                text_color=("black", "white") # 适配深浅色
            ).pack(pady=(10, 10))

            # 2. 按钮组
            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            def on_confirm():
                self._is_exiting_prompt_active = False
                dialog.destroy()
                self._perform_exit()

            # 取消按钮 (灰色边框)
            ctk.CTkButton(
                btn_frame,
                text="取消",
                fg_color="transparent",
                border_width=1,
                border_color=("gray60", "gray40"),
                text_color=("gray10", "gray90"),
                hover_color=("gray90", "gray30"),
                width=90,
                height=32,
                command=on_close
            ).pack(side="left", padx=(10, 10), expand=True)

            # 确认退出按钮 (红色)
            ctk.CTkButton(
                btn_frame,
                text="确认退出",
                fg_color="#D32F2F",
                hover_color="#B71C1C",
                text_color="white",
                width=90,
                height=32,
                command=on_confirm
            ).pack(side="right", padx=(10, 10), expand=True)

            dialog.focus_force()

        except Exception as e:
            print(f"创建退出弹窗失败: {e}")
            self._is_exiting_prompt_active = False

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
        # 非 macOS：不启用录音浮层
        if sys.platform != "darwin":
            self._cocoa_recording_overlay = None
            return

        # 已初始化则跳过
        if self._cocoa_recording_overlay is not None:
            return

        try:
            from .macos_recording_overlay import CocoaRecordingOverlay

            # 录音浮层尺寸：这里决定“黑色圆角胶囊”整体大小（NSPanel + 内容视图同尺寸）
            # 你希望缩小到当前的 1/3：220x60 -> 73x20
            overlay = CocoaRecordingOverlay(width=68, height=32, bottom_margin=40)
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

        def _do_show():
            try:
                # 延迟导入新的 Frame 组件
                from ..core.progress_bar import ProgressBarFrame

                # 如果已存在，直接返回
                if hasattr(self, 'progress_overlay') and self.progress_overlay:
                    self.progress_overlay.lift()
                    return

                title = data.get('title', '正在准备模型...')
                label = data.get('label', '首次运行需要下载模型，请稍候...')

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
            self.progress_overlay.update_progress(progress / 100.0, desc)
            # 强制刷新界面（重要！否则下载密集时界面会卡死）
            self.root.update_idletasks()
        except Exception as e:
            print(f"❌ 更新进度条失败: {e}")

    def _close_progress_window(self):
        """销毁进度条覆盖层"""
        if hasattr(self, 'progress_overlay') and self.progress_overlay:
            try:
                self.progress_overlay.destroy()
            except Exception:
                pass
            self.progress_overlay = None
            print("✅ 进度覆盖层已关闭")

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
        if platform.system() == "Darwin":
            # 创建并设置
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
