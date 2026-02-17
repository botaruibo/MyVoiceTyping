"""
工具函数
"""
import os
import tempfile
import wave
import numpy as np


# def audio_to_wav_bytes(frames, sample_rate=16000):
#     """将音频帧转换为WAV字节"""
#     with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
#         temp_filename = temp_file.name
#
#     try:
#         # 创建WAV文件
#         wf = wave.open(temp_filename, 'wb')
#         wf.setnchannels(1)
#         wf.setsampwidth(2)  # 16-bit
#         wf.setframerate(sample_rate)
#         wf.writeframes(b''.join(frames))
#         wf.close()
#
#         # 读取文件内容
#         with open(temp_filename, 'rb') as f:
#             wav_bytes = f.read()
#
#         return wav_bytes
#     finally:
#         # 清理临时文件
#         if os.path.exists(temp_filename):
#             os.unlink(temp_filename)
#
#
# def normalize_audio(frames, target_db=-20.0):
#     """标准化音频音量"""
#     # 将字节数据转换为numpy数组
#     audio_data = b''.join(frames)
#     audio_array = np.frombuffer(audio_data, dtype=np.int16)
#
#     # 计算当前音量
#     current_rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
#     target_amplitude = 10 ** (target_db / 20.0)
#
#     if current_rms > 0:
#         # 计算增益
#         gain = target_amplitude / current_rms
#         normalized_array = audio_array * gain
#         # 限制在int16范围内
#         normalized_array = np.clip(normalized_array, -32768, 32767)
#
#         # 转换回字节
#         normalized_bytes = normalized_array.astype(np.int16).tobytes()
#         # 重新分块
#         chunk_size = len(frames[0])
#         normalized_frames = [
#             normalized_bytes[i:i+chunk_size]
#             for i in range(0, len(normalized_bytes), chunk_size)
#         ]
#         return normalized_frames
#
#     return frames
