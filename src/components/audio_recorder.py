"""
音频录制模块 - 更新以使用新的配置和数据路径
"""
import sounddevice as sd
import numpy as np
import threading
import time as time_module
from pathlib import Path
from ..config import Config
from datetime import datetime
import soundfile as sf

"""/**
 * 全局音量缓存（供 GUI 轮询读取）。
 *
 * 设计目标：
 * - 录音线程写入：每隔固定时间（例如 50ms）写入一个 0~100 的音量值。
 * - GUI 主线程读取：轮询读取最后一个值并驱动音波绘制。
 *
 * 说明：
 * - 使用锁保证跨线程读写一致性。
 * - 使用 seq 让 GUI 能判断是否有新数据，避免重复重绘。
 */"""
GLOBAL_VOLUME_LEVELS: list[int] = []
GLOBAL_VOLUME_SEQ: int = 0
GLOBAL_VOLUME_LOCK = threading.Lock()

class AudioRecorder:
    def __init__(self):
        self.config = Config()  # 使用新的配置管理器
        self.is_recording = False
        self.audio_data = []
        self.stream = None
        self.record_thread: threading.Thread | None = None

    def start_recording(self):
        """开始录音"""
        self.audio_data = []
        self.is_recording = True

        # 开始录制
        try:
            self.record_thread = threading.Thread(target=self._record)
            self.record_thread.start()
        except Exception as e:
            self.is_recording = False
            self.record_thread = None
            print(f"❌ 开始录音失败：无法启动录音线程: {e}")
            raise

    def stop_recording(self):
        """停止录音"""
        if self.is_recording:
            self.is_recording = False

            t = self.record_thread
            if t is not None and t.is_alive():
                try:
                    t.join()
                except Exception as e:
                    print(f"⚠️ 等待录音线程结束失败（可忽略）: {e}")

        self.record_thread = None
        return self._get_frames()

    def _compute_volume_level(self, indata: np.ndarray) -> int:
        """
        /**
         * 将当前音频块转换为 0~100 的音量级别。
         *
         * 优化目标：
         * 1) 静音/很小声时输出 0（避免无声时音波抖动）
         * 2) 有人声时输出更“明显”的波动幅度
         *
         * 实现策略：
         * - RMS -> dBFS
         * - 自适应噪声底（仅在接近静音时缓慢更新）
         * - 噪声门限（noise gate）+ 小幅度死区
         * - 非线性映射（让中高音量更突出）
         *
         * @param {np.ndarray} indata - int16 单声道音频块（frames x 1）。
         * @returns {number} volume_level - 0~100。
         */
        """
        try:
            if indata is None or getattr(indata, "size", 0) == 0:
                return 0

            s = indata.astype(np.float32).reshape(-1)
            if s.size == 0:
                return 0

            rms = float(np.sqrt(np.mean(s * s)))
            rms_norm = rms / 32768.0

            db = 20.0 * float(np.log10(rms_norm + 1e-12))
            db = max(-90.0, min(0.0, db))

            noise_floor_db = float(getattr(self, "_volume_noise_floor_db", -60.0))
            if db < (noise_floor_db + 6.0):
                alpha = 0.05
                noise_floor_db = (1.0 - alpha) * noise_floor_db + alpha * db
                setattr(self, "_volume_noise_floor_db", noise_floor_db)

            gate_db = noise_floor_db + 10.0
            gate_db = max(-55.0, min(-25.0, gate_db))

            if db < gate_db:
                return 0

            full_db = gate_db + 25.0
            norm = (db - gate_db) / max(1e-6, (full_db - gate_db))
            norm = max(0.0, min(1.0, norm))

            norm = norm ** 1.8

            level = int(round(norm * 100.0))

            if level < 3:
                return 0

            return max(0, min(100, level))
        except Exception as e:
            print(f"⚠️ 计算实时音量失败（可忽略）: {e}")
            return 0


    def _record(self):
        """
        /**
         * 内部录音循环（录音线程）。
         *
         * 方案实现：
         * - 录音期间：每隔一段时间把当前音量（0~100）写入全局数组 `GLOBAL_VOLUME_LEVELS`。
         * - GUI 侧：通过轮询读取该数组的最新值来驱动音波高度。
         *
         * 注意：
         * - 这里运行在非 GUI 线程，不能直接操作 tkinter。
         * - 需要尽量避免耗时计算；这里使用节流（约 20FPS）降低开销。
         *
         * @returns {void}
         */
        """

        global GLOBAL_VOLUME_SEQ

        # 每次开始录音，先清空全局缓存，避免上一次的残留数据影响 UI
        try:
            with GLOBAL_VOLUME_LOCK:
                GLOBAL_VOLUME_LEVELS.clear()
                GLOBAL_VOLUME_SEQ = 0
        except Exception as e:
            print(f"⚠️ 清空全局音量缓存失败（可忽略）: {e}")

        # 录音参数候选
        desired_sr = int(getattr(self.config, "SAMPLE_RATE", 16000) or 16000)
        desired_bs = int(getattr(self.config, "CHUNK_SIZE", 1024) or 1024)

        # 选择输入设备（内联到 _record，避免改动其它函数）
        device_idx = None
        device_info = None

        config_device = getattr(self.config, "INPUT_DEVICE", None)
        if config_device is not None:
            try:
                device_idx = int(config_device)
                device_info = sd.query_devices(device_idx, kind="input")
            except Exception as e:
                device_idx = None
                device_info = None
                print(f"⚠️ 配置的输入设备不可用（INPUT_DEVICE={config_device}）: {e}")

        if device_idx is None:
            try:
                default_device = sd.default.device[0]
                if isinstance(default_device, int) and default_device >= 0:
                    device_idx = default_device
                    device_info = sd.query_devices(device_idx, kind="input")
            except Exception:
                device_idx = None
                device_info = None

        if device_idx is None:
            try:
                devices = sd.query_devices()
                for idx, d in enumerate(devices):
                    try:
                        if int(d.get("max_input_channels", 0)) > 0:
                            device_idx = idx
                            device_info = sd.query_devices(device_idx, kind="input")
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"❌ 无法枚举音频设备: {e}")
                raise

        if device_idx is None or device_info is None:
            raise RuntimeError("未检测到可用的麦克风输入设备")

        default_sr = desired_sr
        try:
            default_sr = int(float(device_info.get("default_samplerate", desired_sr)) or desired_sr)
        except Exception:
            default_sr = desired_sr

        candidates_sr = []
        for sr in (desired_sr, default_sr):
            if sr not in candidates_sr:
                candidates_sr.append(sr)

        candidates_bs = []
        for bs in (desired_bs, 0):
            if bs not in candidates_bs:
                candidates_bs.append(bs)

        stream = None
        last_error = None

        for sr in candidates_sr:
            for bs in candidates_bs:
                try:
                    print(
                        f"尝试打开录音设备: index={device_idx}, name={device_info.get('name')}, "
                        f"samplerate={sr}, blocksize={bs}"
                    )
                    stream = sd.InputStream(
                        samplerate=sr,
                        device=device_idx,
                        channels=1,
                        dtype="int16",
                        blocksize=bs,
                        callback=self._audio_callback,
                    )
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    stream = None
                    print(f"⚠️ 打开 InputStream 失败: samplerate={sr}, blocksize={bs}, error={e}")
            if stream is not None:
                break

        if stream is None:
            raise RuntimeError(f"Error opening InputStream: {last_error}")

        # 节流：约 20 FPS
        emit_interval_s = 0.05
        next_emit_ts = time_module.perf_counter()

        try:
            with stream:
                while self.is_recording:
                    sd.sleep(20)

                    now = time_module.perf_counter()
                    if now < next_emit_ts:
                        continue

                    latest_chunk = None
                    try:
                        if self.audio_data:
                            latest_chunk = self.audio_data[-1]
                    except Exception:
                        latest_chunk = None

                    volume_level = 0
                    if latest_chunk is not None:
                        volume_level = self._compute_volume_level(latest_chunk)

                    try:
                        with GLOBAL_VOLUME_LOCK:
                            GLOBAL_VOLUME_LEVELS.append(int(volume_level))
                            if len(GLOBAL_VOLUME_LEVELS) > 120:
                                del GLOBAL_VOLUME_LEVELS[:-120]
                            GLOBAL_VOLUME_SEQ += 1
                    except Exception as e:
                        print(f"⚠️ 写入全局音量缓存失败（可忽略）: {e}")

                    next_emit_ts = now + emit_interval_s
        except Exception as e:
            print(f"录音错误: {e}")
            print(
                "macOS 可能需要给当前程序/终端授予麦克风权限：\n"
                "系统设置 -> 隐私与安全性 -> 麦克风 -> 勾选你的终端或 PyCharm\n"
                "如果你用的是外接麦克风，也可以尝试在系统声音输入里切换设备后重试。"
            )
            raise

    def _audio_callback(self, indata, frames, time, status):
        """音频数据回调函数"""
        if status:
            print(f"⚠️ 录音回调状态异常: {status}")
        if self.is_recording:
            try:
                self.audio_data.append(indata.copy())
            except Exception as e:
                print(f"⚠️ 录音数据缓存失败（可忽略）: {e}")

    def _get_frames(self):
        """获取音频帧数据"""
        if not self.audio_data:
            return b""
        all_data = np.concatenate(self.audio_data, axis=0)
        return all_data.tobytes()

    def save_audio(self, frames, filename=None):
        """保存音频到文件，默认保存到音频目录"""
        if frames is None or frames == b"":
            raise ValueError("没有录到任何音频数据，无法保存")
        if filename is None:
            # 生成带时间戳的音频文件名

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(self.config.get_audio_dir() / f"recording_{timestamp}.wav")
        
        # 将bytes数据转换为numpy数组
        audio_array = np.frombuffer(frames, dtype=np.int16)
        # 重塑为单声道
        audio_array = audio_array.reshape(-1, 1)
        # 使用soundfile保存

        sf.write(filename, audio_array, self.config.SAMPLE_RATE)
        return filename

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'audio'):
            self.audio.terminate()