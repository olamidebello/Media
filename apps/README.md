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

### LAN device identification

The desktop Scan LAN / Wi-Fi devices action combines TV service discovery with the operating system's IPv4 neighbor table (`ip neigh` on Linux, `arp -a` fallback on Windows/macOS). It shows cached private-network device addresses and MAC addresses where available, plus manufacturer/model metadata advertised by TVs. No public MAC lookup service is contacted. Neighbor tables are partial, may contain stale entries, and cannot enumerate every connected client. Locally administered/random MAC addresses cannot reliably identify a manufacturer. A MAC-only entry remains unclassified and opens the platform selector; no APK is selected solely from a MAC prefix. Android/iOS discovery remains service based because mobile systems restrict access to other devices' MAC addresses.

Automatic app selection uses platform evidence from TV services. Direct ADB installation additionally checks that the paired device reports Android TV/Leanback features, and requires confirmation. Other TV platforms retain their supported installation instructions and signing requirements. This works for devices on Ethernet and Wi-Fi when they share a reachable local network; VLAN/guest isolation may prevent discovery. Update the desktop app after deploying server changes.

### Deploy the LAN/MAC discovery update

Run on the existing Media server as root:

```bash
apt-get update && apt-get install -y ansible git
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-lan-discovery.yml
```

This reuses the database backup, repository pull, dependency installation, restart and health/HTTPS checks, then checks the LAN/MAC interface and desktop discovery source. It preserves the existing server configuration. To publish native app files already downloaded from GitHub Actions and extracted on this server, append `-e media_package_dir=/absolute/server/package/directory`. Follow the exact filenames above; Windows/macOS/Linux build artifacts may need renaming before publishing. Install the new desktop app on the user's LAN computer afterward. This play does not run user-network discovery from the public hosting server, build/sign native apps, or install software on TVs without pairing/approval.


### Active network scanner and click-to-install

In the rebuilt desktop app, open Install on device → Active network scan (desktop). Choose an attached private IPv4 subnet in the native confirmation dialog. The scanner checks fixed web/TV/debugging TCP ports on up to 256 addresses, restricted to that interface's subnet (at most its local /24). It uses native TCP sockets and needs no external scanner installation or administrator privileges. Scanning is bounded to about 30 seconds plus limited device identification requests. Both Ethernet and Wi-Fi interfaces are supported. Unreachable devices, firewalled devices and devices with none of the scanned ports open may not appear. This is not a router's complete connected-client inventory. Scan only your network.

Results show reachable IPs, open ports, available cached MAC addresses and protocol-confirmed platform information. Select **Verify TV and install** for a device advertising the standard ADB TCP port. The app asks for installation confirmation, connects through ADB, requires TV approval/pairing, verifies Android TV/Leanback features and installs the published Android package only after those checks. The open port itself does not prove TV identity. Wireless-debugging devices with dynamic ports can still be found using advertised-service discovery after pairing. Unknown devices and Samsung/LG/Roku/Apple platforms open their installation options rather than receiving an incompatible APK. No credentials are guessed and no platform signing requirement is bypassed. Mobile apps retain advertised-service discovery; active subnet scanning currently requires desktop.

Deploy with `ansible/deploy-lan-discovery.yml`, publish the rebuilt desktop installer and install that new client on the user's LAN computer. Server deployment cannot update a desktop client automatically. Platform Tools (adb) is still required for Android TV installation.

### Install on TV directly from an Android phone

Install the newest universal Android APK on the phone. In `/install`, choose **Pair phone and install on TV**, or select an Android/Fire TV discovered by the native TV picker. The TV may use Ethernet while the phone uses Wi-Fi if both can communicate on the same private network.

For Android/Google TVs with Wireless debugging: enable it in Developer options, select Pair device with pairing code, and enter the TV private IPv4 address, pairing port and six-digit code in the phone app. Tap Pair phone. Then enter the separate connection port from the TV's main Wireless debugging screen and choose Connect, verify TV and install. For Fire/legacy network-debugging TVs, enable ADB debugging, use the TV's network-debugging port (often 5555), skip pairing-code input and approve the phone's connection on the TV.

The phone copies its own universal Africa Media Hub APK directly to the TV over ADB. No desktop or public-server LAN access is required. It checks Android TV/Leanback features before transferring, requires explicit installation confirmation, and reports success only after the TV package installer returns Success. Pairing identity is stored in the phone's private no-backup directory. Pairing codes are cleared after submission. Clear app data to remove the phone's pairing identity; revoke trusted debugging devices in TV settings as needed. Disable TV debugging when no longer required.

Limits: Android phone only; iPhone and normal browsers do not provide this installer. Samsung Tizen, LG webOS, Roku and Apple TV cannot receive Android APKs. Split APK transfer is not supported; use the universal APK built by this repository. Signature/version conflicts or TV restrictions can reject an update; the app never uninstalls the existing TV app automatically. Installation has not been tested on physical TVs. Dependency: LibADB Android 3.1.1 (Apache-2.0 option), Conscrypt and Bouncy Castle, resolved during Android builds. Vendor code and dependency licenses remain applicable.

### Deploy the phone-to-TV installer update

Run on the existing Media server as root:

```bash
apt-get update && apt-get install -y ansible git
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-phone-tv-install.yml
```

This includes the existing database backup, repository pull, dependency installation, service restart, health/HTTPS, My Streaming and LAN checks, then verifies the phone pairing button, bridge integration and native installer source files. It preserves existing server configuration.

To publish the rebuilt universal APK already downloaded from GitHub Actions and extracted on this server, name it `africa-media-android-debug.apk` in an absolute directory and append `-e media_package_dir=/absolute/server/package/directory` to the command. The package directory must be on the target server. Existing packages are not rebuilt by this play. Install the updated APK on the phone afterward; opening the website in a browser does not enable native pairing. TV pairing/approval and physical-device validation remain required.

### Browsing and thumbnail repair

Main navigation exposes Live TV, Movies, Sports, News, Music, Kids & Family and Local Channels directly. News/Music now open independent searchable category grids instead of targeting a removed Live TV dropdown. Category pages have refresh, search, pagination and clear empty/error states. Late navigation responses do not replace the selected tab. Sections without published on-demand videos explain their empty state.

Channel imports preserve HTTPS `tvg-logo` artwork, including for existing channels, without re-enabling disabled entries. Video submissions accept an optional HTTPS thumbnail URL. Cards and guide rows display available artwork and use a clearly labeled branded fallback when an image is missing or broken; fallback graphics are not video screenshots. Existing videos need publisher-supplied poster URLs for actual thumbnail images.

Deploy on the existing Media server:

```bash
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-browse-repair.yml
```

The updater backs up the database and deploys server changes, then adds artwork columns and backfills logos from bundled playlists. It does not fetch new playlists, change channel visibility or guarantee source playback. Refresh other playlists through Admin to bring in their logos. Reload the browser/app after deployment. Physical device and live UI verification remain pending.

### Requested administrator roles

`ansible/deploy-requested-roles.yml` deploys the browsing repair and superadmin-aware authorization, then assigns `dg857641@gmail.com` the admin role and `dobcalldemo@gmail.com` the superadmin role. It requires exactly one existing account for each email before changing either, preserves passwords and account active flags, audits changes and revokes changed accounts' sessions. Both users must sign in again after a role change. Regular admins cannot modify superadmin accounts or grant the superadmin role through account APIs. This server playbook must complete before the account changes are effective.
