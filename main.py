import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio, aiohttp, json, os, re, time, random, base64, platform
from collections import defaultdict

# ================== FLASK WEB SERVER ==================
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot LieuNhuyen dang chay 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# ======================================================

# ============ CẤU HÌNH ============
TOKEN = os.getenv("TOKEN", "DÁN_TOKEN_BOT_VÀO_ĐÂY")          
OWNER_ID = 1371529206470803466            
BOT_NAME = "LieuNhuyen"
GIF_URL = "https://cdn.discordapp.com/attachments/1561230413295259678/1561232395921793105/1000098336.gif?ex=6ad59a79&is=6ad448f9&hm=4a5456d27c3caa58650604acb34d0a5871f3d89d8f2eafe95616e0c61e22d4a0"
INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=1561222080907968585&permissions=8&scope=bot%20applications.commands"
# ==================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, activity=discord.Game(name="Hệ thống phòng thủ đang trực chiến"))
tree = bot.tree
START_TIME = time.time()

# ================== STATE & FILE ==================
DATA_DIR = "server_data"
BACKUP_DIR = "backups"
EMOJI_DIR = "emojis"
LOG_CHANNEL_NAME = "guard-logs"
GIF_PATH = "nuke_gif.gif"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(EMOJI_DIR, exist_ok=True)

SUPPORT_FILE = os.path.join(DATA_DIR, "supported_servers.json")
if not os.path.exists(SUPPORT_FILE): 
    with open(SUPPORT_FILE, "w") as f: json.dump({"servers": []}, f)

DEFAULT_VERIFY_SETTINGS = {
    "title": "🛡️ XÁC MINH THÀNH VIÊN",
    "description": "Bấm nút bên dưới để xác minh và mở khóa chat.",
    "color": 0x2ecc71, "gif_url": "", "role_cho": 0, "role_chinh_1": 0, "role_chinh_2": 0
}

DEFAULT_GUARD = {
    "anti_raid": True, "anti_scam": True, "anti_nuke": True, "anti_cap": True,
    "anti_emoji": True, "anti_invite": True, "anti_link": True, "anti_spam": True, "anti_webhook": True,
    "anti_gif": True, "anti_image": True, "anti_video": True, "anti_bot_raid": True, "anti_sex": True,
    "anti_sex_media": True, "anti_sex_emote": True
}
DEFAULT_SETTINGS = {"cap_threshold": "10-20"}
CAP_RANGES = {"10-20": (10, 20), "30-40": (30, 40), "50-100": (50, 100)}

def get_guild_dir(guild_id):
    path = os.path.join(DATA_DIR, str(guild_id))
    os.makedirs(path, exist_ok=True)
    return path

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f: d = json.load(f)
            for k, v in default.items(): d.setdefault(k, v)
            return d
        except: pass
    return dict(default)

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

def get_guild_data(guild_id, file_name, default_val):
    path = os.path.join(get_guild_dir(guild_id), file_name)
    return load_json(path, default_val)

def save_guild_data(guild_id, file_name, data):
    path = os.path.join(get_guild_dir(guild_id), file_name)
    save_json(path, data)

BACKUPS = {}
def load_backups():
    for fn in os.listdir(BACKUP_DIR):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(BACKUP_DIR, fn)) as f: BACKUPS[int(fn[:-5])] = json.load(f)
            except: pass
load_backups()

MESSAGE_CACHE = defaultdict(list)
JOIN_CACHE = defaultdict(list)
NUKE_CACHE = defaultdict(list)
SPAM_WARN_CACHE = defaultdict(int)

INVITE_RE = re.compile(r"(discord\.gg|discord\.com/invite)/\w+", re.I)
LINK_RE = re.compile(r"https?://\S+", re.I)
EMOJI_RE = re.compile(r"<a?:\w+:\d+>|[\U0001F300-\U0001FAFF\u2600-\u27BF]")
SCAM_WORDS = ["free nitro", "gift nitro", "steam gift", "claim reward", "airdrop", "click here to win", "free robux", "crypto giveaway", "tbank"]
SEX_WORDS = ["sex", "địt", "cặc", "lồn", "buồi", "dâm", "ảnh nóng", "gái gọi", "phim heo", "porn", "nude", "xxx", "18+"]

# ================== HELPER ==================
def is_admin(m): return m.guild_permissions.administrator
def is_owner(uid): return uid == OWNER_ID
def is_whitelisted(guild_id, uid): 
    wl_list = get_guild_data(guild_id, "whitelist.json", {"users": []})["users"]
    return uid in wl_list or uid == bot.user.id

def get_active_vip(guild_id):
    data = get_guild_data(guild_id, "vip.json", {"users": {}})
    if "users" in data and isinstance(data["users"], list):
        old_list = data["users"]
        data["users"] = {str(uid): {"expire": 9999999999} for uid in old_list}
        save_guild_data(guild_id, "vip.json", data)
    return data["users"]

def is_vip(guild_id, uid):
    if is_owner(uid): return True
    vip_users = get_active_vip(guild_id)
    user_data = vip_users.get(str(uid))
    if not user_data: return False
    if time.time() > user_data.get("expire", 0):
        del vip_users[str(uid)]
        save_guild_data(guild_id, "vip.json", {"users": vip_users})
        return False
    return True

# ===== HÀM XỬ LÝ WARN =====
def get_warns(guild_id, uid):
    data = get_guild_data(guild_id, "warns.json", {"users": {}})
    return data["users"].get(str(uid), [])

def add_warn(guild_id, uid, reason):
    data = get_guild_data(guild_id, "warns.json", {"users": {}})
    if str(uid) not in data["users"]: data["users"][str(uid)] = []
    data["users"][str(uid)].append({"reason": reason, "time": time.time()})
    save_guild_data(guild_id, "warns.json", data)
    return len(data["users"][str(uid)])

def clear_warns(guild_id, uid):
    data = get_guild_data(guild_id, "warns.json", {"users": {}})
    if str(uid) in data["users"]:
        del data["users"][str(uid)]
        save_guild_data(guild_id, "warns.json", data)

async def download_gif():
    if not os.path.exists(GIF_PATH):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GIF_URL) as resp:
                    if resp.status == 200:
                        with open(GIF_PATH, "wb") as f: f.write(await resp.read())
        except: pass

