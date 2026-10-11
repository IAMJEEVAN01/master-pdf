import os
import asyncio
import io
import json
import datetime
from aiohttp import web
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault
from pypdf import PdfWriter, PdfReader
from PIL import Image

API_ID = int(os.environ.get("API_ID", 37517668))
API_HASH = os.environ.get("API_HASH", "2416d55a1946a4fb155e1013c19337c0")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8484058723:AAHIyh7XyTqdxFDMyvpRjnpZ38GhkeJW4VI")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BRAND = "THE PARAMOUNT"
BRAND_LINK = "@THEPARAMOUNTT"
FILE_TAG = "@THEPARAMOUNTT"
LOGS_CHANNEL_ID = int(os.environ.get("LOGS_CHANNEL_ID", -1004499257797))
OWNER_ID = int(os.environ.get("OWNER_ID", 5589922297))
PREMIUM_PRICE = 19
PREMIUM_DAYS = 30
CONTACT_USERNAME = "@THEPARAMOUTT01BOT"
FORCE_CHANNEL = "THEPARAMOUNTT"
FORCE_CHANNEL_LINK = "https://t.me/THEPARAMOUNTT"

TEMP_DIR = "pdf_temp"
USERS_FILE = "users.json"
os.makedirs(TEMP_DIR, exist_ok=True)

client = TelegramClient('pdf_master_bot', API_ID, API_HASH)
user_pdfs = {}
user_images = {}
user_state = {}

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

users_db = load_users()

def is_owner(uid):
    return int(uid) == OWNER_ID

def is_premium(uid):
    if is_owner(uid):
        return True
    uid_str = str(uid)
    if uid_str not in users_db:
        return False
    expiry = users_db[uid_str].get("expiry")
    if not expiry:
        return False
    try:
        if datetime.date.fromisoformat(expiry) >= datetime.date.today():
            return True
        return False
    except:
        return False

def add_premium(uid, days):
    uid_str = str(uid)
    if uid_str not in users_db:
        users_db[uid_str] = {}
    today = datetime.date.today()
    current = users_db[uid_str].get("expiry")
    base = today
    if current:
        try:
            b = datetime.date.fromisoformat(current)
            if b > today:
                base = b
        except:
            pass
    new_expiry = base + datetime.timedelta(days=int(days))
    users_db[uid_str]["expiry"] = new_expiry.isoformat()
    users_db[uid_str]["active"] = True
    save_users(users_db)
    return new_expiry.isoformat()

def remove_premium(uid):
    uid_str = str(uid)
    if uid_str in users_db:
        users_db[uid_str]["expiry"] = None
        users_db[uid_str]["active"] = False
        save_users(users_db)

def get_expiry(uid):
    uid_str = str(uid)
    if uid_str in users_db:
        return users_db[uid_str].get("expiry", "N/A")
    return "N/A"

def bar(p):
    f = int(p / 5)
    return "█" * f + "░" * (20 - f)

async def log_file(text, path=None, name=None):
    try:
        if path and os.path.exists(path):
            await client.send_file(LOGS_CHANNEL_ID, path, caption=text, force_document=True, file_name=name)
        else:
            await client.send_message(LOGS_CHANNEL_ID, text)
    except Exception as e:
        print(f"Log err: {e}")

