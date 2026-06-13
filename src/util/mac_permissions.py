"""macOS 权限引导：当检测到缺少 TCC 权限时，弹出置顶原生告警框并跳转到对应设置面板。

后台应用（LSUIElement）无法靠 print 提醒用户，打开的“系统设置”也常被前台应用遮挡。
这里用 osascript 弹出一个置顶 dialog（独立进程、可从子线程安全调用），用户点击后
直接打开精确的隐私面板并把“系统设置”激活到最前。
"""
from __future__ import annotations

import sys
import time
import subprocess
import threading
import ctypes
import ctypes.util
from typing import Dict

# 各权限对应的“系统设置 > 隐私与安全”面板 URL。
_PANE_URLS: Dict[str, str] = {
    "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
}

_TITLES: Dict[str, str] = {
    "input_monitoring": "需要“输入监控”权限",
    "accessibility": "需要“辅助功能”权限",
    "microphone": "需要“麦克风”权限",
}

_MESSAGES: Dict[str, str] = {
    "input_monitoring": (
        "MyVoiceTyping 需要“输入监控”权限，才能在后台监听语音输入快捷键。\n\n"
        "请在打开的“系统设置 > 隐私与安全 > 输入监控”中，开启 MyVoiceTyping，"
        "然后退出并重新打开本应用。"
    ),
    "accessibility": (
        "MyVoiceTyping 需要“辅助功能”权限，才能把转录文字写入当前输入位置。\n\n"
        "请在打开的“系统设置 > 隐私与安全 > 辅助功能”中，开启 MyVoiceTyping，"
        "然后退出并重新打开本应用。"
    ),
    "microphone": (
        "MyVoiceTyping 需要“麦克风”权限，才能录制语音。\n\n"
        "请在打开的“系统设置 > 隐私与安全 > 麦克风”中，开启 MyVoiceTyping。"
    ),
}

# 同一权限的弹窗去抖间隔（秒），避免重复触发时刷屏。
_PROMPT_COOLDOWN_SEC = 30.0
_last_prompt_ts: Dict[str, float] = {}
_lock = threading.Lock()


def is_accessibility_trusted(prompt: bool = False) -> bool:
    """返回当前进程是否已获得 macOS“辅助功能”权限。

    CGEvent 发送键盘事件依赖 Accessibility/TCC。不要用
    CGPreflightPostEventAccess 判断这个权限，它在部分 macOS 版本上会把
    已授权的“辅助功能”误判为未授权。
    """
    if sys.platform != "darwin":
        return True

    try:
        import Quartz  # type: ignore

        if prompt and hasattr(Quartz, "AXIsProcessTrustedWithOptions"):
            options = {Quartz.kAXTrustedCheckOptionPrompt: True}
            return bool(Quartz.AXIsProcessTrustedWithOptions(options))
        if hasattr(Quartz, "AXIsProcessTrusted"):
            return bool(Quartz.AXIsProcessTrusted())
    except Exception:
        pass

    try:
        framework = (
            ctypes.util.find_library("ApplicationServices")
            or "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        app_services = ctypes.CDLL(framework)
        app_services.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(app_services.AXIsProcessTrusted())
    except Exception:
        return False


def request_accessibility_permission() -> bool:
    """请求并引导开启“辅助功能”权限，返回请求后的已授权状态。"""
    if is_accessibility_trusted(prompt=False):
        return True

    now = time.monotonic()
    with _lock:
        key = "accessibility_ax_prompt"
        last = _last_prompt_ts.get(key, 0.0)
        if (now - last) >= _PROMPT_COOLDOWN_SEC:
            _last_prompt_ts[key] = now
            try:
                is_accessibility_trusted(prompt=True)
            except Exception:
                pass

    prompt_permission("accessibility")
    return is_accessibility_trusted(prompt=False)


def _open_settings_pane(permission: str) -> None:
    url = _PANE_URLS.get(permission)
    if not url:
        return
    try:
        subprocess.run(["open", url], check=False)
        # 把“系统设置”激活到最前，避免被其他应用遮挡。
        subprocess.run(
            ["osascript", "-e", 'tell application "System Settings" to activate'],
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def _show_dialog(permission: str) -> bool:
    """弹出置顶告警框。返回用户是否点击了“打开设置”。"""
    title = _TITLES.get(permission, "需要系统权限")
    message = _MESSAGES.get(permission, "MyVoiceTyping 需要额外的系统权限才能正常工作。")
    # display dialog 默认置于最前；用 System Events 进程保证后台应用也能弹出。
    script = (
        'tell application "System Events"\n'
        '    activate\n'
        f'    set theResult to display dialog {_as_applescript_str(message)} '
        f'with title {_as_applescript_str(title)} '
        'with icon caution '
        'buttons {"稍后", "打开设置"} default button "打开设置"\n'
        '    return button returned of theResult\n'
        'end tell'
    )
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        return (proc.stdout or "").strip() == "打开设置"
    except Exception:
        return False


def _as_applescript_str(text: str) -> str:
    """把 Python 字符串安全地转成 AppleScript 字符串字面量。"""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def prompt_permission(permission: str, force: bool = False) -> None:
    """检测到缺少权限时调用：弹置顶告警框，用户确认后打开对应设置面板。

    在独立后台线程执行，避免阻塞调用方（热键监听 / 录音 / 粘贴）。
    """
    if sys.platform != "darwin":
        return

    now = time.monotonic()
    with _lock:
        last = _last_prompt_ts.get(permission, 0.0)
        if not force and (now - last) < _PROMPT_COOLDOWN_SEC:
            return
        _last_prompt_ts[permission] = now

    def _worker() -> None:
        if _show_dialog(permission):
            _open_settings_pane(permission)

    threading.Thread(target=_worker, daemon=True).start()
