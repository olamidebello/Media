# Build a Station

The **Build a Station** section under **My library & tools** lets a signed-in user with a standard profile create up to five account-owned television stations. Open `/build-a-station` directly, including on a phone. This is an Internet television workflow with an external production encoder; it does not provide terrestrial/satellite transmission or a browser replacement for every broadcast control-room system.

## Deploy on the existing Media server

```sh
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-stations.yml
```

The play backs up the SQLite database, pulls source without discarding local changes, migrates tables using the existing service account, restarts the app, and installs Debian's `libnginx-mod-rtmp` and `libnginx-mod-stream`. A separate `africa-media-station` systemd service converts authenticated RTMPS publishing to HLS. The existing public Nginx site, TLS configuration, database and account roles are retained. Existing Let's Encrypt certificates must already be present.

Allow **inbound TCP 1936** in the host and provider firewall for publishers. The play does not change firewall rules. Internal ports 1935 and 18842 bind only to loopback. Viewing uses the existing HTTPS port 443. The certificate renewal hook reloads the station engine after renewals. Error logs rotate weekly; RTMP access logs are disabled to avoid storing stream keys. HLS fragments are transient, approximately a 12-second rolling playlist, with module cleanup enabled. There is no recording archive.

## First broadcast

1. Sign in, select a standard profile, open Build a Station, and create a station.
2. Set station name, description, category, logo and source. Choose **OBS / hardware encoder** for server ingest or provide an existing HTTPS `.m3u8` URL. Upstream external stream health is explicitly unverified, and its origin's access controls remain its operator's responsibility.
3. Under **Live control**, generate an OBS key. The complete stream name and secret are shown once. In OBS Settings → Stream choose Custom, use server `rtmps://media.africandroid.world:1936/live`, and paste the entire generated key, including `station-ID?key=…`. Only a SHA-256 key hash is retained by the application. Rotating the key also sets the station off air.
4. Use H.264 video, AAC audio and two-second keyframes. Start with 720p around 2,500 kbps. This service remuxes one output rendition and does not transcode incompatible codecs. Some hardware/mobile encoders cannot supply RTMPS or stream-name query parameters; use an encoder supporting both.
5. Enable broadcast in the dashboard, start OBS streaming, wait for HLS segments, and preview the output. The status says **Live signal** only when a local HLS playlist was modified within 20 seconds; enabling output alone shows **Waiting for encoder**. Stop output or rotate keys to reject future publishing. Existing publishers are reauthorized every five seconds, and unauthorized HLS reads are rejected immediately. Already buffered frames may continue playing briefly.
6. An administrator reviews the station under **Admin → Broadcast station review** and approves it for public access. Owners and administrators can preview unapproved streams. Suspended users/stations cannot publish or serve local HLS. Changing station identity or source clears approval and stops output.
7. Share the watch link from **Share & guide**. Approved stations with enabled output also appear under **Live TV → Community stations**. Guests can watch approved stations; these independent stations are excluded from the app's Kids profile requests. Shared public URLs are publicly accessible and are not a parental-control boundary.

## Production features

| Feature | Behavior |
| --- | --- |
| Branding | Station name, description, category and HTTPS logo |
| Live control | Authenticated RTMPS, external HLS option, start/stop output, key rotation, encoded-output preview |
| Schedule / EPG | Local-time editing, UTC storage, overlap validation, live/prerecorded/advert break types, public upcoming guide |
| Rundown | Production-only media cue URL and notes, planned/ready/done/skipped status, edit/remove entries |
| Graphics | Logo bug, station name, lower third and scrolling ticker through an OBS browser source, updates about every five seconds |
| Sharing | Public watch page with HLS player, program guide and calendar `.ics` export |
| Moderation | Public approval, suspension/restoration, account ownership and existing CSRF/session checks |
| Cameras, switching, audio, playout | Configure scenes, inputs, Studio Mode, transitions, audio mixing, media sources and emergency slate in OBS |
| Recording | Use OBS local recording; server cloud recording is not provided |

Add the Graphics URL as a 1920×1080 OBS Browser Source. Graphics are included in the transmitted picture **only when the browser source is part of the active OBS scene**. The graphics URL is unlisted rather than private, so it contains only public-facing branding, lower-third text and ticker. Never put secrets in that text. Private production notes remain in the authenticated rundown.

Schedule entries are guide listings and manual production cues. They do not automatically switch or play programs, adverts or fallback material. Server-side 24/7 automatic playout, adaptive bitrate transcoding, simulcast outputs, cloud DVR, audience analytics and multi-user crew permissions are not included in this release. Use an external playout/production service for those workflows. Server bandwidth, encoder uplink and available connection capacity determine concurrent viewing capacity; no load-tested capacity is claimed.

HLS playback uses native browser support when available and a locally vendored HLS.js 1.6.13 (Apache-2.0) for compatible Media Source Extensions browsers. Unsupported clients receive a clear playback message. No remote script/CDN is needed at playback time.

## Verification and operations

```sh
systemctl status africa-media africa-media-station
journalctl -u africa-media-station -n 60 --no-pager
nginx -t -c /etc/africa-media-station/nginx.conf
curl http://127.0.0.1:18842/health
```

A local FFmpeg → RTMPS → HLS smoke test verified real encoder authentication, playable playlist/segment delivery and disconnection after stopping output, using the same Nginx template with local test ports and a temporary certificate. Application tests exercise ownership, CSRF, Kids restrictions, program overlap, moderation, public-data redaction, stream-key revocation, HLS authorization and live-signal freshness. The deployment verifies engine health, assets and rejected unauthenticated access. Complete an actual OBS → RTMPS → HTTPS playback test on the deployed server before relying on it for a broadcast; local unit checks do not verify its firewall, public certificate or real encoder interoperability.

Protocol references: [Nginx RTMP callbacks and HLS](https://github.com/arut/nginx-rtmp-module/wiki/Directives), [Nginx stream TLS](https://nginx.org/en/docs/stream/ngx_stream_ssl_module.html), [HLS.js](https://github.com/video-dev/hls.js). The vendored library's license is in `static/vendor/hls.LICENSE`.
