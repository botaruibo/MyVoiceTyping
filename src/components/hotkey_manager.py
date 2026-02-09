"""
热键管理器
"""
import threading
from pynput import keyboard


class HotkeyManager:
    def __init__(self):
        self.listener = None
        self.active_modifiers = set()
        self.registered_hotkeys = []

        self.enabled = True
        self._hotkeys_lock = threading.Lock()

    def set_enabled(self, enabled: bool) -> None:
        with self._hotkeys_lock:
            self.enabled = bool(enabled)
            if not self.enabled:
                self.active_modifiers = set()

    def reset_hotkeys(self) -> None:
        with self._hotkeys_lock:
            self.active_modifiers = set()
            self.registered_hotkeys = []

    def _modifiers_satisfied(self, required_modifiers: set, active_modifiers: set | None = None) -> bool:
        if not required_modifiers:
            return True

        groups = {
            "cmd": {"cmd", "cmd_l", "cmd_r"},
            "alt": {"alt", "alt_l", "alt_r"},
            "ctrl": {"ctrl", "ctrl_l", "ctrl_r"},
            "shift": {"shift", "shift_l", "shift_r"},
        }

        for mod in required_modifiers:
            if mod in groups:
                if not (self.active_modifiers & groups[mod]):
                    return False
                continue

            if mod in {"cmd_l", "cmd_r", "alt_l", "alt_r", "ctrl_l", "ctrl_r", "shift_l", "shift_r", "fn"}:
                if mod not in self.active_modifiers:
                    return False
                continue

            if mod not in self.active_modifiers:
                return False

        return True

    def _normalize_key_token(self, token: str) -> str:
        token = (token or "").strip().lower()
        if not token:
            return ""

        token = token.strip("<>")
        # 说明：保留左右修饰键（cmd_l/cmd_r 等），否则无法做到“只右 cmd 触发”。
        aliases = {
            "command": "cmd",
            "control": "ctrl",
            "option": "alt",
            "left_command": "cmd_l",
            "right_command": "cmd_r",
            "left_option": "alt_l",
            "right_option": "alt_r",
            "left_control": "ctrl_l",
            "right_control": "ctrl_r",
            "left_shift": "shift_l",
            "right_shift": "shift_r",
        }
        return aliases.get(token, token)

    def _parse_hotkey(self, hotkey_str: str):
        if not hotkey_str:
            return None, set()

        parts = [p.strip() for p in str(hotkey_str).lower().split("+") if p.strip()]
        if not parts:
            return None, set()

        normalized = [self._normalize_key_token(p) for p in parts]
        key = normalized[-1]
        raw_mods = normalized[:-1]

        valid_mods = {
            "alt",
            "alt_l",
            "alt_r",
            "ctrl",
            "ctrl_l",
            "ctrl_r",
            "shift",
            "shift_l",
            "shift_r",
            "cmd",
            "cmd_l",
            "cmd_r",
            "fn",
        }
        modifiers = {m for m in raw_mods if m in valid_mods}

        if not key:
            return None, set()

        return key, modifiers

    def register_toggle_hotkey(self, hotkey, toggle_callback):
        key, modifiers = self._parse_hotkey(hotkey)
        if key:
            with self._hotkeys_lock:
                self.registered_hotkeys.append(
                    {
                        "key": key,
                        "modifiers": modifiers,
                        "type": "toggle",
                        "toggle_callback": toggle_callback,
                        "is_pressed": False,
                    }
                )
            print(f"Registered toggle hotkey: {hotkey}")

    def register_press_hotkey(self, hotkey, start_callback, stop_callback):
        key, modifiers = self._parse_hotkey(hotkey)
        if key:
            with self._hotkeys_lock:
                self.registered_hotkeys.append(
                    {
                        "key": key,
                        "modifiers": modifiers,
                        "type": "press",
                        "start_callback": start_callback,
                        "stop_callback": stop_callback,
                        "is_pressed": False,
                    }
                )
            print(f"Registered press hotkey: {hotkey}")

    def _is_modifier(self, key_name):
        normalized = self._normalize_key_token(key_name or "")
        return normalized in {
            "alt",
            "alt_l",
            "alt_r",
            "ctrl",
            "ctrl_l",
            "ctrl_r",
            "shift",
            "shift_l",
            "shift_r",
            "cmd",
            "cmd_l",
            "cmd_r",
            "fn",
        }

    def _get_key_name(self, key):
        if isinstance(key, keyboard.KeyCode):
            if key.char:
                return str(key.char).lower()
            if key.vk is not None:
                return str(key.vk)
            return ""

        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.cmd_l:
                return "cmd_l"
            if key == keyboard.Key.cmd_r:
                return "cmd_r"
            if key == keyboard.Key.cmd:
                return "cmd"

            if key == keyboard.Key.alt_l:
                return "alt_l"
            if key == keyboard.Key.alt_r:
                return "alt_r"
            if key == keyboard.Key.alt:
                return "alt"

            if key == keyboard.Key.ctrl_l:
                return "ctrl_l"
            if key == keyboard.Key.ctrl_r:
                return "ctrl_r"
            if key == keyboard.Key.ctrl:
                return "ctrl"

            if key == keyboard.Key.shift_l:
                return "shift_l"
            if key == keyboard.Key.shift_r:
                return "shift_r"
            if key == keyboard.Key.shift:
                return "shift"

            name = getattr(key, "name", "")
            return str(name).lower() if name else ""

        return ""

    def on_press(self, key):
        with self._hotkeys_lock:
            if not self.enabled:
                return

        key_name_raw = self._get_key_name(key)
        key_name = self._normalize_key_token(key_name_raw or "")
        if not key_name:
            return

        if self._is_modifier(key_name):
            self.active_modifiers.add(key_name)

        callbacks_to_call = []
        with self._hotkeys_lock:
            # 更新 active_modifiers、筛选匹配热键、设置 is_pressed、收集回调
            hotkeys_snapshot = list(self.registered_hotkeys)

        for hotkey in hotkeys_snapshot:
            if key_name != hotkey["key"]:
                continue
            if not self._modifiers_satisfied(hotkey["modifiers"]):
                continue
            if hotkey["is_pressed"]:
                continue

            hotkey["is_pressed"] = True
            try:
                if hotkey["type"] == "press":
                    cb = hotkey.get("start_callback")
                    if cb:
                        cb()
                elif hotkey["type"] == "toggle":
                    cb = hotkey.get("toggle_callback")
                    if cb:
                        cb()
            except Exception as e:
                print(f"⚠️ 热键回调异常（on_press）：{e}")

    def on_release(self, key):
        with self._hotkeys_lock:
            if not self.enabled:
                return

        key_name_raw = self._get_key_name(key)
        key_name = self._normalize_key_token(key_name_raw or "")
        if not key_name:
            return

        callbacks_to_call = []
        with self._hotkeys_lock:
            # 复位 is_pressed、收集 stop_callback
            hotkeys_snapshot = list(self.registered_hotkeys)

        for hotkey in hotkeys_snapshot:
            if key_name != hotkey["key"]:
                continue
            if not hotkey["is_pressed"]:
                continue

            hotkey["is_pressed"] = False
            if hotkey["type"] == "press":
                try:
                    cb = hotkey.get("stop_callback")
                    if cb:
                        cb()
                except Exception as e:
                    print(f"⚠️ 热键回调异常（on_release）：{e}")

        if self._is_modifier(key_name):
            self.active_modifiers.discard(key_name)

        if key == keyboard.Key.esc:
            self.stop_listening()
            return False

    def start_listening(self):
        """开始监听热键"""
        print(f"🚀 开始监听热键...")
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            self.listener = listener
            listener.join()
        print("Hotkey listener stopped.")

    def stop_listening(self):
        if self.listener:
            self.listener.stop()