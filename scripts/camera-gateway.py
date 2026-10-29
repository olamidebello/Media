#!/usr/bin/env python3
"""Run on an always-on computer on the camera LAN, never on the public Media server."""
import argparse
import base64
import getpass
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def configure(path):
    server = input('Media HTTPS address [https://media.africandroid.world]: ').strip() or 'https://media.africandroid.world'
    u = urlparse(server)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ('','/'):
        raise ValueError('Use the HTTPS site origin without credentials')
    camera_id = int(input('Camera ID from My Streaming: '))
    token = getpass.getpass('One-time gateway pairing token: ').strip()
    source = getpass.getpass('Authorized camera stream URL (kept on this computer): ').strip()
    validate_source(source)
    if camera_id <= 0 or not 32 <= len(token) <= 128: raise ValueError('Invalid pairing details')
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    os.fchmod(descriptor,0o600)
    with os.fdopen(descriptor,'w') as f:
        json.dump({'server':server.rstrip('/'),'camera_id':camera_id,'token':token,'source':source},f)
    print('Gateway configured. Keep this configuration private; start the gateway without --configure.')

def validate_source(source):
    u = urlparse(source)
    if u.scheme not in ('rtsp','rtsps','http','https') or not u.hostname:
        raise ValueError('Use an authorized RTSP, RTSPS, HTTP or HTTPS camera stream URL')
    addresses = socket.getaddrinfo(u.hostname,None,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_private or ipaddress.ip_address(item[4][0]).is_loopback for item in addresses):
        raise ValueError('The camera must resolve to a private network address on this computer')

def upload(config, frame):
    payload = json.dumps({'camera_id':int(config['camera_id']),'jpeg':base64.b64encode(frame).decode()}).encode()
    request = Request(config['server']+'/api/my-streaming/ingest',data=payload,headers={
        'Content-Type':'application/json','Authorization':'Bearer '+config['token']},method='POST')
    with build_opener(NoRedirect).open(request,timeout=15) as response:
        if response.status != 200: raise ValueError('Gateway upload rejected')

def run(config):
    u = urlparse(config['server'])
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:
        raise ValueError('Invalid HTTPS server configuration')
    validate_source(config['source'])
    while True:
        args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-rw_timeout','10000000','-protocol_whitelist','tcp,tls,udp,rtp,rtsp,rtsps,http,https,crypto']
        if urlparse(config['source']).scheme in ('rtsp','rtsps'): args += ['-rtsp_transport','tcp']
        args += ['-i',config['source'],'-an','-vf','fps=1/2,scale=640:-2','-q:v','8','-f','image2pipe','-vcodec','mjpeg','pipe:1']
        process = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        try:
            buffer = b''
            while True:
                block = process.stdout.read1(8192)
                if not block: break
                buffer += block
                while True:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9',start+2) if start >= 0 else -1
                    if end < 0: break
                    frame,buffer = buffer[start:end+2],buffer[end+2:]
                    if len(frame) <= 60000:
                        try: upload(config,frame)
                        except Exception: print('Upload unavailable. Check pairing and connectivity; retrying.',flush=True)
                if len(buffer)>1000000: buffer=b''
        finally:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        print('Camera connection ended. Retrying in 5 seconds.',flush=True)
        time.sleep(5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path.home()/'.config/africa-media/camera-gateway.json')
    parser.add_argument('--configure',action='store_true')
    args = parser.parse_args()
    try:
        if args.configure: configure(args.config)
        else:
            if os.name != 'nt' and args.config.stat().st_mode & 0o077: raise ValueError('Protect gateway config with chmod 600 before starting')
            run(json.loads(args.config.read_text()))
    except KeyboardInterrupt: pass
    except Exception:
        raise SystemExit('Gateway setup failed. Check configuration, file permissions, FFmpeg and camera connectivity. Credentials were not printed.') from None