async def ensure_log_channel(guild, force=False):
    ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if ch and not force: return ch
    try:
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True), guild.owner: discord.PermissionOverwrite(read_messages=True, send_messages=False)}
        if ch: await ch.delete(reason="Recreate log")
        return await guild.create_text_channel(LOG_CHANNEL_NAME, overwrites=overwrites, topic="🛡️ Log bảo vệ - Không xóa!", reason="Auto create log")
    except: return None

async def send_punish_gif(guild, action, member, reason):
    await download_gif()
    ch_log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not ch_log: ch_log = await ensure_log_channel(guild)
    
    if ch_log and os.path.exists(GIF_PATH):
        try:
            e = discord.Embed(
                title=f"🚨 HÌNH PHẠT: {action.upper()} 🚨", 
                description=f"**Đối tượng:** {member.mention} (`{member.id}`)\n**Lý do:** {reason}", 
                color=0xe74c3c if action.lower() in ["ban", "kick"] else 0xf1c40f
            )
            e.set_image(url="attachment://nuke_gif.gif")
            await ch_log.send(embed=e, file=discord.File(GIF_PATH))
        except Exception as e: print(f"Lỗi gửi GIF: {e}")

async def dm_report(guild, member, reason):
    try:
        owner = await bot.fetch_user(OWNER_ID)
        if owner: await owner.send(f"🛡️ **LOG HỆ THỐNG**\n**Server:** {guild.name}\n**Đối tượng:** {member.mention} (`{member.id}`)\n**Hành vi:** {reason}")
    except: pass
    try:
        await member.send(f"⚠️ **CẢNH BÁO TỪ {guild.name}**\nTin nhắn của bạn đã bị xóa vì: `{reason}`.")
    except: pass

