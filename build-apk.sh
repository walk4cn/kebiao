#!/usr/bin/env bash
# 打包 Android APK（可移植版）
#
#   工作区 index.html / data.js
#     -> 无空格构建工程 $PROJ/assets
#     -> Gradle + JDK17 + Android SDK 构建
#     -> kebiao.jks 签名的 release APK
#     -> 拷回工作区 课表.apk
#
# 首次运行会自动：复制 android/ 工程、生成 kebiao.jks 签名、写 local.properties。
# 之后每次运行只同步网页资源并增量构建。
#
# 环境变量（均有默认值，一般不用改）：
#   ANDROID_TOOLS  工具链根目录（无空格），默认 ~/.workbuddy-ai/binaries/android
#   APK_PROJ       构建工程目录（无空格），默认 ~/.workbuddy/projects/kebiao-apk
#   KB_OFFLINE=1   离线构建（依赖已缓存时更快）
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

TOOLS="${ANDROID_TOOLS:-$HOME/.workbuddy-ai/binaries/android}"
PROJ="${APK_PROJ:-$HOME/.workbuddy/projects/kebiao-apk}"

# gradle.bat / keytool 是 Windows 程序，需要 C:\... 形式的路径
winpath() { cygpath -w "$1" 2>/dev/null || echo "$1"; }
export JAVA_HOME="$(winpath "$TOOLS/jdk-17")"
export ANDROID_HOME="$(winpath "$TOOLS/sdk")"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$TOOLS/jdk-17/bin:$PATH"

GRADLE="$TOOLS/gradle-8.7/bin/gradle.bat"
[ -f "$TOOLS/gradle-8.7/bin/gradle" ] && GRADLE="$TOOLS/gradle-8.7/bin/gradle"

die() { echo "错误：$*" >&2; exit 1; }

# ---------- 1. 工具链自检 ----------
[ -f "$TOOLS/jdk-17/bin/java.exe" ]  || die "找不到 JDK：$TOOLS/jdk-17/bin/java.exe"
[ -d "$TOOLS/sdk/platforms" ]         || die "找不到 Android SDK：$TOOLS/sdk"
[ -f "$GRADLE" ]                      || die "找不到 Gradle：$GRADLE"

# ---------- 2. 准备构建工程（无空格路径） ----------
mkdir -p "$PROJ/app/src/main/assets"
cp -f "$ROOT"/android/*.gradle "$ROOT"/android/gradle.properties "$PROJ/" 2>/dev/null || true
mkdir -p "$PROJ/app/src/main/java/com/kebiao/app" "$PROJ/app/src/main/res"
cp -rf "$ROOT"/android/app/. "$PROJ/app/"
# 不删 build 目录：Gradle 自带 up-to-date 检查，保留才能增量构建
# （且批量删除会触发沙箱保护）。需要彻底重建时手动跑 gradle clean

# 网页资源以工作区为准（assets 里的旧副本会被覆盖）
cp -f "$ROOT/index.html" "$ROOT/data.js" "$PROJ/app/src/main/assets/"

# Android SDK 位置
echo "sdk.dir=${ANDROID_HOME//\\/\/}" > "$PROJ/local.properties"

# ---------- 3. 签名文件（缺失则生成） ----------
if [ ! -f "$PROJ/kebiao.jks" ]; then
  echo ">> 未找到签名，生成 kebiao.jks ..."
  "$TOOLS/jdk-17/bin/keytool.exe" -genkeypair -v \
    -keystore "$PROJ/kebiao.jks" -keyalg RSA -keysize 2048 -validity 10950 \
    -alias kebiao -storepass kebiao2026 -keypass kebiao2026 \
    -dname "CN=Kebiao, OU=App, O=Kebiao, L=Unknown, ST=Unknown, C=CN" >/dev/null
fi

# ---------- 4. 构建 ----------
cd "$PROJ"
GRADLE_ARGS=(assembleRelease)
[ -n "$KB_OFFLINE" ] && GRADLE_ARGS+=(--offline)
"$GRADLE" "${GRADLE_ARGS[@]}"

# ---------- 5. 拷回工作区 ----------
APK="$PROJ/app/build/outputs/apk/release/app-release.apk"
[ -f "$APK" ] || die "构建未产出 APK：$APK"
cp -f "$APK" "$ROOT/课表.apk"
echo "OK -> $ROOT/课表.apk"
