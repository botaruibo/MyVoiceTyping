#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版：解决 option 键（及其他修饰键）回调不生效的问题
"""

import ctypes
import ctypes.util
import threading
import time
import sys
import platform
from dataclasses import dataclass
from typing import Callable, Optional, List, Dict, Set, Union, Tuple
from enum import Enum, auto

# 加载框架
Foundation = ctypes.CDLL(ctypes.util.find_library('Foundation'), mode=ctypes.RTLD_GLOBAL)
Quartz = ctypes.CDLL(ctypes.util.find_library('Quartz'))
CoreFoundation = ctypes.CDLL(ctypes.util.find_library('CoreFoundation'))

# 常量
kCGEventTapOptionListenOnly = 1
kCGHeadInsertEventTap = 0
kCGSessionEventTap = 0

kCGEventKeyDown = 10
kCGEventKeyUp = 11
kCGEventFlagsChanged = 12
kCGEventTapDisabledByTimeout = 0xFFFFFFFE

# 所有已知的 Fn 键掩码
KNOWN_FN_MASKS = [0x00800000]

# 修饰键掩码 - 区分左右
MODIFIER_MASKS = {
    'cmd_l': 0x00000008,  # NX_DEVICELCMDKEYMASK
    'cmd_r': 0x00000010,  # NX_DEVICERCMDKEYMASK
    'ctrl_l': 0x00000001,  # NX_DEVICELCTLKEYMASK
    'ctrl_r': 0x00002000,  # NX_DEVICERCTLKEYMASK
    'shift_l': 0x00000002,  # NX_DEVICELSHIFTKEYMASK
    'shift_r': 0x00000004,  # NX_DEVICERSHIFTKEYMASK
    'option_l': 0x00000020,  # NX_DEVICELALTKEYMASK
    'option_r': 0x00000040,  # NX_DEVICERALTKEYMASK
}

# macOS 通用修饰键 flags。部分键盘/系统版本只稳定提供这些高位 mask，
# 不一定稳定提供上面的左右区分低位 mask。
GENERIC_MODIFIER_MASKS = {
    'cmd': 0x00100000,      # kCGEventFlagMaskCommand
    'ctrl': 0x00040000,     # kCGEventFlagMaskControl
    'shift': 0x00020000,    # kCGEventFlagMaskShift
    'option': 0x00080000,   # kCGEventFlagMaskAlternate
}

MODIFIER_KEYCODE_TO_NAME = {
    0x36: 'cmd_r',
    0x37: 'cmd_l',
    0x38: 'shift_l',
    0x3A: 'option_l',
    0x3B: 'ctrl_l',
    0x3C: 'shift_r',
    0x3D: 'option_r',
    0x3E: 'ctrl_r',
}

MODIFIER_NAME_TO_GENERIC = {
    'cmd_l': 'cmd',
    'cmd_r': 'cmd',
    'ctrl_l': 'ctrl',
    'ctrl_r': 'ctrl',
    'shift_l': 'shift',
    'shift_r': 'shift',
    'option_l': 'option',
    'option_r': 'option',
}

# 键码映射
KEY_CODES = {
    0x00: 'a', 0x01: 's', 0x02: 'd', 0x03: 'f', 0x04: 'h', 0x05: 'g',
    0x06: 'z', 0x07: 'x', 0x08: 'c', 0x09: 'v', 0x0B: 'b', 0x0C: 'q',
    0x0D: 'w', 0x0E: 'e', 0x0F: 'r', 0x10: 'y', 0x11: 't', 0x12: '1',
    0x13: '2', 0x14: '3', 0x15: '4', 0x16: '6', 0x17: '5', 0x18: '=',
    0x19: '9', 0x1A: '7', 0x1B: '-', 0x1C: '8', 0x1D: '0', 0x1E: ']',
    0x1F: 'o', 0x20: 'u', 0x21: '[', 0x22: 'i', 0x23: 'p', 0x25: 'l',
    0x26: 'j', 0x27: "'", 0x28: 'k', 0x29: ';', 0x2A: '\\', 0x2B: ',',
    0x2C: '/', 0x2D: 'n', 0x2E: 'm', 0x2F: '.', 0x32: '`', 0x24: 'return',
    0x30: 'tab', 0x31: 'space', 0x33: 'delete', 0x35: 'esc', 0x36: 'right_cmd', 0x37: 'cmd',
    0x38: 'shift', 0x39: 'caps', 0x3A: 'option', 0x3B: 'ctrl', 0x3C: 'right_shift',
    0x3D: 'right_option', 0x3E: 'right_ctrl', 0x3F: 'fn', 0x40: 'f17',
    0x48: 'volume_up', 0x49: 'volume_down', 0x4A: 'mute',
    0x60: 'f5', 0x61: 'f6', 0x62: 'f7', 0x63: 'f3', 0x64: 'f8', 0x65: 'f9',
    0x67: 'f11', 0x69: 'f13', 0x6A: 'f16', 0x6B: 'f14', 0x6D: 'f10',
    0x6F: 'f12', 0x71: 'f15', 0x72: 'help', 0x73: 'home', 0x74: 'pageup',
    0x75: 'delete_forward', 0x76: 'f4', 0x77: 'end', 0x78: 'f2', 0x79: 'pagedown',
    0x7A: 'f1', 0x7B: 'left', 0x7C: 'right', 0x7D: 'down', 0x7E: 'up',
}

# 类型定义
CFMachPortRef = ctypes.c_void_p
CFRunLoopSourceRef = ctypes.c_void_p
CFRunLoopRef = ctypes.c_void_p
CGEventRef = ctypes.c_void_p

# 函数签名
Quartz.CGEventTapCreate.argtypes = [
    ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint64,
    ctypes.c_void_p, ctypes.c_void_p
]
Quartz.CGEventTapCreate.restype = CFMachPortRef
Quartz.CGEventTapEnable.argtypes = [CFMachPortRef, ctypes.c_bool]
Quartz.CGEventTapEnable.restype = None
Quartz.CGEventTapIsEnabled.argtypes = [CFMachPortRef]
Quartz.CGEventTapIsEnabled.restype = ctypes.c_bool
Quartz.CGEventGetFlags.argtypes = [CGEventRef]
Quartz.CGEventGetFlags.restype = ctypes.c_uint64
Quartz.CGEventGetIntegerValueField.argtypes = [CGEventRef, ctypes.c_int32]
Quartz.CGEventGetIntegerValueField.restype = ctypes.c_int64

CoreFoundation.CFMachPortCreateRunLoopSource.argtypes = [
    ctypes.c_void_p, CFMachPortRef, ctypes.c_int64
]
CoreFoundation.CFMachPortCreateRunLoopSource.restype = CFRunLoopSourceRef
CoreFoundation.CFRunLoopGetCurrent.argtypes = []
CoreFoundation.CFRunLoopGetCurrent.restype = CFRunLoopRef
CoreFoundation.CFRunLoopAddSource.argtypes = [CFRunLoopRef, CFRunLoopSourceRef, ctypes.c_void_p]
CoreFoundation.CFRunLoopAddSource.restype = None
CoreFoundation.CFRunLoopRemoveSource.argtypes = [CFRunLoopRef, CFRunLoopSourceRef, ctypes.c_void_p]
CoreFoundation.CFRunLoopRemoveSource.restype = None
CoreFoundation.CFRunLoopRun.argtypes = []
CoreFoundation.CFRunLoopRun.restype = None
CoreFoundation.CFRunLoopStop.argtypes = [CFRunLoopRef]
CoreFoundation.CFRunLoopStop.restype = None
CoreFoundation.CFRelease.argtypes = [ctypes.c_void_p]
CoreFoundation.CFRelease.restype = None

CGEventTapCallback = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p
)


@dataclass
class KeyEvent:
    """键盘事件"""
    event_type: str
    timestamp: float
    raw_flags: int
    keycode: int
    keys_pressed: Set[str]

    def __repr__(self):
        return f"KeyEvent({self.event_type}, keys={self.keys_pressed})"


class ShortcutKey:
    """
    快捷键定义
    规则：
    - 单键：只能是 fn 或修饰键（不能是 space）
    - 双键：space 只能和 fn/修饰键组合
    """

    # 可作为单键的键
    SINGLE_KEYS = {'fn', 'cmd_l', 'cmd_r', 'option_l', 'option_r',
                   'ctrl_l', 'ctrl_r', 'shift_l', 'shift_r'}

    # 可作为组合键的键
    COMBO_KEYS = {'fn', 'space', 'cmd_l', 'cmd_r', 'option_l', 'option_r',
                  'ctrl_l', 'ctrl_r', 'shift_l', 'shift_r'}

    # 排序权重（用于格式化输出）
    KEY_ORDER = {
        'fn': 0,
        'cmd_l': 1, 'cmd_r': 1,
        'option_l': 2, 'option_r': 2,
        'ctrl_l': 3, 'ctrl_r': 3,
        'shift_l': 4, 'shift_r': 4,
        'space': 5,
    }

    def __init__(self, *keys: str):
        keys_set = set(keys)

        # 验证数量
        if len(keys_set) == 0 or len(keys_set) > 2:
            raise ValueError("快捷键必须包含1-2个键")

        # 验证键有效性
        invalid = keys_set - self.COMBO_KEYS
        if invalid:
            raise ValueError(f"无效键: {invalid}，有效键: {self.COMBO_KEYS}")

        # 关键规则：单键不能是 space
        if len(keys_set) == 1 and 'space' in keys_set:
            raise ValueError("space 不能作为单键快捷键，必须与 fn 或修饰键组合")

        # 双键规则验证
        if len(keys_set) == 2:
            if 'space' in keys_set:
                other = (keys_set - {'space'}).pop()
                if other not in self.SINGLE_KEYS:
                    raise ValueError(f"space 只能与 fn 或修饰键组合，不能和 {other} 组合")

        self.keys = frozenset(keys_set)
        self._str = self._format_string()

    def _format_string(self) -> str:
        """格式化输出字符串 - 使用固定排序"""
        sorted_keys = sorted(self.keys, key=lambda x: self.KEY_ORDER.get(x, 99))
        return '+'.join(f'<{k}>' for k in sorted_keys)

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return f"ShortcutKey({self._str})"

    def __hash__(self) -> int:
        return hash(self.keys)

    def __eq__(self, other) -> bool:
        if isinstance(other, ShortcutKey):
            return self.keys == other.keys
        return False

    def match(self, pressed_keys: Set[str]) -> bool:
        """检查按下的键是否匹配此快捷键"""
        return self.keys == pressed_keys

    def is_single_key(self) -> bool:
        return len(self.keys) == 1

    def contains(self, key: str) -> bool:
        return key in self.keys


class UniversalKeyListener:
    """通用键盘监听器"""

    def __init__(self, debug: bool = False):
        self.debug = debug

        self._press_callbacks: List[Callable[[KeyEvent], None]] = []
        self._release_callbacks: List[Callable[[KeyEvent], None]] = []
        self._raw_callbacks: List[Callable[[int, int, int, Set[str]], None]] = []

        self._current_keys: Set[str] = set()
        self._last_keys: Set[str] = set()
        self._modifier_keycode_state: Set[str] = set()
        self._fn_mask: Optional[int] = None

        self._running = False
        self._tap: Optional[CFMachPortRef] = None
        self._source: Optional[CFRunLoopSourceRef] = None
        self._run_loop: Optional[CFRunLoopRef] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._health_timer: Optional[threading.Timer] = None

        self._callback_ptr = CGEventTapCallback(self._event_callback)

    def _detect_fn_mask(self, flags: int) -> Optional[int]:
        if self._fn_mask is not None:
            return self._fn_mask

        for mask in KNOWN_FN_MASKS:
            if flags & mask:
                self._fn_mask = mask
                if self.debug:
                    print(f"🔍 检测到 Fn 掩码: {hex(mask)}")
                return mask
        return None

    def _is_modifier_down(self, flags: int, modifier_name: str) -> bool:
        low_mask = MODIFIER_MASKS.get(modifier_name, 0)
        if low_mask and (flags & low_mask):
            return True

        generic_name = MODIFIER_NAME_TO_GENERIC.get(modifier_name)
        generic_mask = GENERIC_MODIFIER_MASKS.get(generic_name or "", 0)
        return bool(generic_mask and (flags & generic_mask))

    def _update_modifier_keycode_state(self, flags: int, keycode: int) -> None:
        modifier_name = MODIFIER_KEYCODE_TO_NAME.get(keycode)
        if modifier_name is None:
            return

        if self._is_modifier_down(flags, modifier_name):
            self._modifier_keycode_state.add(modifier_name)
        else:
            self._modifier_keycode_state.discard(modifier_name)

    def _flags_to_keys(self, flags: int, keycode: int = -1, event_type: int = -1) -> Set[str]:
        """将 flags 和 keycode 转换为键集合"""
        keys = set()

        # 检测 Fn
        # 方向键等导航键在 macOS 上可能携带 Fn flag。只有 flagsChanged
        # 或明确的 fn+space 场景才把它视为可触发热键的 Fn。
        should_read_fn = event_type == kCGEventFlagsChanged or keycode in (0x3F, 0x31)
        fn_mask = self._detect_fn_mask(flags) if should_read_fn else self._fn_mask
        if should_read_fn and fn_mask and (flags & fn_mask):
            keys.add('fn')

        # 检测修饰键（区分左右）。优先使用低位左右区分 mask。
        for name, mask in MODIFIER_MASKS.items():
            if flags & mask:
                keys.add(name)
                if self.debug:
                    print(
                        f"    [Modifier detected] {name}: flags={hex(flags)} & mask={hex(mask)} = {bool(flags & mask)}")

        # 兜底：部分 macOS/键盘组合只稳定提供通用高位 mask。
        # 对 flagsChanged 事件，用 keycode 维护左右键状态，再合并到当前 keys。
        keys.update(self._modifier_keycode_state)

        # 检测普通键
        if keycode >= 0 and keycode in KEY_CODES:
            key_name = KEY_CODES[keycode]
            if key_name in ['space']:
                keys.add(key_name)

        return keys

    def _event_callback(self, proxy, event_type, event, refcon):
        try:
            if event_type == kCGEventTapDisabledByTimeout:
                if self.debug:
                    print("⚠️  EventTap 超时，重新启用...")
                threading.Thread(target=self._reenable_tap, daemon=True).start()
                return None

            if not event:
                return event

            flags = Quartz.CGEventGetFlags(event)
            keycode = -1

            if event_type in (kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged):
                keycode = Quartz.CGEventGetIntegerValueField(event, 9)

            # 关键：实时转换当前状态
            with self._lock:
                if event_type == kCGEventFlagsChanged:
                    self._update_modifier_keycode_state(flags, keycode)

                current_keys = self._flags_to_keys(flags, keycode, event_type)

                # 检测变化
                new_keys = current_keys - self._current_keys
                released_keys = self._current_keys - current_keys

                # 更新状态
                self._current_keys = current_keys.copy()

                # 触发按下事件
                if new_keys:
                    self._last_keys = current_keys.copy()
                    event_obj = KeyEvent('press', time.time(), flags, keycode, current_keys.copy())

                    if self.debug:
                        print(f"  [Press] current={current_keys}, new={new_keys}, released={released_keys}")

                    for cb in self._press_callbacks:
                        threading.Thread(target=cb, args=(event_obj,), daemon=True).start()

                # 触发释放事件（所有键都释放）
                elif released_keys and not current_keys:
                    self._last_keys = set()
                    event_obj = KeyEvent('release', time.time(), flags, keycode, set())

                    if self.debug:
                        print(f"  [Release] released={released_keys}")

                    for cb in self._release_callbacks:
                        threading.Thread(target=cb, args=(event_obj,), daemon=True).start()

                # 状态变化但仍有键（组合键变化）
                elif released_keys and current_keys:
                    self._last_keys = current_keys.copy()
                    # 触发释放旧组合，按下新组合
                    event_obj_release = KeyEvent('release', time.time(), flags, keycode,
                                                 self._current_keys | released_keys)
                    event_obj_press = KeyEvent('press', time.time(), flags, keycode, current_keys.copy())

                    if self.debug:
                        print(f"  [Change] current={current_keys}, released={released_keys}")

                    for cb in self._release_callbacks:
                        threading.Thread(target=cb, args=(event_obj_release,), daemon=True).start()
                    for cb in self._press_callbacks:
                        threading.Thread(target=cb, args=(event_obj_press,), daemon=True).start()

            # 原始回调
            for cb in self._raw_callbacks:
                try:
                    cb(event_type, flags, keycode, current_keys.copy())
                except:
                    pass

            return event

        except Exception as e:
            if self.debug:
                print(f"Callback error: {e}")
                import traceback
                traceback.print_exc()
            return event

    def _reenable_tap(self):
        try:
            if self._tap and self._running:
                Quartz.CGEventTapEnable(self._tap, False)
                time.sleep(0.01)
                Quartz.CGEventTapEnable(self._tap, True)
        except Exception as e:
            if self.debug:
                print(f"Re-enable error: {e}")

    def _health_check(self):
        if not self._running:
            return

        try:
            if self._tap and not Quartz.CGEventTapIsEnabled(self._tap):
                if self.debug:
                    print("⚠️  健康检查: 恢复 EventTap")
                self._reenable_tap()
        except Exception as e:
            if self.debug:
                print(f"Health check error: {e}")

        self._health_timer = threading.Timer(5.0, self._health_check)
        self._health_timer.daemon = True
        self._health_timer.start()

    def on_press(self, func: Callable[[KeyEvent], None]):
        self._press_callbacks.append(func)
        return func

    def on_release(self, func: Callable[[KeyEvent], None]):
        self._release_callbacks.append(func)
        return func

    def on_raw(self, func: Callable[[int, int, int, Set[str]], None]):
        self._raw_callbacks.append(func)
        return func

    def get_current_keys(self) -> Set[str]:
        with self._lock:
            return self._current_keys.copy()

    def start(self, blocking: bool = False):
        if self._running:
            return True

        try:
            event_mask = (
                    (1 << kCGEventFlagsChanged) |
                    (1 << kCGEventKeyDown) |
                    (1 << kCGEventKeyUp)
            )

            # 在主线程创建 tap 是安全的，且通常需要
            self._tap = Quartz.CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,
                event_mask,
                self._callback_ptr,
                None
            )

            if not self._tap:
                raise PermissionError(
                    "无法创建 EventTap。请前往：\n"
                    "系统设置 > 隐私与安全 > 辅助功能\n"
                    "添加当前终端/IDE 并授权"
                )

            self._running = True
            self._health_check()

            if self.debug:
                print("✅ 键盘监听已启动")

            if blocking:
                self._run_loop_thread()
            else:
                self._thread = threading.Thread(target=self._run_loop_thread, daemon=True)
                self._thread.start()
                # 给一点时间让 RunLoop 初始化
                time.sleep(0.1)

            return True

        except Exception as e:
            # 启动失败时清理 tap
            if self._tap:
                CoreFoundation.CFRelease(self._tap)
                self._tap = None
            self._running = False
            raise e

    def _run_loop_thread(self):
        try:
            # 1. 创建 RunLoopSource
            self._source = CoreFoundation.CFMachPortCreateRunLoopSource(
                ctypes.c_void_p(0), self._tap, 0
            )

            # 2. 获取当前线程（子线程）的 RunLoop
            self._run_loop = CoreFoundation.CFRunLoopGetCurrent()
            kCFRunLoopDefaultMode = ctypes.c_void_p.in_dll(
                CoreFoundation, 'kCFRunLoopDefaultMode'
            )

            # 3. 添加 Source 到当前 RunLoop
            CoreFoundation.CFRunLoopAddSource(
                self._run_loop, self._source, kCFRunLoopDefaultMode
            )

            # 4. 启用 Tap
            Quartz.CGEventTapEnable(self._tap, True)

            # 5. 运行 RunLoop
            CoreFoundation.CFRunLoopRun()
        except Exception as e:
            if self.debug:
                print(f"RunLoop error: {e}")
        finally:
            # RunLoop 退出后，在当前线程清理资源
            self._cleanup_resources()

    def _cleanup_resources(self):
        """仅在 RunLoop 线程中调用"""
        try:
            if self._health_timer:
                self._health_timer.cancel()

            # 确保 tap 被禁用
            if self._tap:
                Quartz.CGEventTapEnable(self._tap, False)

            if self._source and self._run_loop:
                kCFRunLoopDefaultMode = ctypes.c_void_p.in_dll(
                    CoreFoundation, 'kCFRunLoopDefaultMode'
                )
                CoreFoundation.CFRunLoopRemoveSource(
                    self._run_loop, self._source, kCFRunLoopDefaultMode
                )
                CoreFoundation.CFRelease(self._source)

            if self._tap:
                CoreFoundation.CFRelease(self._tap)
        except Exception as e:
            if self.debug:
                print(f"Cleanup error: {e}")
        finally:
            self._tap = None
            self._source = None
            self._run_loop = None

    def stop(self):
        if not self._running:
            return

        self._running = False

        if self._health_timer:
            self._health_timer.cancel()

        # 发送停止信号，这会导致 CFRunLoopRun 返回
        if self._run_loop:
            CoreFoundation.CFRunLoopStop(self._run_loop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self.debug:
            print("✅ 监听已停止")

    def is_running(self) -> bool:
        return self._running

    # 确保在对象销毁时及时清理资源
    def __del__(self):
        try:
            # 先停止运行
            self.stop()
        except Exception:
            pass  # 析构函数中避免抛出异常

class ShortcutDetector:
    """快捷键检测器 - 修复版"""

    def __init__(self, listener: UniversalKeyListener, debug: bool = False):
        self.listener = listener
        self.debug = debug
        self._shortcuts: Dict[ShortcutKey, Dict[str, Optional[Callable]]] = {}
        self._active_shortcut: Optional[ShortcutKey] = None
        self._last_triggered: Optional[ShortcutKey] = None

        self._setup_listener()

    def _setup_listener(self):
        @self.listener.on_press
        def on_press(event: KeyEvent):
            self._handle_press(event)

        @self.listener.on_release
        def on_release(event: KeyEvent):
            self._handle_release(event)

    def _handle_press(self, event: KeyEvent):
        """处理按下事件 - 关键修复：更精确的匹配逻辑"""
        keys = event.keys_pressed

        # 过滤：只处理有效的快捷键组合
        if keys == {'space'}:
            if self.debug:
                print(f"  [Filter] 忽略单独的 space")
            return

        if self.debug:
            print(f"  [ShortcutDetector] 检查按下: {keys}")
            print(f"    已注册: {list(self._shortcuts.keys())}")

        # 遍历所有注册的快捷键，找到匹配的
        for shortcut, callbacks in self._shortcuts.items():
            if shortcut.match(keys):
                # 避免重复触发同一快捷键
                if self._last_triggered != shortcut:
                    if self.debug:
                        print(f"    ✅ 匹配: {shortcut}, 触发 press")
                    self._active_shortcut = shortcut
                    self._last_triggered = shortcut
                    self._trigger(shortcut, 'press', event)
                else:
                    if self.debug:
                        print(f"    ⏭️  已触发过，跳过: {shortcut}")
                return

        if self.debug:
            print(f"    ❌ 无匹配")

    def _handle_release(self, event: KeyEvent):
        """处理释放事件"""
        if self.debug:
            print(f"  [ShortcutDetector] 释放检查: active={self._active_shortcut}, keys={event.keys_pressed}")

        # 如果有激活的快捷键，触发其释放回调
        if self._active_shortcut:
            if self.debug:
                print(f"    ✅ 触发释放: {self._active_shortcut}")
            self._trigger(self._active_shortcut, 'release', event)
            self._active_shortcut = None

        # 重置最后触发（所有键都释放后）
        if not event.keys_pressed:
            if self.debug:
                print(f"    🔄 重置状态")
            self._last_triggered = None

    def _trigger(self, shortcut: ShortcutKey, event_type: str, event: KeyEvent):
        """触发回调"""
        callbacks = self._shortcuts.get(shortcut, {})
        callback = callbacks.get(event_type)

        if callback:
            try:
                if self.debug:
                    print(f"    🚀 执行回调: {event_type}")
                callback()
            except Exception as e:
                print(f"快捷键回调错误 [{shortcut}]: {e}")
                import traceback
                traceback.print_exc()
        else:
            if self.debug:
                print(f"    ⚠️  无 {event_type} 回调")

    def register(self, shortcut: Union[str, ShortcutKey],
                 on_press: Optional[Callable] = None,
                 on_release: Optional[Callable] = None):
        """注册快捷键"""
        if isinstance(shortcut, str):
            keys = [k.strip() for k in shortcut.split('+')]
            shortcut = ShortcutKey(*keys)

        self._shortcuts[shortcut] = {
            'press': on_press,
            'release': on_release
        }

        if self.debug:
            print(f"  [Register] {shortcut} -> press:{on_press is not None}, release:{on_release is not None}")

        return shortcut

    def on(self, shortcut: Union[str, ShortcutKey], event: str = 'press'):
        """装饰器注册"""

        def decorator(func: Callable):
            if isinstance(shortcut, str):
                keys = [k.strip() for k in shortcut.split('+')]
                sk = ShortcutKey(*keys)
            else:
                sk = shortcut

            if sk not in self._shortcuts:
                self._shortcuts[sk] = {'press': None, 'release': None}

            self._shortcuts[sk][event] = func

            if self.debug:
                print(f"  [Decorator] {sk} {event} -> {func.__name__}")

            return func

        return decorator

    def unregister(self, shortcut: Union[str, ShortcutKey]):
        """注销快捷键"""
        if isinstance(shortcut, str):
            keys = [k.strip() for k in shortcut.split('+')]
            shortcut = ShortcutKey(*keys)

        if shortcut in self._shortcuts:
            del self._shortcuts[shortcut]

    def clear_hotkeys(self):
        self._shortcuts = {}

    def list_shortcuts(self) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """列出所有快捷键"""
        result = []
        for shortcut, callbacks in self._shortcuts.items():
            press_name = callbacks.get('press').__name__ if callbacks.get('press') else None
            release_name = callbacks.get('release').__name__ if callbacks.get('release') else None
            result.append((str(shortcut), press_name, release_name))
        return result

    def check_shortcut(self, keys: Set[str]) -> Optional[ShortcutKey]:
        """检查是否匹配"""
        for shortcut in self._shortcuts.keys():
            if shortcut.match(keys):
                return shortcut
        return None


# ========== 完整 Demo ==========

def demo():

    # 创建监听器和检测器（都开启调试）
    listener = UniversalKeyListener(debug=False)
    detector = ShortcutDetector(listener, debug=False)

    print("\n📝 注册快捷键...")

    # 使用 register 方法
    detector.register('fn+shift_l',
                      on_press=lambda s, e: print(f"🎯 {s} 按下 - 特殊功能"),
                      on_release=lambda s, e: print(f"⚪ {s} 释放")
                      )

    try:
        listener.start(blocking=True)
    except PermissionError as e:
        print(f"\n❌ 权限错误: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")

if __name__ == "__main__":
    demo()
