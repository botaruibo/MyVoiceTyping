# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
import importlib.util
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

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
#modelscope_hidden = collect_submodules('modelscope')

# 本地 MLX 纠错后端依赖 mlx / mlx_lm，需收集其子模块
mlx_hidden = []
for pkg in ('mlx', 'mlx_lm'):
    try:
        mlx_hidden += collect_submodules(pkg)
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

        # 本安装包内置本地 MLX 纠错模型，默认启用文本改写。
        # 仅保留本地 MLX 后端，云端 LLM 与 llama.cpp 相关库不打包。
        config['format_text'] = True
        config['llm_text_provider'] = 'local_mlx_corrector'
        config['preload_local_mlx_corrector_on_startup'] = True
        config['preload_llama_cpp_on_startup'] = False

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

for model_name in (
    'SenseVoiceSmall-onnx',
    'punc_ct-onnx',
    # 本地 MLX 中文纠错模型（rewrite 默认后端）
    'chinese-text-correction-1.5b-mlx-4bit',
):
    model_dir = project_root / 'data' / 'models' / model_name
    if model_dir.exists():
        datas.append((str(model_dir), f'data/models/{model_name}'))

# MLX / transformers 的运行期数据文件（tokenizer、配置模板等）
for pkg in ('mlx_lm', 'transformers'):
    try:
        datas += collect_data_files(pkg, include_py_files=False)
    except Exception:
        pass

# MLX 的 Metal shader 运行库不是 dylib，PyInstaller 不会随 dynamic libs 自动收集。
# 缺少该文件时打包应用会报：Failed to load the default metallib.
mlx_metallib_path = None
try:
    mlx_spec = importlib.util.find_spec('mlx')
    mlx_package_dir = None
    if mlx_spec and mlx_spec.origin:
        mlx_package_dir = Path(mlx_spec.origin).resolve().parent
    elif mlx_spec and mlx_spec.submodule_search_locations:
        mlx_package_dir = Path(next(iter(mlx_spec.submodule_search_locations))).resolve()

    if mlx_package_dir is not None:
        candidate = mlx_package_dir / 'lib' / 'mlx.metallib'
        if candidate.exists():
            mlx_metallib_path = candidate
            datas.append((str(candidate), 'mlx/lib'))
except Exception:
    pass

binaries = []
try:
    binaries += collect_dynamic_libs('mlx')
except Exception:
    pass

for libomp_candidate in (
    project_root / '.venv' / 'lib' / 'python3.11' / 'site-packages' / 'torch' / 'lib' / 'libomp.dylib',
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
        'pyautogui',
        'pygetwindow',
        'pyperclip',
        'sounddevice',
        'PIL',
        'numpy',
        'requests',
        'yaml',
        'librosa',
        'scipy',
        'numba',
        'llvmlite',
        'soundfile',
        'soxr',
        'audioread',
        # 本地 MLX 纠错后端
        'mlx',
        'mlx_lm',
        'mlx_lm.models.base',
        'mlx_lm.models.cache',
        'mlx_lm.models.rope_utils',
        'mlx_lm.models.qwen2',
        'transformers',
        'huggingface_hub',
        *mlx_hidden,
#        *funasr_onnx_hidden,
#        *modelscope_hidden,
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
        'modelscope',
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
        'llama_cpp',
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

# BUNDLE 会把 datas 放入 Contents/Resources，而 MLX 的 libmlx 在打包后位于
# Contents/Frameworks/mlx/lib。额外复制一份到 libmlx 同目录，匹配 wheel 原始布局。
try:
    if mlx_metallib_path is not None:
        bundled_mlx_lib = project_root / 'dist' / 'MyVoiceTyping.app' / 'Contents' / 'Frameworks' / 'mlx' / 'lib'
        if bundled_mlx_lib.exists():
            shutil.copy2(mlx_metallib_path, bundled_mlx_lib / 'mlx.metallib')
except Exception as e:
    print(f'⚠️ 复制 MLX metallib 到 Frameworks 失败: {e}')
