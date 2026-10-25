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
