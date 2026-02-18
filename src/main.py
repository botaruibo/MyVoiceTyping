#!/usr/bin/env python3
"""
TypelessApp 类 - 无界输入法核心应用
"""
import os
import sys
import time
import threading
import subprocess

"""/**
 * 兜底记录应用启动时间戳（秒）。
 *
 * 说明：
 * - 正常情况下由 `run.py` 最早写入该环境变量。
 * - 若用户直接运行 `python -m src.main` 或直接运行本文件，也保证存在该变量。
 */"""
os.environ.setdefault("MYVOICEINPUT_APP_START_TS", str(time.time()))

# from .core import STTProcessor, get_rewriter, WindowInfo
# from .components.audio_recorder import AudioRecorder
# from .components.hotkey_manager import HotkeyManager
# try:
#     from .components.tray_icon import TrayIcon
# except Exception as e:
#     print(f"⚠️ TrayIcon 加载失败，将禁用状态栏图标：{e}")
#     TrayIcon = None
from .utils.config_manager import ConfigManager
# from .gui_tk import VoiceInputGUI

class FlashInputApp:
    def __init__(self):
        self.app_name = "闪电输入法"
        self.config_manager = None

        self.audio_recorder = None
        self.stt_processor = None
        self.rewriter = None
        self.window_info = None
        self.hotkey_manager = None
        self.tray_icon = None

        self._stt_ready = threading.Event()
        self._stt_init_lock = threading.Lock()
        self._stt_init_error = None

        self._speaker_state_lock = threading.Lock()
        self._speaker_prev_settings = None

        self.gui = None
        self._processing_lock = threading.Lock()
        self._is_processing = False

        self._post_gui_load_started = False
        self._post_gui_load_lock = threading.Lock()

    def on_gui_ready(self) -> None:
        """/**
         * GUI 首次渲染完成后的回调（由 VoiceInputGUI 触发）。
         *
         * 设计目标：
         * - 必须快速返回，不能阻塞 Tk 主线程。
         * - 所有重型初始化（模型/Quartz/音频/联网/系统钩子等）都应在这里之后启动。
         *
         * @returns {void}
         */"""

        with self._post_gui_load_lock:
            if self._post_gui_load_started:
                return
            self._post_gui_load_started = True

        print("🪟 GUI 已就绪，开始后加载初始化（异步）")

        self._start_post_gui_load_async()

        try:
            self._init_tray_icon_safe()
        except Exception as e:
            print(f"⚠️ 后加载启动托盘失败（可忽略）: {e}")

        try:
            self.init_stt_async()
        except Exception as e:
            print(f"⚠️ 后加载启动 STT 初始化失败（可忽略）: {e}")

        try:
            self.start_listening_hotkey()
        except Exception as e:
            print(f"⚠️ 后加载启动热键监听失败（可忽略）: {e}")

    def _start_post_gui_load_async(self) -> None:
        """/**
         * 启动后加载线程：初始化重型对象。
         *
         * @returns {void}
         */"""

        def _worker() -> None:
            try:
                self._set_status("后加载初始化中…")

                if self.config_manager is None:
                    self.config_manager = ConfigManager()

                try:
                    from .core.text_rewrite import get_rewriter

                    self.rewriter = get_rewriter()
                    if bool(self.config_manager.get("FORMAT_TEXT")):
                        self.rewriter.init_remote_llm_async(reason="post_gui_load")
                except Exception as e:
                    self.rewriter = None
                    print(f"⚠️ 初始化 rewriter 失败（将降级为不改写）: {e}")

                try:
                    from .core.window_info import WindowInfo

                    self.window_info = WindowInfo()
                except Exception as e:
                    self.window_info = None
                    print(f"⚠️ 初始化 WindowInfo 失败（可能影响窗口信息/光标定位）: {e}")

                try:
                    from .components.audio_recorder import AudioRecorder

                    self.audio_recorder = AudioRecorder()
                except Exception as e:
                    self.audio_recorder = None
                    print(f"⚠️ 初始化 AudioRecorder 失败（将导致无法录音）: {e}")

                try:
                    if self.hotkey_manager is None:
                        from .components.hotkey_manager import HotkeyManager

                        self.hotkey_manager = HotkeyManager()
                except Exception as e:
                    self.hotkey_manager = None
                    print(f"⚠️ 初始化 HotkeyManager 失败（将导致无法使用热键）: {e}")

                self._set_status("就绪")
                print("✅ 后加载初始化完成")
            except Exception as e:
                print(f"❌ 后加载初始化异常: {e}")
                self._set_status(f"后加载初始化失败：{e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _init_tray_icon_safe(self) -> None:
        """/**
         * 初始化并启动托盘图标（若依赖可用）。
         *
         * 说明：
         * - 托盘属于可选能力；失败不应影响主流程。
         * - 放在 GUI 就绪后执行，避免启动阶段导入 PIL/pystray 影响首屏速度。
         *
         * @returns {void}
         */"""

        if self.tray_icon is not None:
            return

        try:
            from .components.tray_icon import TrayIcon

            self.tray_icon = TrayIcon(on_show=self.restore_from_tray, on_quit=self.exit_application, title=self.app_name)
        except Exception as e:
            self.tray_icon = None
            print(f"⚠️ TrayIcon 加载失败，将禁用状态栏图标：{e}")
            return

        try:
            self.tray_icon.start()
        except Exception as e:
            print(f"⚠️ 启动托盘失败：{e}")

    def init_stt_async(self) -> None:
        def _worker() -> None:
            with self._stt_init_lock:
                if self.stt_processor is not None:
                    return
                try:
                    self._set_status("正在初始化语音模型…")

                    from .core.stt_processor import STTProcessor

                    self.stt_processor = STTProcessor()

                    """/**
                     * 统计：应用启动 -> STTProcessor 初始化完成耗时。
                     *
                     * 说明：
                     * - 使用 `run.py` / `src/main.py` 写入的 `MYVOICEINPUT_APP_START_TS`。
                     */"""
                    elapsed_s = None
                    try:
                        start_ts_str = os.environ.get("MYVOICEINPUT_APP_START_TS", "")
                        start_ts = float(start_ts_str) if start_ts_str else None
                        if start_ts is not None:
                            elapsed_s = time.time() - start_ts
                    except Exception as e:
                        print(f"⚠️ 启动耗时统计失败（可忽略）: {e}")

                    if elapsed_s is not None:
                        print(f"✅ STT 初始化完成，耗时 {elapsed_s:.2f}s（从应用启动算起）")
                    # ---------------
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

    def _ensure_audio_recorder(self) -> None:
        """/**
         * 确保 AudioRecorder 已初始化（按需延迟创建）。
         *
         * @returns {void}
         */"""
        if self.audio_recorder is not None:
            return
        from .components.audio_recorder import AudioRecorder
        self.audio_recorder = AudioRecorder()

    def _get_rewriter_safe(self):
        """/**
         * 获取 rewriter（按需延迟创建）。
         *
         * @returns {Rewrite | null}
         */"""
        if self.rewriter is not None:
            return self.rewriter
        try:
            from .core.text_rewrite import get_rewriter
            self.rewriter = get_rewriter()
            if self.config_manager is not None and bool(self.config_manager.get("FORMAT_TEXT")):
                self.rewriter.init_remote_llm_async(reason="lazy_get")
            return self.rewriter
        except Exception as e:
            print(f"⚠️ 获取 rewriter 失败（将降级为不改写）: {e}")
            self.rewriter = None
            return None

    def _register_hotkeys_from_config(self) -> None:
        if self.config_manager is None:
            self.config_manager = ConfigManager()

        if self.hotkey_manager is None:
            from .components.hotkey_manager import HotkeyManager
            self.hotkey_manager = HotkeyManager()

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

    def _osascript(self, script: str) -> str:
        """
        /**
         * 执行 AppleScript（仅 macOS）。
         *
         * @param script AppleScript 语句
         * @returns {str} 标准输出（去除首尾空白）
         * @throws {RuntimeError} 执行失败
         */
        """

        if sys.platform != "darwin":
            raise RuntimeError("当前系统非 macOS，无法执行 osascript")

        try:
            proc = subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
            return (proc.stdout or "").strip()
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            raise RuntimeError(f"osascript 执行失败: {stderr}") from e

    def _windows_waveout_get_volume(self) -> int:
        """
        /**
         * Windows：读取 waveOut 音量（左右声道各 16-bit，打包为 32-bit）。
         *
         * 说明：
         * - 这是一个“系统级”音量接口（更接近旧式 waveOut 设备）。
         * - 优点：不需要额外 pip 依赖；缺点：与新式应用的每应用音量不完全等价。
         * - 对“录音期间静音外放”场景足够实用。
         *
         * @returns {number} packed_volume
         * @throws {RuntimeError} 获取失败
         */
        """

        import ctypes
        from ctypes import wintypes

        winmm = ctypes.WinDLL("winmm")
        wave_out_get_volume = winmm.waveOutGetVolume
        wave_out_get_volume.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        wave_out_get_volume.restype = wintypes.UINT

        volume = wintypes.DWORD(0)

        # 优先使用 WAVE_MAPPER(-1)，失败再尝试 0
        for hwo in (ctypes.c_void_p(-1), ctypes.c_void_p(0)):
            rc = wave_out_get_volume(hwo, ctypes.byref(volume))
            if rc == 0:
                return int(volume.value)

        raise RuntimeError(f"waveOutGetVolume 失败，错误码: {rc}")

    def _windows_waveout_set_volume(self, packed_volume: int) -> None:
        """
        /**
         * Windows：设置 waveOut 音量。
         *
         * @param packed_volume 32-bit packed volume
         * @returns {void}
         * @throws {RuntimeError} 设置失败
         */
        """

        import ctypes
        from ctypes import wintypes

        winmm = ctypes.WinDLL("winmm")
        wave_out_set_volume = winmm.waveOutSetVolume
        wave_out_set_volume.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        wave_out_set_volume.restype = wintypes.UINT

        packed = wintypes.DWORD(int(packed_volume) & 0xFFFFFFFF)

        for hwo in (ctypes.c_void_p(-1), ctypes.c_void_p(0)):
            rc = wave_out_set_volume(hwo, packed)
            if rc == 0:
                return

        raise RuntimeError(f"waveOutSetVolume 失败，错误码: {rc}")

    def _macos_get_volume_settings(self) -> dict:
        """
        /**
         * macOS：一次 osascript 获取 output volume/output muted。
         *
         * 说明：
         * - `get volume settings` 返回形如：
         *   `output volume:50, input volume:75, alert volume:100, output muted:false`
         * - 这里用单次 subprocess 调用，减少热键触发后的阻塞时间。
         *
         * @returns {{output_volume: number, output_muted: boolean}} 当前外放设置
         */
        """

        raw = self._osascript("get volume settings")
        text = (raw or "").strip()

        output_volume = 0
        output_muted = False

        try:
            parts = [p.strip() for p in text.split(",") if p.strip()]
            for p in parts:
                if p.startswith("output volume:"):
                    output_volume = int(p.split(":", 1)[1].strip() or "0")
                elif p.startswith("output muted:"):
                    output_muted = p.split(":", 1)[1].strip().lower() == "true"
        except Exception:
            output_volume = 0
            output_muted = False

        return {"output_volume": output_volume, "output_muted": output_muted}

    def _macos_get_settings_and_mute(self) -> dict:
        """
        /**
         * macOS：单次 osascript 完成“读取当前外放设置 + 静音”。
         *
         * 性能收益：
         * - 将原本多次 `osascript` 子进程调用合并为一次，显著降低按键到静音的延迟。
         *
         * @returns {{platform: string, output_volume: number, output_muted: boolean}} 静音前的外放设置
         */
        """

        script = (
            "set v to get volume settings\n"
            "set oldVol to output volume of v\n"
            "set oldMuted to output muted of v\n"
            "set volume with output muted\n"
            "return (oldVol as string) & \",\" & (oldMuted as string)"
        )
        out = self._osascript(script)

        parts = (out.split(",", 1) + [""])[:2]
        vol_str = (parts[0] or "0").strip()
        muted_str = (parts[1] or "false").strip()

        try:
            vol = int(vol_str)
        except Exception:
            vol = 0

        muted = muted_str.lower() == "true"

        return {"platform": "darwin", "output_volume": vol, "output_muted": muted}

    def _macos_restore_speaker_settings(self, output_volume: int, output_muted: bool) -> None:
        """
        /**
         * macOS：单次 osascript 完成“恢复音量 + 恢复静音状态”。
         *
         * 说明：
         * - 把原先多次 `osascript` 调用合并为一次。
         *
         * @param output_volume 音量 0~100
         * @param output_muted 是否静音
         * @returns {void}
         */
        """

        vol = int(max(0, min(100, int(output_volume))))
        muted = bool(output_muted)
        muted_literal = "true" if muted else "false"

        script = (
            f"set volume output volume {vol}\n"
            f"if {muted_literal} then\n"
            "  set volume with output muted\n"
            "else\n"
            "  set volume without output muted\n"
            "end if\n"
        )
        self._osascript(script)

    def _get_speaker_settings(self) -> dict:
        """
        /**
         * 获取系统外放设置（音量/静音）。
         *
         * - macOS：使用 AppleScript 获取 output volume/output muted
         * - Windows：使用 waveOutGetVolume 获取 packed volume（并推算一个 0~100 的近似音量）
         *
         * @returns {object} 当前外放设置（含 platform 字段）
         */
        """

        if sys.platform == "darwin":
            s = self._macos_get_volume_settings()
            return {"platform": "darwin", "output_volume": s["output_volume"], "output_muted": s["output_muted"]}

        if sys.platform == "win32":
            packed = self._windows_waveout_get_volume()
            left = packed & 0xFFFF
            right = (packed >> 16) & 0xFFFF
            avg = int((left + right) / 2)
            approx_volume = int(round(avg / 0xFFFF * 100)) if avg > 0 else 0
            approx_muted = left == 0 and right == 0
            return {
                "platform": "win32",
                "waveout_volume": packed,
                "output_volume": approx_volume,
                "output_muted": approx_muted,
            }

        return {"platform": sys.platform, "supported": False}

    def _set_speaker_settings(self, output_volume: int, output_muted: bool) -> None:
        """
        /**
         * 设置系统外放设置（音量/静音）。
         *
         * - macOS：通过 AppleScript 设置音量/静音
         * - Windows：通过 waveOutSetVolume 设置音量（output_muted=true 时设为 0）
         *
         * @param output_volume 音量 0~100
         * @param output_muted 是否静音
         * @returns {void}
         */
        """

        vol = int(max(0, min(100, int(output_volume))))

        if sys.platform == "darwin":
            muted_literal = "true" if bool(output_muted) else "false"
            script = (
                f"set volume output volume {vol}\n"
                f"if {muted_literal} then\n"
                "  set volume with output muted\n"
                "else\n"
                "  set volume without output muted\n"
                "end if\n"
            )
            self._osascript(script)
            return

        if sys.platform == "win32":
            if output_muted:
                self._windows_waveout_set_volume(0)
                return

            level = int(round(vol / 100 * 0xFFFF))
            packed = (level & 0xFFFF) | ((level & 0xFFFF) << 16)
            self._windows_waveout_set_volume(packed)
            return

        raise RuntimeError(f"当前系统不支持设置外放音量/静音: {sys.platform}")

    def _is_mute_speaker_enabled(self) -> bool:
        """
        /**
         * 判断是否启用录音期间静音外放。
         *
         * 配置项：`mute_speaker`
         *
         * @returns {boolean} 是否启用
         */
        """

        if self.config_manager is None:
            self.config_manager = ConfigManager()

        try:
            return bool(self.config_manager.get("mute_speaker", False))
        except Exception:
            return False

    def _maybe_mute_speaker_before_recording(self) -> None:
        """
        /**
         * 录音开始前：如果配置允许，则静音系统外放，并缓存原始设置。
         *
         * @returns {void}
         */
        """

        if not self._is_mute_speaker_enabled():
            return

        # 仅支持 macOS/Windows
        if sys.platform not in ("darwin", "win32"):
            return

        with self._speaker_state_lock:
            if self._speaker_prev_settings is not None:
                return

            try:
                if sys.platform == "darwin":
                    prev = self._macos_get_settings_and_mute()
                    self._speaker_prev_settings = prev
                    print("🔇 已静音系统外放（macOS 单次 osascript）")
                    return

                # Windows
                prev = self._get_speaker_settings()
                if not isinstance(prev, dict) or prev.get("supported") is False:
                    print(f"⚠️ 当前系统不支持静音外放（platform={sys.platform}），已跳过")
                    self._speaker_prev_settings = None
                    return

                self._speaker_prev_settings = prev
                self._set_speaker_settings(prev.get("output_volume", 0), True)
                print("🔇 已静音系统外放（Windows waveOut）")
            except Exception as e:
                self._speaker_prev_settings = None
                print(f"⚠️ 静音系统外放失败（已跳过，不影响录音）: {e}")

    def _maybe_restore_speaker_after_recording(self) -> None:
        """
        /**
         * 录音结束后：如果此前做过静音，则恢复系统外放设置。
         *
         * @returns {void}
         */
        """

        # 仅支持 macOS/Windows
        if sys.platform not in ("darwin", "win32"):
            return

        with self._speaker_state_lock:
            prev = self._speaker_prev_settings
            self._speaker_prev_settings = None

        if not isinstance(prev, dict) or prev.get("supported") is False:
            return

        try:
            if prev.get("platform") == "win32" and "waveout_volume" in prev:
                self._windows_waveout_set_volume(int(prev["waveout_volume"]))
            elif prev.get("platform") == "darwin":
                self._macos_restore_speaker_settings(
                    output_volume=prev.get("output_volume", 0),
                    output_muted=bool(prev.get("output_muted", False)),
                )
            else:
                self._set_speaker_settings(
                    output_volume=prev.get("output_volume", 0),
                    output_muted=bool(prev.get("output_muted", False)),
                )

            print(f"🔊 已恢复系统外放（录音结束后，platform={prev.get('platform')}）")
        except Exception as e:
            print(f"⚠️ 恢复系统外放失败（可忽略）: {e}")

    def _set_status(self, text: str) -> None:
        print(text)

        gui = self.gui
        if gui is None:
            return

        update_status = getattr(gui, "update_status", None)
        if not callable(update_status):
            return

        post_ui = getattr(gui, "post_ui", None)
        if callable(post_ui):
            try:
                post_ui(update_status, text)
                return
            except Exception:
                pass

        try:
            update_status(text)
        except Exception:
            pass

    def start_recording(self) -> None:
        try:
            self._ensure_audio_recorder()

            if getattr(self.audio_recorder, "is_recording", False):
                return

            try:
                if self.gui is not None and hasattr(self.gui, "show_recording_overlay"):
                    post_ui = getattr(self.gui, "post_ui", None)
                    if callable(post_ui):
                        post_ui(self.gui.show_recording_overlay, "录音中…")
                    else:
                        self.gui.show_recording_overlay("录音中…")
            except Exception as e:
                print(f"⚠️ 显示录音提示框失败（可忽略）: {e}")

            self._maybe_mute_speaker_before_recording()

            self._set_status("录音中…")
            self.audio_recorder.start_recording()
        except Exception as e:
            try:
                self._maybe_restore_speaker_after_recording()
            except Exception:
                pass
            self._set_status(f"开始录音失败：{e}")

    def stop_recording(self) -> None:
        audio_data = b""

        try:
            if not getattr(self.audio_recorder, "is_recording", False):
                return

            self._set_status("停止录音…")
            audio_data = self.audio_recorder.stop_recording()
        except Exception as e:
            self._set_status(f"停止录音失败：{e}")
            return
        finally:
            try:
                if self.gui is not None and hasattr(self.gui, "hide_recording_overlay"):
                    post_ui = getattr(self.gui, "post_ui", None)
                    if callable(post_ui):
                        post_ui(self.gui.hide_recording_overlay)
                    else:
                        self.gui.hide_recording_overlay()
            except Exception as e:
                print(f"⚠️ 隐藏录音提示框失败（可忽略）: {e}")

            # 无论停止录音是否成功，都尽力恢复外放（避免一直静音
            try:
                self._maybe_restore_speaker_after_recording()
            except Exception:
                pass

        if not audio_data:
            self._set_status("没有录制到音频数据")
            return

        try:
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
            time_start = time.time()
            self._ensure_stt_ready()
            print(f"STT 初始化耗时 {time.time() - time_start:.2f}s（从处理开始算起）")
            trans_time = time.time()
            text = self.stt_processor.transcribe(audio_data)
            print("文本转写结果:", text)
            print(f"转录耗时 {time.time() - trans_time:.2f}s（从处理开始算起）")

            """/**
             * 转写后可选的文本改写（LLM）。
             *
             * 说明：
             * - 这里不能假设 `self.rewriter` 一定已完成初始化；GUI 就绪后的后加载是异步的。
             * - 若改写失败/rewriter 不可用，必须降级为原始转写文本，不能影响“写入”主流程。
             */"""
            if not text:
                print("ℹ️ 转写结果为空，跳过改写")
            else:
                try:
                    if self.config_manager is None:
                        self.config_manager = ConfigManager()

                    if bool(self.config_manager.get("FORMAT_TEXT")):
                        self._set_status("改写中…")
                        rewriter = self._get_rewriter_safe()
                        if rewriter is None:
                            print("⚠️ rewriter 不可用，跳过改写")
                        else:
                            rewrite_time = time.time()
                            text = rewriter.rewrite(text)
                            print(f"llm 远程改写耗时 {time.time() - rewrite_time:.2f}s")
                            print(f"✅ 格式化后的文本: {text}")
                    else:
                        print("ℹ️ FORMAT_TEXT 未开启，跳过改写")
                except Exception as e:
                    print(f"⚠️ 文本改写失败（将使用原转写结果）: {e}")

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

        try:
            from .gui_tk import VoiceInputGUI
        except Exception as e:
            print(f"❌ GUI 模块加载失败：{e}")
            raise

        # 1) 启动后初始化 VoiceInputGUI
        self.gui = VoiceInputGUI(self, app_name=self.app_name)

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

    def open_home_page(self) -> None:
        """
        打开主页（供托盘菜单调用）。
        行为：恢复窗口 + 切换到“home”页面。
        @returns None
        """
        print("📌 收到打开主页请求（来自托盘）")

        if self.gui is None or getattr(self.gui, "root", None) is None:
            print("⚠️ GUI 尚未初始化，无法打开主页")
            return

        def _do() -> None:
            try:
                self.gui.restore_from_tray()
            except Exception as e:
                print(f"⚠️ 恢复窗口失败：{e}")

            try:
                # gui_tk.py 里 nav_buttons 已包含 ("主页", "home")
                self.gui.show_page("home")
            except Exception as e:
                print(f"⚠️ 切换到主页失败：{e}")

        try:
            post_ui = getattr(self.gui, "post_ui", None)
            if callable(post_ui):
                post_ui(_do)
            else:
                self.gui.root.after(0, _do)
        except Exception:
            _do()

    def write_appname_to_cursor(self, voice_input: str) -> None:
        """
        /**
         * 将转写/改写后的文本写入到当前光标所在位置。
         *
         * 说明：
         * - 该方法可能运行在后台线程（转写线程），不得触碰 Tk UI。
         * - macOS 下优先使用“写入剪贴板 + 系统粘贴（Cmd+V）”，更稳定且支持中文。
         * - 若剪贴板/粘贴不可用，再回退到逐字输入。
         *
         * @param {string} voice_input - 需要写入的文本。
         * @returns {void}
         */
        """
        if not voice_input:
            print("⚠️ 写入文本为空，跳过写入")
            return

        text = str(voice_input)
        print(f"📝 准备写入文本（长度={len(text)}）")

        # macOS：剪贴板 + Cmd+V
        if sys.platform == "darwin":
            pasted = False

            # 方案 A：pyperclip
            try:
                import pyperclip

                pyperclip.copy(text)
                print("✅ 已写入剪贴板（pyperclip）")

                try:
                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            'tell application "System Events" to keystroke "v" using {command down}',
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print("✅ 已触发系统粘贴（Cmd+V）")
                    pasted = True
                except Exception as e:
                    print(f"⚠️ 系统粘贴失败（将尝试 pbcopy 方案）: {e}")

            except Exception as e:
                print(f"⚠️ pyperclip 不可用（将尝试 pbcopy 方案）: {e}")

            # 方案 B：pbcopy
            if not pasted:
                try:
                    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    try:
                        proc.communicate(input=text.encode("utf-8"), timeout=2)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        raise

                    if proc.returncode not in (0, None):
                        raise RuntimeError(f"pbcopy 返回码异常: {proc.returncode}")

                    print("✅ 已写入剪贴板（pbcopy）")

                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            'tell application "System Events" to keystroke "v" using {command down}',
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print("✅ 已触发系统粘贴（Cmd+V）")
                    pasted = True
                except Exception as e:
                    print(f"⚠️ pbcopy 方案失败（将回退逐字输入）: {e}")

            if pasted:
                return

        # 兜底：逐字输入
        try:
            import pyautogui

            pyautogui.write(text, interval=0.01)
            print("✅ 已逐字输入完成（pyautogui）")
        except Exception as e:
            print(f"❌ 写入失败：所有输入方案均失败: {e}")

    def minimize_to_tray(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.start()
            except Exception:
                pass

        if self.gui is not None and hasattr(self.gui, "minimize_to_tray"):
            try:
                post_ui = getattr(self.gui, "post_ui", None)
                if callable(post_ui):
                    post_ui(self.gui.minimize_to_tray)
                else:
                    self.gui.minimize_to_tray()
            except Exception:
                pass

    def restore_from_tray(self) -> None:
        if self.gui is not None and hasattr(self.gui, "restore_from_tray"):
            try:
                post_ui = getattr(self.gui, "post_ui", None)
                if callable(post_ui):
                    post_ui(self.gui.restore_from_tray)
                else:
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
            post_ui = getattr(self.gui, "post_ui", None)
            if callable(post_ui):
                post_ui(_quit)
            else:
                self.gui.root.after(0, _quit)
        except Exception:
            _quit()

if __name__ == "__main__":
    app = FlashInputApp()
    app.run()