def safe_name(t):
    s = "".join(c for c in t if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return s or "output"

async def get_user_info(event):
    try:
        s = await event.get_sender()
        name = getattr(s, 'first_name', 'Unknown') or 'Unknown'
        if getattr(s, 'last_name', None):
            name += " " + s.last_name
        uname = f"@{s.username}" if getattr(s, 'username', None) else "No username"
        return name, uname
    except:
        return "Unknown", "No username"

async def is_joined(uid):
    try:
        entity = await client.get_entity(FORCE_CHANNEL)
        from telethon.tl.functions.channels import GetParticipantRequest
        from telethon.errors import UserNotParticipantError
        try:
            await client(GetParticipantRequest(channel=entity, participant=uid))
            return True
        except UserNotParticipantError:
            return False
        except:
            return False
    except Exception as e:
        print(f"is_joined err: {e}")
        return False

async def send_join_msg(event):
    text = (
        "╔═══════════════════════════════════════╗\n"
        "║  🔒 CHANNEL JOIN REQUIRED 🔒            ║\n"
        "╚═══════════════════════════════════════╝\n\n"
        "⚠️ Bot use karne ke liye pehle channel join karo!\n\n"
        "👇 Neeche button dabao 👇\n\n"
        f"⚡ Powered by {BRAND}"
    )
    buttons = [
        [Button.url("📢 Join Channel", FORCE_CHANNEL_LINK)],
        [Button.inline("✅ Joined — Check Again", data=b"check_join")],
    ]
    await event.reply(text, buttons=buttons)

def premium_buttons():
    return [
        [Button.inline("Buy Premium", data=b"buy_premium")],
        [Button.inline("Contact Admin", data=b"contact_admin")],
    ]

async def send_premium_msg(event):
    text = (
        "PREMIUM REQUIRED\n\n"
        "Yeh bot sirf Premium users ke liye hai!\n\n"
        f"Price: Rs {PREMIUM_PRICE} / {PREMIUM_DAYS} days\n\n"
        "Premium Features:\n"
        "Merge PDFs\nCompress PDF\nSplit PDF\nRotate PDF\n"
        "Protect PDF\nOrganize pages\nImage to PDF\n\n"
        "Buy Premium to use all features!\n\n"
        f"Powered by {BRAND}\n{BRAND_LINK}"
    )
    await event.reply(text, buttons=premium_buttons())

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if is_owner(uid):
        await event.reply(
            "╔═══════════════════════════════════════╗\n"
            "║  👑 OWNER — PDF MASTER 👑               ║\n"
            "╚═══════════════════════════════════════╝\n\n"
            "💎 Welcome Boss! THE PARAMOUNT 🖤\n\n"
            "🚀 Aapka sab kuch FREE hai!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 PDF TOOLS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📚 /merge — Multiple PDFs → 1\n"
            "🗜️ /compress — Size kam karo\n"
            "✂️ /split — Pages alag karo\n"
            "🔄 /rotate — Pages ghumao\n"
            "🔐 /protect — Password lagao\n"
            "📑 /organize — Order badlo\n"
            "📸 /imgtopdf — Images → PDF\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚡ Powered by\n"
            "💎 @THEPARAMOUNTT"
        )
        await event.reply(
            "╔═══════════════════════════════════════╗\n"
            "║  👑 OWNER COMMANDS 👑                   ║\n"
            "╚═══════════════════════════════════════╝\n\n"
            "🔑 /authuser <id> <days> — Give premium\n"
            "🚫 /revoke <id> — Remove premium\n"
            "📋 /listusers — Premium users\n"
            "🆔 /myid — Check your ID"
        )
    elif is_premium(uid):
        await event.reply(
            "╔═══════════════════════════════════════╗\n"
            "║  💎 USER — PDF MASTER 💎                ║\n"
            "╚═══════════════════════════════════════╝\n\n"
            "🎉 Welcome Premium User! 🖤\n\n"
            f"📅 Expiry: {get_expiry(uid)}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 PDF TOOLS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📚 /merge — Merge PDFs\n"
            "🗜️ /compress — Compress\n"
            "✂️ /split — Split pages\n"
            "🔄 /rotate — Rotate\n"
            "🔐 /protect — Password\n"
            "📑 /organize — Reorder\n"
            "📸 /imgtopdf — Image → PDF\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ OTHER\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 /status — Pending check\n"
            "🗑️ /cancel — Clear all\n"
            "❓ /help — Help\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚡ Powered by\n"
            "💎 @THEPARAMOUNTT"
        )
    else:
        await send_premium_msg(event)

@client.on(events.CallbackQuery(data=b"check_join"))
async def check_join_cb(event):
    uid = event.sender_id
    if await is_joined(uid):
        await event.edit("✅ Verified! Ab /start bhejo bot use karne ke liye.")
    else:
        await event.answer("❌ Abhi bhi join nahi kiya!", alert=True)

@client.on(events.NewMessage(pattern='/help'))
async def help_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    await event.reply(
        "PDF MASTER - HELP\n\n"
        "PDF TOOLS:\n"
        "/merge - Combine PDFs\n"
        "/compress - Reduce size\n"
        "/split - Extract pages\n"
        "/rotate - Rotate 90/180/270\n"
        "/protect - Password protect\n"
        "/organize - Reorder pages\n"
        "/imgtopdf - Images to PDF\n\n"
        "OTHER:\n"
        "/status - Check pending\n"
        "/cancel - Clear all\n\n"
        f"{BRAND_LINK}"
    )

@client.on(events.NewMessage(pattern='/myid'))
async def myid_cmd(event):
    uid = event.sender_id
    await event.reply(f"Your Telegram ID:\n\n`{uid}`\n\nCopy karke admin ko bhejo.\n\n{BRAND_LINK}")
@client.on(events.NewMessage(pattern='/authuser'))
async def authuser_cmd(event):
    if not is_owner(event.sender_id):
        return
    try:
        args = event.text.split()
        if len(args) < 3:
            await event.reply("Usage: /authuser <user_id> <days>")
            return
        target = int(args[1])
        days = int(args[2])
        expiry = add_premium(target, days)
        await event.reply(f"Premium Activated!\n\nUser ID: {target}\nDays: {days}\nExpiry: {expiry}")
        try:
            await client.send_message(target, f"Premium Activated!\n\nDays: {days}\nExpiry: {expiry}\n\n{BRAND_LINK}")
        except:
            pass
    except Exception as e:
        await event.reply(f"Error: {str(e)[:200]}")

@client.on(events.NewMessage(pattern='/revoke'))
async def revoke_cmd(event):
    if not is_owner(event.sender_id):
        return
    try:
        args = event.text.split()
        if len(args) < 2:
            await event.reply("Usage: /revoke <user_id>")
            return
        target = int(args[1])
        remove_premium(target)
        await event.reply(f"Revoked!\n\nUser: {target}")
    except Exception as e:
        await event.reply(f"Error: {str(e)[:200]}")

@client.on(events.NewMessage(pattern='/listusers'))
async def listusers_cmd(event):
    if not is_owner(event.sender_id):
        return
    if not users_db:
        await event.reply("No premium users yet.")
        return
    text = "Premium Users:\n\n"
    for uid, data in users_db.items():
        expiry = data.get("expiry", "N/A")
        active = "OK" if data.get("active") else "NO"
        text += f"[{active}] {uid} - {expiry}\n"
    await event.reply(text)

@client.on(events.CallbackQuery(data=b"buy_premium"))
async def buy_premium_cb(event):
    await event.edit(f"BUY PREMIUM\n\nPrice: Rs {PREMIUM_PRICE} / {PREMIUM_DAYS} days\n\nContact Admin: {CONTACT_USERNAME}\n\nPayment ke baad admin activate karega.\n\nPowered by {BRAND}")

@client.on(events.CallbackQuery(data=b"contact_admin"))
async def contact_admin_cb(event):
    await event.edit(f"CONTACT ADMIN\n\nUsername: {CONTACT_USERNAME}\n\nMessage karo\nPayment screenshot bhejo\nApna /myid bhi bhejo\n\nAdmin reply karega.\n\nPowered by {BRAND}")

@client.on(events.NewMessage(func=lambda e: e.document and e.document.mime_type == 'application/pdf'))
async def receive_pdf(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    if user_state.get(uid, {}).get("waiting"):
        await event.reply(f"Pehle current kaam complete karo!\n\n{BRAND_LINK}")
        return
    if uid not in user_pdfs:
        user_pdfs[uid] = []
    fname = None
    if event.document.attributes:
        for a in event.document.attributes:
            if hasattr(a, 'file_name'):
                fname = a.file_name
                break
    if not fname:
        fname = f"pdf_{len(user_pdfs[uid]) + 1}.pdf"
    path = os.path.join(TEMP_DIR, f"{uid}_{len(user_pdfs[uid])}_{fname}")
    msg = await event.reply(f"Downloading PDF...\n\n{bar(0)} 0%\n\n{BRAND_LINK}")
    last = -1
    async def prog(c, t):
        nonlocal last
        p = int((c / t) * 100) if t else 0
        if p >= last + 20:
            last = p
            try:
                await msg.edit(f"Downloading...\n\n{bar(p)} {p}%\n\n{BRAND_LINK}")
            except:
                pass
    try:
        await client.download_media(event.document, file=path, progress_callback=prog)
        user_pdfs[uid].append({"path": path, "name": fname})
        await msg.edit(f"PDF Added!\n\n{fname}\nTotal: {len(user_pdfs[uid])}\n\nAb command bhejo\n\n{BRAND_LINK}")
        try:
            name, uname = await get_user_info(event)
            await log_file(f"PDF LOG\n\nNAME: {name}\nUSERNAME: {uname}\nUSER ID: {uid}\nPDF: {fname}\n\n{BRAND_LINK}", path, fname)
        except:
            pass
    except Exception as e:
        await msg.edit(f"Error: {str(e)[:200]}\n\n{BRAND_LINK}")

@client.on(events.NewMessage(func=lambda e: e.photo or (e.document and e.document.mime_type and e.document.mime_type.startswith('image/'))))
async def receive_image(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    if user_state.get(uid, {}).get("waiting"):
        return
    if uid not in user_images:
        user_images[uid] = []
    fname = f"img_{len(user_images[uid]) + 1}.jpg"
    if event.document and event.document.attributes:
        for a in event.document.attributes:
            if hasattr(a, 'file_name'):
                fname = a.file_name
                break
    path = os.path.join(TEMP_DIR, f"{uid}_img_{len(user_images[uid])}_{fname}")
    msg = await event.reply(f"Downloading Image...\n\n{BRAND_LINK}")
    try:
        await client.download_media(event.message, file=path)
        user_images[uid].append({"path": path, "name": fname})
        await msg.edit(f"Image Added!\n\n{fname}\nTotal: {len(user_images[uid])}\n\nSend /imgtopdf\n\n{BRAND_LINK}")
        try:
            name, uname = await get_user_info(event)
            await log_file(f"IMAGE LOG\n\nNAME: {name}\nUSERNAME: {uname}\nUSER ID: {uid}\nIMAGE: {fname}\n\n{BRAND_LINK}", path, fname)
        except:
            pass
    except Exception as e:
        await msg.edit(f"Error: {str(e)[:200]}\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/merge'))
async def merge_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 2:
        await event.reply(f"Kam se kam 2 PDFs chahiye!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "merge", "pdfs": pdfs}
    await event.reply(f"{len(pdfs)} PDFs ready!\n\nFinal PDF ka naam bhejo:\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/compress'))
async def compress_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 1:
        await event.reply(f"Pehle PDF bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "compress", "pdfs": pdfs[-1:]}
    await event.reply(f"Compress PDF\n\nFinal naam bhejo:\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/split'))
async def split_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 1:
        await event.reply(f"Pehle PDF bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "split", "pdfs": pdfs[-1:]}
    await event.reply(f"Split PDF\n\nPages range bhejo (1-5):\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/rotate'))
async def rotate_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 1:
        await event.reply(f"Pehle PDF bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "rotate", "pdfs": pdfs[-1:]}
    await event.reply(f"Rotate PDF\n\nAngle bhejo (90/180/270):\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/protect'))
async def protect_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 1:
        await event.reply(f"Pehle PDF bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "protect", "pdfs": pdfs[-1:]}
    await event.reply(f"Protect PDF\n\nPassword bhejo:\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/organize'))
async def organize_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pdfs = user_pdfs.get(uid, [])
    if len(pdfs) < 1:
        await event.reply(f"Pehle PDF bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "organize", "pdfs": pdfs[-1:]}
    await event.reply(f"Organize Pages\n\nNaya order bhejo (3,1,2,5,4):\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/imgtopdf'))
async def imgtopdf_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    imgs = user_images.get(uid, [])
    if len(imgs) < 1:
        await event.reply(f"Pehle images bhejo!\n\n{BRAND_LINK}")
        return
    user_state[uid] = {"waiting": True, "action": "imgtopdf", "images": imgs}
    await event.reply(f"{len(imgs)} Images ready!\n\nPDF ka naam bhejo:\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    pc = len(user_pdfs.get(uid, []))
    ic = len(user_images.get(uid, []))
    await event.reply(f"Pending:\nPDFs: {pc}\nImages: {ic}\n\n{BRAND_LINK}")

@client.on(events.NewMessage(pattern='/cancel'))
async def cancel_cmd(event):
    uid = event.sender_id
    if not is_owner(uid):
        if not await is_joined(uid):
            await send_join_msg(event)
            return
    if not (is_owner(uid) or is_premium(uid)):
        await send_premium_msg(event)
        return
    if uid in user_pdfs:
        for p in user_pdfs[uid]:
            try: os.remove(p["path"])
            except: pass
        user_pdfs[uid] = []
    if uid in user_images:
        for p in user_images[uid]:
            try: os.remove(p["path"])
            except: pass
        user_images[uid] = []
    user_state[uid] = {}
    await event.reply(f"Cleared all files\n\n{BRAND_LINK}")

@client.on(events.NewMessage(func=lambda e: e.is_private and e.text and not e.text.startswith('/') and user_state.get(e.sender_id, {}).get("waiting") and not e.photo and not (e.document and e.document.mime_type and e.document.mime_type.startswith('image/'))))
async def handle_input(event):
    uid = event.sender_id
    if not (is_owner(uid) or is_premium(uid)):
        return
    st = user_state.get(uid, {})
    if not st.get("waiting"):
        return
    action = st.get("action")
    pdfs = st.get("pdfs", [])
    imgs = st.get("images", [])
    text = event.text.strip()
    st["waiting"] = False
    user_state[uid] = st
    try:
        if action == "merge": await do_merge(event, uid, pdfs, text)
        elif action == "compress": await do_compress(event, uid, pdfs, text)
        elif action == "split": await do_split(event, uid, pdfs, text)
        elif action == "rotate": await do_rotate(event, uid, pdfs, text)
        elif action == "protect": await do_protect(event, uid, pdfs, text)
        elif action == "organize": await do_organize(event, uid, pdfs, text)
        elif action == "imgtopdf": await do_imgtopdf(event, uid, imgs, text)
    except Exception as e:
        await event.reply(f"Error: {str(e)[:250]}\n\n{BRAND_LINK}")
        user_state[uid] = {}

async def do_merge(event, uid, pdfs, name):
    sn = safe_name(name)
    out = os.path.join(TEMP_DIR, f"{uid}_merge.pdf")
    msg = await event.reply(f"Merging {len(pdfs)} PDFs...\n\n{bar(0)} 0%\n\n{BRAND_LINK}")
    w = PdfWriter()
    total = len(pdfs)
    for i, p in enumerate(pdfs, 1):
        try:
            r = PdfReader(p["path"])
            for page in r.pages: w.add_page(page)
        except: pass
        pc = int((i / total) * 100)
        try: await msg.edit(f"Merging...\n\n{bar(pc)} {pc}%\n{i}/{total}\n\n{BRAND_LINK}")
        except: pass
        await asyncio.sleep(0.05)
    with open(out, "wb") as f: w.write(f)
    w.close()
    await send_final(event, out, f"{sn}_{FILE_TAG}.pdf", f"Merged {total} PDFs!", uid)
    cleanup_user(uid)

async def do_compress(event, uid, pdfs, name):
    sn = safe_name(name)
    src = pdfs[0]["path"]
    out = os.path.join(TEMP_DIR, f"{uid}_comp.pdf")
    msg = await event.reply(f"Compressing...\n\n{bar(0)} 0%\n\n{BRAND_LINK}")
    orig = os.path.getsize(src) / (1024 * 1024)
    r = PdfReader(src)
    w = PdfWriter()
    total = len(r.pages)
    for i, page in enumerate(r.pages, 1):
        try: page.compress_content_streams()
        except: pass
        w.add_page(page)
        pc = int((i / total) * 100)
        try: await msg.edit(f"Compressing...\n\n{bar(pc)} {pc}%\n\n{BRAND_LINK}")
        except: pass
    with open(out, "wb") as f: w.write(f)
    w.close()
    new = os.path.getsize(out) / (1024 * 1024)
    saved = orig - new
    await send_final(event, out, f"{sn}_{FILE_TAG}.pdf", f"Compressed!\n{orig:.2f} -> {new:.2f} MB\nSaved: {saved:.2f} MB", uid)
    cleanup_user(uid)

async def do_split(event, uid, pdfs, spec):
    src = pdfs[0]["path"]
    out = os.path.join(TEMP_DIR, f"{uid}_split.pdf")
    r = PdfReader(src)
    total = len(r.pages)
    pages = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            try:
                a, b = part.split('-')
                pages.extend(range(int(a) - 1, int(b)))
            except: pass
        elif part.isdigit():
            pages.append(int(part) - 1)
    w = PdfWriter()
    count = 0
    for p in pages:
        if 0 <= p < total:
            w.add_page(r.pages[p])
            count += 1
    with open(out, "wb") as f: w.write(f)
    w.close()
    await send_final(event, out, f"split_{FILE_TAG}.pdf", f"Split: {count} pages", uid)
    cleanup_user(uid)

async def do_rotate(event, uid, pdfs, angle):
    src = pdfs[0]["path"]
    out = os.path.join(TEMP_DIR, f"{uid}_rot.pdf")
    try: a = int(angle)
    except: a = 90
    r = PdfReader(src)
    w = PdfWriter()
    for page in r.pages:
        page.rotate(a)
        w.add_page(page)
    with open(out, "wb") as f: w.write(f)
    w.close()
    await send_final(event, out, f"rotated_{FILE_TAG}.pdf", f"Rotated {a} deg", uid)
    cleanup_user(uid)

async def do_protect(event, uid, pdfs, password):
    src = pdfs[0]["path"]
    out = os.path.join(TEMP_DIR, f"{uid}_prot.pdf")
    r = PdfReader(src)
    w = PdfWriter()
    for page in r.pages: w.add_page(page)
    try:
        w.encrypt(password)
    except:
        await event.reply(f"Encryption failed\n\n{BRAND_LINK}")
        cleanup_user(uid)
        return
    with open(out, "wb") as f: w.write(f)
    w.close()
    await send_final(event, out, f"protected_{FILE_TAG}.pdf", f"Protected!", uid)
    cleanup_user(uid)

async def do_organize(event, uid, pdfs, spec):
    src = pdfs[0]["path"]
    out = os.path.join(TEMP_DIR, f"{uid}_org.pdf")
    r = PdfReader(src)
    total = len(r.pages)
    order = [int(x) - 1 for x in spec.split(',') if x.strip().isdigit()]
    w = PdfWriter()
    for p in order:
        if 0 <= p < total:
            w.add_page(r.pages[p])
    with open(out, "wb") as f: w.write(f)
    w.close()
    await send_final(event, out, f"organized_{FILE_TAG}.pdf", f"Reorganized!", uid)
    cleanup_user(uid)

async def do_imgtopdf(event, uid, images, name):
    sn = safe_name(name)
    out = os.path.join(TEMP_DIR, f"{uid}_img.pdf")
    msg = await event.reply(f"Converting {len(images)} images...\n\n{bar(0)} 0%\n\n{BRAND_LINK}")
    pil_images = []
    total = len(images)
    for i, img in enumerate(images, 1):
        try:
            im = Image.open(img["path"])
            if im.mode in ('RGBA', 'P', 'LA'):
                im = im.convert('RGB')
            pil_images.append(im)
        except Exception as e:
            print(f"Img err: {e}")
        pc = int((i / total) * 100)
        try: await msg.edit(f"Processing...\n\n{bar(pc)} {pc}%\n{i}/{total}\n\n{BRAND_LINK}")
        except: pass
        await asyncio.sleep(0.05)
    if not pil_images:
        await msg.edit(f"No valid images!\n\n{BRAND_LINK}")
        cleanup_user(uid)
        return
    first, rest = pil_images[0], pil_images[1:]
    if rest:
        first.save(out, "PDF", save_all=True, append_images=rest)
    else:
        first.save(out, "PDF")
    await msg.edit(f"Saving...\n\n{bar(100)} 100%\n\n{BRAND_LINK}")
    await send_final(event, out, f"{sn}_{FILE_TAG}.pdf", f"Images to PDF ({len(pil_images)} pages)", uid)
    cleanup_user(uid)

async def send_final(event, path, filename, title, uid):
    if not os.path.exists(path):
        await event.reply(f"File not created\n\n{BRAND_LINK}")
        return
    size = os.path.getsize(path) / (1024 * 1024)
    cap = f"{title}\n\n{filename}\n{size:.2f} MB\n\nPowered by {BRAND}\n{BRAND_LINK}"
    um = await event.reply(f"Uploading...\n\n{bar(0)} 0%\n\n{BRAND_LINK}")
    last = -1
    async def up(c, t):
        nonlocal last
        p = int((c / t) * 100) if t else 0
        if p >= last + 10:
            last = p
            try: await um.edit(f"Uploading...\n\n{bar(p)} {p}%\n\n{BRAND_LINK}")
            except: pass
    await client.send_file(event.chat_id, path, caption=cap, force_document=True, file_name=filename, progress_callback=up)
    try:
        name, uname = await get_user_info(event)
        await log_file(f"FINAL FILE LOG\n\nNAME: {name}\nUSERNAME: {uname}\nUSER ID: {uid}\nFILE: {filename}\nSIZE: {size:.2f} MB\n\n{BRAND_LINK}", path, filename)
    except Exception as e:
        print(f"Log err: {e}")
    try: os.remove(path)
    except: pass

def cleanup_user(uid):
    if uid in user_pdfs:
        for p in user_pdfs[uid]:
            try: os.remove(p["path"])
            except: pass
        user_pdfs[uid] = []
    if uid in user_images:
        for p in user_images[uid]:
            try: os.remove(p["path"])
            except: pass
        user_images[uid] = []
    user_state[uid] = {}

async def set_commands():
    commands = [
        BotCommand(command="start", description="Welcome"),
        BotCommand(command="help", description="Help"),
        BotCommand(command="myid", description="Get ID"),
        BotCommand(command="merge", description="Merge PDFs"),
        BotCommand(command="compress", description="Compress PDF"),
        BotCommand(command="split", description="Split PDF"),
        BotCommand(command="rotate", description="Rotate PDF"),
        BotCommand(command="protect", description="Password PDF"),
        BotCommand(command="organize", description="Reorganize"),
        BotCommand(command="imgtopdf", description="Image to PDF"),
        BotCommand(command="status", description="Pending"),
        BotCommand(command="cancel", description="Clear"),
    ]
    try:
        await client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code="en",
            commands=commands
        ))
        print("Commands set!")
    except Exception as e:
        print(f"Command err: {e}")

async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

async def main():
    await client.start(bot_token=BOT_TOKEN)
    await set_commands()
    await start_web_server()
    print(f"BOT STARTED - {BRAND}")
    print(f"Owner: {OWNER_ID}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
