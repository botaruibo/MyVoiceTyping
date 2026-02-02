"""
窗口信息获取器
用于监听鼠标光标位置并获取当前窗口的应用程序标题和名称
"""
import platform
import time
from typing import Dict, Optional, Tuple

class WindowInfo:
    def __init__(self):
        self.system = platform.system().lower()
        self._initialize_platform_specific()

    def _initialize_platform_specific(self):
        """根据平台初始化特定功能"""
        if self.system == "windows":
            try:
                # 优先用独立 windows_impl
                from .windows_impl import WindowsImpl
                self._impl = WindowsImpl()
            except ImportError:
                # 降级到旧依赖
                import pygetwindow as gw
                import pyautogui
                self.pygetwindow = gw
                self.pyautogui  = pyautogui
        elif self.system == "darwin":
            try:
                from .macos_impl_v1 import MacOSImpl
                self._impl = MacOSImpl()
            except ImportError:
                raise
        elif self.system == "linux":
            try:
                import Xlib
                import Xlib.display
                self.Xlib    = Xlib
                self.display = Xlib.display.Display()
            except ImportError:
                raise ImportError("请安装Linux平台依赖: pip install python-xlib")

    # 新增：取输入光标位置（插入点）
    def get_input_cursor_position(self) -> Tuple[int, int]:
        """获取当前输入光标（插入点）位置"""
        if hasattr(self, '_impl'):
            return self._impl.get_input_cursor_position()

    def get_window_info(self) -> Optional[Dict[str, str]]:
        """获取鼠标光标所在窗口的信息"""
        # cursor_x, cursor_y = self.get_cursor_position()
        (cursor_x, cursor_y) = self.get_input_cursor_position()

        if self.system == "windows":
            return self._get_window_info_windows(cursor_x, cursor_y)
        elif self.system == "darwin":
            return self._get_window_info_macos(cursor_x, cursor_y)
        elif self.system == "linux":
            return self._get_window_info_linux(cursor_x, cursor_y)

    def _get_window_info_windows(self, x: int, y: int) -> Optional[Dict[str, str]]:
        """Windows平台获取窗口信息"""
        try:
            windows = self.pygetwindow.getAllWindows()
            for window in windows:
                # 检查光标是否在窗口范围内
                if (window.left <= x <= window.right and
                    window.top <= y <= window.bottom and
                    window.isActive):
                    return {
                        "title": window.title,
                        "app_name": self._extract_app_name_windows(window.title),
                        "window_id": str(window._hWnd),
                        "position": (window.left, window.top),
                        "size": (window.width, window.height)
                    }
            return None
        except Exception as e:
            print(f"获取Windows窗口信息时出错: {e}")
            return None

    def _get_window_info_macos(self, x: int, y: int) -> Optional[Dict[str, str]]:
        """macOS平台获取窗口信息"""
        try:
            from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
            import Quartz

            windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

            for window in windows:
                bounds = window.get('kCGWindowBounds')
                if bounds:
                    win_x = bounds['X']
                    win_y = bounds['Y']
                    width = bounds['Width']
                    height = bounds['Height']

                    # 检查光标是否在窗口范围内
                    if (win_x <= x <= win_x + width and
                        win_y <= y <= win_y + height):
                        title = window.get('kCGWindowName', '未知')
                        app_name = window.get('kCGWindowOwnerName', '未知')

                        return {
                            "title": title,
                            "app_name": app_name,
                            "window_id": str(window.get('kCGWindowNumber', 'unknown')),
                            "position": (win_x, win_y),
                            "size": (width, height)
                        }
            return None
        except Exception as e:
            print(f"获取macOS窗口信息时出错: {e}")
            return None

    def _get_window_info_linux(self, x: int, y: int) -> Optional[Dict[str, str]]:
        """Linux平台获取窗口信息"""
        try:
            root = self.display.screen().root
            window = root.get_full_property(
                self.Xlib.Xatom.WM_NAME,
                self.Xlib.Xatom.STRING
            )

            # 获取当前活动窗口
            active_window = root.get_full_property(
                self.display.intern_atom('_NET_ACTIVE_WINDOW'),
                self.Xlib.Xatom.WINDOW
            )

            if active_window:
                win_id = active_window.value[0] if active_window.value else None
                if win_id:
                    win = self.display.create_resource_object('window', win_id)
                    title = win.get_wm_name() or "未知"
                    app_name = self._extract_app_name_linux(title)

                    # 获取窗口几何信息
                    geom = win.get_geometry()

                    return {
                        "title": title,
                        "app_name": app_name,
                        "window_id": str(win_id),
                        "position": (geom.x, geom.y),
                        "size": (geom.width, geom.height)
                    }
            return None
        except Exception as e:
            print(f"获取Linux窗口信息时出错: {e}")
            return None

    def _extract_app_name_windows(self, title: str) -> str:
        """从窗口标题中提取应用名称 (Windows)"""
        # 简单的启发式方法，实际可能需要更复杂的逻辑
        if "-" in title:
            parts = title.split("-")
            return parts[-1].strip()
        return title

    def _extract_app_name_linux(self, title: str) -> str:
        """从窗口标题中提取应用名称 (Linux)"""
        # 简单的启发式方法
        if "-" in title:
            parts = title.split("-")
            return parts[-1].strip()
        return title

    def get_current_window_info(self) -> Dict[str, str]:
        """获取当前窗口的完整信息"""
        window_info = self.get_window_info()
        if window_info:
            return window_info
        else:
            # 如果无法获取窗口信息，则返回一个默认值
            print("无法获取窗口信息，返回默认值==返回默认")
            return {
                "title": "未知",
                "app_name": "未知",
                "window_id": "unknown",
                "position": (0, 0),
                "size": (0, 0)
            }

# # 便捷函数
# def get_window_info_at_cursor() -> Dict[str, str]:
#     """便捷函数：获取当前光标所在窗口信息"""
#     window_info = WindowInfo()
#     return window_info.get_current_window_info()



