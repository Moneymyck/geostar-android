[app]

# (str) Title of your application
title = GEOSTAR

# (str) Package name
package.name = geostar

# (str) Package domain (needed for android/ios packaging)
package.domain = org.geostar

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,json,ttf

# (list) Source files to exclude
source.exclude_exts = spec,md,txt

# (list) List of directory to exclude
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, __pycache__, .buildozer

# (str) Application versioning
version = 12.25

# (list) Application requirements
# Note : on ne pin PAS python3 ici, c'est p4a qui gere la version Python
requirements = python3,kivy==2.3.0,pillow,certifi,pyjnius,android

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,VIBRATE

# (int) Target Android API
android.api = 33

# (int) Minimum API
android.minapi = 21

# (int) Android NDK API
android.ndk_api = 21

# (bool) auto-accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) auto backup
android.allow_backup = True

# (str) release format
android.release_artifact = apk

# (str) debug format
android.debug_artifact = apk

#
# Python for android (p4a) - VERSION CRITIQUE
#

# IMPORTANT : on epingle p4a a la release 2024.01.21
# car master utilise Python 3.14 incompatible avec Kivy 2.3.0
# La release 2024.01.21 utilise Python 3.11 (stable, compatible Kivy 2.3.0)
p4a.branch = 2024.01.21

# (str) Bootstrap
p4a.bootstrap = sdl2


[buildozer]

# (int) Log level
log_level = 2

# (int) Warn on root
warn_on_root = 1
