# Africa Media Hub

A working first release for Olamidepanel combining a viewer catalog, creator submissions and live channel scheduling. Built with Python WSGI, SQLite, vanilla JavaScript, Gunicorn and Nginx. No proprietary Hulu or YouTube content is included.

## Implemented

- Responsive Home, TV, Movies, Sports, Shorts, Podcasts, Search, Live TV, My Stuff, History, Creator Studio, Settings, Help and administrator navigation.
- Registration and sign-in, scrypt passwords, expiring HttpOnly sessions, CSRF checks, up to six profiles and child-friendly catalog filtering. Kids profiles are content filters, not PIN-protected parental controls.
- HTTPS media URL submission; draft moderation; administrator publish, unpublish and delete; native browser playback, speed, volume, full screen and browser-supported captions/PiP controls. No sample copyrighted content is seeded.
- Save/remove titles, like/dislike, report, comments (disabled for child-directed content), playlists creation and playlist API, persistent viewing progress and history. Resume UI, playlist contents UI and subscriptions are not yet implemented.
- Live channel and schedule administration; guide and live playback. HLS requires a browser with native HLS support; MP4 works in compatible browsers. The platform does not fetch media server-side.
- Account role management, suspension, reports and administrator audit trail.
- Recorder request schema with honest pending state. Recording is disabled on guide entries until a real capture worker is added.

## Olamidepanel installation

Default hostname: **media.olamidepanel.com**. This is a proposed hostname, not a claim that DNS or hosting is configured. Point its A record to your chosen Olamidepanel server, and remove conflicting AAAA records if IPv6 is unavailable. Use a dedicated hostname without an existing conflicting Nginx server block.

Run on the Debian 12 server:

```bash
sudo apt-get update
sudo apt-get install -y git ansible python3
sudo ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-bootstrap -i localhost, -c local \
  ansible/pull-and-deploy.yml \
  -e media_domain=media.olamidepanel.com \
  -e media_tls=true -e media_email=YOUR_EMAIL
```

After installation, set the administrator account using the private interactive password prompt:

```bash
sudo -u africa-media env MEDIA_DB=/var/lib/africa-media/media.db \
  python3 /opt/africa-media/app.py admin --email YOUR_EMAIL
```

Open `https://media.olamidepanel.com`. No administrator password is committed, generated publicly or assigned to the first registrant. Repeat the Ansible command to update. Persistent data is outside the source tree. Certbot renewals use the system timer installed by Debian. Verify DNS before enabling TLS. Set `media_tls=false` only for a temporary HTTP test; its session cookie is not Secure.

The playbook installs a separate service on loopback port 18840, a dedicated Nginx virtual host and login rate limiting. It does not install or replace the Olamidepanel application, alter other sites, or register an entry in a proprietary panel database. Back up `/var/lib/africa-media/media.db` before updates. SQLite suits an initial deployment; migrate to PostgreSQL and object storage before large-scale distribution.

## Development and checks

```bash
MEDIA_SECURE_COOKIE=0 python3 app.py serve
python3 -m unittest discover -s tests -v
node --check static/app.js
```

Development URL: http://127.0.0.1:18840. Production uses Gunicorn from requirements.txt. Run the init command before starting WSGI directly.

## Remaining work against the requested inventory

This first release does **not** provide feature parity with Hulu, YouTube TV or YouTube. The following need additional implementation and/or provisioned providers:

| Area | Still required |
|---|---|
| Content ingestion | File upload/object storage, transcoding, thumbnails, subtitles ingestion, chapters, editor, scheduled publishing |
| Live operations | Encoder ingest, stream keys, stream health, live chat and moderation, replay and premiere pipelines |
| DVR | Capture worker, retention policy, storage quota, scheduled capture, playback artifacts, series rules, seeking and restart buffer |
| Commercial access | Plans, entitlements, payment webhooks, billing portal, add-ons, concurrent-stream leases, household and territory verification, DRM |
| Creator community | Channel pages, subscriptions, notifications, posts, polls, memberships, payouts, advertising and copyright workflows |
| Discovery and analytics | Recommendation engine, full search filters, reporting dashboards and exports |
| Viewing | Multiview, casting integration, offline rights/downloads, 4K renditions, language tracks, sports stats and key plays |
| Account operations | Verified email, password reset delivery, profile PINs, device management, family invitations and home-network rules |
| Apps | Native Android/iOS/TV clients and app-store builds |

