"""
系统托盘图标组件
"""
import threading
from PIL import Image, ImageDraw
import pystray
import io


class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.thread = None

    def _create_image(self):
        """创建系统托盘图标图像"""
        # 创建一个简单的图标图像
        image = Image.new('RGB', (64, 64), (66, 133, 244))  # 蓝色背景
        draw = ImageDraw.Draw(image)
        
        # 绘制一个简单的麦克风图标
        draw.rectangle([20, 10, 44, 40], fill=(255, 255, 255))  # 麦克风主体
        draw.ellipse([28, 5, 36, 15], fill=(255, 255, 255))     # 麦克风顶部
        draw.rectangle([29, 40, 35, 55], fill=(200, 200, 200))  # 支架
        
        return image

    def _on_quit(self, icon, item):
        """退出程序"""
        # 只调用 app 的退出逻辑，让它统一处理托盘和 GUI
        self.app.exit_application()

    def _on_show(self, icon, item):
        """显示主窗口"""
        self.app.restore_from_tray()

    def create_tray_icon(self):
        """创建系统托盘图标"""
        image = self._create_image()
        
        # 创建菜单
        menu = (
            pystray.MenuItem("显示窗口", self._on_show),
            pystray.MenuItem("退出", self._on_quit)
        )
        
        # 创建系统托盘图标
        self.icon = pystray.Icon("MyVoiceInput", image, "无界输入法", menu)

    def start(self):
        """启动系统托盘图标

        说明：macOS 上 pystray 的 Cocoa 后端对线程比较敏感。
        优先使用 run_detached（如果可用）来与现有 GUI 主循环共存。
        """
        if self.icon is None:
            self.create_tray_icon()

        run_detached = getattr(self.icon, "run_detached", None)
        if callable(run_detached):
            try:
                run_detached()
                return
            except Exception:
                pass

        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止系统托盘图标"""
        if self.icon:
            self.icon.stop()