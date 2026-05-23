[app]

# (str) Title of your application
title = GEOSTAR

# (str) Package name
package.name = geostar

# (str) Package domain (needed for android/ios packaging)
package.domain = org.geostar

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,ttf

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec,md,txt

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, __pycache__, .buildozer

# (str) Application versioning (method 1)
version = 12.25

# (list) Application requirements
# IMPORTANT : python3==3.11.9 obligatoire car Kivy 2.3.0 ne compile pas avec Python 3.14
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,pillow,certifi,pyjnius,android

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,VIBRATE

# (int) Target Android API
android.api = 34

# (int) Minimum API
android.minapi = 21

# (int) Android NDK API to use.
android.ndk_api = 21

# (bool) auto-accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature
android.allow_backup = True

# (str) The format used to package the app for release mode
android.release_artifact = apk

# (str) The format used to package the app for debug mode
android.debug_artifact = apk

# (str) python-for-android branch to use
p4a.branch = master

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2


[buildozer]

# (int) Log level
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