Channel distribution, recording and territorial availability must be configured according to the rights of the supplied media. Adding a URL does not grant distribution rights. Do not enter private provider credentials into public stream URLs.

## Brand identity

**Africa Creates. The World Connects.**

The generated transparent logo is in `static/assets/africa-media-logo.png`. The cinematic artwork with the approved slogan is in `static/assets/africa-media-hero.png`. They are used in navigation, the Home hero and account dialogs. Responsive rendering preserves the full banner instead of cropping its text.

Artwork was edited using the built-in imagegen tool with this prompt: “Change only the two-line tagline to Africa Creates. / The World Connects.; preserve the brand heading, composition, people, Africa emblem and colors.”

### Deployment helper

After cloning, run `sudo bash scripts/deploy-olamidepanel.sh media.olamidepanel.com YOUR_EMAIL`. This invokes the same Ansible playbook with HTTPS enabled. DNS must point to the Olamidepanel server first.

## IPTV channel refresh

Admin → **IPTV playlists** → select **ALL**, **SPORTS**, a category or a language → **Refresh channels**. Includes the supplied IPTV-org index, twelve category playlists and English/French/Arabic playlists. Live TV includes channel search, category selection, refresh and paged display.

Deployment now attempts a directory refresh with `media_playlist_source=all`. Failure to download a playlist is reported and does not remove existing channels or stop application deployment. Set `-e media_refresh_channels=false` to skip or `-e media_playlist_source=sports` to import only sports. Imports include public HTTPS stream URLs; HTTP-only, private literal addresses and unsupported protocols are skipped. Duplicate stream URLs and disabled-channel preferences are preserved. Stream playback is not validated by a directory refresh; browser format support, availability, geographical restrictions and distribution rights still apply.

Refresh on the server independently:

```bash
sudo -u africa-media env MEDIA_DB=/var/lib/africa-media/media.db \
 python3 /opt/africa-media/app.py refresh-channels --source all
```

The directory importer does not supply EPG schedules, DVR capture, subscriptions or rebroadcast rights.

## Pull, back up and deploy an update

Use `ansible/update-and-deploy.yml` for a first install or an update. It creates a consistent SQLite backup under `/var/backups/africa-media/` when a database already exists, verifies backup integrity, then runs the deployment playbook. It defaults to `media.africandroid.world`, loopback port `18841`, HTTPS and the complete channel directory. Backups contain account data, have private permissions and are retained until an administrator removes them. Backup failure stops the update. Database restore is manual; no automatic rollback is claimed.

Run on the Olamidepanel Debian server after the domain DNS points to it:

```bash
sudo apt-get update
sudo apt-get install -y git ansible python3
sudo ansible-pull \
  -U https://github.com/olamidebello/Media.git \
  -C main -d /opt/africa-media-bootstrap \
  -i localhost, -c local \
  ansible/update-and-deploy.yml \
  -e media_email=YOUR_EMAIL
```

Replace `YOUR_EMAIL` with your certificate contact email. The deployment pulls into `/opt/africa-media`, restarts `africa-media.service` when code changes, validates Nginx, obtains HTTPS, imports channels and verifies application identity at `/api/health`. Channel download failures are reported without stopping the web service deployment.

## Expanded Working Channels playlist

The user-supplied playlist is bundled at `data/Working_Channels.m3u`, with original entries preserved and additional HTTPS channels selected from African country, news, sports, music and children’s directories. `data/channel-checks.json` records the checks performed on additions. Validation means the HLS manifest and one media segment were accessible from the checking environment at the recorded time; decoding, continuous playback, device compatibility and regional availability were not established. Original entries were preserved without being certified as working.

