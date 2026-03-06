# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 获取项目根目录
try:
    project_root = Path(SPECPATH).resolve()
except NameError:
    project_root = Path.cwd().resolve()

# 自动收集子模块（只收集真正需要的推理库）
#funasr_onnx_hidden = collect_submodules('funasr_onnx')
#modelscope_hidden = collect_submodules('modelscope')

# 收集必要的数据文件
# 注意：我们尽量减少 collect_data_files 的使用，因为它会带入很多垃圾文件
datas = [
    (str(project_root / 'src'), 'src'),
    (str(project_root / 'requirements.txt'), '.'),
    (str(project_root / 'data/config'), 'data/config'),
]

# 尝试获取 funasr 的版本文件（如果 postprocess 还在用 funasr 库）
#try:
#    import funasr
#    funasr_version_file = Path(funasr.__file__).resolve().parent / 'version.txt'
#    if funasr_version_file.exists():
#        datas.append((str(funasr_version_file), 'funasr'))
#except ImportError:
#    pass

# 图标路径处理
icon_icns = project_root / "assets" / "icon.icns"
if not icon_icns.exists():
    icon_icns = project_root / "icon.icns"

a = Analysis(
    [str(project_root / 'run.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'onnxruntime',
        'funasr_onnx',
        'modelscope',
        'AppKit',
        'Foundation',
        'Quartz',
        'CoreFoundation',
        'pyautogui',
        'pygetwindow',
        'pyperclip',
        'sounddevice',
        'PIL',
        'numpy',
        'requests',
        'yaml',
#        *funasr_onnx_hidden,
#        *modelscope_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / 'runtime_hook.py')],
    # 【关键优化：排除重型依赖】
    excludes=[
        'torch',           # 排除 Torch (约 400MB)
        'torchaudio',      # 排除 TorchAudio (约 100MB)
        'torchvision',     # 排除 TorchVision
        'triton',
        'matplotlib',      # 排除绘图库
        'pandas',
        'IPython',
        'notebook',
        'jedi',
        'PIL.ImageQt',
        'tkinter.test',
        'PyQt5',
        'PySide2',
        'PySide6',
#        'scipy',           # 排除 SciPy
        'sklearn',         # 排除 Scikit-learn
#        'numba',           # 排除 Numba
#        'sympy',
        'networkx',
#        'llvmlite',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MyVoiceInput',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,        # 开启 Strip 移除调试符号
    upx=False,         # macOS 上 UPX 经常失效，建议关闭
    console=False,     # 无终端窗口
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',  # 专门针对 M4 芯片优化
    icon=str(icon_icns) if icon_icns.exists() else None,
    codesign_identity='-',
#    entitlements_file='my.entitlements',  # 关键：添加 entitlements 文件
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    name='MyVoiceInput',
)

app = BUNDLE(
    coll,
    name='MyVoiceInput.app',
    icon=str(icon_icns) if icon_icns.exists() else None,
    bundle_identifier='MyVoiceInput.app', # TODO：未来修改
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        'NSAppleEventsUsageDescription': '此应用需要控制键盘输入以完成跨应用输入文字',
        "NSMicrophoneUsageDescription": "语音输入，需要访问麦克风。",
#        "NSSpeechRecognitionUsageDescription": "用于语音识别转文字。",
        'NSHighResolutionCapable': 'True',
        # 主应用不显示 Dock 图标。
        'LSUIElement': True,
        'LSBackgroundOnly': False,
        # 确保子进程不会创建额外的 Dock 图标
        'NSSupportsSuddenTermination': False,
    },
)