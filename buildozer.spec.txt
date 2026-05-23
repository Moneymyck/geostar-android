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

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec,md,txt

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, __pycache__, .buildozer

# (str) Application versioning (method 1)
version = 12.25

# (list) Application requirements
# Versions volontairement fixées pour compatibilité GitHub Actions / p4a 2024+
requirements = python3,kivy==2.3.0,pillow,certifi,pyjnius,android

# (str) Custom source folders for requirements
# Used to add custom source folders for the requirements
# requirements.source.kivy = ../../kivy

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# Permissions utilisées par l'application (notes, micro, stockage)
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,VIBRATE

# (int) Target Android API, should be as high as possible.
# 34 = Android 14 (exigence Play Store août 2024+)
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
android.ndk_api = 21

# (str) Android NDK version to use
# Laissé vide pour utiliser le NDK installé par GitHub Actions automatiquement.

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer.
android.accept_sdk_license = True

# (list) The Android archs to build for
# arm64-v8a = téléphones modernes 64 bits (obligatoire Play Store)
# armeabi-v7a = anciens téléphones 32 bits
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk).
# apk = installation directe sur tablette/téléphone
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) python-for-android branch to use, defaults to master
p4a.branch = master

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