Deployment imports the bundled playlist after refreshing the directory. HTTP-only original entries are retained in the downloadable M3U but skipped by the HTTPS website importer. Duplicate stream URLs and disabled settings are preserved. To import only this list, choose **Admin → IPTV playlists → WORKING CHANNELS — expanded list**, or run `app.py refresh-channels --source working` using the database environment shown above. Country sources for Nigeria, South Africa, Ghana, Kenya, Tanzania, Uganda, Egypt, Morocco, Ethiopia and Senegal are also available.

Current expansion: **89 additions, 106 total entries**; 180 candidates checked. Seven tests passed.

## Complete category directory

The administrator IPTV selector includes All channels and all 30 requested categories: animation, auto, business, classic, comedy, cooking, culture, documentary, education, entertainment, family, general, interactive, kids, legislative, lifestyle, movies, music, news, outdoor, public, relax, religious, science, series, shop, sports, travel, weather, undefined. Select a category and Refresh channels to import it. All channels remains the deployment default and includes the combined directory; category imports deduplicate by stream URL. These are configured directory sources, not claims that every listed stream has been playback-tested. Existing Working Channels and country/language sources remain available.

## Location dashboard

Local Channels offers opt-in browser geolocation and manual country selection. Reverse lookup sends rounded coordinates to OpenStreetMap Nominatim only after the user clicks Find my location and grants browser permission. Only a country code persists in browser local storage; Clear location removes it. The server accepts an allowlisted country code and fetches its IPTV-org directory with a one-hour in-memory cache. No coordinates are sent to or stored by this application server. Country listings support search, pagination and live playback; this is discovery, not geographic entitlement enforcement or a playback guarantee. HTTPS is required for browser location permission. Provider outages and denial fall back to manual country selection.

## Additional uploaded channels

Imported the supplied `All_Working_Channels.m3u`: one entry, MBC+ Drama, added to the bundled Working Channels playlist. The source file is retained in `data/All_Working_Channels.m3u`. The merged playlist now contains 107 entries; this addition has not been independently playback-tested. Deployment automatically imports the expanded bundled list with URL deduplication.

## Television landing page

Home now presents a cinematic brand hero, real imported channel cards, horizontally scrollable discovery rows, published-content cards, category shortcuts and a local-channel callout. Buttons connect to playback, guide, movies, location discovery and help. Channel initials are used where no logo is stored; no synthetic thumbnails are presented as real movie artwork. Empty catalogs and unavailable guides display explicit states. Mobile layouts and visible keyboard focus are included. JavaScript syntax and the ten existing backend tests pass; browser visual QA and live playback are not verified.

## Free streaming discovery

Home and Movies include official external links to Tubi, Pluto TV and Plex. These are outbound provider links, not embedded streams, account integrations or a redistribution arrangement. Movies also displays imported channels categorized Movies and offers administrators a one-click Movies playlist refresh. The configured source is https://iptv-org.github.io/iptv/categories/movies.m3u. Provider login, availability and playback remain on their websites.

## Smart TV mode

Toggle TV mode in the header for larger targets and directional spatial focus. Arrow keys navigate, Enter activates, Escape/Back returns, Page Up/Down changes live channels, media keys control playback and numeric keys select live channel position. Player buttons offer play/pause, mute, full screen, guide and channel changes or VOD seeking. Stream buffering and errors have on-screen messages. TV mode persists on the device. Existing native video volume/caption controls remain available.

This is browser-level remote support, not an exact Samsung/LG/Android TV operating-system replica. Dedicated remote buttons may require native apps or vendor APIs; fullscreen, codecs, autoplay, power, input, system volume, casting and app installation depend on the device. Remote behavior and playback require validation on physical TVs.

## Al Jazeera and YouTube Live

YouTube Live navigation contains a searchable starting directory of ten broadcaster channel live destinations, the YouTube Live discovery page and Al Jazeera’s official live website. These are external destinations, not direct media streams or a complete inventory of YouTube broadcasts. Current live status and all channel destination redirects are not verified. Existing Ansible update-and-deploy installs these changes without additional credentials.

