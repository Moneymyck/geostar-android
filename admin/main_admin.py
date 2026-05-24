name: Build GEOSTAR Admin APK

on:
  push:
    branches: [ main, master ]
    paths:
      - 'admin/**'
  workflow_dispatch:

jobs:
  build-admin:
    name: Build Admin APK
    runs-on: ubuntu-22.04
    timeout-minutes: 120

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Set up Java 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            git zip unzip openjdk-17-jdk \
            python3-pip autoconf libtool pkg-config \
            zlib1g-dev libncurses5-dev libncursesw5-dev \
            libtinfo5 cmake libffi-dev libssl-dev \
            build-essential ccache autopoint gettext libltdl-dev

      - name: Cache Buildozer
        uses: actions/cache@v4
        with:
          path: ~/.buildozer
          key: buildozer-admin-${{ runner.os }}-${{ hashFiles('admin/buildozer_admin.spec') }}
          restore-keys: |
            buildozer-admin-${{ runner.os }}-

      - name: Install Buildozer & Cython
        run: |
          python -m pip install --upgrade pip setuptools wheel
          pip install --upgrade Cython==0.29.36 virtualenv
          pip install buildozer==1.5.0

      - name: Build Admin APK
        working-directory: admin
        run: |
          cp buildozer_admin.spec buildozer.spec
          cp main_admin.py main.py
          export PATH=$PATH:~/.local/bin/
          yes | buildozer android debug 2>&1 | tee build.log

      - name: Upload Admin APK
        if: success()
        uses: actions/upload-artifact@v4
        with:
          name: geostar-admin-apk
          path: admin/**/*.apk
          retention-days: 30
          if-no-files-found: warn

      - name: Upload log on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: admin-build-log
          path: admin/build.log
          retention-days: 7
          if-no-files-found: ignore

