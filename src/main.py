#!/usr/bin/env python3
"""
TypelessApp 类 - 无界输入法核心应用
"""
import threading

from .core import STTProcessor, Rewrite, WindowInfo
from .components.audio_recorder import AudioRecorder
from .components.hotkey_manager import HotkeyManager
try:
    from .components.tray_icon import TrayIcon
except Exception:
    TrayIcon = None
from .utils.config_manager import ConfigManager
from .gui_tk import VoiceInputGUI

class TypelessApp:
    def __init__(self):
        self.app_name = "闪电输入法"
        self.config_manager = None

        self.audio_recorder = AudioRecorder()
        self.stt_processor = None
        self._stt_ready = threading.Event()
        self._stt_init_lock = threading.Lock()
        self._stt_init_error = None

        self.rewriter = Rewrite()
        self.window_info = WindowInfo()

        self.hotkey_manager = HotkeyManager()
        self.tray_icon = TrayIcon(self) if TrayIcon is not None else None

        self.gui = None
        self._processing_lock = threading.Lock()
        self._is_processing = False

    def init_stt_async(self) -> None:
        def _worker() -> None:
            with self._stt_init_lock:
                if self.stt_processor is not None:
                    return
                try:
                    self._set_status("正在初始化语音模型…")
                    self.stt_processor = STTProcessor()
                    self._set_status("语音模型就绪")
                except Exception as e:
                    self._stt_init_error = e
                    self._set_status(f"语音模型初始化失败：{e}")
                finally:
                    self._stt_ready.set()

        threading.Thread(target=_worker, daemon=True).start()

    def _ensure_stt_ready(self) -> None:
        if self.stt_processor is not None:
            return
        if not self._stt_ready.is_set():
            self.init_stt_async()
        self._stt_ready.wait()
        if self._stt_init_error is not None:
            raise self._stt_init_error

    def _set_status(self, text: str) -> None:
        print(text)
        if self.gui is not None and hasattr(self.gui, "update_status"):
            try:
                self.gui.update_status(text)
            except Exception:
                pass

    def _register_hotkeys_from_config(self) -> None:
        if self.config_manager is None:
            self.config_manager = ConfigManager()

        reset = getattr(self.hotkey_manager, "reset_hotkeys", None)
        if callable(reset):
            reset()
        else:
            self.hotkey_manager.registered_hotkeys = []
            self.hotkey_manager.active_modifiers = set()

        press_hotkey = self.config_manager.get("press_hotkey")
        toggle_hotkey = self.config_manager.get("toggle_hotkey")

        if press_hotkey:
            self.hotkey_manager.register_press_hotkey(
                hotkey=press_hotkey,
                start_callback=self.start_recording,
                stop_callback=self.stop_recording,
            )

        if toggle_hotkey:
            self.hotkey_manager.register_toggle_hotkey(
                hotkey=toggle_hotkey,
                toggle_callback=self.toggle_recording,
            )

    def reload_hotkeys(self) -> None:
        self._register_hotkeys_from_config()

    def start_listening_hotkey(self) -> None:
        def hotkey_thread() -> None:
            self._register_hotkeys_from_config()
            self.hotkey_manager.start_listening()

        threading.Thread(target=hotkey_thread, daemon=True).start()

    def start_recording(self) -> None:
        try:
            if getattr(self.audio_recorder, "is_recording", False):
                return
            self._set_status("录音中…")
            self.audio_recorder.start_recording()
        except Exception as e:
            self._set_status(f"开始录音失败：{e}")

    def stop_recording(self) -> None:
        try:
            if not getattr(self.audio_recorder, "is_recording", False):
                return

            self._set_status("停止录音…")
            audio_data = self.audio_recorder.stop_recording()
            if not audio_data:
                self._set_status("没有录制到音频数据")
                return

            threading.Thread(
                target=self._handle_voice_input_worker,
                args=(audio_data,),
                daemon=True,
            ).start()
        except Exception as e:
            self._set_status(f"停止录音失败：{e}")

    def toggle_recording(self) -> None:
        if getattr(self.audio_recorder, "is_recording", False):
            self.stop_recording()
        else:
            self.start_recording()

    def _handle_voice_input_worker(self, audio_data: bytes) -> None:
        with self._processing_lock:
            if self._is_processing:
                return
            self._is_processing = True

        try:
            self._set_status("转写中…")
            self._ensure_stt_ready()

            text = self.stt_processor.transcribe(audio_data)
            print("文本转写结果:", text)

            self._set_status("写入中…")
            self.write_appname_to_cursor(text)
        except Exception as e:
            self._set_status(f"转写/写入失败：{e}")
        finally:
            self._set_status("就绪")
            with self._processing_lock:
                self._is_processing = False

    def run(self) -> None:
        print(f"🚀 {self.app_name} 启动中...")

        # 1) 启动后初始化 VoiceInputGUI
        self.gui = VoiceInputGUI(self, app_name=self.app_name)

        # 1.1) 启动系统托盘（若可用）
        if self.tray_icon is not None:
            try:
                self.tray_icon.start()
            except Exception:
                pass

        # 2) 加载 config 文件（复用 GUI 的 ConfigManager，避免重复读文件）
        if getattr(self.gui, "config_manager", None) is not None:
            self.config_manager = self.gui.config_manager
        elif self.config_manager is None:
            self.config_manager = ConfigManager()

        # 3) 异步线程加载 stt 对象
        # 4) 同时异步线程启动热键监听
        if getattr(self.gui, "root", None) is not None:
            self.gui.root.after(0, self.init_stt_async)
            self.gui.root.after(0, self.start_listening_hotkey)
        else:
            self.init_stt_async()
            self.start_listening_hotkey()

        self.gui.run()

    def write_appname_to_cursor(self, voice_input :str ) -> None:
        """
        将当前窗口的 appname 写入光标所在位置
        """
        if not voice_input:
            print("无法获取窗口信息，无法写入 app_name")
            return

        print("写入应用名称:", voice_input)

        try:
            import pyperclip
            import subprocess
            pyperclip.copy(voice_input)
            subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to keystroke "v" using {command down}'])
            print("✅ 粘贴成功")
            return
        except ImportError:
            print("⚠️ 未安装 pyperclip，尝试其他方式")
        except Exception as e:
            print("⚠️ 粘贴失败:", e)

        try:
            import pyautogui
            pyautogui.write(voice_input, interval=0.01)
            print("✅ 直接输入成功")
        except ImportError:
            print("⚠️ 未安装 pyautogui")
        except Exception as e:
            print("❌ 所有输入方案均失败:", e)

    def minimize_to_tray(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.start()
            except Exception:
                pass

        if self.gui is not None and hasattr(self.gui, "minimize_to_tray"):
            try:
                self.gui.minimize_to_tray()
            except Exception:
                pass

    def restore_from_tray(self) -> None:
        if self.gui is not None and hasattr(self.gui, "restore_from_tray"):
            try:
                self.gui.restore_from_tray()
            except Exception:
                pass

    def exit_application(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        if self.gui is None or getattr(self.gui, "root", None) is None:
            return

        def _quit() -> None:
            try:
                self.gui.root.quit()
            finally:
                try:
                    self.gui.root.destroy()
                except Exception:
                    pass

        try:
            self.gui.root.after(0, _quit)
        except Exception:
            _quit()

if __name__ == "__main__":
    app = TypelessApp()
    app.run()