## Device detection and installation

The header links to `/install`, which detects mobile, tablet, desktop and common TV user agents, offers manual correction and displays device-specific browser installation instructions. A manifest, 192/512px icons and service worker provide an installable web-app foundation with a static offline notice; video and account responses are not cached. Installation prompts depend on HTTPS, browser support and engagement rules. iOS uses manual Safari Add to Home Screen; native Android/iOS/Tizen/webOS/Fire TV/desktop packages and casting are not yet built or published. Device detection is heuristic. This release does not claim native apps for every device.

## Native app builds and package deployment

See `apps/README.md` for Android (including TV/Fire), desktop, Apple and vendor TV source projects. The Build device apps workflow builds Android development APK and unsigned desktop packages, and compiles Apple simulator targets. Vendor SDKs, signing, notarization and store distribution remain external requirements. No successful native package build has been verified yet.

The existing `ansible/update-and-deploy.yml` deploys web changes. Add `-e media_package_dir=/absolute/server/path/to/packages` to publish completed recognized build files from the target server. `/api/downloads` lists only nonempty deployed packages; `/install` shows available downloads and labels development/unsigned outputs. Package compatibility and signatures must be reviewed before distribution.

Arise News, Superbook and PBS KIDS official viewing links are displayed on Home and Live TV. They open provider pages, not direct video streams.

## Expanded family directory

Home and Live TV now include Arise News, Superbook, PBS KIDS, Yippee Kids, Pure Flix and the family-channel destinations shown in the supplied FaithChannel screenshots. Kids & Family navigation offers search and category filtering. Kids profiles omit news and general-family services from this directory. Provider destinations open externally; no subscription or media redistribution integration is claimed. Moore the Merrier links to the source article because its direct destination was not independently resolved.

Sources: https://www.yippee.tv/ ; https://www.pureflix.com/ ; https://www.faithchannel.com/blogs/best-christian-kid-youtubers .

## In-app provider viewing

External HTTPS links are intercepted into a GUI viewing panel. YouTube watch URLs with a video ID use the supported embed form; channel pages may refuse frames. The panel is sandboxed and provides Back navigation. Android uses an isolated ProviderActivity without the main app bridge; iOS uses an in-app SFSafariViewController; desktop uses a sandboxed child app window. These providers can still reject WebViews, third-party cookies, DRM playback or embedding. No provider restrictions are bypassed, and universal in-app playback is not claimed. Apple TV remains a direct-stream guide and has no general browser view. Updated native behavior requires rebuilding and reinstalling its package.

## Policies and legal contact

Terms, Privacy and Copyright pages are at `/legal/terms`, `/legal/privacy` and `/legal/copyright`. Version 2026-10-25 applies to new registration acknowledgements recorded server-side. Existing accounts are not retroactively recorded as accepting. `/legal/contact` accepts privacy/copyright/terms enquiries with references; Admin shows the inbox. It does not send email notifications. The existing Ansible deployment initializes the new tables and deploys the pages. The operator’s legal identity, monitored business contact, applicable jurisdiction and any designated DMCA-agent registration must be finalized by the operator before public launch; none are fabricated or claimed as completed here.

## Super admin console expansion

Admin now includes media creation/editing, audience and visibility controls, M3U text import, bulk channel enable/disable, permanent account removal and feature switches. Existing account creation/edit/reset/suspend, schedule/channel editing, report/comment moderation, legal inbox and audits remain available. Account removal anonymizes retained content/reports and deletes account-linked profiles/activity; it is not a legal-request erasure workflow. Live TV, catalog, creator submissions, comments and downloads have server-side feature checks; provider panel launches check the public feature configuration. Direct third-party destinations are outside platform control. Expanded country imports cover all 54 African countries plus selected international sources. Source additions do not mean every channel has been imported or playback-tested. Unimplemented billing, DVR capture and store provisioning are not presented as operational admin features.

## Supplied Al Jazeera feeds

