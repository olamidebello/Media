# My Streaming

Private cameras belong to the signed-in user's selected profile. Add manually or discover from native clients. Android and desktop clients send ONVIF WS-Discovery probes on the current LAN/Wi-Fi. iPhone browses advertised RTSP/ONVIF Bonjour services after Local Network permission. Ordinary browsers cannot perform these discovery operations. Cameras without supported local protocols, cameras isolated by guest Wi-Fi, cloud-only models and some sleeping devices may not appear. Discovery never bypasses camera authentication. Use only cameras you own or are authorized to view.

## Server deployment

Run on the existing Media server:

```bash
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-my-streaming.yml
```

The existing updater backs up the database, pulls source and restarts the service; this play also verifies the camera interface and unauthenticated access denial. The camera schema is created lazily on first camera API use, and also by `app.py init`. Updating server code does not publish native builds. Publish and install new Android/desktop packages through the existing device package deployment. Apple native distribution requires signing.

## Remote viewing gateway

A public server cannot reach a user's private Wi-Fi camera by saving its local IP. Keep a Debian/Linux computer or Raspberry Pi on the camera network. It reads the camera's authorized RTSP/RTSPS/HTTP/HTTPS video stream with FFmpeg and uploads live JPEG snapshots over outbound HTTPS. No inbound camera port forwarding is needed. Configure the camera's local streaming feature and obtain its correct stream URL from the vendor. This release does not negotiate ONVIF credentials or automatically guess stream paths.

On that camera-network computer (not the public web server), install Ansible/git, then:

```bash
sudo ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-camera-bootstrap -i localhost, -c local \
  ansible/install-camera-gateway.yml -e camera_instance=entrance
```

1. Sign in at `https://media.africandroid.world/my-streaming` and select the intended standard profile.
2. Discover a camera or add its name/address manually. Select **Pair gateway** and copy its camera ID and one-time token.
3. On the gateway computer, run:

```bash
sudo -u africa-media-camera python3 /opt/africa-media-camera/camera-gateway.py \
  --config /etc/africa-media-camera/entrance.json --configure
sudo systemctl enable --now africa-media-camera@entrance
```

Enter the site address, camera ID, pairing token and local camera stream URL in the interactive prompts. The source URL, including any camera credentials, remains in a mode-600 configuration file on the gateway. FFmpeg needs the source URL locally; do not share gateway configurations or process diagnostics. The web server stores only a hash of the upload token, camera metadata and the latest JPEG frame. A token can upload only to its assigned camera, and cannot read cameras. Pair again to rotate it. **Disconnect** revokes uploads and deletes the current frame; **Remove** deletes the camera. Up to 20 cameras per profile are supported. Use a different systemd instance/configuration for each camera.

Open My Streaming from another network, sign in and select View camera. Snapshot updates are roughly every two seconds, scaled to 640 pixels wide and limited to 60 KB each. This is live snapshot viewing, not full-motion video, audio, PTZ or recording. The browser hides frames older than 30 seconds and reports offline. The server retains only each camera's latest frame until replaced/disconnected/deleted; database backups can retain prior frames and should follow the operator's private-data retention policy. The gateway and both internet connections must remain available. No camera hardware or physical remote-network test has been performed in this workspace.
