"""
音频录制模块 - 更新以使用新的配置和数据路径
"""
import sounddevice as sd
import numpy as np
import threading
from pathlib import Path
from ..config import Config
from datetime import datetime
import soundfile as sf


class AudioRecorder:
    def __init__(self):
        self.config = Config()  # 使用新的配置管理器
        self.is_recording = False
        self.audio_data = []
        self.stream = None

    def start_recording(self):
        """开始录音"""
        self.audio_data = []
        self.is_recording = True

        # 开始录制
        self.record_thread = threading.Thread(target=self._record)
        self.record_thread.start()

    def stop_recording(self):
        """停止录音"""
        if self.is_recording:
            self.is_recording = False

            if self.record_thread.is_alive():
                self.record_thread.join()

        return self._get_frames()

    def _pick_input_device(self):
        """
        /**
         * 选择一个可用的输入设备。
         *
         * 说明：
         * - 你遇到的 AUHAL/PortAudio 错误，经常与设备不可用或参数不兼容有关。
         * - 这里优先使用配置指定的输入设备（如果存在该配置项且有效）。
         * - 否则使用 sounddevice 默认输入设备。
         * - 默认设备不可用时，回退到第一个可用的输入设备。
         *
         * @returns (device_index, device_info)
         */
        """
        config_device = getattr(self.config, "INPUT_DEVICE", None)
        if config_device is not None:
            try:
                idx = int(config_device)
                info = sd.query_devices(idx, kind="input")
                return idx, info
            except Exception as e:
                print(f"⚠️ 配置的输入设备不可用（INPUT_DEVICE={config_device}）: {e}")

        default_device = None
        try:
            default_device = sd.default.device[0]
        except Exception:
            default_device = None

        if isinstance(default_device, int) and default_device >= 0:
            try:
                info = sd.query_devices(default_device, kind="input")
                return default_device, info
            except Exception as e:
                print(f"⚠️ 默认输入设备不可用（device={default_device}）: {e}")

        try:
            devices = sd.query_devices()
        except Exception as e:
            raise RuntimeError(f"无法枚举音频设备: {e}")

        for idx, d in enumerate(devices):
            try:
                if int(d.get("max_input_channels", 0)) > 0:
                    info = sd.query_devices(idx, kind="input")
                    return idx, info
            except Exception:
                continue

        raise RuntimeError("未检测到可用的麦克风输入设备")

    def _create_input_stream(self):
        """
        /**
         * 创建 InputStream（返回可用于 `with stream:` 的对象）。
         *
         * 背景：
         * - macOS AUHAL 下，某些设备不支持 16000Hz 或固定 blocksize，可能触发：
         *   -10851 Audio Unit: Invalid Property Value
         *   -9986 Internal PortAudio error
         *
         * 回退策略：
         * - 采样率：优先用配置 SAMPLE_RATE，其次用设备 default_samplerate
         * - blocksize：优先用配置 CHUNK_SIZE，失败后使用 0（让 PortAudio 自动选择）
         *
         * @returns sounddevice.InputStream
         */
        """
        device_idx, device_info = self._pick_input_device()

        desired_sr = int(getattr(self.config, "SAMPLE_RATE", 16000) or 16000)
        desired_bs = int(getattr(self.config, "CHUNK_SIZE", 1024) or 1024)

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
                    return stream
                except Exception as e:
                    last_error = e
                    print(f"⚠️ 打开 InputStream 失败: samplerate={sr}, blocksize={bs}, error={e}")

        raise RuntimeError(f"Error opening InputStream: {last_error}")

    def _record(self):
        """内部录音循环"""
        try:
            self.stream = self._create_input_stream()
            with self.stream:
                while self.is_recording:
                    sd.sleep(100)  # 短暂休眠，避免占用过多CPU
        except Exception as e:
            print(f"录音错误: {e}")
            print(
                "macOS 可能需要给当前程序/终端授予麦克风权限：\n"
                "系统设置 -> 隐私与安全性 -> 麦克风 -> 勾选你的终端或 PyCharm\n"
                "如果你用的是外接麦克风，也可以尝试在系统声音输入里切换设备后重试。"
            )
            raise
        finally:
            self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        """音频数据回调函数"""
        if status:
            print(f"⚠️ 录音回调状态异常: {status}")
        if self.is_recording:
            self.audio_data.append(indata.copy())

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