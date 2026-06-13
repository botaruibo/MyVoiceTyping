# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

block_cipher = None


def choose_codesign_identity():
    """优先使用固定自签名身份，避免每次重装后 TCC 权限失效。"""
    explicit = os.environ.get('CODESIGN_IDENTITY')
    if explicit:
        return explicit

    preferred = 'MyVoiceTyping Self-Signed'
    try:
        proc = subprocess.run(
            ['security', 'find-identity', '-v', '-p', 'codesigning'],
            check=False,
            capture_output=True,
            text=True,
        )
        if f'"{preferred}"' in (proc.stdout or ''):
            return preferred
    except Exception:
        pass

    return '-'

# 获取项目根目录
try:
    project_root = Path(SPECPATH).resolve()
except NameError:
    project_root = Path.cwd().resolve()

# 自动收集子模块（只收集真正需要的推理库）
#funasr_onnx_hidden = collect_submodules('funasr_onnx')
modelscope_hidden = []
try:
    modelscope_hidden += collect_submodules('modelscope')
except Exception:
    pass

# 本地 llama.cpp 纠错后端依赖 llama_cpp，需收集其子模块与动态库
llama_cpp_hidden = []
try:
    llama_cpp_hidden += collect_submodules('llama_cpp')
except Exception:
    pass

def prepare_package_config() -> Path:
    """Create a sanitized config directory for packaged builds."""
    source = project_root / 'data' / 'config'
    target = project_root / 'build' / 'package_data' / 'config'

    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    app_config = target / 'app_config.json'
    if app_config.exists():
        with app_config.open('r', encoding='utf-8') as f:
            config = json.load(f)

        for key in (
            'api_key',
            'openai_api_key',
            'ollama_api_key',
            'access_token',
            'secret_key',
            'token',
        ):
            if key in config:
                config[key] = ''

        # 本安装包内置本地 GGUF 纠错模型，默认启用文本改写。
        # 仅保留本地 llama.cpp 后端，云端 LLM 相关库不打包。
        config['format_text'] = True
        config['llm_text_provider'] = 'llama_cpp'
        config['preload_llama_cpp_on_startup'] = True

        with app_config.open('w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return target


package_config_dir = prepare_package_config()

# 收集必要的数据文件
# 注意：我们尽量减少 collect_data_files 的使用，因为它会带入很多垃圾文件
datas = [
    (str(project_root / 'src'), 'src'),
    (str(project_root / 'requirements.txt'), '.'),
    (str(project_root / 'assets'), 'assets'),
    (str(package_config_dir), 'data/config'),
]

# 不打包 data/models 下的模型文件；首次启动时下载到用户可写的 Application Support。

binaries = []
try:
    binaries += collect_dynamic_libs('llama_cpp')
except Exception:
    pass

for libomp_candidate in (
    project_root / 'venv' / 'lib' / 'python3.11' / 'site-packages' / 'torch' / 'lib' / 'libomp.dylib',
    Path('/usr/local/lib/libomp.dylib'),
    Path('/opt/homebrew/lib/libomp.dylib'),
):
    if libomp_candidate.exists():
        binaries.append((str(libomp_candidate), '.'))
        break

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
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'onnxruntime',
        'funasr_onnx',
        'AppKit',
        'Foundation',
        'Quartz',
        'CoreFoundation',
        'sounddevice',
        'PIL',
        'numpy',
        'requests',
        'modelscope',
        'yaml',
        'librosa',
        'scipy',
        'numba',
        'llvmlite',
        'soundfile',
        'soxr',
        'audioread',
        # 本地 llama.cpp 纠错后端
        'llama_cpp',
        *llama_cpp_hidden,
#        *funasr_onnx_hidden,
        *modelscope_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / 'runtime_hook.py')],
    # 【关键优化：排除重型依赖】
    excludes=[
        # 注意：funasr_onnx 的 sensevoice_bin 在导入时硬依赖 torch，
        # 因此本地 SenseVoice ASR 必须打包 torch，不能排除。
        'torchaudio',      # 排除 TorchAudio (约 100MB)
        'torchvision',     # 排除 TorchVision
        'triton',
        'tensorflow',
        'keras',
        'datasets',
        'pyarrow',
        'umap',
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
        'sklearn',         # 排除 Scikit-learn
#        'sympy',
        'networkx',
#        'llvmlite',
        'cv2',
        # 本安装包不打包的 rewrite 后端
        'langchain',
        'langchain_core',
        'langchain_openai',
        'langchain_community',
        'gguf',
        'bitsandbytes',
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
    name='MyVoiceTyping',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,        # 开启 Strip 移除调试符号
    upx=False,         # macOS 上 UPX 经常失效，建议关闭
    console=False,     # 无终端窗口
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',  # 专门针对 M4 芯片优化
    icon=str(icon_icns) if icon_icns.exists() else None,
    # 签名身份：默认优先使用固定自签名证书；找不到时才回退到 ad-hoc("-")。
    # 固定签名身份可减少重新打包/重装后 TCC 权限反复失效。
    codesign_identity=choose_codesign_identity(),
#    entitlements_file='my.entitlements',  # 关键：添加 entitlements 文件
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    name='MyVoiceTyping',
)

app = BUNDLE(
    coll,
    name='MyVoiceTyping.app',
    icon=str(icon_icns) if icon_icns.exists() else None,
    bundle_identifier='com.myvoicetyping.desktop',
    info_plist={
        'CFBundleName': 'MyVoiceTyping',
        'CFBundleDisplayName': 'MyVoiceTyping',
        "CFBundleShortVersionString": "1.0.0",
        'NSAppleEventsUsageDescription': '此应用需要控制键盘输入以完成跨应用输入文字',
        'NSAccessibilityUsageDescription': '此应用需要辅助功能权限，以便把转录文字写入当前输入位置。',
        'NSInputMonitoringUsageDescription': '此应用需要输入监控权限，以便在后台监听 Fn 语音输入快捷键。',
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
