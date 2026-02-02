"""
音频录制模块 - 更新以使用新的配置和数据路径
"""
import sounddevice as sd
import numpy as np
import threading
from pathlib import Path
from ..config import Config


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

    def _record(self):
        """内部录音循环"""
        try:
            with sd.InputStream(
                samplerate=self.config.SAMPLE_RATE,
                channels=1,
                dtype='int16',
                blocksize=self.config.CHUNK_SIZE,
                callback=self._audio_callback
            ):
                while self.is_recording:
                    sd.sleep(100)  # 短暂休眠，避免占用过多CPU
        except Exception as e:
            print(f"录音错误: {e}")

    def _audio_callback(self, indata, frames, time, status):
        """音频数据回调函数"""
        if self.is_recording:
            # 复制音频数据到缓冲区
            self.audio_data.append(indata.copy())

    def _get_frames(self):
        """获取音频帧数据"""
        if not self.audio_data:
            return []
        # 合并所有音频数据
        all_data = np.concatenate(self.audio_data, axis=0)
        # 转换为bytes格式
        return all_data.tobytes()

    def save_audio(self, frames, filename=None):
        """保存音频到文件，默认保存到音频目录"""
        if filename is None:
            # 生成带时间戳的音频文件名
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(self.config.get_audio_dir() / f"recording_{timestamp}.wav")
        
        # 将bytes数据转换为numpy数组
        audio_array = np.frombuffer(frames, dtype=np.int16)
        # 重塑为单声道
        audio_array = audio_array.reshape(-1, 1)
        # 使用soundfile保存
        import soundfile as sf
        sf.write(filename, audio_array, self.config.SAMPLE_RATE)
        return filename

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'audio'):
            self.audio.terminate()