All ten supplied feed URLs are retained in `data/Al_Jazeera_Sources.m3u`; the three HTTPS feeds (English, Arabic and Balkans) are also added to the automatic bundled import. Admin can choose ALJAZEERA in the IPTV source selector. The HTTP alternatives are upgraded to HTTPS during import; their upstream servers must support HTTPS. These are supplied sources, not a claim that every endpoint is live, authorized for redistribution or browser-compatible. Availability and network checks must be verified at use time.


### HTTP media links

Manual channel creation, creator submissions, and M3U imports accept public HTTP
and HTTPS URLs. HTTP URLs are internally normalized to HTTPS before storage and
duplicate detection. Explicit port 80 becomes the default HTTPS port; other
ports, paths and signed query strings are preserved. Private/local addresses and
embedded credentials remain rejected. This is a URL upgrade, not a relay:
the upstream must serve valid HTTPS, including HTTPS HLS segments and keys.
HTTP-only origins require a separately configured HTTPS media relay.

### HTTP link compatibility
HTTP media and provider links entered in this platform are upgraded to HTTPS before saving, playlist import, playback, or opening the in-app provider viewer. Existing HTTP channel and video records are upgraded during database initialization on deployment. Paths and query strings are retained; explicit HTTP port 80 becomes the HTTPS default, while custom ports are retained. Import deduplication uses the upgraded URL.

This is URL normalization, not a media proxy or TLS service for remote servers. Sources must support HTTPS with a valid certificate on the resulting URL and port. There is no downgrade to HTTP if an upstream does not support HTTPS. Third-party embedded pages, redirects, and HLS segment URLs remain under the source provider’s control.

### Open provider links externally
Provider panels include **Open externally** to open the HTTPS destination in a browser tab, the desktop default browser, or a supported provider app through the mobile OS. The Android and iOS wrappers also offer **View inside app**. Use external viewing when a provider blocks embedded viewing, requires its own app, or uses an incompatible sign-in flow. Provider access and subscription rules still apply. Native wrapper changes require rebuilding and installing updated packages; web changes apply after deployment.

### Remote channel numbers
Enable **TV mode** (or launch with `?tv=1`). On Home, the guide, or live playback, type a channel number on the remote, then press OK/Enter, or wait 1.8 seconds to tune. Backspace corrects the number; Back/Escape cancels pending entry. Top-row digits, numpad digits, and legacy remote numeric keycodes are supported. Text-entry fields and provider dialogs keep their own keys. Channel numbers appear in the guide and Home live rail and correspond to persistent channel IDs, so category filters and newly imported channels do not renumber existing channels. Disabled or missing channels show an unavailable message. Channel +/- continues to cycle through enabled channels.

### Television startup and viewing controls
The default startup restores the last successfully played platform channel or on-demand item on this device, scoped to account and profile. Catalog entries are revalidated with the API before resuming; only IDs and position are stored locally, not source URLs. Live resumes at the current broadcast. On-demand resumes near its saved position. Browser autoplay restrictions may require pressing Play. Missing or disabled items fall back to Home. Kids profiles do not automatically restore media. Install and video deep links take precedence.

**TV settings** provides a startup opt-out, forget last watched, picture fit/fill, available caption tracks, favorites and a 15/30/60/90-minute playback sleep timer. Player controls include previous-channel recall and Now/Next from supplied guide schedules; remotes can use supported LastChannel, Info and Guide keys. Settings and favorites are local to this profile and device. Sleep pauses app playback, not TV power. Switching profiles stops playback.

This web platform cannot implement every TV hardware feature: antenna scanning, HDMI/source selection, HDMI-CEC, television power and picture calibration, system-volume control, vendor app stores, protected broadcast decoding, and hardware parental locks require vendor/OS integrations. DVR capture, catch-up, start-over and language options require compatible source rights and services. Native tvOS has its own AVPlayer interface and does not run the web TV controls. Physical remote and TV validation remains necessary.