async def check_nsfw_image(url):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {'url': url, 'models': 'nudity-2.0,wad,offensive'}
            async with session.get("https://api.sightengine.com/1.0/check.json", params=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('nudity', {}).get('sexual_activity', 0) > 0.7 or data.get('nudity', {}).get('sexual_display', 0) > 0.7:
                        return True
    except: pass
    return False

# ================== TỰ ĐỘNG QUÉT VIP HẾT HẠN ==================
@tasks.loop(minutes=1)
async def check_vip_expired():
    for g in bot.guilds:
        try:
            vip_users = get_active_vip(g.id)
            changed = False
            now = time.time()
            for uid, data in list(vip_users.items()):
                if now > data.get("expire", 0):
                    del vip_users[uid]
                    changed = True
                    try:
                        member = await g.fetch_member(int(uid))
                        if member:
                            await member.send(f"⚠️ **THÔNG BÁO TỪ {g.name}**\nGói VIP của bạn đã **HẾT HẠN** vào lúc <t:{int(data['expire'])}:F>.\nVui lòng liên hệ Admin để gia hạn và tiếp tục sử dụng!")
                    except: pass
            if changed:
                save_guild_data(g.id, "vip.json", {"users": vip_users})
        except: pass

# ================== LỆNH !getbot (Gửi DM) ==================
class InviteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🤖 Mời Bot Vào Server", url=INVITE_URL, style=discord.ButtonStyle.link))

@bot.command(name="getbot")
async def getbot_cmd(ctx):
    await ctx.send(f"📩 Đã gửi thông tin qua tin nhắn riêng (DM) cho {ctx.author.mention}!")
    e = discord.Embed(
        title="🤖 LIỄU NHUYÊN - VUA BẢO VỆ SERVER",
        description="Ta là **Liễu Vô Song**, kẻ thống trị bóng tối, người bảo vệ server của ngươi!\n\n"
                    "Bấm nút bên dưới để mời ta vào server và trải nghiệm sức mạnh bảo vệ tuyệt đối.",
        color=0x9b59b6
    )
    await download_gif()
    if os.path.exists(GIF_PATH): e.set_image(url="attachment://nuke_gif.gif")
    try:
        if os.path.exists(GIF_PATH): await ctx.author.send(embed=e, view=InviteView(), file=discord.File(GIF_PATH))
        else: await ctx.author.send(embed=e, view=InviteView())
    except discord.Forbidden:
        await ctx.send(f"❌ {ctx.author.mention}, bạn đang tắt tin nhắn riêng (DM). Hãy bật lại để nhận link!")

# ================== SLASH: HELP & DEBUG & LIST SV ==================
@tree.command(name="help", description="📖 Danh sách lệnh")
async def help_cmd(interaction: discord.Interaction):
    # Đã thêm defer để tránh lỗi "Ứng dụng không phản hồi"
    await interaction.response.defer(ephemeral=True)
    
    e = discord.Embed(title=f"📖 HƯỚNG DẪN SỬ DỤNG {BOT_NAME.upper()}", color=0x5865F2)
    e.add_field(name="🛡️ **GUARD** _(Admin)_", value="`/guard` — Bảng bảo vệ\n`/whitelist add|remove|list` — Miễn nhiễm\n`/mute`, `/unmute`, `/kick`, `/ban`, `/unban`", inline=False)
    e.add_field(name="⚠️ **CẢNH CÁO** _(Admin)_", value="`/warn` — Cảnh cáo (2 lần = Mute 5p)\n`/warns` — Xem cảnh cáo\n`/clearwarns` — Xóa cảnh cáo", inline=False)
    e.add_field(name="✅ **VERIFY** _(Owner)_", value="`/verify setup` — Tạo bảng xác minh (2 Role thưởng)\n`/verify setting` — Xem cài đặt", inline=False)
    e.add_field(name="💾 **BACKUP** _(VIP/Owner)_", value="`/backup` — Lưu server\n`/restore` — Khôi phục (Miễn phí)\n`/getfree` — Dùng 1 lần (Free)", inline=False)
    e.add_field(name="👑 **QUẢN LÝ** _(Owner)_", value="`/vip add|remove|list` — Quản lý VIP có thời hạn\n`/listsv` — Danh sách server hỗ trợ\n`/debug` — Gửi báo cáo về DM Owner\n`/notice` | `/unnotice` — Thông báo", inline=False)
    e.set_footer(text="Gõ !getbot để nhận link mời Bot qua DM.")
    
    # Dùng followup.send
    await interaction.followup.send(embed=e, ephemeral=True)

@tree.command(name="debug", description="🛠️ Gửi thông tin hệ thống của Bot về DM Owner")
async def debug_cmd(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        return await interaction.response.send_message("❌ Chỉ Owner mới có quyền xem thông tin này.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    uptime_seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    e = discord.Embed(title="🛠️ BÁO CÁO HỆ THỐNG (DEBUG)", color=0x00FFCC)
    e.add_field(name="⏱️ Thời gian hoạt động", value=f"{hours}h {minutes}m {seconds}s", inline=False)
    e.add_field(name="📡 Độ trễ (Ping)", value=f"{round(bot.latency * 1000)}ms", inline=False)
    e.add_field(name="🌐 Số Server", value=f"{len(bot.guilds)}", inline=False)
    e.add_field(name="👥 Tổng số User", value=f"{len(set(bot.get_all_members()))}", inline=False)
    e.add_field(name="💻 Nền tảng", value=f"Python {platform.python_version()} | Discord.py {discord.__version__}", inline=False)
    
    try:
        owner = await bot.fetch_user(OWNER_ID)
        await owner.send(embed=e)
        await interaction.followup.send("✅ Đã gửi báo cáo vào DM của bạn.", ephemeral=True)
    except:
        await interaction.followup.send("❌ Không thể gửi DM (Bạn đã chặn bot).", ephemeral=True)

@tree.command(name="listsv", description="📋 Danh sách các Server đã kích hoạt VIP (Owner)")
async def listsv_cmd(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): 
        return await interaction.response.send_message("❌ Chỉ Owner mới dùng được lệnh này.", ephemeral=True)
    sup_data = load_json(SUPPORT_FILE, {"servers": []})
    if not sup_data["servers"]:
        return await interaction.response.send_message("📭 Chưa có Server nào được kích hoạt VIP.", ephemeral=True)
    lines = []
    for gid in sup_data["servers"]:
        guild = bot.get_guild(gid)
        g_name = guild.name if guild else "Đã rời Server"
        lines.append(f"• {g_name} (`{gid}`)")
    await interaction.response.send_message(embed=discord.Embed(title="📋 Server Hỗ Trợ VIP", description="\n".join(lines), color=0x00FFCC), ephemeral=True)

# ================== WARN COMMANDS ==================
@tree.command(name="warn", description="⚠️ Cảnh cáo một thành viên (2 lần = Mute 5p)")
@app_commands.describe(member="Thành viên cần cảnh cáo", reason="Lý do cảnh cáo")
async def warn_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    if member.bot: return await interaction.response.send_message("❌ Không thể cảnh cáo Bot.", ephemeral=True)
    
    warns = add_warn(interaction.guild_id, member.id, reason)
    
    if warns >= 2:
        try:
            await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=5), reason="Đạt 2 lần cảnh cáo")
            await send_punish_gif(interaction.guild, "Mute (2 Warns)", member, f"Lý do: {reason}")
            clear_warns(interaction.guild_id, member.id)
            await interaction.response.send_message(f"🔇 {member.mention} đã bị **Mute 5 phút** do nhận đủ 2 cảnh cáo (Warns đã được reset).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Đã cảnh cáo nhưng lỗi Mute: {e}", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Đã cảnh cáo {member.mention} (Lần {warns}/2).\n**Lý do:** {reason}", ephemeral=True)

@tree.command(name="warns", description="📜 Xem danh sách cảnh cáo của thành viên")
@app_commands.describe(member="Thành viên cần xem")
async def warns_cmd(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    warns = get_warns(interaction.guild_id, member.id)
    if not warns:
        return await interaction.response.send_message(f"✅ {member.mention} không có cảnh cáo nào.", ephemeral=True)
    
    e = discord.Embed(title=f"📜 Cảnh cáo của {member.name}", color=0xf1c40f)
    for i, w in enumerate(warns, 1):
        e.add_field(name=f"Lần {i}", value=f"**Lý do:** {w['reason']}\n**Thời gian:** <t:{int(w['time'])}:R>", inline=False)
    await interaction.response.send_message(embed=e, ephemeral=True)

@tree.command(name="clearwarns", description="🗑️ Xóa toàn bộ cảnh cáo của thành viên")
@app_commands.describe(member="Thành viên cần xóa cảnh cáo")
async def clearwarns_cmd(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    clear_warns(interaction.guild_id, member.id)
    await interaction.response.send_message(f"🗑️ Đã xóa toàn bộ cảnh cáo của {member.mention}.", ephemeral=True)

# ================== WHITELIST & VIP & QUẢN LÝ ==================
whitelist_group = app_commands.Group(name="whitelist", description="✅ Quản lý Whitelist")
@whitelist_group.command(name="add", description="Thêm user")
async def wl_add(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    data = get_guild_data(interaction.guild_id, "whitelist.json", {"users": []})
    if user.id not in data["users"]: data["users"].append(user.id)
    save_guild_data(interaction.guild_id, "whitelist.json", data)
    await interaction.response.send_message(f"✅ Đã whitelist {user.mention}", ephemeral=True)
@whitelist_group.command(name="remove", description="Xóa user")
async def wl_remove(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    data = get_guild_data(interaction.guild_id, "whitelist.json", {"users": []})
    if user.id in data["users"]: data["users"].remove(user.id)
    save_guild_data(interaction.guild_id, "whitelist.json", data)
    await interaction.response.send_message(f"🗑️ Đã xóa whitelist {user.mention}", ephemeral=True)
@whitelist_group.command(name="list", description="Xem danh sách")
async def wl_list(interaction: discord.Interaction):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    data = get_guild_data(interaction.guild_id, "whitelist.json", {"users": []})
    lines = [f"• <@{uid}>" for uid in data["users"]]
    await interaction.response.send_message(embed=discord.Embed(title="✅ Whitelist", description="\n".join(lines) or "Trống", color=0x2ecc71), ephemeral=True)
tree.add_command(whitelist_group)

vip_group = app_commands.Group(name="vip", description="👑 Quản lý VIP (Owner)")
@vip_group.command(name="add", description="Thêm VIP có thời hạn")
async def vip_add(interaction: discord.Interaction, user: discord.User, days: int = 30):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    vip_users = get_active_vip(interaction.guild_id)
    expire_time = time.time() + (days * 86400)
    if str(user.id) in vip_users and is_vip(interaction.guild_id, user.id):
        expire_time = max(vip_users[str(user.id)]["expire"], time.time()) + (days * 86400)
    vip_users[str(user.id)] = {"expire": expire_time}
    save_guild_data(interaction.guild_id, "vip.json", {"users": vip_users})
    
    sup_data = load_json(SUPPORT_FILE, {"servers": []})
    if interaction.guild_id not in sup_data["servers"]:
        sup_data["servers"].append(interaction.guild_id)
        save_json(SUPPORT_FILE, sup_data)
        
    await interaction.response.send_message(f"👑 Đã thêm VIP cho {user.mention}.\n**Hết hạn:** <t:{int(expire_time)}:F>", ephemeral=True)

@vip_group.command(name="remove", description="Xóa VIP")
async def vip_remove(interaction: discord.Interaction, user: discord.User):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    vip_users = get_active_vip(interaction.guild_id)
    if str(user.id) in vip_users:
        del vip_users[str(user.id)]
        save_guild_data(interaction.guild_id, "vip.json", {"users": vip_users})
        await interaction.response.send_message(f"🗑️ Đã xóa VIP: {user.mention}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {user.mention} không có trong danh sách VIP.", ephemeral=True)

@vip_group.command(name="list", description="Danh sách VIP")
async def vip_list(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    vip_users = get_active_vip(interaction.guild_id)
    if not vip_users:
        return await interaction.response.send_message("📭 Danh sách VIP trống.", ephemeral=True)
    lines = []
    for uid, data in vip_users.items():
        expire = data.get("expire", 0)
        if time.time() > expire: continue
        lines.append(f"• <@{uid}> — Hết hạn: <t:{int(expire)}:R>")
    if not lines: return await interaction.response.send_message("📭 Tất cả VIP đã hết hạn.", ephemeral=True)
    await interaction.response.send_message(embed=discord.Embed(title="👑 Danh sách VIP", description="\n".join(lines), color=0xF1C40F), ephemeral=True)
tree.add_command(vip_group)

@tree.command(name="mute", description="🔇 Cấm chat (Timeout)")
async def mute_cmd(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "Không có lý do"):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    try:
        await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(f"🔇 Đã mute {member.mention} trong {minutes} phút.", ephemeral=True)
        await send_punish_gif(interaction.guild, "Mute", member, reason)
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@tree.command(name="unmute", description="🔊 Gỡ cấm chat (Timeout)")
async def unmute_cmd(interaction: discord.Interaction, member: discord.Member):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 Đã gỡ mute cho {member.mention}.", ephemeral=True)
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@tree.command(name="kick", description="👢 Đá thành viên")
async def kick_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 Đã kick {member.mention}.", ephemeral=True)
        await send_punish_gif(interaction.guild, "Kick", member, reason)
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@tree.command(name="ban", description="🔨 Cấm vĩnh viễn")
async def ban_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Đã ban {member.mention}.", ephemeral=True)
        await send_punish_gif(interaction.guild, "Ban", member, reason)
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@tree.command(name="unban", description="🔓 Gỡ cấm vĩnh viễn")
async def unban_cmd(interaction: discord.Interaction, user_id: str, reason: str = "Không có lý do"):
    if not is_admin(interaction.user): return await interaction.response.send_message("❌ Cần Admin.", ephemeral=True)
    try:
        user = discord.Object(id=int(user_id))
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"🔓 Đã gỡ ban cho ID `{user_id}`.", ephemeral=True)
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# ================== VERIFY (2 Role Thưởng) ==================
class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✅ XÁC MINH", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_guild_data(interaction.guild_id, "verify_cfg.json", DEFAULT_VERIFY_SETTINGS)
        role1 = interaction.guild.get_role(cfg["role_chinh_1"])
        role2 = interaction.guild.get_role(cfg["role_chinh_2"])
        role_cho = interaction.guild.get_role(cfg["role_cho"])
        
        if not role1: 
            return await interaction.response.send_message("❌ Chưa cài đặt Role Chính 1. Hãy dùng /verify setting để kiểm tra.", ephemeral=True)
        if role1 in interaction.user.roles: 
            return await interaction.response.send_message("✅ Đã xác minh.", ephemeral=True)
        
        try:
            await interaction.user.add_roles(role1)
            if role2: await interaction.user.add_roles(role2)
            if role_cho and role_cho in interaction.user.roles: await interaction.user.remove_roles(role_cho)
            await interaction.response.send_message("✅ Xác minh thành công! Bạn đã có thể chat.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ **Lỗi:** Bot thiếu quyền cấp Role. Hãy kéo Role của Bot lên trên cùng!", ephemeral=True)
        except Exception as e: 
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

verify_group = app_commands.Group(name="verify", description="✅ Quản lý xác minh (Owner)")
@verify_group.command(name="setup", description="Tạo bảng xác minh (2 Role Thưởng)")
async def verify_setup(interaction: discord.Interaction, role_chinh_1: discord.Role, role_chinh_2: discord.Role, role_cho: discord.Role, title: str, description: str, color: str, gif_url: str = None):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    try: hex_color = int(color.replace("#", ""), 16)
    except: hex_color = 0x2ecc71
    cfg = {"title": title, "description": description, "color": hex_color, "gif_url": gif_url or "", "role_chinh_1": role_chinh_1.id, "role_chinh_2": role_chinh_2.id, "role_cho": role_cho.id}
    save_guild_data(interaction.guild_id, "verify_cfg.json", cfg)
    e = discord.Embed(title=title, description=description, color=hex_color)
    if gif_url: e.set_image(url=gif_url)
    await interaction.channel.send(embed=e, view=VerifyView())
    await interaction.response.send_message("✅ Đã tạo bảng xác minh với 2 Role thưởng!", ephemeral=True)

@verify_group.command(name="setting", description="⚙️ Xem cài đặt Role Xác Minh hiện tại")
async def verify_setting(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): 
        return await interaction.response.send_message("❌ Chỉ Owner mới dùng được lệnh này.", ephemeral=True)
    cfg = get_guild_data(interaction.guild_id, "verify_cfg.json", DEFAULT_VERIFY_SETTINGS)
    role1 = interaction.guild.get_role(cfg["role_chinh_1"])
    role2 = interaction.guild.get_role(cfg["role_chinh_2"])
    role_cho = interaction.guild.get_role(cfg["role_cho"])
    e = discord.Embed(title="⚙️ Cài đặt Xác Minh", color=0x5865F2)
    e.add_field(name="Role Chính 1", value=role1.mention if role1 else "❌ Chưa cài", inline=True)
    e.add_field(name="Role Chính 2", value=role2.mention if role2 else "❌ Chưa cài", inline=True)
    e.add_field(name="Role Chờ", value=role_cho.mention if role_cho else "❌ Chưa cài", inline=False)
    await interaction.response.send_message(embed=e, ephemeral=True)
tree.add_command(verify_group)

# ================== NOTICE ==================
@tree.command(name="notice", description="📢 Tạo thông báo (Owner)")
async def notice_cmd(interaction: discord.Interaction, message: str, ping: bool = True):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    content = f"@everyone\n> {message}" if ping else f"📢 **THÔNG BÁO**\n> {message}"
    await interaction.channel.send(content)
    await interaction.response.send_message("✅ Đã gửi.", ephemeral=True)

@tree.command(name="unnotice", description="🗑️ Gỡ thông báo (Owner)")
async def unnotice_cmd(interaction: discord.Interaction):
    if not is_owner(interaction.user.id): return await interaction.response.send_message("❌ Chỉ Owner.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    count = 0
    async for msg in interaction.channel.history(limit=50):
        if msg.author == bot.user and (msg.content.startswith("@everyone") or msg.content.startswith("📢 **")):
            try: await msg.delete(); count += 1
            except: pass
    await interaction.followup.send(f"✅ Đã gỡ {count} thông báo.", ephemeral=True)

# ================== BACKUP & RESTORE ==================
async def do_backup(guild):
    data = {"name": guild.name, "icon": None, "roles": [], "categories": [], "channels": [], "emojis": []}
    if guild.icon:
        try: data["icon"] = base64.b64encode(await guild.icon.read()).decode('utf-8')
        except: pass
    for r in guild.roles:
        if r.is_default() or r.managed: continue
        data["roles"].append({"name": r.name, "color": r.color.value, "hoist": r.hoist, "mentionable": r.mentionable, "permissions": r.permissions.value})
    for c in guild.channels:
        if isinstance(c, discord.CategoryChannel): data["categories"].append({"name": c.name, "position": c.position})
        overwrites = {}
        for target, overwrite in c.overwrites.items():
            target_name = f"role_{target.name}" if isinstance(target, discord.Role) else f"member_{target.id}"
            allow, deny = overwrite.pair()
            overwrites[target_name] = {"allow": allow.value, "deny": deny.value}
        data["channels"].append({"name": c.name, "type": str(c.type), "position": c.position, "topic": getattr(c, "topic", None), "nsfw": getattr(c, "nsfw", False), "slowmode": getattr(c, "slowmode_delay", 0), "category": c.category.name if c.category else None, "overwrites": overwrites})
    emoji_folder = os.path.join(EMOJI_DIR, str(guild.id)); os.makedirs(emoji_folder, exist_ok=True)
    for e in guild.emojis:
        try:
            path = os.path.join(emoji_folder, f"{e.name}.{'gif' if e.animated else 'png'}")
            if not os.path.exists(path): await e.save(path)
            data["emojis"].append({"name": e.name, "path": path, "animated": e.animated})
        except: pass
    BACKUPS[guild.id] = data
    with open(os.path.join(BACKUP_DIR, f"{guild.id}.json"), "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
    return data

FREE_FILE = os.path.join(DATA_DIR, "used_free.json")
if not os.path.exists(FREE_FILE): save_json(FREE_FILE, {"servers": []})

@tree.command(name="getfree", description="🎁 Nhận 1 lần Backup & Restore miễn phí")
async def getfree_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    used_data = load_json(FREE_FILE, {"servers": []})
    if interaction.guild_id in used_data["servers"]:
        return await interaction.followup.send("❌ Server này đã sử dụng lượt Miễn Phí rồi. Hãy nâng cấp VIP!", ephemeral=True)
    used_data["servers"].append(interaction.guild_id)
    save_json(FREE_FILE, used_data)
    data = await do_backup(interaction.guild)
    await interaction.followup.send(
        f"🎁 **ĐÃ KÍCH HOẠT GÓI MIỄN PHÍ!**\n"
        f"┣ `{len(data['roles'])}` Role\n"
        f"┣ `{len(data['channels'])}` Kênh\n"
        f"┗ `{len(data['emojis'])}` Emoji\n"
        f"*(Bạn có thể dùng lệnh /restore 1 lần duy nhất)*", ephemeral=True)

async def restore_server_from_backup(guild, data=None):
    if not data: data = BACKUPS.get(guild.id)
    if not data: return False
    async def safe_coro(coro, name):
        while True:
            try: return await coro
            except discord.HTTPException as e:
                if e.status == 429: await asyncio.sleep(e.retry_after)
                else: print(f"Lỗi tạo {name}: {e}"); return None
            except Exception as e: print(f"Lỗi {name}: {e}"); return None

    print(f"🔄 Đang khôi phục server {guild.name}...")
    edit_kwargs = {}
    if data.get("name"): edit_kwargs["name"] = data["name"]
    if data.get("icon"): 
        try: edit_kwargs["icon"] = base64.b64decode(data["icon"])
        except: pass
    if edit_kwargs:
        try: await guild.edit(**edit_kwargs)
        except: pass

    cats = {}
    for cd in data.get("categories", []):
        c = await safe_coro(guild.create_category(cd["name"]), cd["name"])
        if c: cats[c.name] = c

    roles = {}
    role_list = data.get("roles", [])
    for i in range(0, len(role_list), 5):
        tasks = []
        for rd in role_list[i:i+5]:
            coro = guild.create_role(name=rd["name"], color=discord.Color(rd["color"]), hoist=rd["hoist"], mentionable=rd["mentionable"], permissions=discord.Permissions(rd["permissions"]))
            tasks.append(safe_coro(coro, rd["name"]))
        res = await asyncio.gather(*tasks)
        for r in res:
            if r: roles[r.name] = r
        await asyncio.sleep(1)

    channel_list = data.get("channels", [])
    for i in range(0, len(channel_list), 5):
        tasks = []
        for cd in channel_list[i:i+5]:
            overwrites = {}
            for t_name, p in cd.get("overwrites", {}).items():
                if t_name.startswith("role_"):
                    r_name = t_name.replace("role_", "")
                    target = roles.get(r_name) or discord.utils.get(guild.roles, name=r_name)
                else:
                    target = guild.get_member(int(t_name.replace("member_", "")))
                if target: overwrites[target] = discord.PermissionOverwrite.from_pair(discord.Permissions(p["allow"]), discord.Permissions(p["deny"]))
            
            cat = cats.get(cd.get("category")) if cd.get("category") else None
            coro = None
            if "text" in cd["type"]: coro = guild.create_text_channel(cd["name"], topic=cd.get("topic") or "", nsfw=cd.get("nsfw", False), slowmode_delay=cd.get("slowmode", 0), category=cat, overwrites=overwrites)
            elif "voice" in cd["type"]: coro = guild.create_voice_channel(cd["name"], category=cat, overwrites=overwrites)
            if coro: tasks.append(safe_coro(coro, cd["name"]))
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)

    emoji_list = data.get("emojis", [])
    for i in range(0, len(emoji_list), 5):
        tasks = []
        for ed in emoji_list[i:i+5]:
            if os.path.exists(ed["path"]):
                try:
                    with open(ed["path"], "rb") as f: image_data = f.read()
                    coro = guild.create_custom_emoji(name=ed["name"], image=image_data)
                    tasks.append(safe_coro(coro, ed["name"]))
                except: pass
        if tasks: await asyncio.gather(*tasks)
        await asyncio.sleep(2)
    return True

@tree.command(name="backup", description="💾 Tạo Backup TOÀN BỘ Server [VIP]")
async def backup_cmd(interaction: discord.Interaction):
    if not is_vip(interaction.guild_id, interaction.user.id): return await interaction.response.send_message("❌ Chỉ VIP/Owner.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data = await do_backup(interaction.guild)
    await interaction.followup.send(f"✅ **BACKUP XONG**\n┣ `{len(data['roles'])}` Role\n┣ `{len(data['channels'])}` Kênh\n┗ `{len(data['emojis'])}` Emoji", ephemeral=True)

@tree.command(name="restore", description="♻️ Khôi phục Server (Miễn phí)")
async def restore_cmd(interaction: discord.Interaction):
    data = BACKUPS.get(interaction.guild.id)
    if not data and not os.path.exists(os.path.join(BACKUP_DIR, f"{interaction.guild.id}.json")):
        return await interaction.response.send_message("❌ Không có Backup.", ephemeral=True)
    if not data:
        with open(os.path.join(BACKUP_DIR, f"{interaction.guild.id}.json"), encoding="utf-8") as f: data = json.load(f)

    await interaction.response.defer(ephemeral=True)
    g_data = get_guild_data(interaction.guild_id, "guard.json", DEFAULT_GUARD)
    g_data["anti_nuke"] = False
    save_guild_data(interaction.guild_id, "guard.json", g_data)
    
    for ch in interaction.guild.channels:
        if ch.name != LOG_CHANNEL_NAME:
            try: await ch.delete()
            except: pass
    for r in interaction.guild.roles:
        if not r.is_default() and not r.managed and r < interaction.guild.me.top_role:
            try: await r.delete()
            except: pass
    for e in interaction.guild.emojis:
        try: await e.delete()
        except: pass
        
    est_secs = (len(data["roles"]) // 5) + (len(data["channels"]) // 5) + (len(data["emojis"]) // 5 * 2)
    await interaction.followup.send(f"🔄 **Dự kiến thời gian hồi sinh:** `{est_secs} giây`...", ephemeral=True)

    await restore_server_from_backup(interaction.guild, data)
    await asyncio.sleep(2)
    
    g_data["anti_nuke"] = True
    save_guild_data(interaction.guild_id, "guard.json", g_data)

    await interaction.followup.send("✅ **ĐÃ KHÔI PHỤC XONG!**", ephemeral=True)

# ================== BẢNG GUARD ==================
GUARD_INFO = {
    "anti_nuke": ("🛡️", "Anti-Nuke"), "anti_raid": ("⚔️", "Anti-Raid"),
    "anti_invite": ("🔗", "Anti-Invite"), "anti_webhook": ("🌐", "Anti-Webhook"),
    "anti_image": ("🖼️", "Anti-Image"), "anti_video": ("🎥", "Anti-Video"),
    "anti_link": ("🔗", "Anti-Link"), "anti_scam": ("🚨", "Anti-Scam"),
    "anti_spam": ("💬", "Anti-Spam"), "anti_bot_raid": ("🤖", "Anti-Bot"),
    "anti_gif": ("🎞️", "Anti-GIF"), "anti_emoji": ("😀", "Anti-Emoji"),
    "anti_cap": ("🔠", "Anti-Caps"), "anti_sex": ("🔞", "Anti-Sex"),
    "anti_sex_media": ("🔞", "Anti-Sex Media"), "anti_sex_emote": ("😈", "Anti-Sex Emote")
}

class GuardView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.build_ui()

    def build_ui(self):
        self.clear_items()
        guard_data = get_guild_data(self.guild_id, "guard.json", DEFAULT_GUARD)
        settings_data = get_guild_data(self.guild_id, "settings.json", DEFAULT_SETTINGS)
        
        for i, key in enumerate(GUARD_INFO.keys()):
            icon, name = GUARD_INFO[key]
            is_on = guard_data.get(key, False)
            btn = discord.ui.Button(
                label=name, emoji=icon, 
                style=discord.ButtonStyle.green if is_on else discord.ButtonStyle.red, 
                custom_id=f"toggle_{key}", row=i // 4
            )
            btn.callback = self.make_callback(key)
            self.add_item(btn)

        cap_btn = discord.ui.Button(
            label=f"Ngưỡng Chữ Hoa: {settings_data['cap_threshold']}", emoji="⚙️", 
            style=discord.ButtonStyle.blurple, custom_id="cap_set", row=4 
        )
        cap_btn.callback = self.cap_callback
        self.add_item(cap_btn)

    def make_callback(self, key):
        async def callback(interaction: discord.Interaction):
            guard_data = get_guild_data(self.guild_id, "guard.json", DEFAULT_GUARD)
            guard_data[key] = not guard_data.get(key, False)
            save_guild_data(self.guild_id, "guard.json", guard_data)
            self.build_ui()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        return callback

    async def cap_callback(self, interaction: discord.Interaction):
        settings_data = get_guild_data(self.guild_id, "settings.json", DEFAULT_SETTINGS)
        order = ["10-20", "30-40", "50-100"]
        cur = settings_data["cap_threshold"]
        settings_data["cap_threshold"] = order[(order.index(cur) + 1) % len(order)]
        save_guild_data(self.guild_id, "settings.json", settings_data)
        self.build_ui()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def create_embed(self):
        guard_data = get_guild_data(self.guild_id, "guard.json", DEFAULT_GUARD)
        e = discord.Embed(
            title="⚡ HỆ THỐNG PHÒNG THỦ TRUNG TÂM ⚡",
            description="Dưới đây là danh sách các module bảo vệ. Bấm vào nút tương ứng để **Bật / Tắt**.\n\u200b",
            color=0x2ecc71 if any(guard_data.values()) else 0xFF0000
        )
        
        col1, col2 = [], []
        for key, (icon, name) in GUARD_INFO.items():
            is_on = guard_data.get(key, False)
            status = "🟢" if is_on else "🔴"
            col1.append(f"{icon} **{name}**")
            col2.append(status)
            
        table = ""
        for i in range(len(col1)):
            table += f"{col1[i]:<18} | {col2[i]}\n"
            
        # Chia thành 2 field để tránh vượt quá 1024 ký tự
        half = len(table) // 2
        e.add_field(name="📋 DANH SÁCH MODULE (1/2)", value=f"```ini\n{table[:half]}\n```", inline=False)
        e.add_field(name="📋 DANH SÁCH MODULE (2/2)", value=f"```ini\n{table[half:]}\n```", inline=False)
        
        e.set_footer(text="Hệ thống bảo mật tự động | Yêu cầu quyền Admin")
        e.timestamp = discord.utils.utcnow()
        return e

@tree.command(name="guard", description="🛡️ Bảng điều khiển hệ thống phòng thủ")
async def guard_cmd(interaction: discord.Interaction):
    if not is_admin(interaction.user): 
        return await interaction.response.send_message("❌ Bạn không có quyền truy cập hệ thống.", ephemeral=True)
    
    # Đã thêm defer để tránh lỗi "Ứng dụng không phản hồi"
    await interaction.response.defer(ephemeral=True)
    
    v = GuardView(interaction.guild_id)
    # Dùng followup.send
    await interaction.followup.send(embed=v.create_embed(), view=v)

# ================== HỆ THỐNG ANTI ==================
@bot.event
async def on_webhooks_update(channel: discord.TextChannel):
    if not get_guild_data(channel.guild.id, "guard.json", DEFAULT_GUARD)["anti_webhook"]: return
    try:
        for wh in await channel.webhooks():
            if wh.user and wh.user.id == bot.user.id: continue
            await wh.delete(reason="Anti-Webhook")
            await dm_report(channel.guild, channel.guild.me, f"Đã xóa Webhook lạ tại {channel.mention}")
    except: pass

async def xoa_kenh_role(guild, target_id, action_type, target_name):
    guard_data = get_guild_data(guild.id, "guard.json", DEFAULT_GUARD)
    if not guard_data.get("anti_nuke", True): return
    try:
        async for entry in guild.audit_logs(limit=3, action=action_type):
            if entry.target and entry.target.id == target_id:
                actor = entry.user
                if not actor or is_whitelisted(guild.id, actor.id) or actor.id == guild.owner_id: break
                member = guild.get_member(actor.id)
                if member:
                    try:
                        for ch in guild.text_channels:
                            async for msg in ch.history(limit=20):
                                if msg.author.id == actor.id: await msg.delete()
                    except: pass
                    
                    ban_success = False
                    try:
                        if member.guild_permissions.administrator: await member.edit(roles=[r for r in member.roles if not r.permissions.administrator])
                        await member.ban(reason=f"Anti-Nuke: Phá hoại ({target_name})")
                        ban_success = True
                    except Exception as e: print(f"❌ LỖI BAN: {e}") 
                        
                    if ban_success:
                        try:
                            owner = await bot.fetch_user(OWNER_ID)
                            if owner: await owner.send(f"🚨 **BÁO CÁO**: {member.mention} vừa bị BAN vì xóa `{target_name}` tại **{guild.name}**")
                        except: pass
                        
                        await send_punish_gif(guild, "Ban (Anti-Nuke)", member, f"Phá hoại: {target_name}")
                        await restore_server_from_backup(guild)
                break
    except: pass

@bot.event
async def on_guild_channel_delete(channel):
    if channel.name == LOG_CHANNEL_NAME: await ensure_log_channel(channel.guild, force=True)
    await xoa_kenh_role(channel.guild, channel.id, discord.AuditLogAction.channel_delete, f"Kênh #{channel.name}")

@bot.event
async def on_guild_role_delete(role):
    await xoa_kenh_role(role.guild, role.id, discord.AuditLogAction.role_delete, f"Role {role.name}")

@tasks.loop(seconds=0.5)
async def anti_nuke_scanner():
    for g in bot.guilds:
        guard_data = get_guild_data(g.id, "guard.json", DEFAULT_GUARD)
        if not guard_data.get("anti_nuke", True): continue
        try:
            async for entry in g.audit_logs(limit=5):
                if entry.action in [discord.AuditLogAction.channel_create, discord.AuditLogAction.role_create, discord.AuditLogAction.emoji_create, discord.AuditLogAction.emoji_delete, discord.AuditLogAction.guild_update]:
                    actor = entry.user
                    if not actor or is_whitelisted(g.id, actor.id) or actor.id == g.owner_id: continue
                    now = time.time(); key = (g.id, actor.id)
                    NUKE_CACHE[key].append(now); NUKE_CACHE[key] = [t for t in NUKE_CACHE[key] if now - t < 3.0]
                    
                    if len(NUKE_CACHE[key]) >= 2:
                        member = g.get_member(actor.id)
                        if member:
                            try:
                                if member.guild_permissions.administrator: await member.edit(roles=[r for r in member.roles if not r.permissions.administrator])
                                await member.ban(reason="Anti-Nuke: Phá hoại hàng loạt!")
                                await send_punish_gif(g, "Ban (Anti-Nuke)", member, "Tạo/xóa hàng loạt")
                            except Exception as e: print(f"❌ Lỗi ban: {e}")
                        NUKE_CACHE[key].clear()
        except: pass

@bot.event
async def on_message(message: discord.Message):
    if not message.guild: return
    if message.channel.name == LOG_CHANNEL_NAME: return 
    if message.author.id == bot.user.id: return 
    
    guard_data = get_guild_data(message.guild.id, "guard.json", DEFAULT_GUARD)
    
    if message.author.bot and is_whitelisted(message.guild.id, message.author.id): return
    if not message.author.bot and (is_admin(message.author) or is_whitelisted(message.guild.id, message.author.id)): return
    
    if message.webhook_id and guard_data.get("anti_webhook", True):
        try: await message.delete()
        except: pass
        return

    g, a, content = message.guild, message.author, message.content or ""
    
    if guard_data.get("anti_sex", True):
        if any(w in content.lower() for w in SEX_WORDS):
            try: await message.delete()
            except: pass
            await dm_report(g, a, "Nội dung nhạy cảm (18+)")
            return

    if message.attachments and guard_data.get("anti_sex_media", True):
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm')):
                is_nsfw = await check_nsfw_image(att.url)
                if is_nsfw:
                    try: await message.delete()
                    except: pass
                    await dm_report(g, a, "Gửi phương tiện nhạy cảm (18+)")
                    return

    is_heavy = False
    heavy_reason = ""
    if message.attachments:
        for att in message.attachments:
            if guard_data.get("anti_gif", True) and att.filename.lower().endswith('.gif'): is_heavy, heavy_reason = True, "Gửi GIF"; break
            elif guard_data.get("anti_video", True) and att.filename.lower().endswith(('.mp4', '.mov', '.webm')): is_heavy, heavy_reason = True, "Gửi Video"; break
            elif guard_data.get("anti_image", True) and att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): is_heavy, heavy_reason = True, "Gửi Ảnh"; break

    if not is_heavy:
        if guard_data.get("anti_invite", True) and INVITE_RE.search(content): is_heavy, heavy_reason = True, "Invite Discord"
        elif guard_data.get("anti_link", True) and LINK_RE.search(content): is_heavy, heavy_reason = True, "Gửi link"
        elif guard_data.get("anti_scam", True) and any(w in content.lower() for w in SCAM_WORDS): is_heavy, heavy_reason = True, "Nội dung Scam"

    if is_heavy:
        try: await message.delete()
        except: pass
        try:
            if not a.bot:
                await a.kick(reason=f"Vi phạm nghiêm trọng: {heavy_reason}")
                await send_punish_gif(g, "Kick", a, f"Vi phạm: {heavy_reason}")
            else:
                await a.kick(reason=f"Bot vi phạm: {heavy_reason}")
                await send_punish_gif(g, "Kick Bot", a, f"Vi phạm: {heavy_reason}")
        except: pass
        return

    if guard_data.get("anti_spam", True):
        key = (g.id, a.id); now = time.time()
        MESSAGE_CACHE[key].append(now)
        MESSAGE_CACHE[key] = [t for t in MESSAGE_CACHE[key] if now - t < 3.0]
        
        if len(MESSAGE_CACHE[key]) >= 8:
            try: await message.delete()
            except: pass
            
            spam_key = f"spam_{g.id}_{a.id}"
            SPAM_WARN_CACHE[spam_key] += 1
            count = SPAM_WARN_CACHE[spam_key]

            if count == 1:
                await dm_report(g, a, "Spam tin nhắn (Cảnh cáo 1/2)")
            elif count >= 2:
                if not a.bot:
                    try: 
                        await a.timeout(discord.utils.utcnow() + discord.timedelta(seconds=300), reason="Spam liên tục")
                        await send_punish_gif(g, "Mute", a, "Spam tin nhắn liên tục")
                    except: pass
            MESSAGE_CACHE[key].clear()
            return
            
    await bot.process_commands(message)

@bot.event
async def on_member_join(member: discord.Member):
    g = member.guild
    guard_data = get_guild_data(g.id, "guard.json", DEFAULT_GUARD)
    cfg = get_guild_data(g.id, "verify_cfg.json", DEFAULT_VERIFY_SETTINGS)
    
    if cfg["role_cho"] != 0:
        role_cho = g.get_role(cfg["role_cho"])
        if role_cho:
            try: await member.add_roles(role_cho, reason="Auto Role: Chưa xác minh")
            except: pass

    if guard_data.get("anti_bot_raid", True) and member.bot and not is_whitelisted(g.id, member.id):
        await download_gif()
        try:
            e_dm = discord.Embed(
                title="🤖 LIỄU NHUYÊN - VUA BẢO VỆ SERVER",
                description="Ta là **Liễu Vô Song**, kẻ thống trị bóng tối, người bảo vệ server của ngươi!\n\n"
                            "Hệ thống phát hiện ngươi là Bot lạ chưa được cấp phép. **Ngươi sẽ bị trục xuất khỏi server này ngay lập tức!**\n\n"
                            "Nếu muốn mời ta vào server của ngươi, hãy bấm nút bên dưới.",
                color=0x9b59b6
            )
            if os.path.exists(GIF_PATH): e_dm.set_image(url="attachment://nuke_gif.gif")
            if os.path.exists(GIF_PATH): await member.send(embed=e_dm, view=InviteView(), file=discord.File(GIF_PATH))
            else: await member.send(embed=e_dm, view=InviteView())
        except: pass

        try: await member.kick(reason="Anti-Bot Tuyệt Đối: Bot lạ chưa được whitelist")
        except: pass
        return
        
    if guard_data.get("anti_raid", True):
        JOIN_CACHE[g.id].append(time.time()); JOIN_CACHE[g.id] = [t for t in JOIN_CACHE[g.id] if time.time() - t < 5]
        if len(JOIN_CACHE[g.id]) >= 5:
            try:
                await g.default_role.edit(permissions=discord.Permissions(send_messages=False), reason="Anti-Raid Lockdown")
                await dm_report(g, g.me, "🚨 RAID DETECTED: Khóa chat 10 phút!")
                await asyncio.sleep(600)
                await g.default_role.edit(permissions=discord.Permissions(send_messages=True), reason="Hết hạn Lockdown")
            except: pass

# ================== READY ==================
@bot.event
async def on_ready():
    print(f"✅ Đã đăng nhập: {bot.user} | Owner: {OWNER_ID}")
    
    # Chạy các tác vụ nền
    if not anti_nuke_scanner.is_running(): anti_nuke_scanner.start()
    if not check_vip_expired.is_running(): check_vip_expired.start()
    
    # Tạo kênh log cho tất cả server (có thể bỏ qua nếu muốn nhẹ hơn)
    for g in bot.guilds:
        try:
            await ensure_log_channel(g)
        except:
            pass

    # Đồng bộ slash command trong background, có xử lý lỗi 429
    async def sync_commands():
        try:
            await tree.sync()
            print("✅ Đã đồng bộ lệnh Slash thành công!")
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = e.response.headers.get('Retry-After', 60)
                print(f"⚠️ Bị rate limit khi sync lệnh, chờ {retry_after} giây...")
                await asyncio.sleep(float(retry_after) + 5)
                try:
                    await tree.sync()
                    print("✅ Đã đồng bộ lệnh Slash thành công sau khi chờ!")
                except Exception as e2:
                    print(f"❌ Vẫn không thể sync lệnh: {e2}")
            else:
                print(f"❌ Lỗi khi sync lệnh: {e}")

    # Chạy sync trong background để không block on_ready
    asyncio.create_task(sync_commands())
