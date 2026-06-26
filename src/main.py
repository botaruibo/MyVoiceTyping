#!/usr/bin/env python3
"""
TypelessApp 类 - 无界输入法核心应用
"""
import os
import sys
import time
import json
import threading
import subprocess
from datetime import datetime
from pathlib import Path

"""/**
 * 兜底记录应用启动时间戳（秒）。
 *
 * 说明：
 * - 正常情况下由 `run.py` 最早写入该环境变量。
 * - 若用户直接运行 `python -m src.main` 或直接运行本文件，也保证存在该变量。
 */"""
os.environ.setdefault("MYVOICETYPING_APP_START_TS", str(time.time()))

from .components.config_manager import get_config_manager

class FlashInputApp:
    def __init__(self):
        self.app_name = "MyVoiceTyping"
        # 状态栏应用实例
        self.status_bar_app = None
        self.config_manager = None

        self.audio_recorder = None
        self.stt_processor = None
        self.rewriter = None

        self.hotkey = None

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

        self._model_bootstrap_started = False
        self._model_bootstrap_lock = threading.Lock()

    def on_gui_ready(self) -> None:
        """/**
         * GUI 首次渲染完成后的回调（由 VoiceInputGUI 触发）。
         *
         * 设计目标：
         * - 必须快速返回，不能阻塞 Tk 主线程。
         * - 重型初始化统一放到后台线程中执行。
         *
         * @returns {void}
         */"""
        with self._post_gui_load_lock:
            if self._post_gui_load_started:
                return
            self._post_gui_load_started = True

        print("🪟 GUI 已就绪，开始后加载初始化（异步）")
        self._start_post_gui_load_async()


    def _start_post_gui_load_async(self) -> None:
        """/**
         * 启动后加载线程：统一初始化重型对象，并启动后台服务。
         *
         * 统一入口的好处：
         * - 避免 on_gui_ready 与本方法重复做同一件事。
         * - 便于统一做异常兜底与日志。
         *
         * @returns {void}
         */"""
        def _worker() -> None:
            t0 = time.perf_counter()
            print(f"----异步gui后初始化开始：{t0:0.2f}")
            try:
                self._set_status("后加载初始化中…")

                if self.config_manager is None:
                    self.config_manager = get_config_manager()

                try:
                    from .core.text_rewrite import get_rewriter

                    # 仅创建轻量 rewriter 实例；本地模型的下载与预加载统一由
                    # start_model_bootstrap -> _preload_local_rewriter 处理。
                    self.rewriter = get_rewriter()
                except Exception as e:
                    self.rewriter = None
                    print(f"⚠️ 初始化 rewriter 失败（将降级为不改写）: {e}")

                try:
                    from .components.audio_recorder import AudioRecorder

                    self.audio_recorder = AudioRecorder()
                except Exception as e:
                    self.audio_recorder = None
                    print(f"⚠️ 初始化 AudioRecorder 失败（将导致无法录音）: {e}")

                # 新hotkey注册
                if self.hotkey is None:
                    from .components.hotkey import UniversalKeyListener, ShortcutDetector
                    listener = UniversalKeyListener()
                    self.hotkey = ShortcutDetector(listener)

                self._set_status("就绪")
                print(f"✅ 后加载初始化完成,耗时:{time.perf_counter()-t0:0.2f}")
            except Exception as e:
                print(f"❌ 后加载初始化异常: {e}")
                self._set_status(f"后加载初始化失败：{e}", is_error=True)

        threading.Thread(target=_worker, daemon=True).start()


    def start_model_bootstrap(self) -> None:
        """/**
         * 启动时集中检查并按需下载全部本地模型（仅下载，不加载到内存）。
         *
         * 覆盖 3 个模型：
         * - 语音转录：SenseVoiceSmall-onnx
         * - 标点恢复：punc_ct-onnx
         * - 文本纠错：本地 GGUF 中文纠错模型（仅当 format_text 开启且使用 llama.cpp provider 时）
         *
         * 下载完成后再触发 STT 加载与本地改写模型预加载，避免两个线程同时
         * 下载同一目录造成竞争。
         *
         * @returns {void}
         */"""
        with self._model_bootstrap_lock:
            if self._model_bootstrap_started:
                return
            self._model_bootstrap_started = True

        def _worker() -> None:
            try:
                if self.config_manager is None:
                    self.config_manager = get_config_manager()

                self._set_status("正在检查本地模型…")

                from .core.stt_local_processor import (
                    STT_MODEL_ID,
                    PUNC_MODEL_ID,
                    is_model_downloaded,
                    ensure_model_files,
                )

                for label, model_id in (
                    ("语音转录", STT_MODEL_ID),
                    ("标点恢复", PUNC_MODEL_ID),
                ):
                    try:
                        if is_model_downloaded(model_id):
                            print(f"✅ {label}模型已存在: {model_id}")
                            continue
                        self._set_status(f"正在下载{label}模型…")
                        ensure_model_files(model_id)
                    except Exception as e:
                        print(f"⚠️ {label}模型检查/下载失败: {e}")

                # 文本纠错模型：语音模型完成后再检查；是否预加载仍由 format_text 控制。
                provider = self.config_manager.get("LLM_TEXT_PROVIDER")
                if provider in {"llama_cpp", "local_llama_cpp", "gguf"}:
                    try:
                        from .core.text_rewrite import LocalLlamaCppRewrite

                        self._set_status("正在检查文本纠错模型…")
                        # ensure_model_downloaded 内部已做存在性判断，存在则跳过
                        LocalLlamaCppRewrite().ensure_model_downloaded()
                        print("✅ 文本纠错模型已就绪")
                    except Exception as e:
                        print(f"⚠️ 文本纠错模型检查/下载失败: {e}")

                self._set_status("本地模型检查完成")
            except Exception as e:
                print(f"❌ 模型检查/下载流程异常: {e}")
            finally:
                # 下载就绪后再触发加载与预加载（在各自的异步方法里完成）
                try:
                    if bool(self.config_manager.get("preload_stt_on_startup", True)):
                        self.init_stt_async()
                except Exception as e:
                    print(f"⚠️ 触发 STT 预加载失败: {e}")
                try:
                    self._preload_local_rewriter()
                except Exception as e:
                    print(f"⚠️ 触发本地改写模型预加载失败: {e}")

        threading.Thread(target=_worker, daemon=True).start()


    def _preload_local_rewriter(self) -> None:
        """/**
         * 按当前 provider 预加载本地改写所需的 LLM 模型。
         *
         * 与 STT 预加载对称：把模型加载/预热成本吸收到启动期。
         * 仅在开启 format_text 且使用对应本地 provider 时触发。
         *
         * @returns {void}
         */"""
        if self.config_manager is None:
            self.config_manager = get_config_manager()
        if not bool(self.config_manager.get("FORMAT_TEXT")):
            return
        provider = self.config_manager.get("LLM_TEXT_PROVIDER")

        from .core.text_rewrite import get_rewriter

        if self.rewriter is None:
            self.rewriter = get_rewriter()

        if (
            provider in {"llama_cpp", "local_llama_cpp", "gguf"}
            and bool(self.config_manager.get("preload_llama_cpp_on_startup", True))
        ):
            self.rewriter.init_local_llama_cpp_async(reason="model_bootstrap")

    def init_stt_async(self) -> None:
        def _worker() -> None:
            with self._stt_init_lock:
                if self.stt_processor is not None:
                    return
                try:
                    self._set_status("正在初始化语音模型…")
                    t0 = time.perf_counter()
                    print(f"stt-----开始时间：{t0}")
                    from .core.stt_processor import STTProcessor

                    self.stt_processor = STTProcessor()
                    if bool(self.config_manager.get("stt_warmup_on_startup", True)):
                        try:
                            self._set_status("正在预热语音模型…")
                            self.stt_processor.warm_up()
                        except Exception as e:
                            print(f"⚠️ 语音模型预热失败（可忽略）: {e}")
                    print(f"stt-----结束时间：{time.perf_counter()}")
                    """/**
                     * 统计：应用启动 -> STTProcessor 初始化完成耗时。
                     *
                     * 说明：
                     * - 使用 `run.py` / `src/main.py` 写入的 `MYVOICETYPING_APP_START_TS`。
                     */"""
                    elapsed_s = None
                    try:
                        start_ts_str = os.environ.get("MYVOICETYPING_APP_START_TS", "")
                        start_ts = float(start_ts_str) if start_ts_str else None
                        if start_ts is not None:
                            elapsed_s = time.time() - start_ts
                    except Exception as e:
                        print(f"⚠️ 启动耗时统计失败（可忽略）: {e}")

                    print(f"✅ STT 初始化完成，耗时 {time.perf_counter() - t0:.2f}s")

                    if elapsed_s is not None:
                        print(f"✅ STT 初始化完成，耗时 {elapsed_s:.2f}s（从应用启动算起）")
                    # ---------------
                    self._set_status("语音模型就绪")
                except Exception as e:
                    self._stt_init_error = e
                    self._set_status(f"语音模型初始化失败：{e}", is_error=True)
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

    def _set_status(self, text: str, is_error: bool = False) -> None:
        print(text)
        if self.gui is not None and hasattr(self.gui, "update_status"):
            try:
                if is_error:
                    self.gui.update_status_error(text)
                else:
                    self.gui.update_status_info(text)
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
            provider = self.config_manager.get("LLM_TEXT_PROVIDER") if self.config_manager is not None else None
            if (
                self.config_manager is not None
                and bool(self.config_manager.get("FORMAT_TEXT"))
                and provider == "cloud_llm"
            ):
                self.rewriter.init_remote_llm_async(reason="lazy_get")
            if (
                self.config_manager is not None
                and bool(self.config_manager.get("FORMAT_TEXT"))
                and provider in {"llama_cpp", "local_llama_cpp", "gguf"}
                and bool(self.config_manager.get("preload_llama_cpp_on_startup", True))
            ):
                self.rewriter.init_local_llama_cpp_async(reason="lazy_get")
            return self.rewriter
        except Exception as e:
            print(f"⚠️ 获取 rewriter 失败（将降级为不改写）: {e}")
            self.rewriter = None
            return None

    @staticmethod
    def _text_char_count(text: str) -> int:
        return len("".join(str(text or "").split()))

    def _record_transcription_history(
        self,
        audio_path: str | None,
        raw_text: str,
        final_text: str,
    ) -> dict | None:
        if self.config_manager is None:
            self.config_manager = get_config_manager()

        transcripts_dir = self.config_manager.get_transcripts_dir()
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        record_id = now.strftime("%Y%m%d_%H%M%S_%f")
        history_path = transcripts_dir / "voice_history.jsonl"
        audio_file_name = Path(audio_path).name if audio_path else f"{record_id}.wav"

        payload = {
            "id": record_id,
            "dataId": audio_file_name,
            "created_at": now.isoformat(timespec="seconds"),
            "audio_path": str(audio_path or ""),
            "raw_text": raw_text or "",
            "final_text": final_text or raw_text or "",
            "char_count": self._text_char_count(final_text or raw_text),
        }

        try:
            with history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            print(f"✅ 已记录转写历史: {history_path}")
        except Exception as e:
            print(f"⚠️ 保存转写历史失败（可忽略）: {e}")
            return None

        try:
            if self.gui is not None and hasattr(self.gui, "notify_transcription_record_added"):
                self.gui.notify_transcription_record_added(payload)
        except Exception as e:
            print(f"⚠️ 通知 GUI 刷新历史失败（可忽略）: {e}")

        return payload

    def _register_hotkeys_from_config(self) -> None:
        # 1. 初始化（如果尚未存在）
        if self.config_manager is None:
            self.config_manager = get_config_manager()

        if self.hotkey is None:
            from .components.hotkey import UniversalKeyListener, ShortcutDetector
            listener = UniversalKeyListener()
            self.hotkey = ShortcutDetector(listener)

        try:
            # 2. 清除旧热键
            reset = getattr(self.hotkey, "reset_hotkeys", None)
            if callable(reset):
                reset()
            else:
                self.hotkey.clear_hotkeys()

            # 3. 注册新热键
            press_hotkey = self.config_manager.get("press_hotkey")

            if press_hotkey:
                self.hotkey.register(press_hotkey,
                                     on_press=self.start_recording,
                                     on_release=self.stop_recording
                                     )

            # 免提模式暂不对外支持：保留 toggle_recording 和 toggle_hotkey 配置，
            # 但不注册热键，避免用户误触发隐藏能力。

        except Exception as e:
            print(f"\n❌ 热键注册错误: {e}")

    def reload_hotkeys(self) -> None:
        print("正在重新加载热键配置...")
        self._register_hotkeys_from_config()

    def start_listening_hotkey(self) -> None:
        def hotkey_thread() -> None:
            # 初始注册
            self._register_hotkeys_from_config()

            # 启动阻塞监听循环
            if self.hotkey and self.hotkey.listener:
                try:
                    self.hotkey.listener.start(blocking=True)
                except PermissionError as e:
                    print(f"\n❌ 权限错误: {e}")
                    from .util.mac_permissions import prompt_permission
                    prompt_permission("input_monitoring")
                except Exception as e:
                    print(f"\n❌ 错误: {e}")
                finally:
                    # 只有在线程退出时才清理
                    if self.hotkey and self.hotkey.listener:
                        self.hotkey.listener.stop()
                    self.hotkey = None

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
         *
         * @returns {object} 当前外放设置（含 platform 字段）
         */
        """

        s = self._macos_get_volume_settings()
        return {"platform": "darwin", "output_volume": s["output_volume"], "output_muted": s["output_muted"]}

    def _set_speaker_settings(self, output_volume: int, output_muted: bool) -> None:
        """
        /**
         * 设置系统外放设置（音量/静音）。
         *
         * - macOS：通过 AppleScript 设置音量/静音
         *
         * @param output_volume 音量 0~100
         * @param output_muted 是否静音
         * @returns {void}
         */
        """

        vol = int(max(0, min(100, int(output_volume))))

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

        with self._speaker_state_lock:
            if self._speaker_prev_settings is not None:
                return

            try:
                prev = self._macos_get_settings_and_mute()
                self._speaker_prev_settings = prev
                print("🔇 已静音系统外放（macOS 单次 osascript）")
                return

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
        with self._speaker_state_lock:
            prev = self._speaker_prev_settings
            self._speaker_prev_settings = None

        if not isinstance(prev, dict) or prev.get("supported") is False:
            return

        try:
            self._macos_restore_speaker_settings(
                output_volume=prev.get("output_volume", 0),
                output_muted=bool(prev.get("output_muted", False)),
            )
            print(f"🔊 已恢复系统外放（录音结束后，platform={prev.get('platform')}）")
        except Exception as e:
            print(f"⚠️ 恢复系统外放失败（可忽略）: {e}")

    def _hide_recording_overlay_safe(self) -> None:
        """
        /**
         * 尽力隐藏录音/转写浮层。
         *
         * 说明：
         * - 用于停止录音失败、无音频数据、开始录音失败等异常分支。
         * - 不能让 UI 清理失败影响主录音状态机。
         *
         * @returns {void}
         */
        """
        try:
            if self.gui is not None and hasattr(self.gui, "hide_recording_overlay"):
                self.gui.hide_recording_overlay()
        except Exception as e:
            print(f"⚠️ 隐藏录音提示框失败（可忽略）: {e}")

    def _is_audio_too_short(self, audio_data: bytes) -> tuple[bool, float, int]:
        """
        判断录音时长是否短到应直接跳过。

        PCM int16 单声道下，字节数只代表采样时长，不代表是否有人声。
        """
        byte_len = len(audio_data) if audio_data else 0
        sample_rate = int(self.config_manager.get("sample_rate", 16000) or 16000)
        min_duration_ms = int(self.config_manager.get("min_audio_duration_ms", 400) or 400)
        duration_ms = (byte_len / 2.0) / max(1, sample_rate) * 1000.0
        return duration_ms < min_duration_ms, duration_ms, min_duration_ms

    def _force_reset_after_stuck(self) -> None:
        """
        /**
         * 兜底复位：当上一次录音/转写流程异常未走完时，强制把所有相关状态
         * 拨回初始值，保证下一次按热键能正常工作。
         *
         * 触发场景：
         * - sounddevice stop 卡住，导致 stop_recording 整链路 hang。
         * - GUI 浮窗未隐藏 / speaker 静音状态未恢复。
         * - _is_processing 因为异常未在 finally 复位。
         */
        """
        # 1. 浮窗
        try:
            self._hide_recording_overlay_safe()
        except Exception:
            pass

        # 2. speaker 静音状态
        try:
            self._maybe_restore_speaker_after_recording()
        except Exception:
            pass
        with self._speaker_state_lock:
            self._speaker_prev_settings = None

        # 3. audio recorder 状态
        try:
            if self.audio_recorder is not None:
                self.audio_recorder.is_recording = False
                self.audio_recorder.record_thread = None
        except Exception:
            pass

        # 4. 处理标记
        with self._processing_lock:
            self._is_processing = False

    def start_recording(self) -> None:
        try:
            self._ensure_audio_recorder()

            # 防御：上一次 stop_recording 卡住时，is_recording 可能仍是 True，
            # 或 record_thread 残留。这里先做一次兜底复位，避免本次按键被吞。
            stuck_thread = getattr(self.audio_recorder, "record_thread", None)
            if getattr(self.audio_recorder, "is_recording", False):
                if stuck_thread is None or not stuck_thread.is_alive():
                    print("⚠️ 检测到 is_recording 残留 True，但录音线程已结束，强制复位")
                    self._force_reset_after_stuck()
                else:
                    # 录音线程还活着说明本次按键被视为重复按下，按原语义忽略
                    return

            try:
                if self.gui is not None and hasattr(self.gui, "show_recording_overlay"):
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
            self._hide_recording_overlay_safe()
            self._set_status(f"开始录音失败：{e}", is_error=True)

    def stop_recording(self) -> None:
        audio_data = b""

        try:
            if not getattr(self.audio_recorder, "is_recording", False):
                self._hide_recording_overlay_safe()
                return

            self._set_status("停止录音…")
            audio_data = self.audio_recorder.stop_recording()
        except Exception as e:
            self._hide_recording_overlay_safe()
            self._set_status(f"停止录音失败：{e}", is_error=True)
            # 异常路径同样要兜底复位 speaker / 状态机
            self._force_reset_after_stuck()
            return
        finally:
            # 无论停止录音是否成功，都尽力恢复外放（避免一直静音）
            try:
                self._maybe_restore_speaker_after_recording()
            except Exception:
                pass

        if not audio_data:
            self._hide_recording_overlay_safe()
            self._set_status("没有录制到音频数据")
            return

        is_too_short, duration_ms, min_duration_ms = self._is_audio_too_short(audio_data)
        if is_too_short:
            self._hide_recording_overlay_safe()
            print(
                f"ℹ️ 录音过短，跳过转写和保存: "
                f"{duration_ms:.0f}ms < {min_duration_ms}ms"
            )
            self._set_status("录音太短，已跳过")
            return

        try:
            threading.Thread(
                target=self._handle_voice_input_worker,
                args=(audio_data,),
                daemon=True,
            ).start()
        except Exception as e:
            # 启动转写线程失败：浮窗也要复位，避免一直显示
            self._hide_recording_overlay_safe()
            self._set_status(f"停止录音失败：{e}", is_error=True)

    def toggle_recording(self) -> None:
        if getattr(self.audio_recorder, "is_recording", False):
            self.stop_recording()
        else:
            self.start_recording()

    def _handle_voice_input_worker(self, audio_data: bytes) -> None:
        with self._processing_lock:
            if self._is_processing:
                self._hide_recording_overlay_safe()
                return
            self._is_processing = True

        try:
            # 开始转录前，调整录音提示框效果
            try:
                if self.gui is not None and hasattr(self.gui, "update_transcribe_progress"):
                    byte_len = len(audio_data) if audio_data else 0
                    if byte_len > 10:
                        self.gui.update_transcribe_progress(byte_len)
            except Exception as e:
                print(f"⚠️ 隐藏录音提示框失败（可忽略）: {e}")

            self._set_status("语音转录中…")
            self._ensure_stt_ready()
            trans_time = time.time()
            raw_text = self.stt_processor.transcribe(audio_data)
            final_text = raw_text
            audio_path = getattr(self.stt_processor, "last_audio_path", None)
            print("语音转录结果:", raw_text)
            print(f"转录耗时 {time.time() - trans_time:.2f}s（从处理开始算起）")


            if not raw_text:
                print("ℹ️ 转写结果为空，跳过改写")
            else:
                try:
                    if self.config_manager is None:
                        self.config_manager = get_config_manager()

                    if bool(self.config_manager.get("FORMAT_TEXT")):
                        rewriter = self._get_rewriter_safe()
                        if rewriter is None:
                            print("⚠️ rewriter 不可用，跳过改写")
                        else:
                            rewrite_time = time.time()
                            final_text = rewriter.rewrite(raw_text)
                            print(f"文本改写耗时 {time.time() - rewrite_time:.2f}s")
                            print(f"✅ 格式化改写后的文本: {final_text}")
                    else:
                        print("ℹ️ FORMAT_TEXT 未开启，跳过改写")
                except Exception as e:
                    print(f"⚠️ 文本改写失败（将使用原转写结果）: {e}")
                    final_text = raw_text

            if raw_text or final_text:
                self._record_transcription_history(audio_path, raw_text, final_text)

            self._set_status("写入中…")
            # 隐藏掉录音提示框
            self._hide_recording_overlay_safe()

            if not self.write_appname_to_cursor(final_text):
                print("⚠️ 文本已转录，但没有成功触发粘贴。请检查“辅助功能”权限或当前输入焦点。")
        except Exception as e:
            self._hide_recording_overlay_safe()
            self._set_status(f"转写/写入失败：{e}", is_error=True)
        finally:
            self._set_status("就绪")
            with self._processing_lock:
                self._is_processing = False

    def run(self) -> None:
        _run_t0 = time.perf_counter()
        print(f"🚀 {self.app_name} 启动中...")

        t0 = time.perf_counter()
        print(f"app-----开始时间：{t0}")
        try:
            from .components.gui_tk import VoiceInputGUI
        except Exception as e:
            print(f"❌ GUI 模块加载失败：{e}")
            raise
        print(f"[perf] main: import VoiceInputGUI: {(time.perf_counter() - t0) * 1000:.1f}ms")

        # 1) 启动后初始化 VoiceInputGUI
        t0 = time.perf_counter()
        self.gui = VoiceInputGUI(self, app_name=self.app_name)
        print(f"[perf] main: VoiceInputGUI ctor: {(time.perf_counter() - t0) * 1000:.1f}ms")

        # 2) 加载 config 文件（复用 GUI 的 ConfigManager，避免重复读文件）
        t0 = time.perf_counter()
        self.config_manager = get_config_manager()
        print(f"[perf] main: bind config_manager: {(time.perf_counter() - t0) * 1000:.1f}ms")

        # 3) 启动模型检查/下载引导（下载就绪后触发 STT 加载 + 本地改写预加载）和 热键监听
        t0 = time.perf_counter()
        if getattr(self.gui, "root", None) is not None:
            self.gui.root.after(300, self.start_model_bootstrap)
            self.gui.root.after_idle(self.start_listening_hotkey)
        else:
            self.start_model_bootstrap()
            self.start_listening_hotkey()
        print(f"[perf] main: schedule model bootstrap/hotkey: {(time.perf_counter() - t0) * 1000:.1f}ms")

        print(f"[perf] main: run() pre-mainloop total: {(time.perf_counter() - _run_t0) * 1000:.1f}ms")
        self.gui.run()


    def write_appname_to_cursor(self, voice_input: str) -> bool:
        try:
            if not voice_input:
                print("⚠️ 写入文本为空，跳过写入")
                return False

            if not self._copy_text_to_pasteboard(str(voice_input)):
                return False
            print(f"✅ 已写入剪贴板: {voice_input[:20]}...")

            if self.paste_with_cgevent():
                return True

            print("⚠️ CGEvent 失败，未触发粘贴")
            return False

        except Exception as e:
            print(f"❌ 写入失败: {e}")
            return False

    def _copy_text_to_pasteboard(self, text: str) -> bool:
        """写入系统剪贴板：优先使用进程内 NSPasteboard，pbcopy 仅作兜底。"""
        if self._copy_via_nspasteboard(text):
            return True
        print("⚠️ NSPasteboard 写入失败，回退 pbcopy")
        return self._copy_via_pbcopy(text)

    def _copy_via_nspasteboard(self, text: str) -> bool:
        """使用 AppKit NSPasteboard 在进程内写剪贴板，不受子进程环境/locale 影响。"""
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeString

            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            ok = pasteboard.setString_forType_(text, NSPasteboardTypeString)
            if not ok:
                print("❌ NSPasteboard setString 返回 False")
                return False
            return True
        except Exception as e:
            print(f"❌ NSPasteboard 写入异常: {e}")
            return False

    def _copy_via_pbcopy(self, text: str) -> bool:
        """使用 macOS pbcopy 写入系统剪贴板，作为 NSPasteboard 的兜底路径。"""
        try:
            proc = subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=False,
                capture_output=True,
                timeout=2,
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                print(f"❌ 写入系统剪贴板失败: pbcopy 返回码 {proc.returncode} {stderr}")
                return False
            return True
        except Exception as e:
            print(f"❌ 写入系统剪贴板失败: {e}")
            return False

    def paste_with_cgevent(self) -> bool:
        """macOS CGEvent Cmd+V 粘贴。"""
        import ctypes
        import ctypes.util

        try:
            core_graphics = ctypes.util.find_library('CoreGraphics')
            cg = ctypes.CDLL(core_graphics)

            try:
                from .util.mac_permissions import is_accessibility_trusted, request_accessibility_permission

                if not is_accessibility_trusted(prompt=False):
                    print("⚠️ 需要辅助功能权限才能把文本粘贴到其他应用，正在请求权限...")
                    if not request_accessibility_permission():
                        print(
                            "⚠️ 辅助功能权限尚未授权。请在“系统设置 > 隐私与安全 > 辅助功能”"
                            "中添加并开启 MyVoiceTyping，然后退出并重新打开应用。"
                        )
                        return False
            except Exception as e:
                print(f"⚠️ 辅助功能权限预检失败，将继续尝试 CGEvent 粘贴: {e}")

            # 配置函数参数类型（关键！避免类型错误）
            cg.CGEventSourceCreate.restype = ctypes.c_void_p
            cg.CGEventSourceCreate.argtypes = [ctypes.c_int32]

            cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
            cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]

            cg.CGEventSetFlags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
            cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

            # 创建事件源 (1 = kCGEventSourceStateHIDSystemState)
            source = cg.CGEventSourceCreate(1)
            if not source:
                print("❌ 创建 CGEvent source 失败")
                return False

            keycode_v = 9
            keycode_cmd = 55  # 左 Command
            cmd_flag = 0x00100000
            tap = 0  # kCGHIDEventTap

            cmd_down = cg.CGEventCreateKeyboardEvent(source, keycode_cmd, True)
            v_down = cg.CGEventCreateKeyboardEvent(source, keycode_v, True)
            v_up = cg.CGEventCreateKeyboardEvent(source, keycode_v, False)
            cmd_up = cg.CGEventCreateKeyboardEvent(source, keycode_cmd, False)

            if not all([cmd_down, v_down, v_up, cmd_up]):
                print("❌ 创建键盘事件失败")
                return False

            # 先按下 Cmd，再发送 V，最后释放 Cmd。
            cg.CGEventSetFlags(cmd_down, cmd_flag)
            cg.CGEventSetFlags(v_down, cmd_flag)
            cg.CGEventSetFlags(v_up, cmd_flag)
            cg.CGEventSetFlags(cmd_up, 0)

            cg.CGEventPost(tap, cmd_down)
            time.sleep(0.01)
            cg.CGEventPost(tap, v_down)
            time.sleep(0.01)
            cg.CGEventPost(tap, v_up)
            time.sleep(0.01)
            cg.CGEventPost(tap, cmd_up)

            return True

        except Exception as e:
            print(f"CGEvent error: {e}")
            return False

    def minimize_to_tray(self) -> None:
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
        if self.gui is None or getattr(self.gui, "root", None) is None:
            return

        def _quit() -> None:
            try:
                self.gui.root.quit()
                self.hotkey.listener.stop()
            finally:
                try:
                    self.hotkey.listener.stop()
                    self.gui.root.destroy()
                except Exception:
                    pass

        try:
            self.gui.root.after(0, _quit)
        except Exception:
            _quit()

    # def _check_accessibility_permission(self) -> bool:
    #     """检测并请求辅助功能权限"""
    #     try:
    #         import Quartz
    #         opts = {Quartz.kAXTrustedCheckOptionPrompt: True}
    #         return bool(Quartz.AXIsProcessTrustedWithOptions(opts))
    #     except Exception:
    #         return False
    #
    # def _check_microphone_permission(self) -> bool:
    #     """检测并请求麦克风权限"""
    #     try:
    #         from AVFoundation import AVAudioSession
    #         session = AVAudioSession.sharedInstance()
    #         session.setCategory_error_("AVAudioSessionCategoryPlayAndRecord", 1)
    #         session.setActive_error_(True)
    #         return True
    #     except Exception:
    #         return False
    #
    # def _request_permissions(self):
    #     """请求所有必要权限并引导用户"""
    #     if not self._check_accessibility_permission():
    #         # 显示引导界面，包含截图和步骤说明
    #         self._show_permission_guide(
    #             title="需要辅助功能权限",
    #             description="MyVoiceTyping 需要此权限来监听全局快捷键和在任何应用中输入文本。",
    #             setting_url="x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    #         )
    #
    #     if not self._check_microphone_permission():
    #         # 系统会自动弹窗请求麦克风权限
    #         pass