### Poor connection support
The player offers Auto, Low data and Standard connection modes, saved on this device. Auto detects browser Save-Data, 2G/3G or reported downlink below 2 Mbps when the Network Information API is available. Low data reduces video preloading and hides decorative hero artwork. Native browser HLS playback can select a lower advertised bitrate from CORS-readable HTTPS master playlists; separate audio-group variants are left to browser-managed playback to preserve sound. Master fetches have a 6-second timeout and 256 KiB limit. Unavailable CORS or variants fall back to the original stream; single-quality media cannot be made smaller by this client. Third-party media fetching uses no platform credentials.

Playback shows buffering and offline messages, offers manual retry, and makes up to three delayed recovery attempts for active playback. VOD retries preserve position where supported; live reconnects to the broadcast. Paused or closed players cancel retries. Browser online/offline signals do not guarantee internet reachability. This does not provide offline video downloads or transcode upstream streams. Physical-device, poor-network and upstream playback checks remain necessary.

### Uploaded channels and sports
The seven supplied legacy playlists yield 3,581 unique valid-format HLS URLs in `data/Uploaded_Channels.m3u`. HTTP addresses are normalized to HTTPS, preserving paths and queries. Unsupported schemes, embedded credentials and local/private addresses are excluded. These are source candidates, not verified working channels. The directory contains old entries and must be reviewed for content, availability and distribution permission. New `uploaded` imports start disabled; existing URLs and enabled/disabled preferences are preserved. Admin → IPTV playlists → UPLOADED CHANNELS imports them; Admin → bulk channel controls enables reviewed selections. Pull-and-deploy imports this review queue automatically when playlist refresh is enabled.

The Sports page adds official ESPN, NBA League Pass and FIFA+ destinations, plus search and playback of enabled sports channels. Subscription, location, provider account and blackout rules remain applicable. Sample HTTPS manifest checks of the uploaded ESPN and SuperSoccer entries all failed; no free ESPN or NBA live feed is claimed. See `data/uploaded-sports-checks.json`; these checks do not test every source, playback, rights or future availability. An HTTP-to-HTTPS URL change does not give an HTTP-only server TLS support.

## Super admin people management and marketplace
Admin → Users, groups & marketplace adds account search, account creation/editing, password reset, profile editing, groups, and bulk activation/suspension, role assignment and session revocation. Group membership is organizational and does not grant administrator privileges. The acting administrator cannot suspend or demote themselves. Existing deletion controls remain available; paid order records retain purchase snapshots with the deleted user association removed.

Marketplace supports administrator-created digital products and platform support purchases, prices/currencies, publication controls, delivery instructions, customer order history and administrator order review. Purchases are one-time, not recurring subscriptions or automatic television entitlements. No prices or products are published by default. Fulfillment instructions are returned to the buyer only after verified payment; administrators can inspect them for management. Kids profiles cannot initiate or verify checkout. This is a profile restriction, not age verification.

Stripe Checkout and Paystack hosted checkout are implemented using fixed HTTPS provider APIs. Customer card details stay with the gateway. Server-side price snapshots, checkout request keys and verification of status, amount, currency and order reference protect fulfillment. Browser redirect parameters never mark an order paid. Customers select **Check payment status** after returning or from order history; no webhook or background reconciliation is included. Refunds, disputes, tax calculation and payouts remain managed in the provider dashboard. Test keys and gateway sandbox testing are required before accepting payments; automated tests mock provider calls, not live transactions.

After deploying the latest code, provision `MEDIA_STRIPE_SECRET_KEY` and/or `MEDIA_PAYSTACK_SECRET_KEY` in root-only `/etc/africa-media/payments.env`, then restart `africa-media`. Alternatively use `ansible/configure-payments.yml` with an Ansible Vault variables file containing `media_stripe_secret_key` and/or `media_paystack_secret_key`; tasks suppress secret output and preserve unspecified keys. Do not commit credentials or put live keys in command arguments. The service loads this optional file through systemd. Admin shows configured/missing status and enabled switches; enabling alone does not supply credentials or create a merchant account. `MEDIA_PUBLIC_URL` defaults to `https://media.africandroid.world` for payment return URLs. Only supported two-decimal currencies are exposed; availability still depends on the merchant account and provider.

