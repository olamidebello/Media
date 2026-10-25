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
