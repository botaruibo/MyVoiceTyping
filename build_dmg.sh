#!/bin/bash
set -euo pipefail

# ================= 配置区域 =================
# 应用名称（生成的 .app 文件名，不含后缀）
SRC_APP_NAME="MyVoiceTyping"

# .app 文件所在的目录（通常是 pyinstaller 生成的 dist 目录）
DIST_DIR="dist"
APP_BUNDLE="${DIST_DIR}/${SRC_APP_NAME}.app"

APP_NAME="MyVoiceTyping"

# DMG 暂存目录（仅用于打包，打包后会自动清理）
# 关键修改：使用独立的暂存目录，确保只打包 .app
DMG_STAGING_DIR="dmg_staging"

# 输出的 DMG 文件名
DMG_OUTPUT="MyVoiceTyping_Installer.dmg"

# 图标路径（可选，建议使用 .icns 格式）
ICON_PATH="assets/icon.icns"

# 背景图片路径（可选，建议 600x400 像素）
BACKGROUND_PATH="resources/dmg_background.png"

# 窗口大小
WINDOW_WIDTH=600
WINDOW_HEIGHT=400
ICON_SIZE=100
# ===========================================

cleanup() {
    rm -rf "$DMG_STAGING_DIR"
    for tmp_dmg in rw.*."$DMG_OUTPUT" rw.*"$DMG_OUTPUT"; do
        if [ -e "$tmp_dmg" ]; then
            rm -f "$tmp_dmg"
        fi
    done
}
trap cleanup EXIT

# 检查 .app 是否存在
if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ 错误: 未找到 $APP_BUNDLE"
    echo "请先确保已运行构建命令（如 pyinstaller），并生成了 .app 文件"
    exit 1
fi

echo "🔎 检查打包运行资源..."
REQUIRED_APP_FILES=(
    "$APP_BUNDLE/Contents/Frameworks/mlx/core.cpython-311-darwin.so"
    "$APP_BUNDLE/Contents/Frameworks/mlx/lib/libmlx.dylib"
    "$APP_BUNDLE/Contents/Frameworks/mlx/lib/libjaccl.dylib"
    "$APP_BUNDLE/Contents/Frameworks/mlx/lib/mlx.metallib"
    "$APP_BUNDLE/Contents/Resources/data/config/app_config.json"
    "$APP_BUNDLE/Contents/Resources/data/config/main_prompt.md"
)
for required_file in "${REQUIRED_APP_FILES[@]}"; do
    if [ ! -f "$required_file" ]; then
        echo "❌ 缺少打包资源: $required_file"
        echo "请重新执行: pyinstaller MyVoiceInput.spec"
        exit 1
    fi
done
echo "✅ 打包运行资源检查通过"

choose_codesign_identity() {
    if [ -n "${CODESIGN_IDENTITY:-}" ]; then
        echo "$CODESIGN_IDENTITY"
        return
    fi

    local preferred="MyVoiceTyping Self-Signed"
    if security find-identity -v -p codesigning 2>/dev/null | grep -F "\"${preferred}\"" >/dev/null; then
        echo "$preferred"
        return
    fi

    echo "-"
}

# 签名
# 默认优先使用固定自签名证书；找不到时才回退到 ad-hoc("-")。
# 固定签名身份可以减少重新打包/重装后 TCC 权限反复失效。
CODESIGN_IDENTITY="$(choose_codesign_identity)"
if [ "$CODESIGN_IDENTITY" = "-" ]; then
    echo "🔏 使用 ad-hoc 签名应用（重装后权限会按新应用重新授权，建议先执行 create_signing_cert.sh）..."
else
    echo "🔏 使用证书签名应用: ${CODESIGN_IDENTITY}"
    if ! security find-identity -v -p codesigning 2>/dev/null | grep -F "\"${CODESIGN_IDENTITY}\"" >/dev/null; then
        echo "❌ 找不到有效代码签名身份: ${CODESIGN_IDENTITY}"
        echo "请先执行: bash create_signing_cert.sh"
        echo "并确认输出包含: 1 valid identities found"
        exit 1
    fi