Provider references: https://docs.stripe.com/api/checkout/sessions/create , https://docs.stripe.com/api/checkout/sessions/retrieve , https://paystack.com/docs/api/transaction/ .

## Remove non-working channels
Deployment now runs `tools/prune_channels.py --apply` after imports against the persistent server database. It checks **enabled** stream URLs, traverses HLS playlists and looks for recognizable media bytes. A verified result is a point-in-time transport check, not full decoding or continuous-playback assurance. HTTP 404/410, invalid playlists, invalid media and unsafe addresses are checked twice before deletion. Timeout, DNS, TLS, access-denied, encrypted or other inconclusive results are disabled rather than permanently deleted. Existing disabled review entries are not scanned or enabled. Channel changes made by an administrator during the scan are preserved.

Before modifying channels the tool creates an integrity-checked SQLite backup and private JSON report under `/var/lib/africa-media/channel-backups/`. A scan with no verified channel stops without changing the database, to avoid a network-wide outage purge. Deleting channels also removes their associated schedules through existing database relations. `media_prune_channels=false` skips cleanup when troubleshooting deployment. All imported sources are checked again on subsequent deployments, so previously deleted links may be re-imported and then rechecked.

To run just cleanup after deploying current code:
```bash
sudo -u africa-media /usr/bin/python3 /opt/africa-media/tools/prune_channels.py --database /var/lib/africa-media/media.db --apply
```
Without `--apply`, the tool only reports checks. Local testing on October 25, 2026 could not verify the 117 bundled candidates because outbound DNS resolution failed; none of those source entries were deleted based on that environment-wide failure. Run checks from the streaming server for an applicable network result.

### Clickable dashboards
Home includes shortcuts to viewing, sports, saved content, marketplace, history and settings. Media cards are native buttons whose entire surface opens playback. Administrators see dashboard shortcuts for accounts, creation, groups, content, channels, schedules, reports, products, payment gateways, orders, feature switches, legal inbox and audit. Account/content/channel statistic buttons open the corresponding management controls. Shortcuts expand enclosing sections, scroll to the target and move keyboard focus to its controls; normal buttons work with keyboard and TV-remote OK selection. Shortcuts navigate only; they do not perform destructive actions or bypass backend administrator checks.

### Supplied Samsung TV Plus channels
Added 64 complete HTTPS entries from the supplied text as `data/Samsung_TV_Plus_Supplied.m3u`, available through Admin → IPTV playlists → SAMSUNG TV PLUS. Countries remain United States, United Kingdom and Canada, with regional variants kept separately by stream URL. The final incomplete “Are We There Yet?” entry was excluded because no complete stream URL was supplied. Source IDs, names and provider channel numbers are retained in the playlist; the app continues to use its own stable channel numbers to avoid collisions. The XMLTV URL is retained as source metadata only; this change does not fetch or import its programme guide. Logos are not imported by the current channel schema.

Deployment imports this source before the existing stream cleanup. Existing URLs are deduplicated and administrator disabled states preserved. Stream redirects, device support, regional access and content rights remain provider-dependent. No playback success is claimed for these supplied entries; use the server verification report. Third-party stream restrictions are not bypassed.

### Supplied Roku channels
Added 43 complete HTTPS Roku entries as `data/Roku_Supplied.m3u`, with source IDs, names, categories and original provider channel numbers. Admin → IPTV playlists → ROKU imports them, and deployment imports them before stream cleanup. Includes Unbeaten Sports, FloRacing, Monster Jam, Bowling TV, nature, animation, comedy and cooking destinations. Incomplete final source entry `5a1dec25daac971f191b10e808ec0c5d` was excluded. Provider logos are not imported by the current channel schema. The XMLTV source URL is retained in the playlist header but is not a connected programme-guide feed. The app uses its own stable channel numbers. Availability, redirects and region/device restrictions require server and playback verification; these links are not claimed to be continuously working or freely redistributable.
