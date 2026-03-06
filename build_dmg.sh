#!/bin/bash

# ================= 配置区域 =================
# 应用名称（生成的 .app 文件名，不含后缀）
SRC_APP_NAME="MyVoiceInput"

# .app 文件所在的目录（通常是 pyinstaller 生成的 dist 目录）
DIST_DIR="dist"
APP_BUNDLE="${DIST_DIR}/${SRC_APP_NAME}.app"

APP_NAME="MyVoiceInput"

#cp -R ./data/models $APP_BUNDLE/Contents/Resources/data
#签名
codesign --force --deep --sign - "$APP_BUNDLE"

# DMG 暂存目录（仅用于打包，打包后会自动清理）
# 关键修改：使用独立的暂存目录，确保只打包 .app
DMG_STAGING_DIR="dmg_staging"

# 输出的 DMG 文件名
DMG_OUTPUT="${APP_NAME}_Installer.dmg"

# 图标路径（可选，建议使用 .icns 格式）
ICON_PATH="resources/app.icns"

# 背景图片路径（可选，建议 600x400 像素）
BACKGROUND_PATH="resources/dmg_background.png"

# 窗口大小
WINDOW_WIDTH=600
WINDOW_HEIGHT=400
ICON_SIZE=100
# ===========================================

# 检查 create-dmg 是否安装
if ! command -v create-dmg &> /dev/null; then
    echo "❌ 错误: create-dmg 未安装"
    echo "请运行: brew install create-dmg"
    exit 1
fi

# 检查 .app 是否存在
if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ 错误: 未找到 $APP_BUNDLE"
    echo "请先确保已运行构建命令（如 pyinstaller），并生成了 .app 文件"
    exit 1
fi

# 1. 准备纯净的暂存目录
echo "📂 准备暂存目录: $DMG_STAGING_DIR"
if [ -d "$DMG_STAGING_DIR" ]; then
    rm -rf "$DMG_STAGING_DIR"
fi
mkdir -p "$DMG_STAGING_DIR"

# 2. 只复制 .app 到暂存目录
echo "📋 复制应用到暂存目录..."
cp -R "$APP_BUNDLE" "$DMG_STAGING_DIR/${APP_NAME}.app"

# 3. 清理旧的 DMG 文件
if [ -f "$DMG_OUTPUT" ]; then
    echo "🗑️ 清理旧的 DMG 文件: $DMG_OUTPUT"
    rm "$DMG_OUTPUT"
fi

echo "📦 开始打包 DMG..."

# 4. 构建 create-dmg 命令
# 使用数组来构建命令，避免引用问题
CMD=(create-dmg)
CMD+=(--volname "${APP_NAME} Installer")
CMD+=(--window-pos 200 120)
CMD+=(--window-size "$WINDOW_WIDTH" "$WINDOW_HEIGHT")
CMD+=(--icon-size "$ICON_SIZE")
CMD+=(--icon "${APP_NAME}.app" 175 190)
CMD+=(--hide-extension "${APP_NAME}.app")
CMD+=(--app-drop-link 425 190)
CMD+=(--no-internet-enable)

# 如果有自定义图标
if [ -f "$ICON_PATH" ]; then
    CMD+=(--volicon "$ICON_PATH")
    echo "✅ 使用图标: $ICON_PATH"
else
    # 尝试在资源目录找找看
    if [ -f "src/resources/app.icns" ]; then
         CMD+=(--volicon "src/resources/app.icns")
         echo "✅ 使用图标: src/resources/app.icns"
    else
         echo "⚠️ 警告: 未找到图标文件，将使用默认图标"
    fi
fi

# 如果有背景图
if [ -f "$BACKGROUND_PATH" ]; then
    CMD+=(--background "$BACKGROUND_PATH")
    echo "✅ 使用背景图: $BACKGROUND_PATH"
fi

# 输出文件和源目录（注意这里指向的是暂存目录）
CMD+=("$DMG_OUTPUT")
CMD+=("$DMG_STAGING_DIR/")

# 5. 执行命令
echo "🚀 执行命令: ${CMD[*]}"
"${CMD[@]}"

RET_CODE=$?

# 6. 清理暂存目录
echo "🧹 清理暂存目录..."
rm -rf "$DMG_STAGING_DIR"

if [ $RET_CODE -eq 0 ]; then
    echo ""
    echo "✅ DMG 打包成功: $DMG_OUTPUT"
else
    echo ""
    echo "❌ DMG 打包失败"
    exit 1
fi