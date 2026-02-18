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

# ---- Fully-offline model assets checks (fail fast) ----
# 说明：`datas` 已经把整个 `data/` 打进发行包；这里只是保证你没有漏放离线模型文件。

def _assert_dir_exists(model_name: str, model_dir: Path) -> None:
    if not model_dir.exists():
        raise SystemExit(
            f"[spec] Offline model directory missing: {model_name}: {model_dir}\n"
            f"[spec] Please download/copy the model into `data/models/` before packaging."
        )

def _assert_file_exists(model_name: str, file_path: Path) -> None:
    if not file_path.exists():
        raise SystemExit(
            f"[spec] Offline model file missing: {model_name}: {file_path}\n"
            f"[spec] Please ensure the model files are complete under `data/models/`."
        )

def _assert_has_weights(model_name: str, model_dir: Path) -> None:
    if not any(model_dir.glob("*.pt")):
        raise SystemExit(
            f"[spec] Offline model weights (*.pt) missing: {model_name}: {model_dir}"
        )

# ASR: SenseVoiceSmall
asr_dir = project_root / "data" / "models" / "SenseVoiceSmall"
_assert_dir_exists("SenseVoiceSmall", asr_dir)
_assert_file_exists("SenseVoiceSmall", asr_dir / "configuration.json")
_assert_file_exists("SenseVoiceSmall", asr_dir / "model.pt")

# VAD: speech_fsmn_vad_zh-cn-16k-common-pytorch
vad_dir = project_root / "data" / "models" / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
_assert_dir_exists("speech_fsmn_vad_zh-cn-16k-common-pytorch", vad_dir)
_assert_file_exists("speech_fsmn_vad_zh-cn-16k-common-pytorch", vad_dir / "configuration.json")
_assert_has_weights("speech_fsmn_vad_zh-cn-16k-common-pytorch", vad_dir)

icon_icns = project_root / "assets" / "icon.icns"
if not icon_icns.exists():
    icon_icns = project_root / "icon.icns"
if not icon_icns.exists():
    raise SystemExit(f"[spec] icon.icns not found. Expected: {project_root/'assets'/'icon.icns'}")

a = Analysis(
    [str(project_root / 'run.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'src'), 'src'),
        (str(project_root / 'requirements.txt'), '.'),
        (str(project_root / 'data'), 'data'),
        (str(funasr_version_file), 'funasr'),
        *funasr_datas,
        *modelscope_datas,
    ],
    hiddenimports=[
        'dearpygui',
        'customtkinter',
        'pynput',
        'funasr',
        'modelscope',
        'torch',
        'torchaudio',
        'transformers',
        'openai',
        'pyobjc_framework_ApplicationServices',
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
    icon=str(icon_icns),
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
    icon=str(icon_icns),
    bundle_identifier=None,
    info_plist={
        "NSMicrophoneUsageDescription": "用于语音输入，需要访问麦克风。",
        "NSSpeechRecognitionUsageDescription": "用于语音识别转文字。",
    },
)