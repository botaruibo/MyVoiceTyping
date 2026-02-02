"""
Windows 平台专用实现
"""
import sys
from typing import Tuple

# ---------- 条件导入：仅 Windows 下真正加载 ----------
if sys.platform == "win32":
    import win32gui
    import win32api
    import win32con
    import pygetwindow as gw
    import pyautogui
else:
    # 非 Windows 平台：用占位符，避免编译期报错；真正调用会提示
    _msg = "这些模块仅在 Windows 可用，请安装 pywin32 / pygetwindow / pyautogui 并切换到 Windows 运行"
    win32gui = win32api = win32con = gw = pyautogui = None

# ------------------------------------------------------


class WindowsImpl:
    def get_cursor_position(self) -> Tuple[int, int]:
        # 如果不在 Windows，真正调用时再抛错，方便调试
        if pyautogui is None:
            raise RuntimeError(_msg)
        return pyautogui.position()

    def get_input_cursor_position(self) -> Tuple[int, int]:
        """
        取当前具有输入焦点的控件的屏幕坐标。
        原理：GetGUIThreadInfo 返回 rcCaret，映射到屏幕坐标。
        """
        if sys.platform != "win32":
            raise RuntimeError("get_input_cursor_position 仅限 Windows 平台使用")

        import ctypes
        from ctypes.wintypes import RECT, POINT
        user32 = ctypes.windll.user32

        GUITHREADINFO = ctypes.c_uint * 8
        info = GUITHREADINFO()
        info[0] = ctypes.sizeof(info)

        tid = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        if user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
            # rcCaret 是客户区坐标，需要 ClientToScreen
            hwnd = info[1]  # hwndCaret
            rect = RECT()
            rect.left   = info[6]  # rcCaret left
            rect.top    = info[7]  # rcCaret top
            user32.ClientToScreen(hwnd, ctypes.byref(rect))
        if gw is None:
            raise RuntimeError(_msg)
            # return (rect.left, rect.top)
        # 失败则退化为鼠标位置
        return self.get_cursor_position()

    # def get_window_at_cursor(self, x: int, y: int):
    #     """与主类中原 _get_window_info_windows 逻辑相同，略。"""
    #     windows = gw.getAllWindows()
    #     for w in windows:
    #         if (w.left <= x <= w.right and w.top <= y <= w.bottom and w.isActive):
    #             return {
    #                 "title":    w.title,
    #                 "app_name": w.title.split('-')[-1].strip() if '-' in w.title else w.title,
    #                 "window_id": str(w._hWnd),
    #                 "position": (w.left, w.top),
    #                 "size":     (w.width, w.height)
    #             }
    #     return None
