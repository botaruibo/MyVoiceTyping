#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_ROOT="${LLAMA_CPP_TOOLS_ROOT:-$PROJECT_ROOT/tools}"
if [[ "$TOOLS_ROOT" != /* ]]; then
    TOOLS_ROOT="$PROJECT_ROOT/$TOOLS_ROOT"
fi
REPO_URL="${LLAMA_CPP_REPO_URL:-https://github.com/ggml-org/llama.cpp.git}"
REPO_DIR="${LLAMA_CPP_REPO_DIR:-$TOOLS_ROOT/llama.cpp}"
if [[ "$REPO_DIR" != /* ]]; then
    REPO_DIR="$PROJECT_ROOT/$REPO_DIR"
fi
BUILD_DIR="${LLAMA_CPP_BUILD_DIR:-$REPO_DIR/build}"
if [[ "$BUILD_DIR" != /* ]]; then
    BUILD_DIR="$PROJECT_ROOT/$BUILD_DIR"
fi
BIN_DIR="${LLAMA_CPP_BIN_DIR:-$TOOLS_ROOT/bin}"
if [[ "$BIN_DIR" != /* ]]; then
    BIN_DIR="$PROJECT_ROOT/$BIN_DIR"
fi
MODE="${1:---install}"

CONVERT_LINK="$BIN_DIR/convert_hf_to_gguf.py"
QUANTIZE_LINK="$BIN_DIR/llama-quantize"
ENV_FILE="$PROJECT_ROOT/.env.llama_cpp_tools"

usage() {
    cat <<EOF
Usage:
  bash scripts/install_llama_cpp_tools.sh [--check|--install|--update]

Environment overrides:
  LLAMA_CPP_TOOLS_ROOT  default: $PROJECT_ROOT/tools
  LLAMA_CPP_REPO_URL    default: $REPO_URL
  LLAMA_CPP_REPO_DIR    default: $TOOLS_ROOT/llama.cpp
  LLAMA_CPP_BUILD_DIR   default: $REPO_DIR/build
  LLAMA_CPP_BIN_DIR     default: $TOOLS_ROOT/bin
EOF
}

format_size() {
    local path="$1"
    if [ -e "$path" ]; then
        du -sh "$path" 2>/dev/null | awk '{print $1}'
    else
        echo "0B"
    fi
}

find_convert_script() {
    if [ -n "${LLAMA_CPP_CONVERT_SCRIPT:-}" ] && [ -f "$LLAMA_CPP_CONVERT_SCRIPT" ]; then
        echo "$LLAMA_CPP_CONVERT_SCRIPT"
        return 0
    fi
    if [ -f "$CONVERT_LINK" ]; then
        echo "$CONVERT_LINK"
        return 0
    fi
    if command -v convert_hf_to_gguf.py >/dev/null 2>&1; then
        command -v convert_hf_to_gguf.py
        return 0
    fi
    if [ -f "$REPO_DIR/convert_hf_to_gguf.py" ]; then
        echo "$REPO_DIR/convert_hf_to_gguf.py"
        return 0
    fi
    return 1
}

find_quantize_bin() {
    if [ -n "${LLAMA_CPP_QUANTIZE_BIN:-}" ] && [ -x "$LLAMA_CPP_QUANTIZE_BIN" ]; then
        echo "$LLAMA_CPP_QUANTIZE_BIN"
        return 0
    fi
    if [ -x "$QUANTIZE_LINK" ]; then
        echo "$QUANTIZE_LINK"
        return 0
    fi
    if command -v llama-quantize >/dev/null 2>&1; then
        command -v llama-quantize
        return 0
    fi
    if command -v quantize >/dev/null 2>&1; then
        command -v quantize
        return 0
    fi
    local candidates=(
        "$BUILD_DIR/bin/llama-quantize"
        "$BUILD_DIR/bin/Release/llama-quantize"
        "$BUILD_DIR/tools/quantize/llama-quantize"
    )
    local candidate
    for candidate in "${candidates[@]}"; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

print_check() {
    local convert_path=""
    local quantize_path=""
    if convert_path="$(find_convert_script 2>/dev/null)"; then
        echo "✅ convert_hf_to_gguf.py: $convert_path"
    else
        echo "❌ convert_hf_to_gguf.py: 未找到"
    fi
    if quantize_path="$(find_quantize_bin 2>/dev/null)"; then
        echo "✅ llama-quantize: $quantize_path"
    else
        echo "❌ llama-quantize: 未找到"
    fi

    echo "📦 llama.cpp source: $REPO_DIR ($(format_size "$REPO_DIR"))"
    echo "🧱 llama.cpp build:  $BUILD_DIR ($(format_size "$BUILD_DIR"))"
    echo "🔗 tool links:       $BIN_DIR ($(format_size "$BIN_DIR"))"

    if [ -n "$convert_path" ] && [ -n "$quantize_path" ]; then
        echo "✅ llama.cpp GGUF 工具已就绪"
        return 0
    fi
    return 1
}

install_tools() {
    mkdir -p "$TOOLS_ROOT" "$BIN_DIR"

    if convert_path="$(find_convert_script 2>/dev/null)" && quantize_path="$(find_quantize_bin 2>/dev/null)"; then
        ln -sf "$convert_path" "$CONVERT_LINK"
        ln -sf "$quantize_path" "$QUANTIZE_LINK"
        chmod +x "$CONVERT_LINK" "$QUANTIZE_LINK" || true
        echo "✅ llama.cpp 工具已存在，已刷新链接"
        print_check
        return
    fi

    if ! command -v git >/dev/null 2>&1; then
        echo "❌ 缺少命令: git"
        echo "请先安装 Xcode Command Line Tools / Homebrew 后重试。"
        exit 1
    fi

    CMAKE_BIN="$(command -v cmake || true)"
    if [ -z "$CMAKE_BIN" ]; then
        for candidate in /usr/local/bin/cmake /opt/homebrew/bin/cmake; do
            if [ -x "$candidate" ]; then
                CMAKE_BIN="$candidate"
                break
            fi
        done
    fi
    if [ -z "$CMAKE_BIN" ]; then
        echo "❌ 缺少命令: cmake"
        echo "请先安装 CMake 后重试。"
        exit 1
    fi

    if [ ! -d "$REPO_DIR/.git" ]; then
        echo "⬇️ 克隆 llama.cpp（浅克隆）..."
        git clone --depth 1 "$REPO_URL" "$REPO_DIR"
    elif [ "$MODE" = "--update" ]; then
        echo "🔄 更新 llama.cpp..."
        git -C "$REPO_DIR" pull --ff-only
    else
        echo "✅ llama.cpp 源码已存在: $REPO_DIR"
    fi

    echo "🔨 构建 llama-quantize..."
    "$CMAKE_BIN" -S "$REPO_DIR" -B "$BUILD_DIR" \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_METAL=ON \
        -DLLAMA_BUILD_TESTS=OFF

    if ! "$CMAKE_BIN" --build "$BUILD_DIR" --config Release --target llama-quantize -j "$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"; then
        echo "⚠️ 单独构建 llama-quantize 失败，尝试构建默认目标..."
        "$CMAKE_BIN" --build "$BUILD_DIR" --config Release -j "$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"
    fi

    local convert_path
    local quantize_path
    convert_path="$(find_convert_script)"
    quantize_path="$(find_quantize_bin)"

    ln -sf "$convert_path" "$CONVERT_LINK"
    ln -sf "$quantize_path" "$QUANTIZE_LINK"
    chmod +x "$CONVERT_LINK" "$QUANTIZE_LINK" || true

    cat > "$ENV_FILE" <<EOF
export LLAMA_CPP_CONVERT_SCRIPT="$CONVERT_LINK"
export LLAMA_CPP_QUANTIZE_BIN="$QUANTIZE_LINK"
EOF

    echo "✅ llama.cpp 工具安装完成"
    echo "可选：source $ENV_FILE"
    print_check
}

case "$MODE" in
    --check)
        print_check
        ;;
    --install|--update)
        install_tools
        ;;
    -h|--help)
        usage
        ;;
    *)
        echo "❌ 未知参数: $MODE"
        usage
        exit 2
        ;;
esac
