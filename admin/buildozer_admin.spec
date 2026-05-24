[app]
title = GEOSTAR Admin
package.name = geostaradmin
package.domain = org.geostar
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
source.exclude_exts = spec,md,txt
source.exclude_dirs = tests,bin,venv,.venv,.git,.github,__pycache__,.buildozer
version = 1.0
requirements = python3,kivy==2.3.0,pillow,certifi,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.release_artifact = apk
android.debug_artifact = apk
p4a.branch = v2024.01.21
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
