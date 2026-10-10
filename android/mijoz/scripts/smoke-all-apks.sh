#!/usr/bin/env bash
set -euo pipefail
adb wait-for-device
for flavor in mijoz kuryer oshxona admin; do
  case "$flavor" in
    mijoz) package="uz.alikuryer.customer" ;;
    kuryer) package="uz.alikuryer.courier" ;;
    oshxona) package="uz.alikuryer.restaurant" ;;
    admin) package="uz.alikuryer.admin" ;;
  esac
  adb install -r "android/mijoz/app/build/outputs/apk/$flavor/debug/app-$flavor-debug.apk"
  adb logcat -c
  adb shell am start -n "$package/uz.alikuryer.customer.MainActivity"
  sleep 8
  adb exec-out screencap -p > "/tmp/ali-kuryer-$flavor.png"
  adb logcat -d -s AndroidRuntime:E > "/tmp/ali-kuryer-$flavor-runtime.log"
  if grep -E "FATAL EXCEPTION|Unable to start activity|Process: $package" "/tmp/ali-kuryer-$flavor-runtime.log"; then
    echo "$flavor APP CRASHED"
    exit 1
  fi
  if ! adb shell pidof "$package"; then
    echo "$flavor APP NOT RUNNING"
    exit 1
  fi
  echo "$flavor APP LAUNCH SUCCESS"
  adb shell am force-stop "$package"
done
