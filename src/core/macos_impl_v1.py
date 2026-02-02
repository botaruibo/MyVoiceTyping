import sys
from typing import Tuple

import Quartz
import ApplicationServices
import subprocess

# 获取输入光标所在窗口名称并写入光标位置的输入，如果出错则写入错误原因
class MacOSImpl:
    def get_cursor_position(self) -> Tuple[int, int]:
        if sys.platform != "darwin":
            return (0, 0)
        # 修正：直接获取位置，Quartz 已经处理了底层转换
        point = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        return int(point.x), int(point.y)

    def get_input_cursor_position(self) -> Tuple[int, int]:
        """获取当前输入光标位置（改进版）"""
        if sys.platform != "darwin":
            return self.get_cursor_position()

        # 1. 获取系统级对象（PyObjC 已封装类型，无需手动 createOpaquePointerType）
        system_wide = ApplicationServices.AXUIElementCreateSystemWide()

        # 2. 获取焦点元素
        # PyObjC 风格：函数直接返回 (Error, Result) 元组
        error, focused = ApplicationServices.AXUIElementCopyAttributeValue(
            system_wide,
            ApplicationServices.kAXFocusedUIElementAttribute,
            None
        )

        if error != 0 or not focused:
            print("没有获取到焦点元素. 尝试使用鼠标位置兜底1")
            return self.get_cursor_position()

        # 3. 获取元素位置（通常插入点坐标在 kAXSelectedTextRangeAttribute 相关的范围内）
        # 但如果是获取元素本身的 Frame：
        error, frame_ref = ApplicationServices.AXUIElementCopyAttributeValue(
            focused,
            ApplicationServices.kAXSelectedTextRangeAttribute,
            None
        )

        if error != 0 or not frame_ref:
            print("没有获取到焦点元素. 尝试使用鼠标位置兜底2")
            return self.get_cursor_position()

        # 4. 解析 AXValue 中的 CGRect
        # PyObjC 风格：无需传 None 作为最后参数，直接返回 (Success, Value)

        # frame_ref 现在是 {start, length} 列表，先尝试解析成 NSRange
        if isinstance(frame_ref, list) and len(frame_ref) == 2:
            start, length = frame_ref
            # 用 start 作为插入点横坐标，纵坐标暂时用元素中心兜底
            err, frame_val = ApplicationServices.AXUIElementCopyAttributeValue(
                focused, ApplicationServices.kAXFrameAttribute, None
            )
            if err == 0 and frame_val and hasattr(frame_val, 'cgRectValue'):
                rect = frame_val.cgRectValue()
                print(f"🎯 真正捕捉到光标坐标: x={rect.origin.x}, y={rect.origin.y}")
                return int(rect.origin.x + start * 7), int(rect.origin.y + rect.size.height // 2)  # 粗略估算
        # 如果拿不到文本范围，退回到元素 Frame
        if isinstance(frame_ref, ApplicationServices.AXValueRef):
            error, rect_ref = ApplicationServices.AXUIElementCopyParameterizedAttributeValue(
                focused,
                "AXBoundsForRange",
                frame_ref,
                None
            )

            if error == 0 and rect_ref:
                ok, rect = ApplicationServices.AXValueGetValue(
                    rect_ref,
                    ApplicationServices.kAXValueCGRectType,
                    None
                )
                if ok:
                    print(f"🎯 真正捕捉到光标坐标: x={rect.origin.x}, y={rect.origin.y}")
                    return int(rect.origin.x), int(rect.origin.y)

        # 如果 AXBoundsForRange 失败（部分 App 如 Chrome 可能不支持）
        print("没有获取到插入点坐标，尝试使用元素 Frame 兜底")
        return self._get_fallback_position(focused)


    def _get_fallback_position(self, element):
        """兜底方案：返回元素本身的中心点"""
        err, frame_ref = ApplicationServices.AXUIElementCopyAttributeValue(
            element, "AXFrame", None
        )
        if err == 0 and frame_ref and hasattr(frame_ref, 'cgRectValue'):
            rect = frame_ref.cgRectValue()
            if rect is not None:
                print(f"🎯 兜底方案：使用元素 Frame 坐标: x={rect.origin.x}, y={rect.origin.y}")
                return int(rect.origin.x), int(rect.origin.y)
        print("兜底方案失败，返回 (0, 0)")
        return 0, 0

    def get_window_at_cursor(self, x: int, y: int):
        # 确保选项正确
        windows = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        for w in windows:
            # CGWindowListCopyWindowInfo 返回的是 Python 字典，直接访问即可
            b = w.get('kCGWindowBounds')
            if b and b['X'] <= x <= b['X'] + b['Width'] and b['Y'] <= y <= b['Y'] + b['Height']:
                return {
                    "title": w.get('kCGWindowName', '未知'),
                    "app_name": w.get('kCGWindowOwnerName', '未知'),
                    "window_id": str(w.get('kCGWindowNumber', 'unknown')),
                    "position": (b['X'], b['Y']),
                    "size": (b['Width'], b['Height'])
                }
        return None


def write_appname_to_cursor(window_info: dict) -> None:
    """
    将当前窗口的 appname 写入光标所在位置
    """
    appname = window_info.get('app_name', '')
    if not appname:
        print("无法获取窗口信息，无法写入 app_name")
        return

    print("写入应用名称:", appname)

    # 使用 pyperclip 复制粘贴（支持中文）
    try:
        import pyperclip
        pyperclip.copy(appname)

        # 使用 Apple Script 粘贴
        subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "v" using {command down}'])
        print("✅ 粘贴成功")
        return
    except ImportError:
        print("⚠️ 未安装 pyperclip，尝试其他方式")
    except Exception as e:
        print("⚠️ 粘贴失败:", e)

    # 备用方案：直接输入（可能不支持中文）
    try:
        import pyautogui
        pyautogui.write(appname, interval=0.01)
        print("✅ 直接输入成功")
    except ImportError:
        print("⚠️ 未安装 pyautogui")
    except Exception as e:
        print("❌ 所有输入方案均失败:", e)

# --- 使用示例 ---
if __name__ == "__main__":
    impl = MacOSImpl()
    # 模拟 STT 流程，获取光标位置
    print("请在 3 秒内切换到目标输入框（如 VS Code 或 WPS）...")
    import time

    time.sleep(3)

    x, y = impl.get_input_cursor_position()
    info = impl.get_window_at_cursor(x, y)

    # 写入光标位置
    write_appname_to_cursor(info)

    print("-" * 30)
    print(f"当前应用: {info})")

    print(f"目标坐标: {(x, y )}")