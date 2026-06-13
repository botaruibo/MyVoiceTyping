#!/bin/bash
set -euo pipefail

# ============================================================================
# 创建一张本地“自签名代码签名证书”，用于稳定签名 MyVoiceTyping。
#
# 为什么需要它：
#   ad-hoc 签名(codesign --sign -)没有稳定身份，其 TCC“指定要求”只能锚定到
#   cdhash，而 cdhash 由二进制内容决定 —— 每次重新打包都会变，导致系统认为是
#   “另一个应用”，已授予的输入监控/辅助功能等权限随之失效，必须手动删除重加。
#
#   改用一张固定的自签名证书后，TCC 指定要求会锚定到证书，重新打包(cdhash 变化)
#   仍然匹配，权限得以长期保留。该证书完全本地、免费，不需要 Apple 开发者账号。
#
# 用法：
#   bash create_signing_cert.sh                 # 使用默认证书名
#   CERT_NAME="My Cert" bash create_signing_cert.sh
#
# 创建完成后，用同名身份打包即可：
#   CODESIGN_IDENTITY="MyVoiceTyping Self-Signed" bash build_dmg.sh
# ============================================================================

CERT_NAME="${CERT_NAME:-MyVoiceTyping Self-Signed}"
KEYCHAIN="${KEYCHAIN:-$HOME/Library/Keychains/login.keychain-db}"

echo "🔐 准备创建自签名代码签名证书: ${CERT_NAME}"

# 已存在有效签名身份则跳过，避免重复创建。
if security find-identity -v -p codesigning "$KEYCHAIN" 2>/dev/null | grep -F "\"${CERT_NAME}\"" >/dev/null; then
    echo "✅ 有效签名身份已存在，无需重复创建: ${CERT_NAME}"
    echo "   可直接打包: CODESIGN_IDENTITY=\"${CERT_NAME}\" bash build_dmg.sh"
    exit 0
fi

# 如果只有同名证书但没有有效私钥/信任关系，先删除同名证书后重建。
if security find-certificate -c "$CERT_NAME" "$KEYCHAIN" >/dev/null 2>&1; then
    echo "⚠️ 发现同名证书，但它不是有效代码签名身份；将删除后重建: ${CERT_NAME}"
    security delete-certificate -c "$CERT_NAME" "$KEYCHAIN" >/dev/null 2>&1 || true
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# openssl 配置：关键是 extendedKeyUsage = codeSigning，否则 codesign 不接受。
cat > "$WORKDIR/cert.cnf" <<EOF
[ req ]
distinguished_name = dn
x509_extensions = v3_ext
prompt = no

[ dn ]
CN = ${CERT_NAME}

[ v3_ext ]
basicConstraints = critical,CA:true
keyUsage = critical,digitalSignature,keyCertSign
extendedKeyUsage = critical,codeSigning
EOF

echo "🧪 生成密钥与自签名证书..."
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$WORKDIR/key.pem" \
    -out "$WORKDIR/cert.pem" \
    -days 3650 \
    -config "$WORKDIR/cert.cnf"

# 直接导入 PEM 证书和私钥，避免 PKCS#12 在 macOS security import 中
# 偶发出现 "MAC verification failed during PKCS12 import"。
echo "📥 导入登录钥匙串..."
security import "$WORKDIR/cert.pem" \
    -k "$KEYCHAIN" \
    -T /usr/bin/codesign \
    -T /usr/bin/security

security import "$WORKDIR/key.pem" \
    -k "$KEYCHAIN" \
    -T /usr/bin/codesign \
    -T /usr/bin/security

echo "🔏 信任为代码签名证书..."
security add-trusted-cert \
    -r trustRoot \
    -p codeSign \
    -k "$KEYCHAIN" \
    "$WORKDIR/cert.pem"

# 设置私钥访问控制，避免 codesign 时反复弹出钥匙串授权框。
security set-key-partition-list -S apple-tool:,apple: -k "" "$KEYCHAIN" >/dev/null 2>&1 || true

if ! security find-identity -v -p codesigning "$KEYCHAIN" 2>/dev/null | grep -F "\"${CERT_NAME}\"" >/dev/null; then
    echo "❌ 证书已导入，但没有形成有效代码签名身份。"
    echo "   请打开“钥匙串访问”，检查 ${CERT_NAME} 是否包含私钥并被信任。"
    exit 1
fi

echo ""
echo "✅ 证书已创建并导入: ${CERT_NAME}"
echo ""
echo "下一步：用这张证书打包（权限将在重装后保留）"
echo "    CODESIGN_IDENTITY=\"${CERT_NAME}\" bash build_dmg.sh"
echo ""
echo "开发期如需清理旧的僵尸权限授权，可执行："
echo "    tccutil reset All com.myvoicetyping.desktop"
