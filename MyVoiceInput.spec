# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

import funasr
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

try:
    project_root = Path(SPECPATH).resolve()
except NameError:
    project_root = Path.cwd().resolve()

funasr_version_file = Path(funasr.__file__).resolve().parent / 'version.txt'

funasr_hiddenimports = collect_submodules('funasr')
modelscope_hiddenimports = collect_submodules('modelscope')

try:
    funasr_datas = collect_data_files('funasr', include_py_files=True)
except TypeError:
    funasr_datas = collect_data_files('funasr')

modelscope_datas = collect_data_files('modelscope')

# ---- Fully-offline model assets checks (Removed for flexible packaging) ----
# 说明：原先的 check 逻辑已移除，允许仅打包 config 文件夹。
# 运行时若缺少模型，由应用自行处理或用户手动下载。

def _assert_dir_exists(model_name: str, model_dir: Path) -> None:
    pass

def _assert_file_exists(model_name: str, file_path: Path) -> None:
    pass

# ASR: SenseVoiceSmall-onnx
# asr_dir = project_root / "data" / "models" / "SenseVoiceSmall-onnx"
# _assert_dir_exists("SenseVoiceSmall-onnx", asr_dir)

icon_icns = project_root / "assets" / "icon.icns"
if not icon_icns.exists():
    icon_icns = project_root / "icon.icns"
if not icon_icns.exists():
    # 这里保持警告或报错，图标通常是必须的
    print(f"[spec] Warning: icon.icns not found at {project_root/'assets'/'icon.icns'}")

a = Analysis(
    [str(project_root / 'run.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'src'), 'src'),
        (str(project_root / 'requirements.txt'), '.'),
        # 修改：仅包含 config 文件夹，其他 data 子文件夹不打包
        (str(project_root / 'data/config'), 'data/config'),
        (str(funasr_version_file), 'funasr'),
        *funasr_datas,
        *modelscope_datas,
    ],
    hiddenimports=[
        'dearpygui',
        'customtkinter',
        'funasr',
        'modelscope',
        'torch',
        'torchaudio',
        'transformers',
        'openai',
        'pyobjc_framework_ApplicationServices',
        # 新增：macOS 系统框架依赖
        'AppKit',
        'Foundation',
        'Quartz',
        'CoreFoundation',
        # 新增：其他核心依赖
        'pyautogui',
        'pygetwindow',
        'pyperclip',
        'sounddevice',
        'onnxruntime',
        'langchain_openai',
        'langchain_core',
        'PIL',
        'numpy',
        'requests',
        'websockets',
        'charset_normalizer',
        'funasr.utils',
        'funasr.models',
        'encodings',
        'encodings.idna',
        'encodings.utf_8',
        'encodings.latin_1',
        'yaml',
        *funasr_hiddenimports,
        *modelscope_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / 'runtime_hook.py')],
    excludes=[
        # 注意：GUI 已切换为 Tkinter + CustomTkinter，不能再排除 tkinter
        'yaml._yaml',  # 排除 x86_64 的 C 扩展，使用纯 Python 实现
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
    strip=False,
    upx=False,  # 关闭 UPX 压缩以避免潜在问题
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',  # 专门针对 M4 芯片优化
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_icns) if icon_icns.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MyVoiceInput',
)

app = BUNDLE(
    coll,
    name='MyVoiceInput.app',
    icon=str(icon_icns) if icon_icns.exists() else None,
    bundle_identifier=None,
    info_plist={
        "NSMicrophoneUsageDescription": "用于语音输入，需要访问麦克风。",
        "NSSpeechRecognitionUsageDescription": "用于语音识别转文字。",
        "NSAppleEventsUsageDescription": "用于自动化控制和快捷键监听。",
    },
)

#如果要增加一个安装步骤呢，在安装时检查data/models 文件夹下是否有两个模型文件夹和对应的文件。如果没有就触发
