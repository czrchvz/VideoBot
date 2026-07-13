[app]
title           = VideoBot
package.name    = videobot
package.domain  = org.cesarbot
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json
version         = 1.0
requirements    = python3,kivy==2.2.1,requests,certifi,urllib3,charset-normalizer,idna
orientation     = portrait
fullscreen      = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api     = 33
android.minapi  = 26
android.ndk     = 25b
android.archs   = arm64-v8a
android.allow_backup = True
[buildozer]
log_level = 2
warn_on_root = 1