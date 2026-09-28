#!/usr/bin/env python3
"""
FaceCam - Responsive mobile & desktop
"""
import os, sys, random, string, subprocess, platform
import socket as sock_module

def ensure_deps():
    try:
        import flask, flask_socketio, eventlet
    except ImportError:
        print("[*] Installing dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                "--break-system-packages", "-r", "requirements.txt"])
        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                "-r", "requirements.txt"])

ensure_deps()

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'facecam-secret-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet',
                    ping_timeout=60, ping_interval=25)

rooms = {}

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

BASE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html, body {
  height:100%; width:100%;
  font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background:#0a0a0f; color:#fff; overflow:hidden;
  -webkit-user-select:none; user-select:none;
}
body {
  background:
    radial-gradient(circle at 20% 20%, rgba(99,102,241,0.15), transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(236,72,153,0.15), transparent 50%),
    #0a0a0f;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  position:relative;
}
body::before {
  content:''; position:fixed; inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size:40px 40px; pointer-events:none; z-index:0;
}
body.overflow-auto { overflow:auto; }
.container { width:100%; max-width:440px; position:relative; z-index:1; padding:16px; animation:fadeUp .5s ease; }
@keyframes fadeUp { from{opacity:0; transform:translateY(15px);} to{opacity:1; transform:translateY(0);} }
.card {
  background:rgba(20,20,30,0.7); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.08); border-radius:24px;
  padding:32px 24px; box-shadow:0 20px 60px rgba(0,0,0,0.5);
}
.logo { display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:8px; }
.logo-icon {
  width:44px; height:44px; border-radius:12px;
  background:linear-gradient(135deg,#6366f1,#ec4899);
  display:flex; align-items:center; justify-content:center; font-size:22px;
  box-shadow:0 8px 24px rgba(99,102,241,0.4);
}
h1 {
  font-size:28px; font-weight:700; letter-spacing:-0.5px;
  background:linear-gradient(135deg,#fff,#a5b4fc);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.subtitle { text-align:center; color:#6b7280; font-size:14px; margin-bottom:28px; }
.btn {
  width:100%; padding:16px; font-size:16px; font-weight:600;
  border:none; border-radius:14px; cursor:pointer; transition:all .2s;
  display:flex; align-items:center; justify-content:center; gap:10px;
  font-family:inherit; margin-bottom:12px;
}
.btn:active { transform:scale(0.97); }
.btn-primary { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; box-shadow:0 8px 24px rgba(99,102,241,0.4); }
.btn-primary:hover { box-shadow:0 12px 32px rgba(99,102,241,0.6); }
.btn-secondary { background:rgba(255,255,255,0.06); color:#e5e7eb; border:1px solid rgba(255,255,255,0.1); }
.btn-secondary:hover { background:rgba(255,255,255,0.1); }
.input {
  width:100%; padding:18px; font-size:26px; font-weight:700;
  text-align:center; letter-spacing:8px; text-transform:uppercase;
  background:rgba(0,0,0,0.3); border:2px solid rgba(255,255,255,0.1);
  border-radius:14px; color:#fff; font-family:'SF Mono',Menlo,monospace;
  transition:all .2s; outline:none; margin-bottom:16px;
}
.input:focus { border-color:#6366f1; box-shadow:0 0 0 4px rgba(99,102,241,0.15); }
.input::placeholder { color:#374151; }
.error-msg { color:#f87171; font-size:13px; text-align:center; margin-top:8px; min-height:18px; }
.host-screen {
  position:fixed; inset:0; background:#000; z-index:1; overflow:hidden;
}
.host-screen video {
  position:absolute; inset:0; width:100%; height:100%; object-fit:cover;
  background:#000; display:block; transition:transform 0.3s ease, object-fit 0.3s;
}
.host-screen video.fit-contain { object-fit:contain; }
.video-placeholder {
  position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  flex-direction:column; gap:14px; color:#4b5563; font-size:14px;
  background:radial-gradient(circle at 50% 50%, rgba(99,102,241,0.08), transparent 60%), #000;
  z-index:2;
}
.video-placeholder .big { font-size:64px; opacity:.3; }
.video-placeholder.hidden { display:none; }
.top-bar {
  position:fixed; top:0; left:0; right:0; padding:12px 14px;
  padding-top:max(12px, env(safe-area-inset-top));
  display:flex; align-items:center; justify-content:space-between;
  background:linear-gradient(to bottom, rgba(0,0,0,0.75), transparent);
  z-index:100; pointer-events:none; gap:10px;
}
.top-bar > * { pointer-events:auto; }
.room-chip, .status-pill {
  display:flex; align-items:center; background:rgba(0,0,0,0.55);
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,0.12);
}
.room-chip { gap:6px; border-radius:24px; padding:5px 10px; font-size:10px; text-transform:uppercase; letter-spacing:1.5px; color:#9ca3af; font-weight:600; }
.room-chip .code {
  font-family:'SF Mono',Menlo,monospace; font-size:13px; font-weight:800; letter-spacing:2px;
  background:linear-gradient(135deg,#a5b4fc,#f0abfc); -webkit-background-clip:text;
  -webkit-text-fill-color:transparent; background-clip:text;
}
.chip-btn {
  background:rgba(255,255,255,0.15); border:none; color:#fff; width:24px; height:24px;
  border-radius:50%; font-size:11px; cursor:pointer; display:flex; align-items:center;
  justify-content:center; transition:all .15s;
}
.chip-btn:active { transform:scale(0.9); }
.status-pill { gap:5px; border-radius:20px; padding:5px 10px; font-size:10px; font-weight:600; color:#d1d5db; }
.status-pill .dot { width:6px; height:6px; border-radius:50%; background:#fbbf24; animation:pulse 1.5s infinite; }
.status-pill .dot.live { background:#ef4444; animation:none; box-shadow:0 0 8px #ef4444; }
.status-pill .dot.error { background:#ef4444; animation:none; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.ctrl-btn {
  width:44px; height:44px; border-radius:50%; background:rgba(0,0,0,0.55);
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,0.15); color:#fff; font-size:18px; cursor:pointer;
  display:flex; align-items:center; justify-content:center; transition:all .2s; flex-shrink:0;
}
.ctrl-btn:active { transform:scale(0.9); }
.ctrl-btn.active { background:linear-gradient(135deg,#6366f1,#8b5cf6); border-color:transparent; }
.shutter {
  width:64px; height:64px; border-radius:50%; background:#fff;
  border:3px solid rgba(255,255,255,0.35); cursor:pointer; transition:all .12s;
  box-shadow:0 0 0 3px rgba(255,255,255,0.15), 0 6px 20px rgba(0,0,0,0.5); flex-shrink:0;
}
.shutter:active { transform:scale(0.88); box-shadow:0 0 0 8px rgba(255,255,255,0.25), 0 6px 20px rgba(0,0,0,0.5); }
.album-btn {
  width:44px; height:44px; border-radius:12px; background:rgba(255,255,255,0.15);
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,0.25); color:#fff; font-size:18px; cursor:pointer;
  display:flex; align-items:center; justify-content:center; transition:all .2s; overflow:hidden; position:relative; flex-shrink:0;
}
.album-btn:active { transform:scale(0.9); }
.album-btn img { width:100%; height:100%; object-fit:cover; border-radius:11px; }
.album-btn .album-empty { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:18px; color:#e5e7eb; }
.mobile-controls {
  position:fixed; bottom:0; left:0; right:0; padding:14px 16px;
  padding-bottom:max(16px, env(safe-area-inset-bottom));
  background:linear-gradient(to top, rgba(0,0,0,0.85), transparent);
  display:flex; align-items:center; justify-content:space-between; z-index:100; gap:12px;
}
.mobile-controls .side-group,.mobile-controls .center-group,.mobile-controls .end-group { display:flex; align-items:center; }
.mobile-controls .side-group,.mobile-controls .end-group { gap:8px; }
.mobile-controls .center-group { justify-content:center; }
.mobile-float-right { position:fixed; top:64px; right:12px; display:flex; flex-direction:column; gap:8px; z-index:100; }
.mobile-float-left { position:fixed; top:64px; left:12px; display:flex; flex-direction:column; gap:8px; z-index:100; }
.mobile-float-right .ctrl-btn,.mobile-float-left .ctrl-btn { width:40px; height:40px; font-size:16px; }
.zoom-indicator {
  position:fixed; top:108px; right:12px; padding:4px 10px; background:rgba(0,0,0,0.75);
  border-radius:12px; font-size:11px; font-weight:700; color:#a5b4fc; opacity:0;
  transition:opacity .3s; z-index:100;
}
.zoom-indicator.show { opacity:1; }
.desktop-sidebar {
  display:none; position:fixed; right:16px; top:50%; transform:translateY(-50%);
  flex-direction:column; gap:8px; z-index:100;
}
.desktop-sidebar .ctrl-btn,.desktop-sidebar .album-btn { width:40px; height:40px; font-size:15px; }
.desktop-sidebar .shutter { width:52px; height:52px; border:3px solid rgba(255,255,255,0.35); margin:4px 0; }
.desktop-sidebar .group {
  display:flex; flex-direction:column; gap:6px; background:rgba(0,0,0,0.4);
  backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,0.1);
  border-radius:24px; padding:8px;
}
@media (min-width:900px) {
  .mobile-controls,.mobile-float-left,.mobile-float-right,.zoom-indicator { display:none !important; }
  .desktop-sidebar { display:flex; }
  .zoom-indicator.desktop-zoom { top:auto; bottom:30px; right:70px; }
}
@media (min-width:601px) and (max-width:899px) {
  .ctrl-btn { width:48px; height:48px; font-size:20px; }
  .shutter { width:72px; height:72px; }
  .album-btn { width:48px; height:48px; font-size:20px; }
  .mobile-controls { padding:16px 24px; padding-bottom:max(20px, env(safe-area-inset-bottom)); }
}
.flash { position:fixed; inset:0; background:#fff; opacity:0; pointer-events:none; z-index:9999; transition:opacity .25s; }
.flash.active { opacity:1; transition:none; }
.album-view { position:fixed; inset:0; background:#0a0a0f; z-index:1000; display:none; flex-direction:column; }
.album-view.show { display:flex; animation:fadeUp .3s ease; }
.album-header {
  display:flex; align-items:center; justify-content:space-between; padding:16px 20px;
  padding-top:max(16px, env(safe-area-inset-top)); background:rgba(20,20,30,0.95);
  border-bottom:1px solid rgba(255,255,255,0.08);
}
.album-header h2 { font-size:18px; font-weight:700; }
.album-header .count { color:#6b7280; font-size:13px; margin-left:8px; }
.album-close {
  width:38px; height:38px; border-radius:50%; background:rgba(255,255,255,0.1);
  border:none; color:#fff; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;
}
.album-grid { flex:1; overflow-y:auto; padding:12px; display:grid; grid-template-columns:repeat(auto-fill,minmax(100px,1fr)); gap:6px; }
.album-grid img { width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px; cursor:pointer; }
@media (min-width:900px) { .album-grid { grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; padding:16px; } }
.album-empty { grid-column:1/-1; text-align:center; color:#4b5563; padding:60px 20px; font-size:14px; }
.photo-viewer { position:fixed; inset:0; background:#000; z-index:1001; display:none; flex-direction:column; }
.photo-viewer.show { display:flex; }
.photo-viewer-header { display:flex; align-items:center; justify-content:space-between; padding:16px; background:rgba(0,0,0,0.9); padding-top:max(16px,env(safe-area-inset-top)); }
.photo-viewer-title { font-size:14px; font-weight:600; color:#e5e7eb; }
.photo-viewer-close { width:38px; height:38px; border-radius:50%; background:rgba(255,255,255,0.1); border:none; color:#fff; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center; }
.photo-viewer-body { flex:1; display:flex; align-items:center; justify-content:center; padding:16px; overflow:auto; }
.photo-viewer-body img { max-width:100%; max-height:100%; border-radius:12px; object-fit:contain; }
.photo-viewer-actions { padding:16px 24px; padding-bottom:max(24px,env(safe-area-inset-bottom)); display:flex; gap:10px; justify-content:center; }
.photo-viewer-actions button { padding:14px 24px; border-radius:12px; border:none; font-size:14px; font-weight:600; cursor:pointer; font-family:inherit; min-width:120px; }
.photo-viewer-actions .save-btn { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; }
.photo-viewer-actions .close-btn { background:rgba(255,255,255,0.1); color:#e5e7eb; }
body.quiet-mode { background:#000; padding:0; overflow:hidden; }
body.quiet-mode::before { display:none; }
body.quiet-mode .container { display:none; }
#quietScreen { display:none; position:fixed; inset:0; background:#000; z-index:9999; align-items:center; justify-content:center; flex-direction:column; gap:20px; }
body.quiet-mode #quietScreen { display:flex; }
.quiet-dot { width:12px; height:12px; border-radius:50%; background:#10b981; box-shadow:0 0 24px #10b981; animation:quietPulse 2s infinite; }
@keyframes quietPulse { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:.4;transform:scale(.85);} }
.quiet-text { color:#2a2a2a; font-size:11px; letter-spacing:6px; text-transform:uppercase; font-weight:600; }
.quiet-flash { position:fixed; inset:0; background:#fff; opacity:0; pointer-events:none; transition:opacity .12s; z-index:99999; }
.quiet-flash.flash { opacity:1; transition:none; }
.toast {
  position:fixed; top:80px; left:50%; transform:translateX(-50%) translateY(-120px);
  background:rgba(16,185,129,0.95); color:#fff; padding:10px 20px; border-radius:12px;
  font-size:13px; font-weight:600; z-index:99999; transition:transform .3s ease;
  box-shadow:0 8px 24px rgba(0,0,0,0.4); white-space:nowrap;
}
.toast.show { transform:translateX(-50%) translateY(0); }
"""

INDEX_HTML = """<!DOCTYPE html><html lang="id"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>FaceCam</title><style>{{ css }}</style></head><body class="overflow-auto">
<div class="container"><div class="card">
<div class="logo"><div class="logo-icon">📹</div></div>
<h1 style="text-align:center;">FaceCam</h1>
<p class="subtitle">Host kontrol penuh, viewer jadi kamera</p>
<button class="btn btn-primary" onclick="location.href='/host'"><span>✨</span> Create Room</button>
<button class="btn btn-secondary" onclick="location.href='/viewer'"><span>📷</span> Join Face Cam</button>
</div></div></body></html>"""

HOST_HTML = """<!DOCTYPE html><html lang="id"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#000000"><title>Host - FaceCam</title><style>{{ css }}</style></head><body>
<div class="host-screen"><video id="remoteVideo" autoplay playsinline></video>
<div class="video-placeholder" id="placeholder"><div class="big">📷</div><div>Menunggu viewer join...</div></div></div>
<div class="top-bar"><div class="room-chip"><span>ID</span><span class="code" id="roomId">······</span>
<button class="chip-btn" id="copyBtn" onclick="copyId()">📋</button></div>
<div class="status-pill"><span class="dot" id="statusDot"></span><span id="statusText">Menunggu</span></div></div>
<div class="mobile-float-right"><button class="ctrl-btn" id="zoomBtnMobile" onclick="toggleZoom()">🔍</button></div>
<div class="mobile-float-left"><button class="ctrl-btn" data-fit="cover" onclick="setFit('cover')" title="Penuh">⛶</button>
<button class="ctrl-btn" data-fit="contain" onclick="setFit('contain')" title="Fit">▢</button></div>
<div class="zoom-indicator" id="zoomIndicatorMobile">2x</div>
<div class="mobile-controls"><div class="side-group"><button class="ctrl-btn" onclick="switchCamera()" title="Ganti Kamera">🔄</button></div>
<div class="center-group"><button class="shutter" onclick="takePhoto()" title="Ambil Foto"></button></div>
<div class="end-group"><button class="album-btn" onclick="openAlbum()" id="albumBtnMobile" title="Album"><div class="album-empty">🖼️</div></button></div></div>
<div class="desktop-sidebar"><div class="group">
<button class="ctrl-btn" onclick="switchCamera()" title="Ganti Kamera">🔄</button>
<button class="ctrl-btn" id="zoomBtnDesktop" onclick="toggleZoom()" title="Zoom">🔍</button>
<button class="ctrl-btn" data-fit="cover" onclick="setFit('cover')" title="Penuh">⛶</button>
<button class="ctrl-btn" data-fit="contain" onclick="setFit('contain')" title="Fit">▢</button>
<button class="album-btn" onclick="openAlbum()" id="albumBtnDesktop" title="Album"><div class="album-empty">🖼️</div></button>
</div><div class="group" style="padding:6px;"><button class="shutter" onclick="takePhoto()" title="Ambil Foto"></button></div></div>
<div class="album-view" id="albumView"><div class="album-header"><div><h2 style="display:inline;">Album</h2><span class="count" id="albumCount">(0)</span></div>
<button class="album-close" onclick="closeAlbum()">✕</button></div><div class="album-grid" id="albumGrid"><div class="album-empty">Belum ada foto</div></div></div>
<div class="photo-viewer" id="photoViewer"><div class="photo-viewer-header"><div class="photo-viewer-title" id="photoTitle">Foto</div>
<button class="photo-viewer-close" onclick="closePhoto()">✕</button></div><div class="photo-viewer-body"><img id="photoViewerImg" src=""></div>
<div class="photo-viewer-actions"><button class="close-btn" onclick="closePhoto()">Tutup</button><button class="save-btn" onclick="savePhoto()">💾 Simpan</button></div></div>
<div class="flash" id="flash"></div><div class="toast" id="toast"></div>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script><script>
const socket=io();let pc=null,roomId=null,currentFacing='user',zoomOn=false,currentFit='cover';const photos=[];let currentPhotoIdx=-1;
socket.emit('create_room');
socket.on('room_created',d=>{roomId=d.room_id;document.getElementById('roomId').textContent=roomId;});
socket.on('viewer_joined',()=>setStatus('Viewer join...','pending'));
socket.on('offer',async data=>{setStatus('Terima kamera...','pending');if(pc)pc.close();pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'},{urls:'stun:stun1.l.google.com:19302'}]});
pc.ontrack=e=>{const v=document.getElementById('remoteVideo');if(v.srcObject!==e.streams[0])v.srcObject=e.streams[0];v.play().catch(()=>{});document.getElementById('placeholder').classList.add('hidden');setStatus('LIVE','live');};
pc.oniceconnectionstatechange=()=>{if(pc.iceConnectionState==='failed')setStatus('Gagal - HTTPS?','error');};
pc.onicecandidate=e=>{if(e.candidate)socket.emit('ice_candidate',{room_id:roomId,candidate:e.candidate,from:'host'});};
await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));const answer=await pc.createAnswer();await pc.setLocalDescription(answer);socket.emit('answer',{room_id:roomId,sdp:answer});});
socket.on('ice_candidate',async d=>{if(pc){try{await pc.addIceCandidate(new RTCIceCandidate(d.candidate));}catch(e){}}});
function toggleZoom(){zoomOn=!zoomOn;document.getElementById('remoteVideo').style.transform=zoomOn?'scale(2)':'scale(1)';document.querySelectorAll('#zoomBtnMobile,#zoomBtnDesktop').forEach(b=>b.classList.toggle('active',zoomOn));const ind=document.getElementById('zoomIndicatorMobile');ind.textContent=zoomOn?'2x':'1x';ind.classList.add('show');setTimeout(()=>ind.classList.remove('show'),1200);}
function setFit(mode){currentFit=mode;document.getElementById('remoteVideo').classList.toggle('fit-contain',mode==='contain');document.querySelectorAll('[data-fit]').forEach(b=>b.classList.toggle('active',b.dataset.fit===mode));toast(mode==='cover'?'⛶ Mode Penuh':'▢ Mode Fit');}
function switchCamera(){if(!roomId)return;currentFacing=currentFacing==='user'?'environment':'user';socket.emit('switch_camera',{room_id:roomId,facing:currentFacing});toast(currentFacing==='user'?'🤳 Depan':'📸 Belakang');}
function takePhoto(){if(!roomId)return;const flash=document.getElementById('flash');flash.classList.add('active');setTimeout(()=>flash.classList.remove('active'),120);socket.emit('take_photo',{room_id:roomId});const video=document.getElementById('remoteVideo');if(!video.srcObject||!video.videoWidth){toast('❌ Belum ada stream');return;}const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;const ctx=canvas.getContext('2d');if(currentFacing==='user'){ctx.translate(canvas.width,0);ctx.scale(-1,1);}ctx.drawImage(video,0,0);canvas.toBlob(blob=>{const url=URL.createObjectURL(blob);photos.push({url,blob,time:Date.now()});renderAlbumThumb();toast('✓ Foto tersimpan');},'image/jpeg',.92);}
function renderAlbum(){const grid=document.getElementById('albumGrid');document.getElementById('albumCount').textContent=`(${photos.length})`;if(!photos.length){grid.innerHTML='<div class="album-empty">Belum ada foto</div>';return;}grid.innerHTML=photos.map((p,i)=>`<img src="${p.url}" onclick="openPhoto(${i})">`).join('');}
function renderAlbumThumb(){const latest=photos.length?photos[photos.length-1].url:null;['albumBtnMobile','albumBtnDesktop'].forEach(id=>{const btn=document.getElementById(id);if(!btn)return;btn.innerHTML=latest?`<img src="${latest}">`:'<div class="album-empty">🖼️</div>';});}
function openAlbum(){renderAlbum();document.getElementById('albumView').classList.add('show');}function closeAlbum(){document.getElementById('albumView').classList.remove('show');}
function openPhoto(i){currentPhotoIdx=i;document.getElementById('photoViewerImg').src=photos[i].url;document.getElementById('photoTitle').textContent='Foto '+(i+1)+' / '+photos.length;document.getElementById('photoViewer').classList.add('show');}
function closePhoto(){document.getElementById('photoViewer').classList.remove('show');currentPhotoIdx=-1;}
function savePhoto(){if(currentPhotoIdx<0)return;const p=photos[currentPhotoIdx],a=document.createElement('a');a.href=p.url;a.download='facecam_'+new Date(p.time).toISOString().replace(/[:.]/g,'-')+'.jpg';a.click();toast('💾 Foto disimpan');}
function setStatus(t,type){document.getElementById('statusText').textContent=t;const dot=document.getElementById('statusDot');dot.className='dot'+(type==='live'?' live':type==='error'?' error':'');}
function copyId(){if(!roomId)return;navigator.clipboard.writeText(roomId).then(()=>{const b=document.getElementById('copyBtn');b.textContent='✓';setTimeout(()=>b.textContent='📋',1500);});}
function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000);}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;if(e.code==='Space'){e.preventDefault();takePhoto();}if(e.key==='c'||e.key==='C')switchCamera();if(e.key==='z'||e.key==='Z')toggleZoom();if(e.key==='f'||e.key==='F')setFit(currentFit==='cover'?'contain':'cover');});
</script></body></html>"""

VIEWER_HTML = """<!DOCTYPE html><html lang="id"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Viewer - FaceCam</title><style>{{ css }}</style></head><body class="overflow-auto">
<div class="container"><div class="card"><div class="logo"><div class="logo-icon">📷</div></div>
<h1 style="text-align:center;">Join Face Cam</h1><p class="subtitle">Masukkan Room ID dari host</p>
<input class="input" id="roomInput" placeholder="ABC123" maxlength="6" autocomplete="off" autocapitalize="characters" oninput="this.value=this.value.toUpperCase()">
<p class="error-msg" id="errorMsg"></p><button class="btn btn-primary" onclick="joinRoom()"><span>📷</span> Join</button>
<button class="btn btn-secondary" onclick="location.href='/'">← Kembali</button></div></div>
<div id="quietScreen"><div class="quiet-dot"></div><div class="quiet-text" id="quietText">Connected</div></div><div class="quiet-flash" id="flash"></div>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script><script>
const socket=io();let pc=null,roomId=null,localStream=null,currentFacing='user';
async function joinRoom(){const input=document.getElementById('roomInput').value.trim().toUpperCase();if(input.length!==6){document.getElementById('errorMsg').textContent='Room ID harus 6 karakter';return;}roomId=input;document.getElementById('errorMsg').textContent='Meminta akses kamera...';try{localStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:currentFacing,width:{ideal:1280},height:{ideal:720}},audio:false});}catch(err){document.getElementById('errorMsg').textContent='Akses kamera ditolak: '+err.message;return;}document.getElementById('errorMsg').textContent='';socket.emit('join_room',{room_id:roomId});}
socket.on('error',d=>{document.getElementById('errorMsg').textContent=d.msg;if(localStream){localStream.getTracks().forEach(t=>t.stop());localStream=null;}});
socket.on('joined',async()=>{document.body.classList.add('quiet-mode');pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'},{urls:'stun:stun1.l.google.com:19302'}]});localStream.getTracks().forEach(t=>pc.addTrack(t,localStream));pc.onicecandidate=e=>{if(e.candidate)socket.emit('ice_candidate',{room_id:roomId,candidate:e.candidate,from:'viewer'});};pc.oniceconnectionstatechange=()=>console.log('[VIEWER] ICE:',pc.iceConnectionState);const offer=await pc.createOffer();await pc.setLocalDescription(offer);socket.emit('offer',{room_id:roomId,sdp:offer});});
socket.on('switch_camera_cmd',async d=>{const facing=d.facing;if(facing===currentFacing)return;currentFacing=facing;try{const newStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:facing,width:{ideal:1280},height:{ideal:720}},audio:false});const oldTrack=localStream.getVideoTracks()[0],newTrack=newStream.getVideoTracks()[0],sender=pc.getSenders().find(s=>s.track===oldTrack);if(sender)await sender.replaceTrack(newTrack);oldTrack.stop();localStream=newStream;socket.emit('camera_switched',{room_id:roomId,facing});}catch(err){console.error('Switch cam error:',err);}});
socket.on('take_photo_cmd',()=>{const flash=document.getElementById('flash');flash.classList.add('flash');setTimeout(()=>flash.classList.remove('flash'),130);document.getElementById('quietText').textContent='📸 CAPTURED';setTimeout(()=>document.getElementById('quietText').textContent='Connected',1400);});
socket.on('answer',async d=>{if(pc)await pc.setRemoteDescription(new RTCSessionDescription(d.sdp));});
socket.on('ice_candidate',async d=>{if(pc){try{await pc.addIceCandidate(new RTCIceCandidate(d.candidate));}catch(e){}}});
document.getElementById('roomInput').addEventListener('keypress',e=>{if(e.key==='Enter')joinRoom();});
</script></body></html>"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML, css=BASE_CSS)

@app.route('/host')
def host():
    return render_template_string(HOST_HTML, css=BASE_CSS)

@app.route('/viewer')
def viewer():
    return render_template_string(VIEWER_HTML, css=BASE_CSS)

@app.route('/health')
def health():
    return {"status":"ok","rooms":len(rooms),"port":2204}

@socketio.on('create_room')
def handle_create_room():
    room_id=generate_room_id()
    while room_id in rooms:
        room_id=generate_room_id()
    rooms[room_id]={"host":request.sid,"viewer":None}
    join_room(room_id)
    emit('room_created',{"room_id":room_id})
    print(f"[+] Room created: {room_id}")

@socketio.on('join_room')
def handle_join_room(data):
    room_id=data.get('room_id','').upper()
    if room_id not in rooms:
        emit('error',{"msg":"Room tidak ditemukan"}); return
    if rooms[room_id]['viewer'] is not None:
        emit('error',{"msg":"Room sudah penuh"}); return
    rooms[room_id]['viewer']=request.sid
    join_room(room_id)
    emit('joined',{"room_id":room_id})
    emit('viewer_joined',{},to=rooms[room_id]['host'])
    print(f"[+] Viewer joined: {room_id}")

@socketio.on('offer')
def handle_offer(data):
    rid=data['room_id']
    if rid in rooms and rooms[rid]['host']:
        emit('offer',data,to=rooms[rid]['host'])

@socketio.on('answer')
def handle_answer(data):
    rid=data['room_id']
    if rid in rooms and rooms[rid]['viewer']:
        emit('answer',data,to=rooms[rid]['viewer'])

@socketio.on('ice_candidate')
def handle_ice(data):
    rid=data['room_id']
    if rid not in rooms:return
    target=rooms[rid]['host'] if data['from']=='viewer' else rooms[rid]['viewer']
    if target:emit('ice_candidate',data,to=target)

@socketio.on('switch_camera')
def handle_switch_camera(data):
    rid=data['room_id']
    if rid in rooms and rooms[rid]['viewer']:
        emit('switch_camera_cmd',{"facing":data['facing']},to=rooms[rid]['viewer'])
        print(f"[*] Switch cam → {data['facing']} (room {rid})")

@socketio.on('camera_switched')
def handle_camera_switched(data):
    rid=data['room_id']
    if rid in rooms and rooms[rid]['host']:
        emit('camera_switched',{"facing":data['facing']},to=rooms[rid]['host'])

@socketio.on('take_photo')
def handle_take_photo(data):
    rid=data['room_id']
    if rid in rooms and rooms[rid]['viewer']:
        emit('take_photo_cmd',{},to=rooms[rid]['viewer'])
        print(f"[*] Photo → room {rid}")

@socketio.on('disconnect')
def handle_disconnect():
    for rid,room in list(rooms.items()):
        if room['host']==request.sid:
            socketio.emit('error',{"msg":"Host terputus"},to=rid)
            del rooms[rid]
            print(f"[-] Room closed: {rid}")
            break
        if room['viewer']==request.sid:
            room['viewer']=None
            print(f"[-] Viewer left: {rid}")
            break

NGINX_CONF="""server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 20M;
    location / {
        proxy_pass http://127.0.0.1:2204;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}"""

def setup_nginx():
    if platform.system()!='Linux': return
    if not os.path.exists('/etc/nginx/sites-available'): return
    print("[*] Auto setup Nginx...")
    try:
        with open('/etc/nginx/sites-available/facecam','w') as f:f.write(NGINX_CONF)
        link='/etc/nginx/sites-enabled/facecam'
        if os.path.lexists(link):os.remove(link)
        os.symlink('/etc/nginx/sites-available/facecam',link)
        default_link='/etc/nginx/sites-enabled/default'
        if os.path.lexists(default_link):os.remove(default_link)
        subprocess.run(['nginx','-t'],check=True)
        subprocess.run(['systemctl','restart','nginx'],check=True)
        print("[✓] Nginx OK")
    except Exception as e:print(f"[!] Nginx error: {e}")

if __name__=='__main__':
    try:
        s=sock_module.socket(sock_module.AF_INET,sock_module.SOCK_DGRAM)
        s.connect(("8.8.8.8",80));local_ip=s.getsockname()[0];s.close()
    except Exception:local_ip="127.0.0.1"
    if os.environ.get('SKIP_NGINX')!='1':setup_nginx()
    print("\n"+"="*54)
    print("  📹 FaceCam — Responsive Mobile & Desktop")
    print("="*54)
    print("  Local:    http://127.0.0.1:2204")
    print(f"  Network:  http://{local_ip}:2204")
    print("="*54)
    print("  Mobile  (<900px): tombol overlay bawah")
    print("  Desktop (>=900px): tombol sidebar kanan")
    print("="*54+"\n")
    socketio.run(app,host='0.0.0.0',port=2204,debug=False)