fi
codesign --force --deep --sign "$CODESIGN_IDENTITY" "$APP_BUNDLE"
codesign --verify --deep --strict "$APP_BUNDLE"

if [ "$CODESIGN_IDENTITY" != "-" ]; then
    if ! spctl -a -t exec -vv "$APP_BUNDLE" >/tmp/myvoicetyping_spctl.log 2>&1; then
        cat /tmp/myvoicetyping_spctl.log
        echo "⚠️ Gatekeeper 仍可能拒绝本地自签名应用。"
        echo "   这是 Apple Developer ID / notarization 分发评估，不代表 codesign 签名损坏。"
        echo "   本地自签名主要用于稳定 TCC 权限身份；首次安装后如被拦截，请在“隐私与安全性”中允许打开。"
    fi
fi

# 1. 清理旧的 DMG 文件
if [ -f "$DMG_OUTPUT" ]; then
    echo "🗑️ 清理旧的 DMG 文件: $DMG_OUTPUT"
    rm "$DMG_OUTPUT"
fi

echo "📦 开始打包 DMG..."

# 2. 打包 DMG。优先使用 create-dmg；没有安装时使用 macOS 自带 hdiutil。
if command -v create-dmg &> /dev/null; then
    echo "📂 准备暂存目录: $DMG_STAGING_DIR"
    if [ -d "$DMG_STAGING_DIR" ]; then
        rm -rf "$DMG_STAGING_DIR"
    fi
    mkdir -p "$DMG_STAGING_DIR"

    echo "📋 复制应用到暂存目录..."
    cp -R "$APP_BUNDLE" "$DMG_STAGING_DIR/${APP_NAME}.app"

    CMD=(create-dmg)
    CMD+=(--volname "${APP_NAME} Installer")
    CMD+=(--window-pos 200 120)
    CMD+=(--window-size "$WINDOW_WIDTH" "$WINDOW_HEIGHT")
    CMD+=(--icon-size "$ICON_SIZE")
    CMD+=(--icon "${APP_NAME}.app" 175 190)
    CMD+=(--hide-extension "${APP_NAME}.app")
    CMD+=(--app-drop-link 425 190)
    CMD+=(--no-internet-enable)

    if [ -f "$ICON_PATH" ]; then
        CMD+=(--volicon "$ICON_PATH")
        echo "✅ 使用图标: $ICON_PATH"
    elif [ -f "assets/icon.icns" ]; then
        CMD+=(--volicon "assets/icon.icns")
        echo "✅ 使用图标: assets/icon.icns"
    else
        echo "⚠️ 警告: 未找到图标文件，将使用默认图标"
    fi

    if [ -f "$BACKGROUND_PATH" ]; then
        CMD+=(--background "$BACKGROUND_PATH")
        echo "✅ 使用背景图: $BACKGROUND_PATH"
    fi

    CMD+=("$DMG_OUTPUT")
    CMD+=("$DMG_STAGING_DIR/")

    echo "🚀 执行命令: ${CMD[*]}"
    "${CMD[@]}"

else
    echo "⚠️ 未安装 create-dmg，改用 hdiutil 生成基础 DMG"
    echo "📂 准备暂存目录: $DMG_STAGING_DIR"
    rm -rf "$DMG_STAGING_DIR"
    mkdir -p "$DMG_STAGING_DIR"

    echo "📋 复制应用到暂存目录..."
    cp -R "$APP_BUNDLE" "$DMG_STAGING_DIR/${APP_NAME}.app"

    APP_LINK="$DMG_STAGING_DIR/Applications"
    rm -f "$APP_LINK"
    ln -s /Applications "$APP_LINK"
    hdiutil create \
        -volname "${APP_NAME} Installer" \
        -srcfolder "$DMG_STAGING_DIR" \
        -ov \
        -format UDZO \
        "$DMG_OUTPUT"
fi

echo ""
echo "✅ DMG 打包成功: $DMG_OUTPUT"
