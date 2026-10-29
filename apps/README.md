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
| Roku | roku | SceneGraph live channel guide and HTTPS HLS/MP4 playback; development sideload ZIP, physical testing required |

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


## TV detection and installation

`/install` selects the package by operating system, never by brand alone. Users can override the estimate. Android, Fire TV, Samsung Tizen, LG webOS, Roku, Apple TV, VIDAA and Titan OS have separate instructions. A package link is shown only if its download is published. No native VIDAA/Titan client or public store listing is configured.

The desktop app discovers ADB and SSDP services on private IPv4 LAN addresses. SSDP results choose platform guidance; they do not imply install permission. Direct Android/Fire installation requires Platform Tools and TV pairing/approval. Cast and AirPlay are not app installers. Samsung uses the existing Tizen project and requires Samsung SDK and signing certificates; Apple CI only compiles simulator apps and cannot produce a distributable tvOS build without provisioning.

### Mobile Wi-Fi discovery

The Android app's Install on device button opens a native discovery screen after confirmation. It searches advertised Cast, Android TV, ADB, AirPlay, webOS and Roku services for 12 seconds, with additional SSDP discovery on Android. Private IPv4 addresses remain on the phone. Selecting a result opens `/install?tvPlatform=...` with the recommended platform selected and a manual override. Cast/AirPlay service discovery is an estimate, not proof of a TV OS. Samsung/Fire/other TVs without these services may not appear.

Phone-to-TV APK installation is not implemented: paired ADB installation currently requires the desktop app. Samsung/LG/Roku use their developer installation processes; Apple requires signed distribution. The iOS native app also provides Bonjour discovery over Wi-Fi after Local Network permission, with platform selection and installation guidance. Ordinary mobile browsers provide manual platform selection only. iOS distribution still requires Apple signing/TestFlight or the App Store. Guest Wi-Fi isolation, permissions and TV standby can prevent discovery. The Android app must be rebuilt for this capability.

### Build outputs

`python3 scripts/package-roku.py` produces `packages/africa-media-roku.zip`; upload this file through the TV's Roku Development Application Installer after enabling Developer Mode. The current sideloaded channel is replaced. The Roku app plays compatible HTTPS HLS/MP4 channels from the live guide; browser-provider pages and DRM sources are excluded.

The Build device apps workflow builds Android/Fire, desktop, Roku ZIP and LG webOS IPK, and compiles Apple simulator apps. LG uses the official `@webos-tools/cli`. Samsung package creation remains dependent on a configured Samsung SDK/certificate profile; no unsigned ZIP is advertised as an installable WGT. For Samsung, run the SDK commands listed in the table above on your configured signing workstation. Store approval and device tests are separate from packaging.

Publish `africa-media-roku.zip` alongside the existing package filenames using `ansible/deploy-device-apps.yml`. Workflow artifacts are not automatically copied to the live server.

## Deploy the TV and mobile installation update

On the server already hosting Media, run as root:

```bash
apt-get update && apt-get install -y ansible git
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-tv-install.yml
```

This backs up SQLite, pulls main into `/opt/africa-media`, installs requirements, checks Python syntax, restarts `africa-media`, and verifies local health, installation assets and public HTTPS. Existing Nginx, TLS, credentials and channel settings are preserved. Local source edits cause the pull to fail rather than being overwritten. Failures are reported; no automatic database rollback is attempted. Override `media_root`, `media_port` or `media_domain` with `-e` for a customized installation. Use `-e media_verify_https=false` only when intentionally skipping the public check.

To also publish completed native packages downloaded from GitHub Actions and extracted on the server, append `-e media_package_dir=/absolute/path/to/packages`. Use the exact filenames listed above; this does not build packages or configure store signing. The new mobile/desktop clients must be installed for native discovery. `scripts/deploy-tv-install.sh` wraps the same command and accepts the optional package directory as its first argument.
