# Device apps

These projects are build sources. A committed project is not evidence of a successful native package build or store acceptance. All clients require the live server at https://media.africandroid.world.

| Device | Project | Build output / limit |
|---|---|---|
| Android phone/tablet | android | Development-signed APK; Java 17, Gradle 8.9, SDK 35 |
| Android/Google TV, Fire TV | android | Same APK declares TV launcher and no touchscreen requirement; physical remote/media testing required |
| Windows | desktop | Unsigned NSIS installer |
| macOS | desktop | Unsigned/unnotarized DMG |
| Linux | desktop | AppImage |
| iPhone/iPad | apple | WKWebView iOS source; CI simulator compile only |
| Apple TV | apple | Native SwiftUI guide and AVPlayer live playback; CI simulator compile only |
| LG webOS | tv-web | `ares-package apps/tv-web`; vendor SDK/Developer Mode required |
| Samsung Tizen | tv-web | `tizen build-web -- apps/tv-web` then `tizen package -t wgt -s YOUR_PROFILE -- apps/tv-web/.buildResult`; vendor SDK and signing profile required |
| Chromebook/other browser devices | installed PWA | Use /install |
| Roku | Not implemented | Requires a separate SceneGraph client; browser/PWA cannot be assumed |

GitHub Actions `Build device apps` runs for app source pushes and manual dispatch. Android/desktop jobs upload workflow artifacts. Apple jobs compile simulator targets and do not produce distributable IPA files. Workflow success must be checked; no package has been verified at source creation time.

Release signing, notarization and store submission are separate steps. Do not use the debug Android key for production updates. Download/debug sideloads may require developer permissions; unsigned desktop software may prompt security dialogs. Clients do not implement DRM or guarantee every media codec.

To publish approved outputs to the server, put them in `/var/lib/africa-media/downloads` with these exact names:

- africa-media-android-debug.apk
- africa-media-windows.exe
- africa-media-macos.dmg
- africa-media-linux.AppImage
- africa-media-samsung.wgt
- africa-media-lg.ipk

Run `ansible/deploy-device-apps.yml` with `-e media_package_dir=/absolute/server/path/to/approved/packages` after the web deployment. The directory is on the target server. Only nonempty recognized files are copied. The install page fetches availability from the server, so no missing package is advertised. Existing deployed packages are not automatically deleted.
