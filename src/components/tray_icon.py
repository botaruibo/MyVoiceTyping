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
        """创建系统托盘图标图像

        @returns Image.Image 托盘图标图像（优先 assets/icon.png）
        """
        # 1) 优先加载 assets/icon.png（开发态 + 打包态兼容）
        try:
            import sys
            from pathlib import Path

            candidates = []

            # PyInstaller 打包态：资源通常在 sys._MEIPASS 下
            if hasattr(sys, "_MEIPASS"):
                candidates.append(Path(sys._MEIPASS))

            # 开发态：tray_icon.py -> components -> src -> project_root
            try:
                candidates.append(Path(__file__).resolve().parents[3])
            except Exception:
                pass

            # 兜底：当前工作目录
            candidates.append(Path.cwd().resolve())

            for root in candidates:
                icon_path = root / "assets" / "icon.png"
                try:
                    if icon_path.exists() and icon_path.is_file():
                        img = Image.open(icon_path).convert("RGBA")

                        # 菜单栏图标一般较小，做一次缩放（系统也会再缩放）
                        try:
                            resampling = Image.Resampling.LANCZOS  # Pillow >= 9
                        except Exception:
                            resampling = Image.LANCZOS

                        img = img.resize((24, 24), resampling)
                        print(f"✅ 托盘图标加载成功：{icon_path}")
                        return img
                except Exception as e:
                    print(f"⚠️ 托盘图标读取失败：{icon_path}，原因：{e}")

            print("⚠️ 未找到 assets/icon.png，使用默认绘制图标")
        except Exception as e:
            print(f"⚠️ 加载 assets/icon.png 过程异常，使用默认绘制图标：{e}")

        # 2) 兜底：继续使用原先绘制的简单图标
        image = Image.new('RGB', (64, 64), (66, 133, 244))  # 蓝色背景
        draw = ImageDraw.Draw(image)

        draw.rectangle([20, 10, 44, 40], fill=(255, 255, 255))  # 麦克风主体
        draw.ellipse([28, 5, 36, 15], fill=(255, 255, 255))  # 麦克风顶部
        draw.rectangle([29, 40, 35, 55], fill=(200, 200, 200))  # 支架

        return image

    def _on_open_home(self, icon, item):
        """
        打开主页（托盘菜单回调）
        @param icon: 托盘图标实例（pystray.Icon）
        @param item: 菜单项实例（pystray.MenuItem）
        @returns None
        """
        print("📌 托盘菜单：打开主页")
        open_home = getattr(self.app, "open_home_page", None)
        if callable(open_home):
            try:
                open_home()
                return
            except Exception as e:
                print(f"❌ 托盘打开主页失败：{e}")

        # 兜底：至少恢复窗口
        try:
            self.app.restore_from_tray()
        except Exception as e:
            print(f"❌ 托盘恢复窗口失败：{e}")

    def _on_quit(self, icon, item):
        """
        退出程序（托盘菜单回调）
        @param icon: 托盘图标实例（pystray.Icon）
        @param item: 菜单项实例（pystray.MenuItem）
        @returns None
        """
        print("🛑 托盘菜单：退出")
        try:
            # 只调用 app 的退出逻辑，让它统一处理托盘和 GUI
            self.app.exit_application()
        except Exception as e:
            print(f"❌ 托盘退出失败：{e}")

    def _on_show(self, icon, item):
        """
        显示主窗口（托盘菜单回调）
        @param icon: 托盘图标实例（pystray.Icon）
        @param item: 菜单项实例（pystray.MenuItem）
        @returns None
        """
        print("🪟 托盘菜单：显示窗口")
        try:
            self.app.restore_from_tray()
        except Exception as e:
            print(f"❌ 托盘显示窗口失败：{e}")

    def create_tray_icon(self):
        """
        创建系统托盘图标
        说明：菜单栏下拉按钮只保留“打开主页 / 退出”。
        @returns None
        """
        image = self._create_image()

        menu = (
            pystray.MenuItem("打开主页", self._on_open_home),
            pystray.MenuItem("退出", self._on_quit),
        )

        self.icon = pystray.Icon("MyVoiceInput", image, "无界输入法", menu)

    def start(self):
        """启动系统托盘图标

        说明：macOS 上 pystray 的 Cocoa 后端对线程比较敏感。
        优先使用 run_detached（如果可用）来与现有 GUI 主循环共存。
        """
        if self.icon is None:
            try:
                self.create_tray_icon()
            except Exception as e:
                print(f"❌ 创建托盘图标失败：{e}")
                return

        run_detached = getattr(self.icon, "run_detached", None)
        if callable(run_detached):
            try:
                print("✅ 托盘图标启动：run_detached")
                run_detached()
                return
            except Exception as e:
                print(f"⚠️ 托盘 run_detached 启动失败：{e}")

        import sys
        if sys.platform == "darwin":
            print("❌ 当前环境无法启动托盘：macOS 需要在主线程运行 Cocoa 事件循环（建议检查 PyObjC/pystray 打包依赖）")
            return

        try:
            print("✅ 托盘图标启动（thread + run）")
            self.thread = threading.Thread(target=self.icon.run, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"❌ 托盘线程启动失败：{e}")

    def stop(self):
        """停止系统托盘图标"""
        if self.icon:
            try:
                print("🧹 停止托盘图标")
                self.icon.stop()
            except Exception as e:
                print(f"⚠️ 停止托盘图标失败：{e}")