#!/usr/bin/env bash
# 打包 Android APK：
#   工作区 index.html/data.js  ->  无空格构建工程 .workbuddy/projects/kebiao-apk/assets
#   -> 本地 Gradle 8.7 + JDK17 构建 kebiao.jks 签名的 release APK -> 拷回工作区 课表.apk
set -e
cd "$(dirname "$0")"
PROJ="C:/Users/Lenovo/.workbuddy/projects/kebiao-apk"

mkdir -p "$PROJ/app/src/main/assets"
cp index.html data.js "$PROJ/app/src/main/assets/"

export JAVA_HOME='C:\Users\Lenovo\.workbuddy\binaries\android\jdk-17'
export ANDROID_HOME='C:\Users\Lenovo\Android\Sdk'
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

cd "$PROJ"
"C:/Users/Lenovo/.workbuddy/binaries/android/gradle-8.7/bin/gradle.bat" --offline -q assembleRelease
cp app/build/outputs/apk/release/app-release.apk "C:/Users/Lenovo/Documents/Default Project/kebiao/课表.apk"
echo "OK -> 课表.apk"
