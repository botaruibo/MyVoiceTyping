#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
PYINSTALLER_BIN="$PROJECT_ROOT/venv/bin/pyinstaller"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "❌ 未找到项目虚拟环境: $PYTHON_BIN"
    echo "请先创建或修复 venv，然后执行: venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

if [ ! -x "$PYINSTALLER_BIN" ]; then
    echo "❌ 未找到 PyInstaller: $PYINSTALLER_BIN"
    echo "请先执行: venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

export PYINSTALLER_CONFIG_DIR="$PROJECT_ROOT/.pyinstaller-cache"

echo "🐍 Python: $("$PYTHON_BIN" -V)"
echo "📦 PyInstaller: $("$PYINSTALLER_BIN" --version)"
echo "🧰 PyInstaller cache: $PYINSTALLER_CONFIG_DIR"

"$PYINSTALLER_BIN" --noconfirm MyVoiceTyping.spec
