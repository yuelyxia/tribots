#  yuelyxia  ©  2025 – 2026

# standard libraries
import asyncio
import inspect
import datetime
import io
import os
import re
import time
import uuid
import json
import html
import base64
from asyncio import Lock
from collections import defaultdict
from typing import Literal, Optional
from zoneinfo import ZoneInfo, available_timezones

# 3rd party libraries
import aiohttp
import discord
import pymongo
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
from gtts import gTTS
from pymongo import UpdateOne

# local imports


# environment
load_dotenv()

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb
client = pymongo.MongoClient(CLIENT)
kafu = client["kafu"]
db = client["database"]
trusteduserscol = db["trusted_users"]
staffweeklycol = db["staff_weekly"]

servers = kafu["servers"]
timezones = kafu["timezones"]
vouch_servers = kafu["vouch_servers"]
voices = kafu["voices"]
votes = kafu["votes"]
ticket_claims = kafu["ticket_claims"]
afk = kafu["afk"]

tickets = kafu["tickets"]
transcripts = kafu["transcripts"]
counters = kafu["counters"]

# ids

TRI_Archive = 1371673839695826974
Tethys = 1434471275723493388
ticket_ping = 1449382692671193294
sr_ping = 1375254710952661102
adm_ping = 1375276457890287748
KAFU = 1457009979817988241
MIKU = 1457309787044839477

yuelyxia = 1303291812282372137

USERGUIDE = "https://docs.google.com/document/d/1Af_bHhXTjpJ9GkIPihmSQYibDVMYTFnUBhaA7DlQ29s/"
JSON_CHANNEL = 1520096583595724982
ATTACHMENT_CHANNEL = 1520096619012292659
TRANSCRIPT_CHANNEL = 1375269831934476318

TIMEZONES = sorted(available_timezones())

def is_sr(user):
    return any(role.id in (sr_ping, adm_ping) for role in user.roles)

# bot setup
intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=",",
    help_command=None,
    intents=intents
)

# on ready
@bot.event
async def on_ready():
    bot.add_view(TRITicketView())
    bot.add_view(BanReqView())
    bot.add_view(PilotView())
    bot.add_view(PilotFormsView())
    bot.add_view(MMView())
    bot.add_view(MMFormsView())
    bot.add_view(MMRisksView())
    bot.add_view(TranscriptView(ticket_data={}))
    bot.add_view(TranscriptDMView(ticket_data={}))
    if not hasattr(bot, "ticket_manager"):
        bot.ticket_manager = TicketManager(
            bot,
            tickets,
            transcripts,
            JSON_CHANNEL,
            ATTACHMENT_CHANNEL,
            counters
        )
    await bot.add_cog(Logger(bot))
    quota_check.start()
    customrole_expiry_loop.start()
    vote_auto_close_loop.start()
    vote_cleanup_loop.start()
    ticket_claim_cleanup_loop.start()
    if not hasattr(bot, "queue_started"):
        bot.loop.create_task(message_update_worker())
        bot.queue_started = True

    await bot.tree.sync()

guild_locks = {}
def get_lock(guild_id):
    if guild_id not in guild_locks:
        guild_locks[guild_id] = Lock()
    return guild_locks[guild_id]

def parse_duration(s: str):
    matches = re.findall(r"(\d+)([smhd])", s.lower())
    if not matches:
        return None
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }
    total = 0
    for value, unit in matches:
        total += int(value) * multipliers[unit]
    return total

@bot.tree.command(name="help", description="KAFU user guide.")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(f"KAFU user guide [here]({USERGUIDE})")

# voice
voice_clients = {}
active_text_channel = {}
tts_queues = defaultdict(asyncio.Queue)
tts_workers = {}

async def tts_worker(guild_id: int):
    try:
        while True:
            vc = voice_clients.get(guild_id)
            if not vc or not vc.is_connected():
                await asyncio.sleep(1)
                continue
            try:
                text, lang = await asyncio.wait_for(
                    tts_queues[guild_id].get(),
                    timeout=15
                )
            except asyncio.TimeoutError:
                continue
            try:
                await play_tts(vc, text, lang)
            except Exception as e:
                print(f"TTS playback error: {e}")
    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"TTS worker fatal error: {e}")

async def play_tts(vc: discord.VoiceClient, text: str, lang: str = "en"):
    filename = f"tts_{uuid.uuid4().hex}.mp3"
    tts = gTTS(text=text, lang=lang)
    tts.save(filename)
    source = discord.FFmpegPCMAudio(filename)
    vc.play(source)
    while vc.is_playing():
        await asyncio.sleep(0.5)
    try:
        os.remove(filename)
    except:
        pass

ACCENTS = [
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Polish", "pl"),
    ("Russian", "ru"),
    ("Swedish", "sv"),
    ("Danish", "da"),
    ("Norwegian", "no"),
    ("Finnish", "fi"),
    ("Greek", "el"),
    ("Turkish", "tr"),
    ("Czech", "cs"),
    ("Slovak", "sk"),
    ("Romanian", "ro"),
    ("Hungarian", "hu"),
    ("Ukrainian", "uk"),

    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Chinese", "zh"),
    ("Hindi", "hi"),
    ("Thai", "th"),
    ("Vietnamese", "vi"),
    ("Indonesian", "id"),
    ("Malay", "ms"),
    ("Bengali", "bn"),
    ("Tamil", "ta"),
    ("Telugu", "te"),
    ("Malayalam", "ml"),
    ("Marathi", "mr"),
    ("Urdu", "ur"),

    ("Arabic", "ar"),
    ("Persian", "fa"),
    ("Hebrew", "he"),
    ("Swahili", "sw"),
    ("Afrikaans", "af"),

    ("Catalan", "ca"),
    ("Croatian", "hr"),
    ("Slovenian", "sl"),
    ("Lithuanian", "lt"),
    ("Latvian", "lv"),
    ("Estonian", "et"),
    ("Filipino", "tl"),
]

def set_accent(user_id: int, accent: str):
    voices.update_one(
        {"_id": str(user_id)},
        {"$set": {"accent": accent}},
        upsert=True
    )
def get_accent(user_id: int):
    data = voices.find_one({"_id": str(user_id)})
    if data:
        return data.get("accent", "en")
    return "en"
async def accent_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    results = []
    for label, value in ACCENTS:
        if current in label.lower() or current in value.lower():
            results.append(
                app_commands.Choice(name=label, value=value)
            )
    return results[:25]
def replace_mentions(message: discord.Message):
    text = message.content
    for user in message.mentions:
        text = re.sub(
            rf"<@!?{user.id}>",
            user.display_name,
            text
        )
    for role in message.role_mentions:
        text = re.sub(
            rf"<@&{role.id}>",
            role.name,
            text
        )
    for channel in message.channel_mentions:
        text = text.replace(
            f"<#{channel.id}>",
            channel.name
        )
    def emoji_replacer(match):
        emoji_name = match.group(1)
        return emoji_name.replace("_", " ")
    text = re.sub(r"<a?:([a-zA-Z0-9_]+):\d+>", emoji_replacer, text)
    text = text.replace("@everyone", "everyone")
    text = text.replace("@here", "here")
    text = re.sub(r"https?://\S+|www\.\S+", "link", text)
    return text

@bot.tree.command(name="accent", description="Set your TTS accent.")
@app_commands.autocomplete(accent=accent_autocomplete)
async def accent(interaction: discord.Interaction, accent: str):
    set_accent(interaction.user.id, accent)
    label = next((l for l, v in ACCENTS if v == accent), accent)
    await interaction.response.send_message(
        f"Accent set to **{label}** (`{accent}`)",
        ephemeral=True
    )

@bot.tree.command(name="join", description="KAFU joins the voice channel.")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("You're not in a voice channel.", ephemeral=True)
    channel = interaction.user.voice.channel
    guild_id = interaction.guild.id
    existing_vc = voice_clients.get(guild_id)
    if existing_vc and existing_vc.is_connected():
        active_text_channel[guild_id] = channel.id
        if existing_vc.channel.id == channel.id:
            return await interaction.response.send_message(f"Already connected to {channel.mention}.", ephemeral=True)
        await existing_vc.move_to(channel)
        return await interaction.response.send_message(f"Moved to {channel.mention}.")
    vc = await channel.connect()
    voice_clients[guild_id] = vc
    active_text_channel[guild_id] = channel.id
    tts_queues[guild_id] = asyncio.Queue()
    if guild_id not in tts_workers or tts_workers[guild_id].done():
        tts_workers[guild_id] = asyncio.create_task(tts_worker(guild_id))
    await interaction.response.send_message(f"Joined {channel.mention} and linked to its text channel.")

async def cleanup_guild(guild_id: int):
    vc = voice_clients.pop(guild_id, None)
    if vc:
        await vc.disconnect()
    active_text_channel.pop(guild_id, None)
    worker = tts_workers.pop(guild_id, None)
    if worker:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
    if guild_id in tts_queues:
        tts_queues[guild_id] = asyncio.Queue()

@bot.tree.command(name="leave", description="KAFU leaves the voice channel.")
async def leave(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    await cleanup_guild(guild_id)
    await interaction.response.send_message("Disconnected.")


# loop tasks

QUOTA_CHECK_DAY = 1

@tasks.loop(time=datetime.time(hour=0, minute=0))
async def quota_check():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.day == QUOTA_CHECK_DAY:
        guilds = servers.find({})  # all servers
        for server_info in guilds:
            guild_id = int(server_info["_id"])
            if guild_id == TRI_Archive:
                continue
            try:
                guild = await bot.fetch_guild(guild_id)
            except discord.NotFound:
                continue  # bot is not in this guild anymore
            except discord.Forbidden:
                continue  # no access
            else:
                staff_lb_channel = server_info.get("staff_lb_channel")
                if staff_lb_channel:
                    try:
                        channel = await guild.fetch_channel(int(staff_lb_channel.replace("<#", "").replace(">", "")))
                        total_moderations = 0
                        total_tickets = 0
                        staff = server_info.get("staff", {})
                        sorted_staff = sorted(
                            staff.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_staff, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_moderations += monthly
                        staff_embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
                        sorted_tickets = sorted(
                            staff.items(),
                            key=lambda x: x[1].get("monthly_tickets", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_tickets, start=1):
                            monthly_tickets = data.get("monthly_tickets", 0)
                            tickets = data.get("tickets", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{tickets}** all ㆍ **{monthly_tickets}** month\n"
                            total_tickets += monthly_tickets
                        tickets_embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
                        summary = discord.Embed(colour=0xffffff)
                        summary.description = (
                                f"✦　　┈　　total moderations　　┈　　**{total_moderations}**\n✦　　┈　　total tickets　　┈　　**{total_tickets}**")
                        await channel.send("## _ _　　　staff leaderboard", embed=staff_embed)
                        await channel.send("## _ _　　　tickets leaderboard", embed=tickets_embed)
                        await channel.send("## _ _　　　monthly summary", embed=summary)
                    except discord.NotFound: pass
                    except discord.Forbidden: pass
                services_lb_channel = server_info.get("services_lb_channel")
                if services_lb_channel:
                    try:
                        channel = await guild.fetch_channel(int(services_lb_channel.replace("<#", "").replace(">", "")))
                        total_mm_vouches = 0
                        total_pilot_services = 0
                        mms = server_info.get("mms", {})
                        sorted_mms = sorted(
                            mms.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_mms, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_mm_vouches += monthly
                        mms_embed = discord.Embed(description=desc if desc else "No mms found.", colour = 0xffffff)
                        pilots = server_info.get("pilots", {})
                        sorted_pilots = sorted(
                            pilots.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_pilots, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_pilot_services += monthly
                        pilots_embed = discord.Embed(description=desc if desc else "No pilots found.", colour = 0xffffff)
                        summary = discord.Embed(colour=0xffffff)
                        total_mm_services = total_mm_vouches // 2
                        total_services = total_pilot_services + total_mm_services
                        summary.description = (
                            f"✦　　┈　　total services　　┈　　**{total_services}**\n✦　　┈　　total mm services　　┈　　**{total_mm_services}** ({total_mm_vouches} mmv)\n✦　　┈　　total pilot services　　┈　　**{total_pilot_services}**")
                        await channel.send("## _ _　　　mm leaderboard", embed=mms_embed)
                        await channel.send("## _ _　　　pilot leaderboard", embed=pilots_embed)
                        await channel.send("## _ _　　　monthly summary", embed=summary)
                    except discord.NotFound: pass
                    except discord.Forbidden: pass
                for category in ["staff", "mms", "pilots"]:
                    if category in server_info and isinstance(server_info[category], dict):
                        for user_id in server_info[category]:
                            if "monthly" in server_info[category][user_id]:
                                server_info[category][user_id]["monthly"] = 0
                            if "monthly_tickets" in server_info[category][user_id]:
                                server_info[category][user_id]["monthly_tickets"] = 0
                servers.replace_one({"_id": server_info["_id"]}, server_info)


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    intervals = (
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    )
    result = []
    for suffix, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value > 1:
                result.append(f"{value} {suffix}s")
            else:
                result.append(f"{value} {suffix}")
    return " ".join(result)

@bot.event
async def on_message(message: discord.Message):
    if message.author.id == bot.user.id:
        return

    data = afk.find_one({"_id": message.author.id})
    if data:
        duration = int(time.time()) - data["since"]
        duration = format_duration(duration)
        mentions = data.get("mentions", [])
        lines = []
        for i, mention in enumerate(mentions[:20], start=1):
            lines.append(f"-# {i}ㆍ　<@{mention["user_id"]}>　–　{mention["jump_url"]}")

        embed = discord.Embed(
            colour=0xffffff,
            title="Welcome back!",
            description=
            f"You were afk for {duration}.\n\n"
            f"You received **{len(mentions)}** mention(s).\n"
        )
        if lines:
            embed.description +="\n".join(lines)
        await message.reply(embed=embed)
        afk.delete_one({"_id": message.author.id})

    for member in message.mentions:
        if member.id == message.author.id:
            continue
        data = afk.find_one({"_id": member.id})
        if not data:
            continue
        afk.update_one({"_id": member.id}, {"$push": {"mentions": {"user_id": message.author.id, "jump_url": message.jump_url}}})
        embed = discord.Embed(colour=0xffffff, description=f"**{member.display_name}** has been afk since <t:{data["since"]}:R>\nReason: **{data["reason"]}**")
        await message.reply(embed=embed)

    guild_id = message.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if server_info:
        mm_vouch_channel = server_info.get("mm_vouch_channel")
        if mm_vouch_channel:
            if message.channel.id == int(mm_vouch_channel.replace("<#", "").replace(">", "")):
                if message.mentions:
                    first_user = message.mentions[0]
                    user_id = str(first_user.id)
                    if user_id in server_info.get("mms", {}):
                        server_info["mms"][user_id]["monthly"] = (server_info["mms"][user_id].get("monthly", 0) + 1)
                        server_info["mms"][user_id]["alltime"] = (server_info["mms"][user_id].get("alltime", 0) + 1)
                        servers.replace_one(server_query, server_info)
                        await message.add_reaction("<:whitetick:1462774288020013161>")
                    else:
                        await message.add_reaction("<:whitecross:1462774085737119828>")
        pilot_vouch_channel = server_info.get("pilot_vouch_channel")
        if pilot_vouch_channel:
            if message.channel.id == int(pilot_vouch_channel.replace("<#", "").replace(">", "")):
                if message.mentions:
                    first_user = message.mentions[0]
                    user_id = str(first_user.id)
                    if user_id in server_info.get("pilots", {}):
                        server_info["pilots"][user_id]["monthly"] = (
                                    server_info["pilots"][user_id].get("monthly", 0) + 1)
                        server_info["pilots"][user_id]["alltime"] = (
                                    server_info["pilots"][user_id].get("alltime", 0) + 1)
                        servers.replace_one(server_query, server_info)
                        await message.add_reaction("<:whitetick:1462774288020013161>")
                    else:
                        await message.add_reaction("<:whitecross:1462774085737119828>")

    if guild_id in voice_clients:
        if active_text_channel.get(guild_id) == message.channel.id:
            vc = voice_clients.get(guild_id)
            if vc:
                text = replace_mentions(message).strip()
                if text:
                    accent = get_accent(message.author.id)
                    await tts_queues[guild_id].put((
                        f"{message.author.display_name} says {text}",
                        accent))

    await bot.process_commands(message)

@bot.event
async def on_member_remove(member):
    server = servers.find_one({"_id": str(member.guild.id)})
    if server:
        roles = server.get("custom_roles", {})
        async with get_lock(member.guild.id):
            for role_id, data in list(roles.items()):
                if data["owner"] == str(member.id):
                    role = member.guild.get_role(int(role_id))
                    if role:
                        await role.delete()
                    servers.update_one(
                        {"_id": member.guild.id},
                        {"$unset": {f"custom_roles.{role_id}": ""}}
                )

# text commands

@bot.command(name="afk")
async def afk_command(ctx, *, reason="none"):
    embed = discord.Embed(colour=0xffffff, description=f"You are now afk with reason: **{reason}**")
    await ctx.reply(embed=embed)
    afk.update_one({"_id": ctx.author.id}, {"$set": {"reason": reason, "since": int(time.time()), "mentions": []}},
                   upsert=True)

@bot.command(name="pilot")
async def pilot(ctx, *, desc:str=None):
    if not desc:
        await ctx.send(view=PilotView())
    if desc == "forms":
        await ctx.send("> By filling any of the forms below, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.", view=PilotFormsView())

class PilotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="forms", style=discord.ButtonStyle.grey, custom_id="pilot:forms")
    async def forms_button(self, interaction, button):
        await interaction.response.send_message(view=PilotFormsView())

class PilotFormsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="genshin", style=discord.ButtonStyle.grey, custom_id="pilot_forms:genshin")
    async def genshin_button(self, interaction, button):
        await interaction.response.send_message("""
### Genshin Impact Pilot Form
Account Size: 
Server: 
Task: 
Time Limit: 
Fee: 
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="hsr", style=discord.ButtonStyle.grey, custom_id="pilot_forms:hsr")
    async def hsr_button(self, interaction, button):
        await interaction.response.send_message("""
### Honkai: Star Rail Pilot Form
Account Size: 
Server: 
Task: 
Time Limit: 
Fee: 
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="wuwa", style=discord.ButtonStyle.grey, custom_id="pilot_forms:wuwa")
    async def wuwa_button(self, interaction, button):
        await interaction.response.send_message("""
### Wuthering Waves Pilot Form
Account Size: 
Server: 
Task: 
Time Limit: 
Fee: 
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="roblox", style=discord.ButtonStyle.grey, custom_id="pilot_forms:roblox")
    async def roblox_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox Pilot Form
Roblox Game: 
Task: 
Time Limit: 
Fee: 
Do’s & Don’ts: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")


@bot.command(name="mm")
async def mm(ctx, *, desc: str=None):
    if not desc:
        await ctx.send(view=MMView())
    if desc == "forms":
        await ctx.send("> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.", view=MMFormsView())
    if desc == "risks":
        await ctx.send(view=MMRisksView())

class MMView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="forms", style=discord.ButtonStyle.grey, custom_id="mm:forms")
    async def forms_button(self, interaction, button):
        await interaction.response.send_message(view=MMFormsView())
    @discord.ui.button(label="risks", style=discord.ButtonStyle.grey, custom_id="mm:risks")
    async def risks_button(self, interaction, button):
        await interaction.response.send_message(view=MMRisksView())

class MMFormsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="genshin", style=discord.ButtonStyle.grey, custom_id="mm_forms:genshin")
    async def genshin_button(self, interaction, button):
        await interaction.response.send_message("""
### Genshin Impact MM Form
Account Size: 
Adventure Rank: 
Server: 
5 star characters, constellations & weapons: 
Deadlinks: 
H.abyss? 
Lost Receipts? 
Are you the original owner? 
Can the email be surrendered? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="hsr", style=discord.ButtonStyle.grey, custom_id="mm_forms:hsr")
    async def hsr_button(self, interaction, button):
        await interaction.response.send_message("""
### Honkai: Star Rail MM form
Account Size: 
Trailblaze Level: 
Server: 
5 star characters, eidolons & lightcones: 
Deadlinks: 
Lost Receipts? 
Are you the original owner? 
Can the email be surrendered? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="wuwa", style=discord.ButtonStyle.grey, custom_id="mm_forms:wuwa")
    async def wuwa_button(self, interaction, button):
        await interaction.response.send_message("""
### Wuthering Waves MM form
Account Size: 
Union Level: 
Server: 
5 star characters, sequences & weapons: 
Deadlinks: 
H.tower? 
Lost Receipts? 
Are you the original owner? 
**Please note that email __must__ be surrendered for wuwa accounts.**
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="roblox", style=discord.ButtonStyle.grey, custom_id="mm_forms:roblox")
    async def roblox_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox MM form
Username: 
Do you have the original email? 
Can the email be surrendered? 
PIN Set or Unset? 
Lost Receipts? 
Are you the original owner? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="roblox items", style=discord.ButtonStyle.grey, custom_id="mm_forms:roblox_items")
    async def roblox_items_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox Items MM form
Username: 
Roblox Game: 
Roblox Game Items: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

class MMRisksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="deadlinks", style=discord.ButtonStyle.grey, custom_id="mm_risks:deadlinks")
    async def deadlinks_button(self, interaction, button):
        await interaction.response.send_message("""
## Deadlinks <a:whitealert:1496542298908000257>
> 3rd party links are links binded to the hoyoverse account which serves as an alternative way to login - Facebook, Game Center, Google, PSN, Apple, Twitter. A deadlink is a 3rd party link where the owner no longer has access to the 3rd party account and is unable to unlink it, but also unable to login via the link, e.g. Twitter account was deleted.
**__Risks__**
- **Hoyoverse:** Facebook, Twitter, Google, Apple and Game Center links are __safe__ and can be secured easily by removing all trusted devices via the [Hoyoverse website](https://account.hoyoverse.com). Attempts to login via these links will require a verification code sent to the linked email.
- **Wuthering Waves:** Note that in Wuwa, ANY 3rd party links attached can be used to log into the account __without a verification code__, even after the password has been changed.
- A deadlink may not be truly dead; scammers may lie about deadlinks and use them to attempt to retrieve the account later on.
- **PSN and Xbox links are especially __dangerous__** as they do not require new device verification and require Hoyoverse CS to unlink. a PSN link may be considered dead if the most recent trophy was gained >6 months ago.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                    """)

    @discord.ui.button(label="hacked abyss", style=discord.ButtonStyle.grey, custom_id="mm_risks:hacked_abyss")
    async def hacked_abyss_button(self, interaction, button):
        await interaction.response.send_message("""
## Hαcked Abyss <a:whitealert:1496542298908000257>
> A h.abyss account is where a bot was used to complete spiral abyss to gain primogems. A h.abyss account can be identified when a high number of stars has been obtained with missing stats (e.g. most damage taken) or an unusually low "strongest single strike" in the abyss challenge summary. They typically apply to reroll accounts using starter characters. However, other characters can also be used.
**__Risks__**
- As it is against Hoyoverse’s ToS, your account and/or IP address may get banned.
- Asia accounts seem to be riskier than EU or NA accounts.
- The risk may not be high, but it is always there and should always be mentioned when trading.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                    """)

    @discord.ui.button(label="lost receipts", style=discord.ButtonStyle.grey, custom_id="mm_risks:lost_receipts")
    async def lost_receipts_button(self, interaction, button):
        await interaction.response.send_message("""
## Lost Receipts <a:whitealert:1496542298908000257>
> These risks apply to **ALL __P2W__ accounts**, even if you have receipts. P2W is when there has been **any** purchase on the account, regardless of amount, when the purchase was made and from where (in-game top-up, codashop, giveaway win etc.)
> Receipts must have the __amount spent, transaction ID and what was purchased__ in a **__full__ screenshot** (preferably uncropped) to be a valid receipt.
**__Risks__**
- Increased chances of retrieval from the owner who purchased something. the older the receipt, the easier the retrieval.
- Scammers may lie about having lost the receipts when they still have possession of them but are unwilling to provide them so that they can retrieve the account from Hoyoverse CS later on.
- Purchase records are only kept for 6 months in currency records.
- Purchases made within 2 weeks can be __refunded.__ It will result in **negative premium currency (e.g. primogems) which needs to be brought back to 0 or more within __1 week__ or the account will be banned.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                        """)

    @discord.ui.button(label="email surrender", style=discord.ButtonStyle.grey, custom_id="mm_risks:email_surrender")
    async def email_surrender_button(self, interaction, button):
        await interaction.response.send_message("""
## Email Surrender <a:whitealert:1496542298908000257>
> Email surrender requires giving up the entire email, fully losing access of it, so ensure you will never need it in the future.
**__Risks__**
- Higher chance of retrieval.
- Email can be disabled/frozen, meaning you cannot receive any new verification codes.
- Previously surrendered emails are more risky.
- Gmail holds recovery info for up to 2 weeks.
**__FOR GMAILS: Do not change password within the first 72h__ and avoid changing recovery info frequently to prevent locking.** __Outlook__ emails are __safe__ to change password immediately.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                            """)

@bot.command(name="adm", help="Pings ADM+.")
async def adm(ctx):
    if ctx.guild.id == TRI_Archive:
        return
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    adm_ping = server_info.get("adm_ping")
    if adm_ping:
        await ctx.reply(f"{adm_ping}")

@bot.command(name="revive", help="Pings revive.")
async def revive(ctx):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    revive_ping = server_info.get("revive_ping")
    if revive_ping:
        await ctx.reply(f"{revive_ping}")

@bot.command(name="lb", help="Sends the current month’s leaderboard.")
async def lb(ctx, *, category: str=None):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if ctx.guild.id == TRI_Archive:
        return
    if not server_info:
        return
    if category == "s":
        staff = server_info.get("staff", {})
        sorted_staff = sorted(
            staff.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_staff, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
        await ctx.send("## _ _　　　staff leaderboard", embed=embed)
    if category == "t":
        staff = server_info.get("staff", {})
        sorted_tickets = sorted(
            staff.items(),
            key=lambda x: x[1].get("monthly_tickets", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_tickets, start=1):
            if rank > 50:
                break
            monthly_tickets = data.get("monthly_tickets", 0)
            tickets = data.get("tickets", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{tickets}** all ㆍ **{monthly_tickets}** month\n"
        embed = discord.Embed(description=desc if desc else "No staff found.", colour=0xffffff)
        await ctx.send("## _ _　　　tickets leaderboard", embed=embed)
    if category == "m":
        mms = server_info.get("mms", {})
        sorted_mms = sorted(
            mms.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_mms, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No mms found.", colour = 0xffffff)
        await ctx.send("## _ _　　　mm leaderboard", embed=embed)
    if category == "p":
        pilots = server_info.get("pilots", {})
        sorted_pilots = sorted(
            pilots.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_pilots, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No pilots found.", colour = 0xffffff)
        await ctx.send("## _ _　　　pilot leaderboard", embed=embed)


@bot.command(name="rn")
@commands.cooldown(2, 600, commands.BucketType.channel)
async def rn(ctx, *, new_name: str):
    if ctx.guild.id == TRI_Archive or ctx.guild.id == Tethys:
        return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    if server_info:
        staff_role = server_info.get("staff_role")
    if (staff_role and get(ctx.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", "")))) in ctx.author.roles or ctx.author.guild_permissions.manage_channels:
        if isinstance(ctx.channel, discord.Thread):
            try:
                await ctx.channel.edit(name=new_name)
            except Exception as e:
                await ctx.send(f"Renaming failed due to an error: {e}")
        elif isinstance(ctx.channel, discord.TextChannel):
            try:
                await ctx.channel.edit(name=new_name)
                await ctx.send(f"Channel renamed to **{new_name}**.")
            except Exception as e:
                await ctx.send(f"Renaming failed due to an error: {e}")
        else:
            await ctx.send("This command can only be used in a channel or thread.")
@rn.error
async def rn_error(ctx, error):
    if ctx.guild.id == TRI_Archive or ctx.guild.id == Tethys:
        return
    if isinstance(error, commands.CommandOnCooldown):
        remaining = error.retry_after  # cooldown time in seconds
        return await ctx.send(f"This command is on cooldown. Retry in {round(remaining)} seconds.")
    raise error

async def get_active_claims(channel_id):
    data = ticket_claims.find_one({"_id": channel_id})
    if not data:
        return []
    return data.get("claimed_by", [])

async def active_claim(channel_id, user_id):
    data = ticket_claims.find_one({"_id": channel_id})
    if not data:
        return False
    return user_id in data.get("claimed_by", [])

async def get_uncredited_claims(channel_id):
    data = ticket_claims.find_one({"_id": channel_id})
    if not data:
        return []
    claimed = set(data.get("claimed_by", []))
    closed = set(data.get("closed_claims", []))
    return list(claimed - closed)

@tasks.loop(hours=1)
async def ticket_claim_cleanup_loop():
    cutoff = int(time.time()) - 86400
    ticket_claims.delete_many({
        "closed": True,
        "closed_at": {"$lte": cutoff}
    })

@bot.command(name="claim")
async def claim(ctx, mode: str = None, member: discord.Member = None):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info.get("staff_role"):
        await ctx.reply("**staff role** has not been set up for this server.")
        return
    if not server_info.get("adm_ping"):
        await ctx.reply("**adm ping** has not been set up for this server.")
        return
    staff_role = server_info["staff_role"]
    adm_ping = server_info["adm_ping"]
    if get(ctx.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) not in ctx.author.roles:
        return
    target = ctx.author
    if mode == "force":
        if not (get(ctx.guild.roles, id=int(adm_ping.replace("<@&", "").replace(">", ""))) in ctx.author.roles or ctx.author.guild_permissions.manage_roles):
            await ctx.reply("Unauthorised.")
            return
        if not member:
            await ctx.reply("Please specify a user to force claim.")
            return
        target = member
    already_claimed = await active_claim(ctx.channel.id, target.id)
    if already_claimed:
        await ctx.reply("User has already claimed this ticket.")
        return
    ticket_claims.update_one({"_id": ctx.channel.id},
                             {"$addToSet": {"claimed_by": target.id}, "$set": {"closed": False}}, upsert=True)
    if ctx.guild.id == TRI_Archive:
        manager = getattr(bot, "ticket_manager", None)
        if manager:
            ticket = await manager.from_thread(ctx.channel.id)
            if ticket:
                await ticket.claim(target.id)
    embed = discord.Embed(colour=0xffffff, description=f"{target.mention} has claimed the ticket.")
    await ctx.reply(embed=embed)

@bot.command(name="unclaim")
async def unclaim(ctx, mode: str = None, member: discord.Member = None):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info.get("staff_role"):
        await ctx.reply("**staff role** has not been set up for this server.")
        return
    if not server_info.get("adm_ping"):
        await ctx.reply("**adm ping** has not been set up for this server.")
        return
    staff_role = server_info["staff_role"]
    adm_ping = server_info["adm_ping"]
    if get(ctx.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) not in ctx.author.roles:
        return
    target = ctx.author
    if mode == "force":
        if not (get(ctx.guild.roles, id=int(adm_ping.replace("<@&", "").replace(">", ""))) in ctx.author.roles or ctx.author.guild_permissions.manage_roles):
            await ctx.reply("Unauthorised.")
            return
        if not member:
            await ctx.reply("Please specify a user to force unclaim.")
            return
        target = member
    already_claimed = await active_claim(ctx.channel.id, target.id)
    if not already_claimed:
        await ctx.reply("User has not claimed this ticket.")
        return
    ticket_claims.update_one(
        {"_id": ctx.channel.id},
        {"$pull": {"claimed_by": target.id}}
    )
    if ctx.guild.id == TRI_Archive:
        manager = getattr(bot, "ticket_manager", None)
        if manager:
            ticket = await manager.from_thread(ctx.channel.id)
            if ticket:
                await ticket.unclaim(target.id)
    embed = discord.Embed(colour=0xffffff, description=f"{target.mention} has unclaimed the ticket.")
    await ctx.reply(embed=embed)

@bot.command(name="claims")
async def claims(ctx, *args):
    if args:
        return
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info.get("staff_role"):
        await ctx.reply("**staff role** has not been set up for this server.")
        return
    staff_role = server_info["staff_role"]
    if get(ctx.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) not in ctx.author.roles:
        return
    active_claims = await get_active_claims(ctx.channel.id)
    mentions = [f"<@{uid}>" for uid in active_claims]
    embed = discord.Embed(colour=0xffffff, description=f"Ticket has been claimed by **{len(mentions)}** user(s)\n" + ", ".join(mentions))
    await ctx.reply(embed=embed)

@bot.command(name="close")
async def close(ctx, *args):
    if args:
        return
    server_info = await asyncio.to_thread(
        servers.find_one_and_update,
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info or not server_info.get("staff_role"):
        await ctx.reply("**staff role** has not been set up for this server.")
        return
    staff_role = server_info.get("staff_role")
    adm_ping = server_info.get("adm_ping")
    if get(ctx.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in ctx.author.roles:
        active_claims = await get_uncredited_claims(ctx.channel.id)
        if ctx.guild.id == TRI_Archive:
            if not (get(ctx.guild.roles, id=int(adm_ping.replace("<@&", "").replace(">", ""))) in ctx.author.roles or ctx.author.guild_permissions.manage_roles):
                return await ctx.reply("You are not authorised to close this ticket.")
        else:
            if not active_claims:
                await ctx.reply("No new ticket credits to give.")
                return
        mentions = [f"<@{uid}>" for uid in active_claims]
        embed = discord.Embed(colour=0xffffff, description=f"Ticket has been claimed by **{len(mentions)}** user(s)\n" + ", ".join(mentions))
        if ctx.guild.id == TRI_Archive:
            ticket = await bot.ticket_manager.from_thread(ctx.channel.id)
            if not ticket:
                return await ctx.reply("This channel is not an active ticket thread.")
            claims_doc = await asyncio.to_thread(ticket_claims.find_one, {"_id": ctx.channel.id})
            all_claims = claims_doc.get("claimed_by", []) if claims_doc else ticket.data.get("claimed_by", [])
            credited_users = ticket.data.get("credited_users", [])
            new_claims = [uid for uid in all_claims if uid not in credited_users]
            past_claims = [uid for uid in all_claims if uid in credited_users]
            new_mentions = ", ".join([f"<@{uid}>" for uid in new_claims]) if new_claims else "None"
            past_mentions = ", ".join([f"<@{uid}>" for uid in past_claims]) if past_claims else "None"
            embed = discord.Embed(colour=0xffffff)
            embed.description = (
                f"### Ticket Claim Status\n"
                f"**Newly claimed:** {new_mentions}\n"
                f"**Previously credited:** {past_mentions}"
            )

            async def get_miku_closing(thread: discord.Thread):
                async for message in thread.history(limit=None, oldest_first=True):
                    if message.author.id == MIKU:
                        if message.embeds:
                            embed = message.embeds[0]
                            if embed.fields:
                                field = embed.fields[0]
                                closing = field.value.strip("`")
                                return closing
                        break
                return ""
            detected = await get_miku_closing(ctx.channel)
            embed.add_field(name="Closing", value=detected, inline=True)
            await ctx.reply(embed=embed, view=TRICloseView(active_claims))
        else:
            await ctx.reply(embed=embed, view=TicketCloseView(active_claims))

class TicketClosingModal(discord.ui.Modal, title="Ticket Closing Reason"):
    closing = discord.ui.TextInput(label="Closing", required=False, style=discord.TextStyle.paragraph)
    def __init__(self, message: discord.Message, active_claims: list):
        super().__init__()
        self.message = message
        self.active_claims = active_claims
        embed = message.embeds[0]
        current_closing = ""
        if embed.fields:
            current_closing = embed.fields[0].value.strip("`") or ""
        self.closing.default = current_closing

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0]
        val = f"{self.closing.value}" if self.closing.value.strip() else ""
        if embed.fields:
            embed.set_field_at(0, name="Closing", value=val, inline=False)
        else:
            embed.add_field(name="Closing", value=val, inline=False)
        await self.message.edit(embed=embed, view=TRICloseView(self.active_claims))
        await interaction.response.send_message("Closing updated.", ephemeral=True)

class TRICloseView(discord.ui.View):
    def __init__(self, active_claims):
        super().__init__(timeout=120)
        self.active_claims = active_claims

    @discord.ui.button(label="Closing", style=discord.ButtonStyle.blurple, custom_id="triclose:closing",
                       row=0)
    async def closing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketClosingModal(interaction.message, self.active_claims))

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="triclose:confirm")
    async def confirm_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        if not is_sr(interaction.user):
            return await interaction.followup.send("You do not have permission to close this ticket.", ephemeral=True)

        closing = None
        if interaction.message.embeds and interaction.message.embeds[0].fields:
            closing = interaction.message.embeds[0].fields[0].value

        if not closing:
            return await interaction.followup.send("Please add a closing before confirming.", ephemeral=True)

        ticket = await bot.ticket_manager.from_thread(interaction.channel_id)
        if ticket is None:
            return await interaction.followup.send("This channel is not an active ticket thread.", ephemeral=True)

        claims_doc = ticket_claims.find_one({"_id": interaction.channel_id})
        claims_to_process = claims_doc.get("claimed_by", []) if claims_doc else ticket.data.get("claimed_by", [])

        if "credited_users" not in ticket.data:
            ticket.data["credited_users"] = []
        new_claims = [uid for uid in self.active_claims if uid not in ticket.data["credited_users"]]

        weekly_operations = []
        alltime_operations = []
        closer_id = str(interaction.user.id)

        for uid in new_claims:
            uid_str = str(uid)
            weekly_operations.append(UpdateOne({"_id": uid_str}, {"$inc": {"weekly_tickets": 1}}))
            alltime_operations.append(UpdateOne({"_id": uid_str}, {"$inc": {"tickets": 1}}))
            ticket.data["credited_users"].append(uid)

        weekly_operations.append(UpdateOne({"_id": closer_id}, {"$inc": {"weekly_closes": 1}}))
        alltime_operations.append(UpdateOne({"_id": closer_id}, {"$inc": {"closes": 1}}))

        await ticket.save()
        if weekly_operations:
            await asyncio.to_thread(staffweeklycol.bulk_write, weekly_operations)
        if alltime_operations:
            await asyncio.to_thread(trusteduserscol.bulk_write, alltime_operations)

        await interaction.edit_original_response(content="Ticket credit(s) have been given.", view=None)
        closing_embed = discord.Embed(description=f"""
**Ticket closed by {interaction.user.mention}**
\n**Closing:**\n{closing}
        """)
        await interaction.channel.send(embed=closing_embed)
        try:
            await bot.ticket_manager.close(
                ticket=ticket,
                closed_by=interaction.user.id,
                closing=closing
            )
            await interaction.followup.send("Ticket closed successfully!", ephemeral=True)
            await interaction.channel.edit(locked=True, archived=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="triclose:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        await interaction.edit_original_response(content="**Cancelled.** Ticket credit(s) have not been given.",view=None)


class TicketCloseView(discord.ui.View):
    def __init__(self, active_claims):
        super().__init__(timeout=120)
        self.active_claims = active_claims

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="ticketclose:confirm")
    async def confirm_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        server_query = {"_id": str(interaction.guild.id)}
        server_info = servers.find_one(server_query)
        if not server_info: return
        staff_role = server_info.get("staff_role")
        adm_ping = server_info["adm_ping"]
        if not staff_role: return
        if get(interaction.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
            if interaction.guild.id == TRI_Archive:
                if not (get(interaction.guild.roles, id=int(adm_ping.replace("<@&", "").replace(">", ""))) in interaction.user.roles or interaction.user.guild_permissions.manage_roles):
                    return await interaction.followup.send("You are not authorised to close this ticket.")
            operations = []
            for uid in self.active_claims:
                staff_data = server_info.get("staff", {}).get(str(uid))
                if staff_data is None:
                    await interaction.followup.send(f"Unable to add ticket credit to <@{uid}>.", ephemeral=True)
                    continue
                operations.append(UpdateOne(
                    {"_id": str(interaction.guild.id), f"staff.{str(uid)}": {"$exists": True}},
                    {"$inc": {f"staff.{str(uid)}.monthly_tickets": 1, f"staff.{str(uid)}.tickets": 1},
                     }))

            if operations:
                servers.bulk_write(operations)
            ticket_claims.update_one({"_id": interaction.channel.id},
                                     {"$addToSet": {"closed_claims": {"$each": self.active_claims}},
                                      "$set": {"closed": True, "closed_at": int(time.time())}}, upsert=True)
            await interaction.edit_original_response(content="Ticket credit(s) have been given.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="ticketclose:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        await interaction.edit_original_response(content="**Cancelled.** Ticket credit(s) have not been given.",view=None)

def user_info(user, staff_data=None, mm_data=None, pilot_data=None):
    profile = discord.Embed()
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"{user.display_name}\n`{user.id}`\n{user.mention}\n`{user.name}`"
    profile.description += f"\n**Account Created:** <t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)\n"
    if staff_data is not None:
        profile.add_field(
            name="staff",
            value=f"**{staff_data.get('alltime', 0)}** all ㆍ **{staff_data.get('monthly', 0)}** month",
            inline=False
        )
        profile.add_field(
            name="tickets",
            value=f"**{staff_data.get('tickets', 0)}** all ㆍ **{staff_data.get('monthly_tickets', 0)}** month",
            inline=False
        )
    if mm_data is not None:
        profile.add_field(
            name="mm",
            value=f"**{mm_data.get('alltime', 0)}** all ㆍ **{mm_data.get('monthly', 0)}** month",
            inline=False
        )
    if pilot_data is not None:
        profile.add_field(
            name="pilot",
            value=f"**{pilot_data.get('alltime', 0)}** all ㆍ **{pilot_data.get('monthly', 0)}** month",
            inline=False
        )
    profile.set_footer(text="✦　Use ,c to check if user is reported, unreported or trusted.")
    return profile

@bot.command(name="p")
async def profile(ctx, user:str = None):
    if user is None:
        user = ctx.author
    else:
        try:
            user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
        except Exception:
            await ctx.reply("Please provide a valid user ID.")
            return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    if not server_info:
        await ctx.reply(embed=user_info(user))
        return
    uid = str(user.id)
    staff = server_info.get("staff", {})
    mms = server_info.get("mms", {})
    pilots = server_info.get("pilots", {})
    roles = []
    if uid in staff:
        roles.append("staff")
        staff_data = staff.get(uid, {})
    else:
        staff_data = None
    if uid in mms:
        roles.append("mm")
        mm_data = mms.get(uid, {})
    else:
        mm_data = None
    if uid in pilots:
        roles.append("pilot")
        pilot_data = pilots.get(uid, {})
    else:
        pilot_data = None
    await ctx.reply(embed=user_info(user, staff_data, mm_data, pilot_data))

def format_time_utc(tz_str: str):
    now = datetime.datetime.now(ZoneInfo(tz_str))
    offset = now.utcoffset()
    total_minutes = int(offset.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = abs(total_minutes % 60)
    if minutes == 0:
        utc_str = f"UTC{hours:+}"
    else:
        utc_str = f"UTC{hours:+}:{minutes:02d}"
    time_str = now.strftime("%I:%M %p")
    return f"{time_str} ({utc_str})"

@bot.command(name="tz")
async def tz(ctx, user:str = None):
    if user is None:
        user = ctx.author
    else:
        try:
            user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
        except Exception:
            await ctx.reply("Please provide a valid user ID.")
            return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    uid = str(user.id)
    if server_info:
        staff = server_info.get("staff", {})
        if uid in staff:
            profile = timezones.find_one({"_id": uid})
            user_tz = profile.get("timezone") if profile else None
            if user_tz is not None:
                formatted = format_time_utc(user_tz)
                await ctx.reply(f"It is now **{formatted}** for **{user.name}**")
            else:
                await ctx.reply(f"`{user.id}` has not set their timezone.")
        else:
            await ctx.reply(f"`{user.id}` is not appointed as staff.")

async def timezone_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    matches = [tz for tz in TIMEZONES if current.lower() in tz.lower()][:25]
    return [app_commands.Choice(name=tz.replace("_", " "), value=tz) for tz in matches]

settings = app_commands.Group(name="set", description="Set.")
bot.tree.add_command(settings)

@settings.command(name="timezone", description="Set your timezone")
@app_commands.autocomplete(timezone=timezone_autocomplete)
async def set_timezone(interaction: discord.Interaction, timezone: str):
    if timezone not in TIMEZONES:
        await interaction.response.send_message("Invalid timezone.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if server_info:
        if not server_info.get("staff_role"):
            await interaction.response.send_message("**staff role** has not been set up for this server.", ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        if get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
            server_info.setdefault("staff", {})
            uid = str(interaction.user.id)
            staff = server_info.get("staff", {})
            if uid in staff:
                timezones.update_one(
                    {"_id": uid},
                    {"$set": {"timezone": timezone}},
                    upsert=True
                )
            now = datetime.datetime.now(ZoneInfo(timezone))
            offset = now.utcoffset()
            total_minutes = int(offset.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = abs(total_minutes % 60)
            if minutes == 0:
                utc = f"UTC{hours:+}"
            else:
                utc = f"UTC{hours:+}:{minutes:02d}"
            await interaction.response.send_message(f"Your timezone has been set to **{timezone.replace("_", " ")} ({utc})**.")

@settings.command(name="points", description="Set points to a certain value.")
async def set_points(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot", "tickets"], timeframe: Literal["monthly", "alltime"], value: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    if guild_id == TRI_Archive:
        return await interaction.followup.send(f"KAFU leaderboard is disabled in TRI Archive.", ephemeral=True)
    if not is_int(value):
        await interaction.followup.send("Please input a valid integer value.", ephemeral=True)
        return
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except Exception:
        await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
    else:
        user_id = user.id
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        if category == "tickets":
            field_name = "tickets" if timeframe == "alltime" else "monthly_tickets"
            db_path = f"staff.{user_id}.{field_name}"
            check_path = f"staff.{user_id}"
        elif category == "pilot":
            db_path = f"pilots.{user_id}.{timeframe}"
            check_path = f"pilots.{user_id}"
        elif category == "mm":
            db_path = f"mms.{user_id}.{timeframe}"
            check_path = f"mms.{user_id}"
        else:
            db_path = f"{category}.{user_id}.{timeframe}"
            check_path = f"{category}.{user_id}"
        result = servers.update_one(
            {
                "_id": str(guild_id),
                check_path: {"$exists": True}
            },
            {"$set": {db_path: int(value)}}
        )
        if result.modified_count > 0:
            await interaction.followup.send(
                f"`{user_id}`’s **{timeframe} {category}** points has been set to **{value}**.", ephemeral=True)
        else:
            if category == "tickets": category = "staff"
            await interaction.followup.send(
                f"`{user_id}` is not appointed as **{category}**.",
                ephemeral=True)

@settings.command(name="vouchserver", description="Set your vouch server invite.")
@app_commands.describe(invite="Invite link to your vouch server.")
async def set_vouchserver(interaction: discord.Interaction, invite: str):
    await interaction.response.defer()
    if not interaction.guild:
        await interaction.followup.send("This command can only be used in a server.")
        return
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    user_id = str(interaction.user.id)
    is_mm = user_id in server_info.get("mms", {})
    is_pilot = user_id in server_info.get("pilots", {})
    if not is_mm and not is_pilot:
        await interaction.followup.send("Only appointed mms or pilots can set a vouch server.")
        return
    try:
        invite = await bot.fetch_invite(invite)
    except discord.NotFound:
        await interaction.followup.send("Invalid invite link.")
        return
    except discord.HTTPException:
        await interaction.followup.send("Failed to fetch invite.")
        return
    if not invite.guild:
        await interaction.followup.send("Invalid invite link.")
        return
    vouch_servers.update_one({"_id": user_id}, {"$set": {"invite": invite.url}}, upsert=True)
    await interaction.followup.send(f"Your vouch server has been set to:\n{invite.url}")

@bot.command(name="vouch")
async def vouch(ctx):
    if not ctx.guild:
        return
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    user_id = str(ctx.author.id)
    vouch_server = vouch_servers.find_one({"_id": user_id})
    is_mm = user_id in server_info.get("mms", {})
    is_pilot = user_id in server_info.get("pilots", {})
    if not is_mm and not is_pilot:
        await ctx.reply("You are not appointed as a mm or pilot.")
        return
    if not vouch_server:
        await ctx.reply("You have not set a vouch server.")
        return
    invite = vouch_server["invite"]
    lines = [f"<:whiteheart:1434538078747365507>　Please vouch for {ctx.author.mention} at the links below:", f"<:greyreply:1448474301673115748><:blank:1383116055550890095>[vouch server]({invite})"]
    if is_mm:
        mm_vouch_channel = server_info.get("mm_vouch_channel")
        if mm_vouch_channel:
            lines.append(f"<:greyreply:1448474301673115748><:blank:1383116055550890095>{mm_vouch_channel}")
    if is_pilot:
        pilot_vouch_channel = server_info.get("pilot_vouch_channel")
        if pilot_vouch_channel:
            lines.append(f"<:greyreply:1448474301673115748><:blank:1383116055550890095>{pilot_vouch_channel}")
    await ctx.send("\n".join(lines))

@bot.command(name="cr")
async def cr(ctx):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    role_id = next((r for r, d in custom_roles.items() if d.get("owner") == str(ctx.author.id)), None)
    if not role_id:
        await ctx.reply("You do not have a custom role.")
        return
    role = ctx.guild.get_role(int(role_id))
    if not role:
        await ctx.reply("Your custom role no longer exists.")
        return
    data = custom_roles[role_id]
    if data["type"] == "booster":
        expiry = "booster (active while boosting)"
    elif data.get("expires_at"):
        expiry = f"<t:{data["expires_at"]}:R>"
    else:
        expiry = "no expiry"
    embed = discord.Embed(
        colour=role.colour,
        description=f"**Role:** {role.mention} `{role.id}`\n**Owner:** {ctx.author.mention}\n**Expires:** {expiry}"
    )
    embed.set_author(name=role.name, icon_url=role.icon.url if role.icon else None)
    await ctx.reply(embed=embed)

@tasks.loop(hours=1)
async def customrole_expiry_loop():
    now = int(time.time())
    for server_info in servers.find({}):
        guild = bot.get_guild(int(server_info["_id"]))
        if not guild:
            continue
        roles = server_info.get("custom_roles", {})
        for role_id, data in list(roles.items()):
            role = guild.get_role(int(role_id))
            if not role:
                continue
            owner = guild.get_member(int(data["owner"]))
            if data["type"] == "booster":
                if not owner or not owner.premium_since:
                    await role.delete(reason="Booster custom role expired")
                    servers.update_one(
                        {"_id": server_info["_id"]},
                        {"$unset": {f"custom_roles.{role_id}": ""}}
                    )
                continue
            if data["expires_at"] and now >= data["expires_at"]:
                await role.delete(reason="Custom role expired")
                servers.update_one(
                    {"_id": server_info["_id"]},
                    {"$unset": {f"custom_roles.{role_id}": ""}}
                )

@tasks.loop(hours=6)
async def cleanup_custom_roles():
    for server in servers.find({}):
        guild = bot.get_guild(int(server["_id"]))
        if not guild:
            continue
        custom_roles = server.get("custom_roles", {})
        for role_id in list(custom_roles.keys()):
            role = guild.get_role(int(role_id))
            if role is None:
                servers.update_one(
                    {"_id": server["_id"]},
                    {"$unset": {f"custom_roles.{role_id}": ""}}
                )

customrole = app_commands.Group(name="customrole", description="Manage custom roles.")
bot.tree.add_command(customrole)

@customrole.command(name="list", description="List all custom roles.")
async def customrole_list(interaction: discord.Interaction):
    server_info = servers.find_one({"_id": str(interaction.guild.id)})
    roles = server_info.get("custom_roles", {})
    desc = ""
    for role_id, data in roles.items():
        role = interaction.guild.get_role(int(role_id))
        if not role:
            continue
        owner = f"<@{data["owner"]}>"
        if data["type"] == "booster":
            expiry = "booster"
        elif data["expires_at"]:
            expiry = f"<t:{data["expires_at"]}:R>"
        else:
            expiry = "no expiry"
        desc += f"{role.mention}　–　{owner}　–　expires {expiry}\n"
    embed = discord.Embed(description=desc or "No custom roles.")
    await interaction.response.send_message(embed=embed)

@customrole.command(name="edit", description="Edit a custom role.")
async def customrole_edit(interaction: discord.Interaction,
                            name: Optional[str]=None,
                            colour: Optional[str] = None,
                            emoji: Optional[str] = None,
                            image: Optional[discord.Attachment] = None
                            ):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    role_id = next((r for r, d in custom_roles.items() if d.get("owner") == str(interaction.user.id)), None)
    if not role_id:
        await interaction.followup.send("You do not have a custom role.")
        return
    role = interaction.guild.get_role(int(role_id))
    if not role:
        await interaction.followup.send("Your custom role no longer exists.")
        return
    if not name and not colour and not emoji and not image:
        await interaction.followup.send("Specify at least one change.")
    bot_member = interaction.guild.me
    if role.position >= bot_member.top_role.position:
        await interaction.followup.send(
            "Missing permissions. Check if KAFU’s highest role is above the role you are trying to edit.",
            ephemeral=True)
        return
    if role.managed:
        await interaction.followup.send("KAFU cannot edit integration-managed roles.", ephemeral=True)
        return
    if name:
        await role.edit(name=name)
    if colour:
        try: await role.edit(colour=discord.Colour(int(colour.strip("#"), 16)))
        except Exception: await interaction.followup.send("Invalid HEX code.", ephemeral=True)
    # role icon
    if image:
        data = await image.read()
        try: await role.edit(display_icon=data)
        except Exception:
            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    if emoji:
        match = re.search(r"<a?:\w+:(\d+)>", emoji or "")
        if not match:
            await interaction.followup.send("Invalid custom emoji format.", ephemeral=True)
        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Failed to fetch emoji.", ephemeral=True)
                    else:
                        data = await resp.read()
                        try:
                            await role.edit(display_icon=data)
                        except Exception:
                            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)

@customrole.command(name="create", description="Create a custom role.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_create(interaction: discord.Interaction,
    owner: discord.Member,
    name: str,
    duration: Optional[str] = None,  # seconds
    booster: Optional[bool] = False,
    colour: Optional[str] = None,
    emoji: Optional[str] = None,
    image: Optional[discord.Attachment] = None
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        if data["owner"] == str(owner.id):
            role = interaction.guild.get_role(int(role_id))
            if role:
                await interaction.followup.send("User already has a custom role.", ephemeral=True)
                return
    # create role
    role = await interaction.guild.create_role(
        name=name,
        colour=discord.Colour(int(colour.strip("#"), 16)) if colour else discord.Colour.default()
    )
    # move role under bot
    bot_top = interaction.guild.me.top_role
    await interaction.guild.edit_role_positions({role: bot_top.position - 1})
    # role icon
    if image:
        data = await image.read()
        try: await role.edit(display_icon=data)
        except Exception:
            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    if emoji:
        match = re.search(r"<a?:\w+:(\d+)>", emoji or "")
        if not match:
            await interaction.followup.send("Invalid custom emoji format.", ephemeral=True)
        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Failed to fetch emoji.", ephemeral=True)
                    else:
                        data = await resp.read()
                        try:
                            await role.edit(display_icon=data)
                        except Exception:
                            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    # assign
    await owner.add_roles(role)
    # expiry
    if booster:
        expires_at = None
        role_type = "booster"
    else:
        duration = parse_duration(duration) if duration else None
        expires_at = int(time.time()) + duration if duration else None
        role_type = "time"
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
                f"custom_roles.{role.id}": {
                    "owner": str(owner.id),
                    "expires_at": expires_at,
                    "type": role_type
                }
            }
        },
        upsert=True
    )
    await interaction.followup.send(f"Custom role {role.mention} created for {owner.mention}")

@customrole.command(name="delete", description="Delete a custom role.")
async def customrole_delete(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    bot_member = interaction.guild.me
    if role:
        if role.managed:
            await interaction.followup.send("Cannot delete integration-managed role.")
        elif role.position >= bot_member.top_role.position:
            await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to delete.")
        else:
            try:
                await role.delete(reason="Custom role deleted")
            except discord.Forbidden:
                await interaction.followup.send("Missing permissions to delete role.")
    if str(role.id) in server_info.get("custom_roles", {}):
        servers.update_one(
            {"_id": str(interaction.guild.id)},
            {"$unset": {f"custom_roles.{role.id}": ""}}
        )
    await interaction.followup.send(f"Custom role deleted.")

@customrole.command(name="add", description="Add an existing role to custom roles.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_add(
    interaction: discord.Interaction,
    role: discord.Role,
    owner: discord.Member,
    duration: Optional[str] = None,
    booster: Optional[bool] = False
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        if data["owner"] == str(owner.id):
            role = interaction.guild.get_role(int(role_id))
            if role:
                await interaction.followup.send("User already has a custom role.", ephemeral=True)
                return
    bot_top = interaction.guild.me.top_role
    try: await interaction.guild.edit_role_positions({role: bot_top.position - 1})
    except discord.Forbidden: pass
    duration = parse_duration(duration) if duration else None
    expires_at = None if booster else int(time.time()) + duration if duration else None
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
                f"custom_roles.{role.id}": {
                    "owner": str(owner.id),
                    "expires_at": expires_at,
                    "type": "booster" if booster else "time"
                }
            }
        },
        upsert=True
    )
    await interaction.followup.send("Custom role added.")

@customrole.command(name="remove", description="Remove a role from custom roles.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_remove(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if str(role.id) not in server_info.get("custom_roles", {}):
        await interaction.followup.send("This role is not registered as a custom role.")
        return
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {"$unset": {f"custom_roles.{role.id}": ""}}
    )
    await interaction.followup.send(f"{role.mention} removed from database.")

@customrole.command(name="setexpiry", description="Set expiry for an existing custom role.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_setexpiry(
    interaction: discord.Interaction,
    role: discord.Role,
    duration: Optional[str] = None,
    booster: Optional[bool] = False
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.followup.send("Custom role no longer exists.", ephemeral=True)
            return
    duration = parse_duration(duration) if duration else None
    expires_at = None if booster else int(time.time()) + duration if duration else None
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
            f"custom_roles.{role.id}.expires_at": expires_at,
            f"custom_roles.{role.id}.type": "booster" if booster else "time"
        }}, upsert=True)
    await interaction.followup.send("Custom role updated.")

edit_queue = defaultdict(asyncio.Queue)
edit_locks = defaultdict(asyncio.Lock)

def queue_message_update(message_id: int, payload):
    edit_queue[message_id].put_nowait(payload)

async def message_update_worker():
    while True:
        for message_id, queue in list(edit_queue.items()):
            if queue.empty():
                continue
            async with edit_locks[message_id]:
                try:
                    payload = await queue.get()
                    message = payload["message"]
                    embed = payload["embed"]
                    await message.edit(embed=embed)
                    await asyncio.sleep(2.5)
                except Exception:
                    continue
        await asyncio.sleep(0.5)

def build_vote_embed(session):
    options = session["options"]
    vote_map = session.get("vote_map", {})
    counts = [0] * len(options)
    for user_votes in vote_map.values():
        for i in user_votes:
            if i < len(counts):
                counts[i] += 1
    desc = ""
    for i, opt in enumerate(options):
        desc += f"{i+1}ㆍ　{opt}　–　**{counts[i]}** votes\n"
    ends = f"<t:{session['ends_at']}:R>"
    return discord.Embed(
        title=session["question"],
        description=f"{desc}\nEnds {ends}",
        color=0xffffff
    )

async def handle_vote(interaction, session, option_index):
    user_id = str(interaction.user.id)
    vote_map = session.setdefault("vote_map", {})
    user_choices = set(vote_map.get(user_id, []))
    multi_select = session.get("multi", False)
    if option_index in user_choices:
        user_choices.remove(option_index)
        message = f"Removed vote from option {option_index + 1}."
    else:
        if not multi_select:
            user_choices = {option_index}
        else:
            user_choices.add(option_index)
        message = f"Voted for option {option_index + 1}."
    vote_map[user_id] = list(user_choices)
    votes.update_one(
        {"_id": interaction.message.id},
        {"$set": {"vote_map": vote_map}}
    )
    await interaction.followup.send(message, ephemeral=True)
    return vote_map

vote = app_commands.Group(name="vote", description="Vote.")
bot.tree.add_command(vote)

@vote.command(name="create", description="Create a new vote.")
async def vote_create(
    interaction: discord.Interaction,
    question: app_commands.Range[str, 1, 240],
    duration: str,
    multi: bool = False,
    option1: str = None,
    option2: str = None,
    option3: str = None,
    option4: str = None,
    option5: str = None,
    option6: str = None,
    option7: str = None,
    option8: str = None,
    option9: str = None,
    option10: str = None
):
    await interaction.response.defer()
    options = [o for o in [
        option1, option2, option3, option4, option5,
        option6, option7, option8, option9, option10
    ] if o]
    if not options:
        return await interaction.followup.send("No options provided.", ephemeral=True)
    duration = parse_duration(duration)
    if not duration:
        return await interaction.followup.send("Invalid duration.", ephemeral=True)
    ends_at = int(time.time()) + duration
    session = {
        "channel_id": interaction.channel.id,
        "question": question,
        "options": options,
        "multi": multi,
        "ends_at": ends_at,
        "vote_map": {}
    }
    embed = build_vote_embed(session)
    msg = await interaction.followup.send(
        embed=embed,
        view=VoteView(len(options))
    )
    votes.update_one(
        {"_id": msg.id},
        {
            "$set": {
                "channel_id": interaction.channel.id,
                "question": question,
                "options": options,
                "multi": multi,
                "ends_at": ends_at,
                "vote_map": {}
            }
        },
        upsert=True
    )

class VoteView(discord.ui.View):
    def __init__(self, option_count: int):
        super().__init__(timeout=None)
        for i in range(option_count):
            self.add_item(VoteButton(i))

class VoteButton(discord.ui.Button):
    def __init__(self, index: int):
        super().__init__(
            label=str(index + 1),
            style=discord.ButtonStyle.primary,
            custom_id=f"vote:{index}"
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        session = votes.find_one({"_id": interaction.message.id})
        if not session:
            return
        vote_map = await handle_vote(interaction, session, self.index)
        session["vote_map"] = vote_map
        queue_message_update(
            interaction.message.id,
            {
                "message": interaction.message,
                "embed": build_vote_embed(session)
            }
        )

def build_final_results(session):
    options = session["options"]
    vote_map = session.get("vote_map", {})
    counts = [0] * len(options)
    for user_votes in vote_map.values():
        for i in user_votes:
            if i < len(counts):
                counts[i] += 1
    ranked = sorted(
        enumerate(options),
        key=lambda x: counts[x[0]],
        reverse=True
    )
    desc = ""
    for i, (idx, opt) in enumerate(ranked, start=1):
        desc += f"{i}ㆍ　{opt}　–　**{counts[idx]}** votes\n"
    return discord.Embed(
        title=f"Final Results: {session['question']}",
        description=desc,
        color=0xffffff
    )

@tasks.loop(seconds=10)
async def vote_auto_close_loop():
    now = int(time.time())
    for session in votes.find({"ends_at": {"$lte": now}}):
        try:
            channel = bot.get_channel(session["channel_id"])
            if not channel:
                continue
            message = await channel.fetch_message(session["_id"])
            if not message.components:
                continue
            results = build_final_results(session)
            await message.edit(embed=results, view=None)
            await message.reply("**Vote has ended.**")
            votes.update_one(
                {"_id": session["_id"]},
                {"$set": {"closed": True}}
            )
        except Exception:
            continue

@tasks.loop(minutes=5)
async def vote_cleanup_loop():
    now = int(time.time())
    one_hour_ago = now - 3600
    votes.delete_many({
        "closed": True,
        "closed_at": {"$lte": one_hour_ago}
    })


role = app_commands.Group(name="role", description="Manage roles.")
bot.tree.add_command(role)

@role.command(name="massadd", description="Adds a role to multiple users.")
@app_commands.describe(role="Role to add", users="Users or IDs (separate with a space)")
@app_commands.default_permissions(manage_roles=True)
async def role_massadd(interaction: discord.Interaction, role: discord.Role, users: str):
    await interaction.response.defer()
    guild = interaction.guild
    bot_member = guild.me
    if role.position >= bot_member.top_role.position:
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.")
        return
    ids = re.findall(r"\d+", users)
    if not ids:
        await interaction.followup.send("No valid users provided.")
        return
    success = 0
    failed = 0
    failed_ids = []
    for uid in ids:
        member = guild.get_member(int(uid))
        if not member:
            failed += 1
            failed_ids.append(uid)
            continue
        if member.bot:
            failed += 1
            failed_ids.append(uid)
            continue
        try:
            await member.add_roles(role)
            success += 1
        except discord.Forbidden:
            failed += 1
            failed_ids.append(uid)
        except Exception:
            failed += 1
            failed_ids.append(uid)
    await interaction.followup.send(f"Added {role.mention} to **{success}** users. Failed: `{"` `".join(failed_ids)}`" if failed_ids else f"Added {role.mention} to **{success}** users.")

mass = app_commands.Group(name="mass", description="Mass do something.")
bot.tree.add_command(mass)

@mass.command(name="delete", description="Delete messages between two message IDs.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(start='start message ID or "oldest"', end="end message ID")
async def mass_delete(interaction: discord.Interaction, start: str, end: str):
    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    try:
        end_msg = await channel.fetch_message(int(end))
    except discord.NotFound:
        return await interaction.followup.send("End message not found.", ephemeral=True)
    start_msg = None
    if start.lower() == "oldest":
        after = discord.utils.MISSING
    else:
        try:
            start_msg = await channel.fetch_message(int(start))
        except discord.NotFound:
            return await interaction.followup.send("Start message not found.", ephemeral=True)
        except ValueError:
            return await interaction.followup.send("Invalid start message ID.", ephemeral=True)
        after = start_msg
    if start_msg:
        if start_msg.created_at > end_msg.created_at:
            return await interaction.followup.send("Invalid range: start must be earlier than end.", ephemeral=True)
    progress = await interaction.followup.send("Starting deletion... 0 messages deleted.", wait=True)
    count = 0
    async for msg in channel.history(limit=None, oldest_first=True, after=after, before=end_msg):
        try:
            await msg.delete()
            count += 1
            if count % 5 == 0:
                await progress.edit(content=f"Deleting... **{count}** messages deleted.")
        except discord.HTTPException:
            pass
    await progress.edit(content=f"Done. Deleted **{count}** messages.")

@bot.tree.command(name="say", description="KAFU will speak on your behalf.")
@app_commands.checks.cooldown(1, 3)
@app_commands.describe(message="Your message")
async def anon_say(interaction: discord.Interaction, message: str):
    message = message.replace("\\n", "\n")
    try:
        await interaction.response.send_message(message, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False))
    except Exception as e:
        await interaction.response.send_message(f"Unable to send message: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Bans a user.")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: str, reason: Optional[str], image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except ValueError:
        await interaction.followup.send("Please provide a valid user or user ID.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("User not found.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.followup.send("An error occurred while fetching the user.", ephemeral=True)
        return
    if user == interaction.user:
        await interaction.followup.send("You cannot ban yourself!", ephemeral=True)
        return
    try: member = await interaction.guild.fetch_member(user.id)
    except discord.NotFound: pass
    else:
        if member and interaction.user.top_role <= member.top_role:
            await interaction.followup.send("You cannot ban a user with an equal or higher role than yourself.",
                                                ephemeral=True)
            return
    if reason is None:
        reason = "No reason specified."
    #
    if interaction.user.guild_permissions.ban_members:
        await interaction.followup.send(
            embed=discord.Embed(description=f'{user.mention} `{user.id}` has been banned. Reason: {reason}'))
        try:
            await user.send(f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
        except discord.Forbidden:
            pass
        await interaction.guild.ban(user, reason=reason, delete_message_seconds=604800)
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.")
                return
            bans_warns_channel = server_info.get("bans_warns_channel")
            bans_warns_channel = bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", "")))
            try:
                images = [img for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                          img is not None]
                files_to_send = []
                async with aiohttp.ClientSession() as session:
                    for img in images:
                        if img.content_type and img.content_type.startswith('image/'):
                            async with session.get(img.url) as resp:
                                if resp.status == 200:
                                    data = io.BytesIO(await resp.read())
                                    files_to_send.append(discord.File(data, filename=img.filename))
                if files_to_send:
                    await bans_warns_channel.send(
                        content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}\nㆍ　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one_and_update(
            {"_id": str(interaction.guild.id)},
            {"$setOnInsert": {"_id": str(interaction.guild.id)}},
            upsert=True,
            return_document=True
        )
        if not server_info.get("staff_role"):
            await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
            return
        if not server_info.get("bans_warns_channel"):
            await interaction.followup.send("**bans warns channel** has not been set up for this server.", ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        ban_perms = server_info.get("ban_perms")
        bans_warns_channel = server_info.get("bans_warns_channel")
        server_info.setdefault("bans_warns_req", {})
        if get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
            if str(user.id) in server_info["bans_warns_req"]:
                await interaction.followup.send(f"There already exists a ban/unban request on `{user.id}`: [Jump]({server_info["bans_warns_req"][str(user.id)][2]}).")
            else:
                try:
                    images = [img for img in
                              [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                              img is not None]
                    files_to_send = []
                    async with aiohttp.ClientSession() as session:
                        for img in images:
                            if img.content_type and img.content_type.startswith('image/'):
                                async with session.get(img.url) as resp:
                                    if resp.status == 200:
                                        data = io.BytesIO(await resp.read())
                                        files_to_send.append(discord.File(data, filename=img.filename))
                    if files_to_send:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=BanReqView())
                    else:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=BanReqView())
                except Exception:
                    if ban_perms:
                        ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                            content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    else:
                        ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                            content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
                await interaction.followup.send(f"A ban request has been sent: [Jump]({ban_req.jump_url})",
                                                        ephemeral=True)
                server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id), str(ban_req.jump_url)]
                server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                servers.replace_one(server_query, server_info)
@ban.error
async def ban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

class BanReqView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept")
    async def accept_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                user = await bot.fetch_user(int(user_id.replace("<@", "").replace(">", "")))
                try:
                    await user.send(
                        f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
                except discord.Forbidden:
                    pass
                await interaction.guild.ban(user, reason=reason, delete_message_seconds=604800)
                await interaction.response.edit_message(
                    content=f"**Ban Accepted**\nㆍ　User ID: {user_id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {requested_by}\nㆍ　Accepted by: {interaction.user.id}\nㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                await interaction.followup.send(f"Ban request accepted.", ephemeral=True)
                try:
                    server_info.get("staff").get(requested_by)["monthly"] = server_info.get("staff").get(requested_by).get(
                        "monthly", 0) + 1
                    server_info.get("staff").get(requested_by)["alltime"] = server_info.get("staff").get(requested_by).get(
                        "alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to <@{requested_by}>.", ephemeral=True)
                try:
                    server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("monthly", 0) + 1
                    server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
                servers.replace_one(server_query, server_info)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="reject")
    async def reject_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                await interaction.response.edit_message(
                    content=f"> **Ban Rejected**\n> ㆍ　User ID: {user_id}\n> ㆍ　Reason: {reason}\n> ㆍ　Requested by: {requested_by}\n> ㆍ　Rejected by: {interaction.user.id}\n> ㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"Ban request rejected.", ephemeral=True)

@bot.tree.command(name="unban", description="Unbans a user.")
@app_commands.describe(user="User to unban", reason="Reason for unban")
async def unban(interaction: discord.Interaction, user: str, reason: Optional[str], image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except ValueError:
        await interaction.followup.send("Please provide a valid user or user ID.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("User not found.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.followup.send("An error occurred while fetching the user.", ephemeral=True)
        return
    if user == interaction.user:
        await interaction.followup.send("You cannot unban yourself!", ephemeral=True)
        return
    if reason is None:
        reason = "No reason specified"
    banned_users = []
    async for ban_entry in interaction.guild.bans():
        banned_users.append(ban_entry.user)
    if user not in banned_users:
        await interaction.response.send_message(f"{user.mention} is not currently banned.", ephemeral=True)
        return
    if interaction.user.guild_permissions.ban_members:
        await interaction.guild.unban(user, reason=reason)
        await interaction.followup.send(embed=discord.Embed(description=
            f"Successfully unbanned {user.mention} `{user.id}`. Reason: {reason}"))
        try:
            await user.send(f"You have been unbanned from {interaction.guild.name} for the following reason: {reason}")
        except discord.Forbidden:
            pass
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.")
                return
            bans_warns_channel = server_info.get("bans_warns_channel")
            bans_warns_channel = bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", "")))
            try:
                images = [img for img in
                          [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                          img is not None]
                files_to_send = []
                async with aiohttp.ClientSession() as session:
                    for img in images:
                        if img.content_type and img.content_type.startswith('image/'):
                            async with session.get(img.url) as resp:
                                if resp.status == 200:
                                    data = io.BytesIO(await resp.read())
                                    files_to_send.append(discord.File(data, filename=img.filename))
                if files_to_send:
                    await bans_warns_channel.send(
                        content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}\nㆍ　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.",
                                                ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one_and_update(
            {"_id": str(interaction.guild.id)},
            {"$setOnInsert": {"_id": str(interaction.guild.id)}},
            upsert=True,
            return_document=True
        )
        if not server_info.get("staff_role"):
            await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
            return
        if not server_info.get("bans_warns_channel"):
            await interaction.followup.send("**bans warns channel** has not been set up for this server.",
                                            ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        ban_perms = server_info.get("ban_perms")
        bans_warns_channel = server_info.get("bans_warns_channel")
        server_info.setdefault("bans_warns_req", {})
        if get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
            if str(user.id) in server_info["bans_warns_req"]:
                await interaction.followup.send(
                    f"There already exists a ban/unban request on `{user.id}`: [Jump]({server_info["bans_warns_req"][str(user.id)][2]}).")
            else:
                try:
                    images = [img for img in
                              [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                              img is not None]
                    files_to_send = []
                    async with aiohttp.ClientSession() as session:
                        for img in images:
                            if img.content_type and img.content_type.startswith('image/'):
                                async with session.get(img.url) as resp:
                                    if resp.status == 200:
                                        data = io.BytesIO(await resp.read())
                                        files_to_send.append(discord.File(data, filename=img.filename))
                    if files_to_send:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=UnbanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=UnbanReqView())
                    else:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=UnbanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                                content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=UnbanReqView())
                except Exception:
                    if ban_perms:
                        ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                            content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    else:
                        ban_req = await bot.get_channel(int(bans_warns_channel.replace("<#", "").replace(">", ""))).send(
                            content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    await interaction.followup.send(f"Unable to send unban log images.", ephemeral=True)
                await interaction.followup.send(f"An unban request has been sent: [Jump]({ban_req.jump_url})",
                                                ephemeral=True)
                server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id),
                                                               str(ban_req.jump_url)]
                server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                servers.replace_one(server_query, server_info)

@unban.error
async def unban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

class UnbanReqView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept")
    async def accept_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                user = await bot.fetch_user(int(user_id.replace("<@", "").replace(">", "")))
                await interaction.guild.unban(user, reason=reason)
                await interaction.followup.send(embed=discord.Embed(description=
                                                                    f"Successfully unbanned {user.mention} `{user.id}`. Reason: {reason}"))
                try:
                    await user.send(
                        f"You have been unbanned from {interaction.guild.name} for the following reason: {reason}")
                except discord.Forbidden:
                    pass
                await interaction.response.edit_message(
                    content=f"**Unban Accepted**\nㆍ　User ID: {user_id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {requested_by}\nㆍ　Accepted by: {interaction.user.id}\nㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                await interaction.followup.send(f"Unban request accepted.", ephemeral=True)
                try:
                    server_info.get("staff").get(requested_by)["monthly"] = server_info.get("staff").get(requested_by).get(
                        "monthly", 0) + 1
                    server_info.get("staff").get(requested_by)["alltime"] = server_info.get("staff").get(requested_by).get(
                        "alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to <@{requested_by}>.", ephemeral=True)
                try:
                    server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("monthly", 0) + 1
                    server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
                servers.replace_one(server_query, server_info)
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="reject")
    async def reject_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                await interaction.response.edit_message(
                    content=f"> **Unban Rejected**\n> ㆍ　User ID: {user_id}\n> ㆍ　Reason: {reason}\n> ㆍ　Requested by: {requested_by}\n> ㆍ　Rejected by: {interaction.user.id}\n> ㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"Unban request rejected.", ephemeral=True)

#

"""@bot.tree.command(name="whitelist")
@app_commands.describe(server="Server invite")
@app_commands.checks.has_permissions(administrator=True)
async def whitelist(interaction: discord.Interaction, server: str):
    if interaction.user.id == yuelyxia:
        try:
            invite = await bot.fetch_invite(server)
        except discord.NotFound:
            await interaction.response.send_message("The invite link is **invalid** or **expired**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Unable to access details of invite.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        else:
            guild_id = invite.guild.id
            server_query = {"_id": str(guild_id)}
            server_info = servers.find_one(server_query)
            if server_info:
                await interaction.response.send_message(f"`{guild_id}` is already whitelisted.")
            else:
                server_info = {
                    "_id": str(guild_id),
                }
                servers.insert_one(server_info)
                await interaction.response.send_message(f"`{guild_id}` has been whitelisted.")"""

@bot.tree.command(name="break", description="Toggle staff/mm/pilot break.")
async def break_command(interaction: discord.Interaction, category: Literal["staff", "mm", "pilot"]):
    await interaction.response.defer()
    if interaction.guild.id == TRI_Archive:
        return await interaction.followup.send("This command cannot be used in this server.")
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_break = server_info.get("staff_break")
    mm_break = server_info.get("mm_break")
    pilot_break = server_info.get("pilot_break")
    staff_ping = server_info.get("staff_ping")
    mm_ping = server_info.get("mm_ping")
    pilot_ping = server_info.get("pilot_ping")
    uid = str(interaction.user.id)
    if category == "staff":
        if staff_break:
            if uid in server_info.get("staff", {}):
                if get(interaction.user.guild.roles, id=int(staff_break.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(staff_break.replace("<@&", "").replace(">", ""))))
                    if staff_ping: await interaction.user.add_roles(interaction.guild.get_role(int(staff_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been unroled **staff break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(staff_break.replace("<@&", "").replace(">", ""))))
                    if staff_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(staff_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been roled **staff break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**staff break** has not been set up for this server.")
    if category == "mm":
        if mm_break:
            if uid in server_info.get("mms", {}):
                if get(interaction.user.guild.roles, id=int(mm_break.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(mm_break.replace("<@&", "").replace(">", ""))))
                    if mm_ping: await interaction.user.add_roles(interaction.guild.get_role(int(mm_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been unroled **mm break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(mm_break.replace("<@&", "").replace(">", ""))))
                    if mm_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(mm_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been roled **mm break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**mm break** has not been set up for this server.")
    if category == "pilot":
        if pilot_break:
            if uid in server_info.get("pilots", {}):
                if get(interaction.user.guild.roles, id=int(pilot_break.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(pilot_break.replace("<@&", "").replace(">", ""))))
                    if pilot_ping: await interaction.user.add_roles(interaction.guild.get_role(int(pilot_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been unroled **pilot break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(pilot_break.replace("<@&", "").replace(">", ""))))
                    if pilot_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(pilot_ping.replace("<@&", "").replace(">", ""))))
                    await interaction.followup.send(f"You have been roled **pilot break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**staff break** has not been set up for this server.")

def is_int(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

appoint = app_commands.Group(name="appoint", description="Appoint a staff/mm/pilot.")
bot.tree.add_command(appoint)

@appoint.command(name="staff", description="Appoint a staff.")
@app_commands.describe(user="User/role to appoint as staff", role="Staff role to assign.")
async def appoint_staff(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if staff_role and not get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.replace("<@&", "").replace(">", "")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to staff.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("staff", {})
                server_info["staff"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to staff.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.followup.send(f"Unauthorised.", ephemeral=True)
            return
        server_info.setdefault("staff", {})
        server_info["staff"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to staff.")
        staff_role = server_info.get("staff_role")
        if staff_role: await member.add_roles(interaction.guild.get_role(int(staff_role.replace("<@&", "").replace(">", ""))))
        staff_ping = server_info.get("staff_ping")
        if staff_ping: await member.add_roles(interaction.guild.get_role(int(staff_ping.replace("<@&", "").replace(">", ""))))
        if role is not None and server_info.get("staff_roles"):
            staff_roles = server_info["staff_roles"].split()
            if str(role.mention) in staff_roles:
                for r in staff_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.replace("<@&", "").replace(">", ""))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.",
                                                ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**staff roles** have not been set up.", ephemeral=True)

@appoint.command(name="mm", description="Appoint a mm.")
@app_commands.describe(user="User/role to appoint as mm", role="mm role to assign.")
async def appoint_mm(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.replace("<@&", "").replace(">", "")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to mms.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("mms", {})
                server_info["mms"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to mms.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        server_info.setdefault("mms", {})
        server_info["mms"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to mms.")
        mm_role = server_info.get("mm_role")
        if mm_role: await member.add_roles(interaction.guild.get_role(int(mm_role.replace("<@&", "").replace(">", ""))))
        mm_ping = server_info.get("mm_ping")
        if mm_ping: await member.add_roles(interaction.guild.get_role(int(mm_ping.replace("<@&", "").replace(">", ""))))
        if role is not None and server_info.get("mm_roles"):
            mm_roles = server_info["mm_roles"].split()
            if str(role.mention) in mm_roles:
                for r in mm_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.replace("<@&", "").replace(">", ""))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.",
                                                ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**mm roles** have not been set up.", ephemeral=True)

@appoint.command(name="pilot", description="Appoint a pilot.")
@app_commands.describe(user="User/role to appoint as pilot", role="pilot role to assign.")
async def appoint_pilot(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.replace("<@&", "").replace(">", "")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to pilots.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("pilots", {})
                server_info["pilots"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to pilots.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        server_info.setdefault("pilots", {})
        server_info["pilots"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to pilots.")
        pilot_role = server_info.get("pilot_role")
        if pilot_role: await member.add_roles(interaction.guild.get_role(int(pilot_role.replace("<@&", "").replace(">", ""))))
        pilot_ping = server_info.get("pilot_ping")
        if pilot_ping: await member.add_roles(interaction.guild.get_role(int(pilot_ping.replace("<@&", "").replace(">", ""))))
        if role is not None and server_info.get("pilot_roles"):
            pilot_roles = server_info["pilot_roles"].split()
            if str(role.mention) in pilot_roles:
                for r in pilot_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.replace("<@&", "").replace(">", ""))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.", ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**pilot roles** have not been set up.", ephemeral=True)

@appoint.error
async def appoint_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    if isinstance(original, discord.Forbidden):
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.", ephemeral=True)
    else:
        await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

@bot.tree.command(name="dismiss", description="Dismiss staff/mm/pilot.")
@app_commands.describe(user="User to dismiss")
async def dismiss(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot"]):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.replace("<@&", "").replace(">", ""))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.replace("<@", "").replace(">", "")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.replace("<@&", "").replace(">", "")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Dismissing {len(role_members)} users from {category}.", ephemeral=True)
            #
            def parse_roles(raw):
                if not raw:
                    return []
                return raw.replace("<@&", "").replace(">", "").split()
            staff_roles = parse_roles(server_info.get("staff_roles"))
            staff_roles += parse_roles(server_info.get("staff_role"))
            staff_roles += parse_roles(server_info.get("staff_ping"))
            staff_roles += parse_roles(server_info.get("staff_break"))
            staff_roles += parse_roles(server_info.get("adm_ping"))
            staff_roles += parse_roles(server_info.get("ban_perms"))
            mm_roles = parse_roles(server_info.get("mm_roles"))
            mm_roles += parse_roles(server_info.get("mm_role"))
            mm_roles += parse_roles(server_info.get("mm_ping"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            mm_roles += parse_roles(server_info.get("mm_supervisor"))
            mm_roles += parse_roles(server_info.get("mm_trainer"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            pilot_roles = parse_roles(server_info.get("pilot_roles"))
            pilot_roles += parse_roles(server_info.get("pilot_role"))
            pilot_roles += parse_roles(server_info.get("pilot_ping"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            pilot_roles += parse_roles(server_info.get("pilot_supervisor"))
            pilot_roles += parse_roles(server_info.get("pilot_trainer"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            for m in role_members:
                uid = str(m.id)
                if category == "staff":
                    server_info.setdefault("staff", {}).pop(uid, None)
                    roles = staff_roles
                    await interaction.followup.send(f"`{uid}` has been dismissed from staff.")
                    still_staff = servers.find_one({
                        f"staff.{uid}": {"$exists": True}
                    })
                    if not still_staff:
                        timezones.delete_one({"_id": uid})
                elif category == "mm":
                    server_info.setdefault("mms", {}).pop(uid, None)
                    roles = mm_roles
                    await interaction.followup.send(f"`{uid}` has been dismissed from mms.")
                elif category == "pilot":
                    server_info.setdefault("pilots", {}).pop(uid, None)
                    roles = pilot_roles
                    await interaction.followup.send(f"`{uid}` has been dismissed from pilots.")
                # remove roles
                for role_id in roles:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        await m.remove_roles(role)
                still_mm = uid in server_info.get("mms", {})
                still_pilot = uid in server_info.get("pilots", {})
                if not still_mm and not still_pilot:
                    if "vouch_servers" in server_info and uid in server_info["vouch_servers"]:
                        del server_info["vouch_servers"][uid]
            servers.replace_one(server_query, server_info)
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot dismiss yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if category in ["staff", "mm", "pilot"]:
            def parse_roles(raw):
                if not raw:
                    return []
                return raw.replace("<@&", "").replace(">", "").split()
            staff_roles = parse_roles(server_info.get("staff_roles"))
            staff_roles += parse_roles(server_info.get("staff_role"))
            staff_roles += parse_roles(server_info.get("staff_ping"))
            staff_roles += parse_roles(server_info.get("staff_break"))
            staff_roles += parse_roles(server_info.get("adm_ping"))
            staff_roles += parse_roles(server_info.get("ban_perms"))
            mm_roles = parse_roles(server_info.get("mm_roles"))
            mm_roles += parse_roles(server_info.get("mm_role"))
            mm_roles += parse_roles(server_info.get("mm_ping"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            mm_roles += parse_roles(server_info.get("mm_supervisor"))
            mm_roles += parse_roles(server_info.get("mm_trainer"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            pilot_roles = parse_roles(server_info.get("pilot_roles"))
            pilot_roles += parse_roles(server_info.get("pilot_role"))
            pilot_roles += parse_roles(server_info.get("pilot_ping"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            pilot_roles += parse_roles(server_info.get("pilot_supervisor"))
            pilot_roles += parse_roles(server_info.get("pilot_trainer"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            if category == "staff":
                if not interaction.user.guild_permissions.manage_roles:
                    await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                    return
                server_info.setdefault("staff", {}).pop(str(user_id), None)
                roles = staff_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from staff.")
                still_staff = servers.find_one({
                    f"staff.{str(user_id)}": {"$exists": True}
                })
                if not still_staff:
                    timezones.delete_one({"_id": str(user_id)})
            elif category == "mm":
                server_info.setdefault("mms", {}).pop(str(user_id), None)
                roles = mm_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from mms.")
            elif category == "pilot":
                server_info.setdefault("pilots", {}).pop(str(user_id), None)
                roles = pilot_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from pilots.")
            # remove roles
            if member:
                for role_id in roles:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        await member.remove_roles(role)
            still_mm = str(user_id) in server_info.get("mms", {})
            still_pilot = str(user_id) in server_info.get("pilots", {})
            if not still_mm and not still_pilot:
                if "vouch_servers" in server_info and str(user_id) in server_info["vouch_servers"]:
                    del server_info["vouch_servers"][str(user_id)]
        servers.replace_one(server_query, server_info)

@dismiss.error
async def dismiss_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    if isinstance(original, discord.Forbidden):
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.", ephemeral=True)
    else:
        await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

@bot.tree.command(name="setup", description="Set up KAFU.")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, topic: Optional[Literal[
    "bans warns channel", "transcripts channel", "staff lb channel", "services lb channel", "revive ping",
    "staff roles", "staff role", "staff ping", "staff break", "adm ping", "ban perms",
    "mm roles", "mm role", "mm ping", "mm supervisor", "mm trainer", "mm break", "mm vouch channel",
    "pilot roles", "pilot role", "pilot ping", "pilot supervisor", "pilot trainer", "pilot break", "pilot vouch channel"
]]=None, input: Optional[str]=None):
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if topic is None:
        general_embed = discord.Embed(colour=0xffffff)
        general_embed.add_field(name="bans warns channel", value=server_info.get("bans_warns_channel", "unset"), inline=False) #
        general_embed.add_field(name="transcripts channel", value=server_info.get("transcripts_channel", "unset"), inline=False) #
        general_embed.add_field(name="staff lb channel", value=server_info.get("staff_lb_channel", "unset"), inline=False) #
        general_embed.add_field(name="services lb channel", value=server_info.get("services_lb_channel", "unset"), inline=False) #
        general_embed.add_field(name="revive ping", value=server_info.get("services_lb_channel", "unset"), inline=False)  #
        staff_embed = discord.Embed(colour=0xffffff)
        staff_embed.add_field(name="staff roles", value=server_info.get("staff_roles", "unset"), inline=False) #
        staff_embed.add_field(name="staff role", value=server_info.get("staff_role", "unset"), inline=False) #
        staff_embed.add_field(name="staff ping", value=server_info.get("staff_ping", "unset"), inline=False) #
        staff_embed.add_field(name="staff break", value=server_info.get("staff_break", "unset"), inline=False)  #
        staff_embed.add_field(name="adm ping", value=server_info.get("adm_ping", "unset"), inline=False) #
        staff_embed.add_field(name="ban perms", value=server_info.get("ban_perms", "unset"), inline=False)  #
        service_embed = discord.Embed(colour=0xffffff)
        service_embed.add_field(name="mm roles", value=server_info.get("mm_roles", "unset"), inline=False) #
        service_embed.add_field(name="mm role", value=server_info.get("mm_role", "unset"), inline=False) #
        service_embed.add_field(name="mm ping", value=server_info.get("mm_ping", "unset"), inline=False) #
        service_embed.add_field(name="mm supervisor", value=server_info.get("mm_supervisor", "unset"), inline=False) #
        service_embed.add_field(name="mm trainer", value=server_info.get("mm_trainer", "unset"), inline=False) #
        service_embed.add_field(name="mm break", value=server_info.get("mm_break", "unset"), inline=False) #
        service_embed.add_field(name="mm vouch channel", value=server_info.get("mm_vouch_channel", "unset"), inline=False)
        service_embed.add_field(name="pilot roles", value=server_info.get("pilot_roles", "unset"), inline=False) #
        service_embed.add_field(name="pilot role", value=server_info.get("pilot_role", "unset"), inline=False) #
        service_embed.add_field(name="pilot ping", value=server_info.get("pilot_ping", "unset"), inline=False) #
        service_embed.add_field(name="pilot supervisor", value=server_info.get("pilot_supervisor", "unset"), inline=False) #
        service_embed.add_field(name="pilot trainer", value=server_info.get("pilot_trainer", "unset"), inline=False) #
        service_embed.add_field(name="pilot break", value=server_info.get("pilot_break", "unset"), inline=False) #
        service_embed.add_field(name="pilot vouch channel", value=server_info.get("pilot_vouch_channel", "unset"), inline=False)
        embeds = [general_embed, staff_embed, service_embed]
        await interaction.response.send_message(embeds=embeds, ephemeral=True)
    if topic == "bans warns channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["bans_warns_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("The **bans warns channel** has been reset.")
            return
        try: bans_warns_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            bans_warns_channel = f"<#{bans_warns_channel.id}>"
            server_info["bans_warns_channel"] = bans_warns_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **bans warns channel** has been set to {bans_warns_channel}.")
    if topic == "transcripts channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["transcripts_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("The **transcripts channel** has been reset.")
            return
        try: transcripts_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            transcripts_channel = f"<#{transcripts_channel.id}>"
            server_info["transcripts_channel"] = transcripts_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **transcripts channel** has been set to {transcripts_channel}.")
    if topic == "staff lb channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["staff_lb_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("The **staff lb channel** has been reset.")
            return
        try: staff_lb_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            staff_lb_channel = f"<#{staff_lb_channel.id}>"
            server_info["staff_lb_channel"] = staff_lb_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **staff lb channel** has been set to {staff_lb_channel}.")
    if topic == "services lb channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["services_lb_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("The **services lb channel** has been reset.")
            return
        try:
            services_lb_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            services_lb_channel = f"<#{services_lb_channel.id}>"
            server_info["services_lb_channel"] = services_lb_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(
                f"The **services lb channel** has been set to {services_lb_channel}.")
    if topic == "revive ping" and input is not None:
        if input.strip().lower() == "none":
            server_info["revive_ping"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**revive ping** has been reset.")
            return
        revive_ping = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(revive_ping))
        if role:
            revive_ping = f"<@&{role.id}>"
            server_info["revive_ping"] = revive_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**revive ping** has been set to {revive_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff roles" and input is not None:
        if input.strip().lower() == "none":
            server_info["staff_roles"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**staff roles** have been reset.")
            return
        staff_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for staff_role in staff_roles:
            role = interaction.guild.get_role(int(staff_role))
            if role:
                valid_roles.append(staff_role)
        staff_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if staff_roles:
            server_info["staff_roles"] = staff_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff roles** have been set to {staff_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "staff role" and input is not None:
        if input.strip().lower() == "none":
            server_info["staff_role"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**staff role** has been reset.")
            return
        staff_role = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(staff_role))
        if role:
            staff_role = f"<@&{role.id}>"
            server_info["staff_role"] = staff_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff role** has been set to {staff_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff ping" and input is not None:
        if input.strip().lower() == "none":
            server_info["staff_ping"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**staff ping** has been reset.")
            return
        staff_ping = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(staff_ping))
        if role:
            staff_ping = f"<@&{role.id}>"
            server_info["staff_ping"] = staff_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff ping** has been set to {staff_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff break" and input is not None:
        if input.strip().lower() == "none":
            server_info["staff_break"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**staff break** has been reset.")
            return
        staff_break = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(staff_break))
        if role:
            staff_break = f"<@&{role.id}>"
            server_info["staff_break"] = staff_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff break** has been set to {staff_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "adm ping" and input is not None:
        if input.strip().lower() == "none":
            server_info["adm_ping"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**adm ping** has been reset.")
            return
        adm_ping = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(adm_ping))
        if role:
            adm_ping = f"<@&{role.id}>"
            server_info["adm_ping"] = adm_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**adm ping** has been set to {adm_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "ban perms" and input is not None:
        if input.strip().lower() == "none":
            server_info["ban_perms"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**ban perms** has been reset.")
            return
        ban_perms = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(ban_perms))
        if role:
            ban_perms = f"<@&{role.id}>"
            server_info["ban_perms"] = ban_perms
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**ban perms** has been set to {ban_perms}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm roles" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_roles"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm roles** have been reset.")
            return
        mm_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for mm_role in mm_roles:
            role = interaction.guild.get_role(int(mm_role))
            if role:
                valid_roles.append(mm_role)
        mm_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if mm_roles:
            server_info["mm_roles"] = mm_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm roles** have been set to {mm_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "mm role" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_role"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm role** has been reset.")
            return
        mm_role = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(mm_role))
        if role:
            mm_role = f"<@&{role.id}>"
            server_info["mm_role"] = mm_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm role** has been set to {mm_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm ping" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_ping"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm ping** has been reset.")
            return
        mm_ping = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(mm_ping))
        if role:
            mm_ping = f"<@&{role.id}>"
            server_info["mm_ping"] = mm_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm ping** has been set to {mm_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm supervisor" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_supervisor"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm supervisor** has been reset.")
            return
        mm_supervisor = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(mm_supervisor))
        if role:
            mm_supervisor = f"<@&{role.id}>"
            server_info["mm_supervisor"] = mm_supervisor
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm supervisor** has been set to {mm_supervisor}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm trainer" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_trainer"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm trainer** has been reset.")
            return
        mm_trainer = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(mm_trainer))
        if role:
            mm_trainer = f"<@&{role.id}>"
            server_info["mm_trainer"] = mm_trainer
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm trainer** has been set to {mm_trainer}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm break" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_break"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm break** has been reset.")
            return
        mm_break = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(mm_break))
        if role:
            mm_break = f"<@&{role.id}>"
            server_info["mm_break"] = mm_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm break** has been set to {mm_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm vouch channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["mm_vouch_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**mm vouch channel** has been reset.")
            return
        try:
            mm_vouch_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            mm_vouch_channel = f"<#{mm_vouch_channel.id}>"
            server_info["mm_vouch_channel"] = mm_vouch_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **mm vouch channel** has been set to {mm_vouch_channel}.")
    if topic == "pilot roles" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_roles"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot roles** have been reset.")
            return
        pilot_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for pilot_role in pilot_roles:
            role = interaction.guild.get_role(int(pilot_role))
            if role:
                valid_roles.append(pilot_role)
        pilot_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if pilot_roles:
            server_info["pilot_roles"] = pilot_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot roles** have been set to {pilot_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "pilot role" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_role"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot role** has been reset.")
            return
        pilot_role = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(pilot_role))
        if role:
            pilot_role = f"<@&{role.id}>"
            server_info["pilot_role"] = pilot_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot role** has been set to {pilot_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot ping" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_ping"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot ping** has been reset.")
            return
        pilot_ping = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(pilot_ping))
        if role:
            pilot_ping = f"<@&{role.id}>"
            server_info["pilot_ping"] = pilot_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot ping** has been set to {pilot_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot supervisor" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_supervisor"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot supervisor** has been reset.")
            return
        pilot_supervisor = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(pilot_supervisor))
        if role:
            pilot_supervisor = f"<@&{role.id}>"
            server_info["pilot_supervisor"] = pilot_supervisor
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot supervisor** has been set to {pilot_supervisor}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot trainer" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_trainer"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot trainer** has been reset.")
            return
        pilot_trainer = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(pilot_trainer))
        if role:
            pilot_trainer = f"<@&{role.id}>"
            server_info["pilot_trainer"] = pilot_trainer
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot trainer** has been set to {pilot_trainer}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot break" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_break"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot break** has been reset.")
            return
        pilot_break = input.replace("<@&", "").replace(">", "")
        role = interaction.guild.get_role(int(pilot_break))
        if role:
            pilot_break = f"<@&{role.id}>"
            server_info["pilot_break"] = pilot_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot break** has been set to {pilot_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot vouch channel" and input is not None:
        if input.strip().lower() == "none":
            server_info["pilot_vouch_channel"] = None
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message("**pilot vouch channel** has been reset.")
            return
        try:
            pilot_vouch_channel = await interaction.guild.fetch_channel(int(input.replace("<#", "").replace(">", "")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            pilot_vouch_channel = f"<#{pilot_vouch_channel.id}>"
            server_info["pilot_vouch_channel"] = pilot_vouch_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(
                f"The **pilot vouch channel** has been set to {pilot_vouch_channel}.")


# TRI


@bot.command(name="add")
async def add(ctx, mode: str = None, member: str = None):
    if get(ctx.guild.roles, id=ticket_ping) not in ctx.author.roles:
        return
    if mode and mode != "all":
        member = mode
        mode = None
    if not member:
        await ctx.reply("Please specify a user to add to tickets.")
        return
    try:
        member_obj = await commands.MemberConverter().convert(ctx, member)
    except commands.BadArgument:
        await ctx.reply("Could not find that user in this server. Make sure it's a valid mention or user ID.")
        return

    manager = getattr(bot, "ticket_manager", None)
    if not manager:
        await ctx.reply("Ticket manager is not initialized.")
        return

    if mode == "all":
        if not is_sr(ctx.author):
            await ctx.reply("Unauthorised.")
            return
        active_tickets = manager.tickets.find({"status": "open"})
        count = 0

        for ticket_doc in active_tickets:
            ticket_id = ticket_doc["_id"]
            manager.tickets.update_one(
                {"_id": ticket_id},
                {"$addToSet": {"allowed_users": member_obj.id}}
            )
            thread_id = ticket_doc.get("thread_id") or ticket_id
            thread = ctx.guild.get_thread(thread_id)
            if not thread:
                try:
                    thread = await ctx.guild.fetch_channel(thread_id)
                except discord.HTTPException:
                    thread = None
            if isinstance(thread, discord.Thread):
                try:
                    await thread.add_user(member_obj)
                    count += 1
                except discord.HTTPException:
                    pass
        embed = discord.Embed(colour=0xffffff, description=f"Successfully added {member_obj.mention} to {count} ticket threads.")
        await ctx.reply(embed=embed)
        return
    else:
        ticket = await manager.from_ticket(ctx.channel.id)
        if not ticket or ticket.data.get("status") != "open":
            await ctx.reply(
                "This command can only be used within an active ticket thread.")
            return
        manager.tickets.update_one(
            {"_id": ticket.id},
            {"$addToSet": {"allowed_users": member_obj.id}}
        )
        if isinstance(ctx.channel, discord.Thread):
            try:
                await ctx.channel.add_user(member_obj)
            except discord.HTTPException as e:
                await ctx.reply(f"Updated transcript permissions, but failed to add them to the thread: {e}")
                return
        embed = discord.Embed(colour=0xffffff, description=f"Added {member_obj.mention} to this ticket.")
        await ctx.reply(embed=embed)

@bot.command(name="remove")
async def remove(ctx, mode: str = None, target: str = None):
    if get(ctx.guild.roles, id=ticket_ping) not in ctx.author.roles:
        return
    if mode and mode != "all":
        target = mode
        mode = None
    if not target:
        await ctx.reply("Please specify a user or user ID to remove from tickets.")
        return
    try:
        member_obj = await commands.MemberConverter().convert(ctx, target)
    except commands.BadArgument:
        await ctx.reply("Could not find that user in this server. Make sure it's a valid mention or user ID.")
        return
    manager = getattr(bot, "ticket_manager", None)
    if not manager:
        await ctx.reply("Ticket manager is not initialized.")
        return
    if mode == "all":
        if not is_sr(ctx.author):
            await ctx.reply("Unauthorised.")
            return
        active_tickets = manager.tickets.find({"status": "open"})
        count = 0

        await ctx.reply(f"Removing {member_obj.mention} from all active ticket threads...")

        for ticket_doc in active_tickets:
            ticket_id = ticket_doc["_id"]

            manager.tickets.update_one(
                {"_id": ticket_id},
                {"$pull": {"allowed_users": member_obj.id}}
            )

            thread_id = ticket_doc.get("thread_id") or ticket_id
            thread = ctx.guild.get_thread(thread_id)
            if not thread:
                try:
                    thread = await ctx.guild.fetch_channel(thread_id)
                except discord.HTTPException:
                    thread = None

            if isinstance(thread, discord.Thread):
                try:
                    await thread.remove_user(member_obj)
                    count += 1
                except discord.HTTPException:
                    pass
        embed = discord.Embed(colour=0xffffff, description=f"Successfully removed {member_obj.mention} from {count} ticket threads.")
        await ctx.reply(embed=embed)
        return
    else:
        ticket = await manager.from_ticket(ctx.channel.id)
        if not ticket or ticket.data.get("status") != "open":
            await ctx.reply(
                "This command can only be used within an active ticket thread.")
            return
        manager.tickets.update_one(
            {"_id": ticket.id},
            {"$pull": {"allowed_users": member_obj.id}}
        )
        if isinstance(ctx.channel, discord.Thread):
            try:
                await ctx.channel.remove_user(member_obj)
            except discord.HTTPException as e:
                await ctx.reply(f"Revoked transcript permissions, but failed to remove them from the thread: {e}")
                return
        embed = discord.Embed(colour=0xffffff, description=f"Removed {member_obj.mention} from this ticket.")
        await ctx.reply(embed=embed)


@bot.tree.command(name="panel", description="Sends a ticket panel.")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    guild_id = interaction.guild.id
    if guild_id == TRI_Archive:
        await interaction.channel.send(embed=discord.Embed(colour=colour, description="""
## 　　<:2paperclip:1449650494044639335>　　┈　open ticket　✦୧
　<:whiteheartsmall:1462773852441677958>　provide __uncropped__ & **unedited** proofs
　<:whiteheartsmall:1462773852441677958>　fake proofs / disrespect = **ban**
　<:whiteheartsmall:1462773852441677958>　**do not open** for appeals on bans
-# _ _　 ✦ 　not following rules / ghosting = close
                """), view=TRITicketView())
        await interaction.followup.send("Panel has been sent.", ephemeral=True)

tri_ticket_options = [
    discord.SelectOption(emoji="<a:purplebow2:1522142135544184853>", label="ㆍㆍReport", value="report"),
    discord.SelectOption(emoji="<:pinkheart:1518434487007186994>", label="ㆍㆍAppeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍVerify", value="verify"),
    discord.SelectOption(emoji="<a:purple_flower:1515565233798778930>", label="ㆍㆍOthers", value="others"),
    ]

class TRITicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=tri_ticket_options, placeholder="‎　　Select a ticket type . . .　　　", custom_id="ticket",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if interaction.guild.id == TRI_Archive:
            if self.select_callback.values[0] == "report":
                await interaction.response.send_modal(ReportModal())
            elif self.select_callback.values[0] == "appeal":
                await interaction.response.send_modal(AppealModal())
            elif self.select_callback.values[0] == "verify":
                await interaction.response.send_modal(VerifyModal())
            elif self.select_callback.values[0] == "others":
                await interaction.response.send_modal(OthersModal())

async def create_ticket(
    interaction: discord.Interaction,
    *,
    ticket_type: str,
    embed: discord.Embed
):
    await interaction.response.defer()

    thread = await interaction.channel.create_thread(
        name=f"{ticket_type}-{interaction.user.name}",
        auto_archive_duration=10080,
        type=discord.ChannelType.private_thread
    )
    allowed_ids = [interaction.user.id]
    guild = interaction.guild
    ticket_ping_role = guild.get_role(int(ticket_ping))
    if ticket_ping_role:
        for member in ticket_ping_role.members:
            if not member.bot and member.id not in allowed_ids:
                allowed_ids.append(member.id)
    adm_ping_role = guild.get_role(int(adm_ping))
    if adm_ping_role:
        for member in adm_ping_role.members:
            if not member.bot and member.id not in allowed_ids:
                allowed_ids.append(member.id)
    try:
        ticket = await bot.ticket_manager.create(thread, interaction.user, ticket_type)
    except ValueError as e:
        return await interaction.followup.send(f"> {e}", ephemeral=True)
    ticket.data["allowed_users"] = allowed_ids
    await ticket.save()
    await interaction.followup.send(
        f"> Created new ticket: {thread.jump_url}",
        ephemeral=True
    )
    await thread.send(f"{interaction.user.mention} <@&{ticket_ping}>")
    await thread.send(embed=embed)

class ReportModal(discord.ui.Modal, title="ㆍㆍReport"):
    user_id = discord.ui.TextInput(
        label='ㆍㆍWho are you reporting?',
        style=discord.TextStyle.short,
        placeholder='User ID / Server Invite / Game UID',
    )
    game = discord.ui.TextInput(
        label='ㆍㆍGame?',
        style=discord.TextStyle.short,
        placeholder='N/A if not applicable',
    )
    anon = discord.ui.TextInput(
        label='ㆍㆍAnonymous?',
        style=discord.TextStyle.short,
        placeholder='Yes (Remain Anonymous) / No (Credit as Contributor)',
    )
    desc = discord.ui.TextInput(
        label='ㆍㆍBriefly describe the situation.',
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed=discord.Embed(colour=0xffffff, description=f"""
## ‎　　report　。。。ticket　ೀ　

-# **ㆍ　opened by** – {interaction.user.mention} `{interaction.user.id}`
-# **ㆍ　reporting** – <@{self.user_id.value}> `{self.user_id.value}`
-# **ㆍ　game** – {self.game.value}
-# **ㆍ　anonymous** – {self.anon.value}

**➴　 description**\n{self.desc.value}
        """)
        await create_ticket(
            interaction,
            ticket_type="report",
            embed=embed
        )

class AppealModal(discord.ui.Modal, title="ㆍㆍAppeal"):
    user_id = discord.ui.TextInput(
        label='ㆍㆍWho are you appealing?',
        style=discord.TextStyle.short,
        placeholder='Self / User ID',
    )
    desc = discord.ui.TextInput(
        label='ㆍㆍBriefly describe the situation.',
        style=discord.TextStyle.long,
    )
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=0xffffff, description=f"""
## ‎　　appeal　。。。ticket　ೀ　

-# **ㆍ　opened by** – {interaction.user.mention} `{interaction.user.id}`
-# **ㆍ　appealing** – <@{self.user_id.value}> `{self.user_id.value}`

**➴　 description**\n{self.desc.value}
""")
        await create_ticket(
            interaction,
            ticket_type="appeal",
            embed=embed
        )

class VerifyModal(discord.ui.Modal, title="ㆍㆍVerify"):
    desc = discord.ui.TextInput(
        label='ㆍㆍVerification issue?',
        style=discord.TextStyle.long,
        placeholder='Access Denied / VPN, explain if needed.',
    )
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=0xffffff, description=f"""
## ‎　　verify　。。。ticket　ೀ　

-# **ㆍ　opened by** – {interaction.user.mention} `{interaction.user.id}`

**➴　 description**\n{self.desc.value}
""")
        await create_ticket(
            interaction,
            ticket_type="verify",
            embed=embed
        )

class OthersModal(discord.ui.Modal, title="ㆍㆍOthers"):
    desc = discord.ui.TextInput(
        label='ㆍㆍReason for opening?',
        style=discord.TextStyle.long,
    )
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=0xffffff, description=f"""
## ‎　　others　。。。ticket　ೀ　

-# **ㆍ　opened by** – {interaction.user.mention} `{interaction.user.id}`

**➴　 description**\n{self.desc.value}
""")
        await create_ticket(
            interaction,
            ticket_type="others",
            embed=embed
        )

# logger

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ticket(self, thread_id: int):
        return await self.bot.ticket_manager.from_thread(thread_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.Thread):
            return
        ticket = await self.ticket(message.channel.id)
        if ticket is None:
            return
        await ticket.log_message(message)
        if ticket.data.get("status") == "closed":
            if message.channel.locked:
                return
            await self.bot.ticket_manager.reopen(ticket)
            await message.channel.send("**Ticket reopened.**")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not isinstance(after.channel, discord.Thread):
            return

        ticket = await self.ticket(after.channel.id)
        if ticket is None:
            return
        await ticket.edit_message(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not isinstance(message.channel, discord.Thread):
            return
        ticket = await self.ticket(message.channel.id)
        if ticket is None:
            return
        await ticket.delete_message(message)

    @commands.Cog.listener()
    async def on_thread_members_update(self, added_members: list[discord.ThreadMember], removed_members: list[discord.ThreadMember]):
        sample_member = added_members[0] if added_members else (removed_members[0] if removed_members else None)
        if not sample_member:
            return

        ticket = await self.ticket(sample_member.thread_id)
        if ticket is None:
            return
        updated = False
        for member in added_members:
            if member.id not in ticket.data["allowed_users"]:
                ticket.data["allowed_users"].append(member.id)
                updated = True
        for member in removed_members:
            if member.id == ticket.creator_id:
                continue

            if member.id in ticket.data["allowed_users"]:
                ticket.data["allowed_users"].remove(member.id)
                updated = True
        if updated:
            await ticket.save()

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        ticket = await self.ticket(after.id)
        if ticket is None:
            return

        if before.name != after.name:
            await ticket.manager.transcript.add_event(
                ticket.id,
                {
                    "type": "thread_rename",
                    "before": before.name,
                    "after": after.name,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc)
                }
            )


# exporter


class TranscriptExporter:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def parse_ansi(text: str) -> str:
        """Converts Discord ANSI color escapes inside code blocks into styled HTML."""
        if "\u001b[" not in text:
            return text

        ansi_map = {
            "30": "color: #4f545c;", "31": "color: #f04747;", "32": "color: #43b581;",
            "33": "color: #faa61a;", "34": "color: #7289da;", "35": "color: #eb459e;",
            "36": "color: #00b0f4;", "37": "color: #ffffff;", "40": "background-color: #1e1f22;",
            "41": "background-color: #f04747;", "42": "background-color: #43b581;",
            "1": "font-weight: bold;", "4": "text-decoration: underline;"
        }

        parts = text.split("\u001b[")
        result = [parts[0]]
        open_spans = 0

        for part in parts[1:]:
            if ";" in part or "m" in part:
                code_match = re.match(r"^([0-9;]+)m", part)
                if code_match:
                    codes = code_match.group(1).split(";")
                    text_content = part[len(code_match.group(0)):]

                    if "0" in codes:
                        result.append("</span>" * open_spans)
                        open_spans = 0

                    styles = [ansi_map[c] for c in codes if c in ansi_map]
                    if styles:
                        result.append(f"<span style='{'; '.join(styles)}'>")
                        open_spans += 1

                    result.append(text_content)
                    continue
            result.append("\u001b[" + part)

        result.append("</span>" * open_spans)
        return "".join(result)

    @classmethod
    def format_markdown(cls, text: str) -> str:
        text = html.escape(text)

        def code_block_sub(match):
            lang = match.group(1) or ""
            code_content = match.group(2)
            if lang.strip().lower() == "ansi":
                code_content = cls.parse_ansi(code_content)
            return f'<pre style="background: #202225; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; margin-top: 6px;">{code_content}</pre>'

        text = re.sub(r"```(\w*)\n([\s\S]*?)\n```", code_block_sub, text)
        text = re.sub(r"`([^`\n]+)`",
                      r'<code style="background: #202225; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
                      text)

        text = re.sub(r"^###\s+([\s\S]+?)$",
                      r'<h3 style="color: #fff; margin: 8px 0 4px 0; font-size: 1.15em;">\1</h3>', text,
                      flags=re.MULTILINE)
        text = re.sub(r"^##\s+([\s\S]+?)$", r'<h2 style="color: #fff; margin: 12px 0 6px 0; font-size: 1.4em;">\1</h2>',
                      text, flags=re.MULTILINE)
        text = re.sub(r"^#\s+([\s\S]+?)$", r'<h1 style="color: #fff; margin: 16px 0 8px 0; font-size: 1.75em;">\1</h1>',
                      text, flags=re.MULTILINE)
        text = re.sub(r"^-#\s+([\s\S]+?)$",
                      r'<span style="font-size: 0.82em; color: #72767d; display: block; margin: 2px 0;">\1</span>',
                      text, flags=re.MULTILINE)

        text = re.sub(r"\*\*([\s\S]+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*([\s\S]+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"__([\s\S]+?)__", r"<u>\1</u>", text)

        text = re.sub(r"^&gt;\s([\s\S]+?)$",
                      r'<blockquote style="border-left: 4px solid #4f545c; padding-left: 8px; margin: 4px 0; color: #b9bbbe;">\1</blockquote>',
                      text, flags=re.MULTILINE)

        return text.replace("\n", "<br>")

    async def export(self, ticket: dict, transcript: dict):
        messages = transcript.get("messages", [])
        events = transcript.get("events", [])

        raw_created = ticket.get("created_at")
        raw_closed = ticket.get("closed_at")

        if isinstance(raw_created, (int, float)):
            created_at = datetime.datetime.fromtimestamp(raw_created, datetime.timezone.utc).replace(tzinfo=None)
        elif isinstance(raw_created, str):
            try:
                created_at = datetime.datetime.strptime(raw_created.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                created_at = datetime.datetime.now()
        elif isinstance(raw_created, datetime.datetime):
            created_at = raw_created.replace(tzinfo=None)
        else:
            created_at = datetime.datetime.now()

        if isinstance(raw_closed, (int, float)):
            closed_at = datetime.datetime.fromtimestamp(raw_closed, datetime.timezone.utc).replace(tzinfo=None)
        elif isinstance(raw_closed, str):
            try:
                closed_at = datetime.datetime.strptime(raw_closed.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                closed_at = None
        elif isinstance(raw_closed, datetime.datetime):
            closed_at = raw_closed.replace(tzinfo=None)
        else:
            closed_at = None

        duration = None
        if closed_at:
            duration = (closed_at - created_at).total_seconds()


        exported = {
            "ticket": {
                "id": ticket["_id"],
                "guild_id": ticket["guild_id"],
                "thread_id": ticket["thread_id"],
                "thread_name": ticket["thread_name"],
                "creator_id": ticket["creator_id"],
                "type": ticket["type"],
                "status": ticket["status"],
                "claimed_by": ticket["claimed_by"],
                "created_at": created_at,
                "closed_by": ticket["closed_by"],
                "closed_at": closed_at,
                "open_duration": duration,
                "closing": ticket["closing"],
                "allowed_users": ticket["allowed_users"]
            },
            "statistics": ticket["statistics"],
            "messages": messages,
            "events": events,
            "exported_at": datetime.datetime.now(datetime.timezone.utc)
        }

        return exported

    async def to_html(self, exported_data: dict) -> str:
        ticket_info = exported_data["ticket"]
        messages = exported_data["messages"]

        guild_id = ticket_info.get("guild_id") or TRI_Archive
        guild = self.bot.get_guild(guild_id)

        async def resolve_mentions(text: str) -> str:
            if not text:
                return ""

            # Users
            for match in re.finditer(r"&lt;@!?(\d+)&gt;", text):
                u_id = match.group(1)
                u_id_int = int(u_id)
                user_obj = guild.get_member(u_id_int) if guild else None
                if not user_obj:
                    try:
                        user_obj = await guild.fetch_member(u_id_int) if guild else None
                    except discord.HTTPException:
                        pass
                if not user_obj:
                    user_obj = self.bot.get_user(u_id_int)
                    if not user_obj:
                        try:
                            user_obj = await self.bot.fetch_user(u_id_int)
                        except discord.HTTPException:
                            pass

                display_name = user_obj.display_name if user_obj else f"User ({u_id})"
                safe_html = f'<span class="mention-user">@{html.escape(display_name)}</span>'
                text = text.replace(match.group(0), safe_html)

            # Roles
            for match in re.finditer(r"&lt;@&amp;(\d+)&gt;", text):
                r_id = match.group(1)
                r_id_int = int(r_id)
                role_obj = guild.get_role(r_id_int) if guild else None
                if not role_obj:
                    for g in self.bot.guilds:
                        role_obj = g.get_role(r_id_int)
                        if role_obj: break
                role_name = role_obj.name if role_obj else f"Deleted Role"
                safe_html = f'<span class="mention-role">@{html.escape(role_name)}</span>'
                text = text.replace(match.group(0), safe_html)

            # Channels
            for match in re.finditer(r"&lt;#(\d+)&gt;", text):
                c_id = match.group(1)
                c_id_int = int(c_id)
                chan_obj = self.bot.get_channel(c_id_int)
                if not chan_obj:
                    try:
                        chan_obj = await self.bot.fetch_channel(c_id_int)
                    except discord.HTTPException:
                        pass
                chan_name = chan_obj.name if chan_obj else "deleted-channel"
                safe_html = f'<span class="mention-channel">#{html.escape(chan_name)}</span>'
                text = text.replace(match.group(0), safe_html)

            return text

        def process_discord_elements(text: str) -> str:
            if not text:
                return ""

            # Emojis
            emoji_pattern = r"(?:<|&lt;)(a?):([a-zA-Z0-9_]+):(\d+)(?:>|&gt;)"

            def emoji_replacer(match):
                is_animated = bool(match.group(1))
                name = match.group(2)
                emoji_id = match.group(3)
                ext = "gif" if is_animated else "png"
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
                return f'<img class="discord-emoji" src="{url}" alt=":{name}:" title=":{name}:" style="height: 1.375em; vertical-align: bottom; margin: 0 1px;">'

            text = re.sub(emoji_pattern, emoji_replacer, text)

            # Timestamps
            timestamp_pattern = r"(?:<|&lt;)t:(-?\d+)(?::([tTdDfFR]))?(?:>|&gt;)"

            def timestamp_replacer(match):
                epoch = int(match.group(1))
                flag = match.group(2) or "f"
                dt = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)

                if flag == "t":
                    display_str = dt.strftime("%I:%M %p")
                elif flag == "T":
                    display_str = dt.strftime("%I:%M:%S %p")
                elif flag == "d":
                    display_str = dt.strftime("%d/%m/%Y")
                elif flag == "D":
                    display_str = dt.strftime("%d %B %Y")
                elif flag == "F":
                    display_str = dt.strftime("%A, %d %B %Y %I:%M %p")
                elif flag == "R":
                    display_str = dt.strftime("%b %d, %Y %I:%M %p")
                else:
                    display_str = dt.strftime("%d %B %Y %I:%M %p")

                return f'<time class="discord-timestamp" datetime="{dt.isoformat()}" data-epoch="{epoch}" data-flag="{flag}">{display_str}</time>'

            return re.sub(timestamp_pattern, timestamp_replacer, text)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Transcript - Ticket #{ticket_info['id']}</title>
            <style>
                body {{ font-family: sans-serif; background: #36393f; color: #dcddde; padding: 20px; }}
                .ticket-header {{ border-bottom: 1px solid #4f545c; padding-bottom: 10px; margin-bottom: 20px; }}

                /* Layout structural updates */
                .message-wrapper {{ display: flex; margin-bottom: 15px; padding: 5px; padding-left: 10px; }}
                .avatar-container {{ margin-right: 12px; }}
                .avatar {{ width: 40px; height: 40px; border-radius: 50%; background: #2f3136; }}
                .message-body {{ flex: 1; }}

                .author {{ font-weight: bold; color: #fff; margin-right: 8px; }}
                .timestamp {{ font-size: 0.8em; color: #72767d; }}
                .content {{ margin-top: 4px; word-break: break-word; }}

                /* Styling to simulate real Discord mentions */
                .mention-user, .mention-role, .mention-channel {{
                    background: rgba(88, 101, 242, 0.3);
                    color: #dee0fc;
                    padding: 0 4px;
                    border-radius: 3px;
                    font-weight: 500;
                    font-family: inherit;
                }}
                .mention-user:hover, .mention-role:hover, .mention-channel:hover {{
                    background: #5865f2;
                    color: #fff;
                    cursor: pointer;
                }}
                
                /* Requested Element Formatting */
                .deleted {{ color: #f04747; background: rgba(240, 71, 71, 0.1); padding: 2px 5px; border-radius: 3px; }}
                .edited-tag {{ font-size: 0.75em; color: #72767d; margin-left: 4px; }}
                .edit-history {{ font-size: 0.8em; color: #b9bbbe; margin-top: 4px; font-style: italic; background: #2f3136; padding: 4px 8px; border-radius: 4px; display: inline-block; }}

                /* Attachments */
                .attachment-img {{ max-width: 400px; max-height: 300px; border-radius: 4px; margin-top: 8px; display: block; }}

                /* Rich Embed Layouts */
                .embed-block {{ background: #2f3136; border-left: 4px solid #1e1f22; border-radius: 4px; padding: 12px; margin-top: 8px; max-width: 520px; display: flex; flex-direction: column; gap: 6px; }}
                .embed-flex-wrapper {{ display: flex; justify-content: space-between; gap: 10px; }}
                .embed-content {{ flex: 1; }}
                .embed-title {{ font-weight: bold; color: #fff; font-size: 1em; margin-bottom: 4px; }}
                .embed-description {{ font-size: 0.9em; color: #dcddde; white-space: normal; word-break: break-word;}}
                .embed-thumbnail {{ width: 80px; height: 80px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }}
                .embed-image {{ max-width: 100%; border-radius: 4px; margin-top: 6px; }}
                .embed-footer {{ font-size: 0.75em; color: #72767d; margin-top: 4px; }}
            </style>
        </head>
        <body>
            <div class="ticket-header">
                <h1>Ticket #{ticket_info['id']} ({html.escape(ticket_info['thread_name'])})</h1>
                <p>Creator ID: {ticket_info['creator_id']} | Type: {ticket_info['type']}</p>
            </div>
            <div class="messages">
        """
        for msg in messages:
            author_data = msg.get("author", {})
            author_name = author_data.get("display_name", "Unknown User")
            avatar_base64 = author_data.get("avatar_base64")
            avatar_src = f"data:image/png;base64,{avatar_base64}" if avatar_base64 else "https://discord.com/assets/c09a43a372ba40e301147888bbd1d325.png"

            is_deleted = msg.get("is_deleted", False)
            content_class = "content deleted" if is_deleted else "content"

            raw_content = msg.get("content", "")
            content_text = TranscriptExporter.format_markdown(raw_content)
            content_text = await resolve_mentions(content_text)
            content_text = process_discord_elements(content_text)

            if is_deleted:
                content_text += " (deleted)"

            raw_msg_time = msg.get('created_at', '')
            if isinstance(raw_msg_time, datetime.datetime):
                msg_timestamp_str = raw_msg_time.strftime("%d %b %Y %I:%M %p")
            elif isinstance(raw_msg_time, (int, float)):
                msg_timestamp_str = datetime.datetime.fromtimestamp(raw_msg_time, datetime.timezone.utc).strftime(
                    "%d %b %Y %I:%M %p")
            else:
                msg_timestamp_str = str(raw_msg_time).split(".")[0]

            html_content += f"""
                            <div class="message-wrapper">
                                <div class="avatar-container">
                                    <img class="avatar" src="{avatar_src}" alt="Avatar">
                                </div>
                                <div class="message-body">
                                    <span class="author">{html.escape(author_name)}</span> 
                                    <span class="timestamp">{msg_timestamp_str}</span>
                        """
            edited_tag = '<span class="edited-tag">(edited)</span>' if msg.get("edited_at") else ''
            html_content += f'<div class="{content_class}">{content_text}{edited_tag}</div>'
            edit_history = msg.get("edit_history", [])
            if edit_history and not is_deleted:
                html_content += '<div class="edit-history-container">'
                for old_version in edit_history:
                    old_content = html.escape(old_version.get("content", ""))
                    html_content += f'<div class="edit-history">Before edit: "{old_content}"</div><br>'
                html_content += '</div>'

            for attach in msg.get("attachments", []):
                content_type = attach.get("content_type", "")
                is_video = attach.get("is_video", False)
                channel_id = attach.get("archive_channel")
                message_id = attach.get("archive_message")
                target_filename = attach.get("filename")

                url = None

                if channel_id and message_id:
                    try:
                        target_channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                            channel_id)
                        if target_channel:
                            live_msg = await target_channel.fetch_message(message_id)

                            for live_attach in live_msg.attachments:
                                if live_attach.filename == target_filename:
                                    url = live_attach.url
                                    if not content_type or content_type == "application/octet-stream":
                                        content_type = live_attach.content_type or ""
                                    break

                            if not url and live_msg.attachments:
                                url = live_msg.attachments[0].url
                                if not content_type or content_type == "application/octet-stream":
                                    content_type = live_msg.attachments[0].content_type or ""
                    except Exception as e:
                        print(f"Could not fetch live attachment link: {e}")

                if not url:
                    continue

                if "media.discordapp.net" in url:
                    url = url.replace("media.discordapp.net", "cdn.discordapp.com")

                filename_lower = target_filename.lower() if target_filename else ""
                if not is_video:
                    is_video = content_type.startswith("video/") or filename_lower.endswith(
                        ('.mp4', '.webm', '.mov', '.mkv', '.3gp'))

                if is_video:
                    if not content_type.startswith("video/") or content_type == "application/octet-stream":
                        if filename_lower.endswith('.webm'):
                            content_type = "video/webm"
                        elif filename_lower.endswith('.mov'):
                            content_type = "video/quicktime"
                        else:
                            content_type = "video/mp4"
                    html_content += f"""
                                            <div class="video-container" style="margin-top: 10px; margin-bottom: 10px;">
                                                <video class="attachment-video" controls preload="auto" crossorigin="anonymous" style="max-width: 500px; width: 100%; border-radius: 6px; background: #202225; display: block; border: 1px solid #2f3136;">
                                                    <source src="{url}" type="{content_type}">
                                                    Your browser does not support the video tag.
                                                </video>
                                                <span style="font-size: 0.75em; color: #72767d; display: block; margin-top: 4px; font-family: monospace;">
                                                    🎥 <a href="{url}" style="color: #7289da; text-decoration: none;" target="_blank">Download {html.escape(target_filename)}</a>
                                                </span>
                                            </div>
                                            """
                elif content_type.startswith("image/"):
                    html_content += f'<img class="attachment-img" src="{url}" alt="Attachment Image" style="max-width: 400px; max-height: 300px; border-radius: 4px; margin-top: 8px; display: block;">'

            embeds = msg.get("embeds", [])
            if embeds:
                html_content += '<div class="message-embeds-container" style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">'
                for embed in embeds:
                    if embed.get("type") in ["image", "link"] and not embed.get("title") and not embed.get(
                            "description"):
                        continue
                    color_hex = f"#{embed.get('color', 0):06x}" if embed.get('color') else "#1e1f22"
                    title = embed.get("title", "")

                    raw_description = embed.get("description", "")
                    description = TranscriptExporter.format_markdown(raw_description) if raw_description else ""
                    description = await resolve_mentions(description)
                    description = process_discord_elements(description)

                    thumbnail = embed.get("thumbnail", {}).get("url", "")
                    image = embed.get("image", {}).get("url", "")
                    footer_data = embed.get("footer", {})
                    footer_text = footer_data.get("text", "")
                    footer_icon = footer_data.get("icon_url", "")

                    html_content += f"""
                                    <div class="embed-block" style="border-left-color: {color_hex}; margin-top: 0;">
                                        <div class="embed-flex-wrapper">
                                            <div class="embed-content">
                                    """
                    if title:
                        html_content += f'<div class="embed-title">{html.escape(title)}</div>'
                    if description:
                        html_content += f'<div class="embed-description">{description}</div>'
                    fields = embed.get("fields", [])
                    if fields:
                        html_content += '<div class="embed-fields">'
                        for field in fields:
                            f_name = html.escape(field.get("name", ""))

                            # Process field formatting, mentions, and timestamps safely
                            raw_f_val = field.get("value", "")
                            f_val = TranscriptExporter.format_markdown(raw_f_val) if raw_f_val else ""
                            f_val = await resolve_mentions(f_val)
                            f_val = process_discord_elements(f_val)

                            inline_style = "display: inline-block; width: 30%;" if field.get(
                                "inline") else "width: 100%;"
                            html_content += f"""
                                            <div class="embed-field" style="{inline_style}">
                                                <div class="embed-field-name">{f_name}</div>
                                                <div class="embed-field-value">{f_val}</div>
                                            </div>
                                            """
                        html_content += '</div>'

                    html_content += '</div>'
                    if thumbnail:
                        html_content += f'<img class="embed-thumbnail" src="{thumbnail}" alt="Thumbnail">'
                    html_content += '</div>'
                    if image:
                        html_content += f'<img class="embed-image" src="{image}" alt="Embed Image">'
                    if footer_text:
                        html_content += '<div class="embed-footer" style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">'
                        if footer_icon:
                            html_content += f'<img src="{footer_icon}" alt="Footer Icon" style="width: 20px; height: 20px; border-radius: 50%; object-fit: cover;">'
                        html_content += f'<span style="font-size: 0.75em; color: #72767d;">{html.escape(footer_text)}</span>'
                        html_content += '</div>'
                    html_content += '</div>'
                html_content += '</div>'
            html_content += """
                    </div>
                </div>
            """
        html_content += "</div></body></html>"
        return html_content


# transcript

class TranscriptManager:

    def __init__(self, transcripts, archive):
        self.transcripts = transcripts
        self.archive = archive

    def _now(self):
        return datetime.datetime.now(datetime.timezone.utc)

    async def _author(self, user):
        avatar_base64 = None
        try:
            avatar = user.display_avatar.with_size(64)
            avatar_bytes = await avatar.read()
            avatar_base64 = base64.b64encode(avatar_bytes).decode("utf-8")
        except Exception as e:
            print(e)
        return {
            "id": user.id,
            "username": user.name,
            "display_name": user.display_name,
            "bot": user.bot,
            "avatar_base64": avatar_base64
        }

    async def _attachments(self, message):
        attachments = []

        for attachment in message.attachments:
            uploaded = await self.archive.upload_attachment(attachment)
            if uploaded is None:
                continue

            content_type = uploaded.get("content_type") or attachment.content_type or ""
            filename_lower = attachment.filename.lower()

            is_video = content_type.startswith("video/") or filename_lower.endswith(
                ('.mp4', '.webm', '.mov', '.mkv', '.3gp'))

            if is_video and not content_type.startswith("video/"):
                if filename_lower.endswith('.webm'):
                    content_type = "video/webm"
                elif filename_lower.endswith('.mov'):
                    content_type = "video/quicktime"
                else:
                    content_type = "video/mp4"

            attachments.append({
                "filename": attachment.filename,
                "content_type": content_type,
                "size": attachment.size,
                "archive_channel": uploaded["channel_id"],
                "archive_message": uploaded["message_id"],
                "is_video": is_video
            })
        return attachments

    async def _message(self, message):
        return {
            "message_id": message.id,
            "channel_id": message.channel.id,
            "message_type": message.type.name,
            "system": message.is_system(),
            "author": await self._author(message.author),
            "content": message.content,
            "reference": (
                message.reference.message_id
                if message.reference and message.reference.message_id
                else None
            ),
            "mentions": {
                "users": message.raw_mentions,
                "roles": message.raw_role_mentions,
                "channels": message.raw_channel_mentions,
            },
            "stickers": [{"id": s.id, "name": s.name} for s in message.stickers],
            "created_at": message.created_at,
            "edited_at": None,
            "deleted_at": None,
            "is_deleted": False,
            "edit_history": [],
            "attachments": await self._attachments(message),
            "embeds": [embed.to_dict() for embed in message.embeds]
        }

    async def create(self, ticket_id: int):
        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {
                "$setOnInsert": {
                    "messages": [],
                    "events": [],
                    "created_at": self._now(),
                    "closed": False,
                    "closed_at": None
                }
            },
            upsert=True
        )

    async def get(self, ticket_id: int):
        return await asyncio.to_thread(self.transcripts.find_one, {"_id": ticket_id})

    async def add_message(self, ticket_id: int, message):
        message_data = await self._message(message)
        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {"$push": {"messages": message_data}}
        )

    async def edit_message(self, ticket_id: int, before, after):
        now = self._now()
        update_payload = {
            "$set": {
                "messages.$[m].content": after.content,
                "messages.$[m].edited_at": now,
                "messages.$[m].embeds": [embed.to_dict() for embed in after.embeds]
            }
        }
        if not before.author.bot:
            author_data = await self._author(before.author)
            update_payload["$push"] = {
                "messages.$[m].edit_history": {
                    "content": before.content,
                    "edited_at": now
                },
                "events": {
                    "type": "message_edit",
                    "message_id": before.id,
                    "author": author_data,
                    "timestamp": now
                }
            }

        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            update_payload,
            array_filters=[{"m.message_id": before.id}]
        )


    async def delete_message(self, ticket_id: int, message):
        now = self._now()
        author_data = await self._author(message.author)

        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {
                "$set": {
                    "messages.$[m].is_deleted": True,
                    "messages.$[m].deleted_at": now
                },
                "$push": {
                    "events": {
                        "type": "message_delete",
                        "message_id": message.id,
                        "author": author_data,
                        "timestamp": now
                    }
                }
            },
            array_filters=[{"m.message_id": message.id}]
        )

    async def add_event(self, ticket_id: int, event: dict):
        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {"$push": {"events": event}}
        )

    async def finalise(self, ticket_id: int):
        now = self._now()

        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {
                "$set": {
                    "closed": True,
                    "closed_at": now
                },
                "$push": {
                    "events": {
                        "type": "ticket_closed",
                        "timestamp": now
                    }
                }
            }
        )
        return await self.get(ticket_id)

    async def reopen(self, ticket_id: int):
        now = self._now()

        await asyncio.to_thread(
            self.transcripts.update_one,
            {"_id": ticket_id},
            {
                "$set": {
                    "closed": False,
                    "closed_at": None
                },
                "$push": {
                    "events": {
                        "type": "ticket_reopened",
                        "timestamp": now
                    }
                }
            }
        )

# uploader

class ArchiveUploader:

    def __init__(self, bot, json_channel: int, attachment_channel: int):
        self.bot = bot
        self.json_channel = json_channel
        self.attachment_channel = attachment_channel

        self.attachment_cache = {}
        self.avatar_cache = {}

    def json_channel_obj(self):
        return self.bot.get_channel(self.json_channel)

    def attachment_channel_obj(self):
        return self.bot.get_channel(self.attachment_channel)

    async def upload_json(self, ticket_id: int, transcript: dict):
        channel = self.json_channel_obj()
        if channel is None:
            return None

        buffer = io.BytesIO(
            json.dumps(
                transcript,
                indent=4,
                default=str
            ).encode("utf-8")
        )

        file = discord.File(
            buffer,
            filename=f"ticket_{ticket_id}.json"
        )

        message = await channel.send(
            content=f"Ticket #{ticket_id}",
            file=file
        )

        return {
            "json_channel": channel.id,
            "json_message": message.id,
            "uploaded_at": datetime.datetime.now(datetime.timezone.utc)
        }

    async def upload_attachment(self, attachment):
        cached = self.attachment_cache.get(attachment.id)
        if cached:
            return cached

        channel = self.attachment_channel_obj()
        if channel is None:
            return None

        try:
            file = await attachment.to_file()
            message = await channel.send(file=file)
            uploaded = message.attachments[0]

            result = {
                "filename": uploaded.filename,
                "url": uploaded.url,
                "content_type": attachment.content_type,  # Ensure content_type is captured
                "message_id": message.id,
                "channel_id": channel.id
            }
            self.attachment_cache[attachment.id] = result
            return result
        except Exception as e:
            print(f"UPLOAD FAILED: {attachment.filename}")
            print(type(e), e)
            raise

    async def upload_avatar(self, user):
        cached = self.avatar_cache.get(user.id)
        if cached:
            return cached

        channel = self.attachment_channel_obj()
        if channel is None:
            return None

        try:
            file = await user.display_avatar.to_file()
            message = await channel.send(file=file)
            uploaded = message.attachments[0]

            result = {
                "url": uploaded.url,
                "message_id": message.id,
                "channel_id": channel.id
            }
            self.avatar_cache[user.id] = result
            return result
        except discord.HTTPException:
            return None

    async def upload_html(self, ticket_id: int, html_string: str):
        channel = self.attachment_channel_obj()
        if channel is None:
            return None

        buffer = io.BytesIO(html_string.encode("utf-8"))
        file = discord.File(buffer, filename=f"ticket_{ticket_id}.html")
        message = await channel.send(file=file)
        uploaded = message.attachments[0]

        return {
            "url": uploaded.url,
            "message_id": message.id,
            "channel_id": channel.id
        }

# ticket

class Ticket:

    def __init__(self, manager, data: dict):
        self.manager = manager
        self.data = data

        self.data.setdefault("statistics", {
            "messages": 0,
            "attachments": 0,
            "edits": 0,
            "deletions": 0
        })

    @property
    def id(self):
        return self.data["_id"]

    @property
    def guild_id(self):
        return self.data["guild_id"]

    @property
    def thread_id(self):
        return self.data["thread_id"]

    @property
    def thread_name(self):
        return self.data["thread_name"]

    @property
    def creator_id(self):
        return self.data["creator_id"]

    @property
    def status(self):
        return self.data["status"]

    @property
    def claimed_by(self):
        return self.data["claimed_by"]

    @property
    def allowed_users(self):
        return self.data["allowed_users"]

    @property
    def closing(self):
        return self.data["closing"]

    async def save(self):
        self.data["last_updated"] = datetime.datetime.now(datetime.timezone.utc)
        if inspect.iscoroutinefunction(self.manager.save):
            await self.manager.save(self)
        else:
            await asyncio.to_thread(self.manager.save, self)

    async def log_message(self, message):
        await self.manager.transcript.add_message(self.id, message)
        self.data["statistics"]["messages"] += 1
        self.data["statistics"]["attachments"] += len(message.attachments)
        await self.save()

    async def edit_message(self, before, after):
        await self.manager.transcript.edit_message(self.id, before, after)
        self.data["statistics"]["edits"] += 1
        await self.save()

    async def delete_message(self, message):
        await self.manager.transcript.delete_message(self.id, message)
        self.data["statistics"]["deletions"] += 1
        await self.save()

    async def claim(self, user_id: int):
        if user_id not in self.data["claimed_by"]:
            self.data["claimed_by"].append(user_id)
            await self.save()

    async def unclaim(self, user_id: int):
        if user_id in self.data["claimed_by"]:
            self.data["claimed_by"].remove(user_id)
            await self.save()

    def add_user(self, user_id: int):
        if user_id not in self.data["allowed_users"]:
            self.data["allowed_users"].append(user_id)

    def remove_user(self, user_id: int):
        if user_id in self.data["allowed_users"]:
            self.data["allowed_users"].remove(user_id)

    async def close(self, closed_by: int, closing: str):
        await self.manager.close(self, closed_by, closing)

    async def reopen(self):
        await self.manager.reopen(self)

# manager

class TicketManager:

    def __init__(self, bot, tickets, transcripts, json_channel: int, attachment_channel: int,
                 counters_collection):
        self.bot = bot
        self.tickets = tickets
        self.transcripts = transcripts
        self.counters = counters_collection
        self.archive = ArchiveUploader(bot, json_channel, attachment_channel)
        self.transcript = TranscriptManager(transcripts, self.archive)
        self.exporter = TranscriptExporter(bot=self.bot)

    async def _get_next_ticket_id(self) -> int:

        def db_op():
            result = self.counters.find_one_and_update(
                {"_id": "ticket_id"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True
            )
            return result["seq"]

        return await asyncio.to_thread(db_op)

    async def create(self, thread: discord.Thread, creator: discord.Member, ticket_type: str):
        def count_open():
            return self.tickets.count_documents({
                "creator_id": creator.id,
                "status": "open"
            })

        open_count = await asyncio.to_thread(count_open)
        if open_count >= 2:
            raise ValueError("You have reached the maximum limit of 2 active tickets.")

        ticket_id = await self._get_next_ticket_id()
        now = datetime.datetime.now(datetime.timezone.utc)

        document = {
            "_id": ticket_id,
            "guild_id": thread.guild.id,
            "thread_id": thread.id,
            "thread_name": thread.name,
            "type": ticket_type,
            "creator_id": creator.id,
            "claimed_by": [],
            "credited_users": [],
            "created_at": now,
            "closed_by": None,
            "closed_at": None,
            "closing": None,
            "status": "open",
            "allowed_users": [creator.id],
            "archive": {
                "json_channel": None,
                "json_message": None
            },
            "statistics": {
                "messages": 0,
                "attachments": 0,
                "edits": 0,
                "deletions": 0
            },
            "last_updated": now
        }

        await asyncio.to_thread(self.tickets.insert_one, document)
        await self.transcript.create(ticket_id)
        return Ticket(self, document)

    async def from_thread(self, thread_id: int):
        document = await asyncio.to_thread(self.tickets.find_one, {"thread_id": thread_id})
        if document is None:
            return None
        return Ticket(self, document)

    async def from_ticket(self, ticket_id: int):
        document = await asyncio.to_thread(self.tickets.find_one, {"_id": ticket_id})
        if document is None:
            return None
        return Ticket(self, document)

    async def save(self, ticket):
        await asyncio.to_thread(
            self.tickets.replace_one,
            {"_id": ticket.id},
            ticket.data
        )

    async def close(self, ticket, closed_by: int, closing: str):
        ticket.data["status"] = "closed"
        ticket.data["closed_by"] = closed_by
        ticket.data["closed_at"] = datetime.datetime.now(datetime.timezone.utc)
        ticket.data["closing"] = closing

        await self.transcript.finalise(ticket.id)
        fresh_transcript = await self.transcript.get(ticket.id)
        exported = await self.exporter.export(ticket.data, fresh_transcript)

        json_archive = await self.archive.upload_json(ticket.id, exported)
        if json_archive:
            ticket.data["archive"] = json_archive

        html_str = await self.exporter.to_html(exported)
        html_archive = await self.archive.upload_html(ticket.id, html_str)
        if html_archive:
            ticket.data["html_url"] = html_archive["url"]

        embed = discord.Embed(
            title=f"Ticket #{ticket.id} Closed",
            color=0xffffff,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if ticket.data.get("created_at"):
            created_val = ticket.data["created_at"]
            if isinstance(created_val, datetime.datetime):
                if created_val.tzinfo is None:
                    created_val = created_val.replace(tzinfo=datetime.timezone.utc)
                created_unix = int(created_val.timestamp())
            else:
                created_unix = int(created_val)
            created_str = f"<t:{created_unix}:F> (<t:{created_unix}:R>)"
        else:
            created_str = "Unknown"

        closed_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        closed_str = f"<t:{closed_unix}:F> (<t:{closed_unix}:R>)"


        claims = "None"
        try:
            global ticket_claims
            claims_doc = await asyncio.to_thread(ticket_claims.find_one, {"_id": ticket.thread_id})
            if claims_doc and claims_doc.get("claimed_by"):
                legacy_claims = claims_doc["claimed_by"]
                if isinstance(legacy_claims, list) and len(legacy_claims) > 0:
                    claims = " ".join([f"<@{u_id}>" for u_id in legacy_claims])
                    ticket.data["claimed_by"] = legacy_claims
                    await self.save(ticket)
        except Exception as e:
            print(f"Fallback check failed: {e}")

        if claims == "None":
            raw_claims = ticket.data.get("claimed_by", [])
            if isinstance(raw_claims, list) and len(raw_claims) > 0:
                claims = " ".join([f"<@{u_id}>" for u_id in raw_claims])

        embed.add_field(name="type", value=ticket.data["type"], inline=True)
        embed.add_field(name="claimed by", value=claims, inline=False)
        embed.add_field(name="closed by", value=f"<@{closed_by}>", inline=True)
        embed.add_field(name="created at", value=created_str, inline=False)
        embed.add_field(name="closed at", value=closed_str, inline=False)

        raw_duration = exported["ticket"].get("open_duration")
        if raw_duration is not None:
            seconds = int(raw_duration)
            days = seconds // 86400
            seconds %= 86400
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            duration_parts = []
            if days > 0:
                duration_parts.append(f"{days}d")
            if hours > 0 or days > 0:
                duration_parts.append(f"{hours}h")
            if minutes > 0 or hours > 0 or days > 0:
                duration_parts.append(f"{minutes}m")
            duration_value = " ".join(duration_parts)
        else:
            duration_value = "N/A"

        embed.add_field(name="duration", value=duration_value, inline=True)
        embed.add_field(name="closing", value=closing, inline=False)

        view = TranscriptView(ticket.data)

        transcript_channel = self.bot.get_channel(TRANSCRIPT_CHANNEL)
        if transcript_channel:
            msg = await transcript_channel.send(embed=embed, view=view)
            ticket.data["summary_message_id"] = msg.id
        try:
            creator = self.bot.get_user(ticket.creator_id) or await self.bot.fetch_user(ticket.creator_id)
            if creator:
                view = TranscriptDMView(ticket.data)
                dm_msg = await creator.send(embed=embed, view=view)
                ticket.data["dm_message_id"] = dm_msg.id
        except discord.HTTPException:
            print(f"Could not DM transcript summary to user {ticket.creator_id}")
            ticket.data["dm_message_id"] = None
        await self.save(ticket)

    async def reopen(self, ticket):
        ticket.data["status"] = "open"
        ticket.data["closed_by"] = None
        ticket.data["closed_at"] = None
        ticket.data["closing"] = None

        summary_id = ticket.data.get("summary_message_id")
        dm_id = ticket.data.get("dm_message_id")

        if summary_id:
            try:
                transcript_channel = self.bot.get_channel(TRANSCRIPT_CHANNEL) or await self.bot.fetch_channel(
                    TRANSCRIPT_CHANNEL)
                if transcript_channel:
                    try:
                        old_msg = await transcript_channel.fetch_message(summary_id)
                        if old_msg and old_msg.embeds:
                            for field in old_msg.embeds[0].fields:
                                if field.name.lower() == "claimed by" and field.value != "None":
                                    extracted_ids = [int(uid) for uid in re.findall(r'<@!?(\d+)>', field.value)]
                                    for uid in extracted_ids:
                                        if uid not in ticket.data.setdefault("claimed_by", []):
                                            ticket.data["claimed_by"].append(uid)
                                    break
                    except discord.NotFound:
                        pass
                    partial_msg = transcript_channel.get_partial_message(summary_id)
                    await partial_msg.delete()
            except Exception as delete_error:
                print(f"An error occurred while deleting channel summary: {delete_error}")
            ticket.data["summary_message_id"] = None

        if dm_id:
            try:
                creator = self.bot.get_user(ticket.creator_id) or await self.bot.fetch_user(ticket.creator_id)
                if creator:
                    dm_channel = creator.dm_channel or await creator.create_dm()
                    partial_dm = dm_channel.get_partial_message(dm_id)
                    await partial_dm.delete()
            except Exception as delete_error:
                print(f"An error occurred while deleting DM summary: {delete_error}")
            ticket.data["dm_message_id"] = None

        global ticket_claims
        await asyncio.to_thread(
            ticket_claims.update_one,
            {"_id": ticket.thread_id},
            {"$set": {"closed": False}}
        )

        await self.transcript.reopen(ticket.id)
        await self.save(ticket)


class TranscriptView(discord.ui.View):
    def __init__(self, ticket_data: dict):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data

        guild_id = ticket_data.get("guild_id")
        thread_id = ticket_data.get("thread_id")

        if guild_id and thread_id:
            thread_url = f"https://discord.com/channels/{guild_id}/{thread_id}"

            self.add_item(discord.ui.Button(
                label="thread",
                style=discord.ButtonStyle.link,
                url=thread_url
            ))

    @discord.ui.button(label="html", style=discord.ButtonStyle.blurple, custom_id="transcript:html")
    async def view_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        ticket_id = self.ticket_data.get("_id")
        manager = getattr(interaction.client, "ticket_manager", None)
        fresh_ticket = await manager.from_ticket(ticket_id) if manager else None
        data = fresh_ticket.data if fresh_ticket else self.ticket_data

        allowed_users = data.get("allowed_users", [])
        if interaction.user.id not in allowed_users:
            await interaction.followup.send("You do not have permission to view this transcript.", ephemeral=True)
            return

        html_url = data.get("html_url")
        if not html_url:
            await interaction.followup.send("HTML file could not be found.", ephemeral=True)
            return

        await interaction.followup.send(f"[Transcript here.]({html_url})", ephemeral=True)

    @discord.ui.button(
        label="edit closing",
        style=discord.ButtonStyle.gray,
        custom_id="transcript:editclosing",
        row=0
    )
    async def edit_closing(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_id = self.ticket_data.get("_id")
        fresh_ticket = await interaction.client.ticket_manager.from_ticket(ticket_id)
        data = fresh_ticket.data if fresh_ticket else self.ticket_data

        if not is_sr(interaction.user):
            await interaction.response.send_message("You cannot modify this close reason.", ephemeral=True)
            return

        await interaction.response.send_modal(EditClosingModal(data))


class TranscriptDMView(discord.ui.View):
    def __init__(self, ticket_data: dict):
        super().__init__(timeout=None)
        self.ticket_data = ticket_data

        guild_id = ticket_data.get("guild_id")
        thread_id = ticket_data.get("thread_id")

        if guild_id and thread_id:
            thread_url = f"https://discord.com/channels/{guild_id}/{thread_id}"

            self.add_item(discord.ui.Button(
                label="thread",
                style=discord.ButtonStyle.link,
                url=thread_url
            ))

    @discord.ui.button(label="html", style=discord.ButtonStyle.blurple, custom_id="transcriptdm:html")
    async def view_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        ticket_id = self.ticket_data.get("_id")
        manager = getattr(interaction.client, "ticket_manager", None)
        fresh_ticket = await manager.from_ticket(ticket_id) if manager else None
        data = fresh_ticket.data if fresh_ticket else self.ticket_data

        allowed_users = data.get("allowed_users", [])
        if interaction.user.id not in allowed_users:
            await interaction.followup.send("You do not have permission to view this transcript.", ephemeral=True)
            return

        html_url = data.get("html_url")
        if not html_url:
            await interaction.followup.send("HTML file could not be found.", ephemeral=True)
            return

        await interaction.followup.send(f"[Transcript here.]({html_url})", ephemeral=True)


class EditClosingModal(discord.ui.Modal, title="Edit Closing"):
    def __init__(self, ticket_data: dict):
        super().__init__()
        self.ticket_data = ticket_data

        self.new_closing = discord.ui.TextInput(
            label="New Closing",
            style=discord.TextStyle.long,
            default=ticket_data.get("closing", ""),
            max_length=3500
        )
        self.add_item(self.new_closing)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bot = interaction.client
        manager = getattr(bot, "ticket_manager", None)

        ticket = await manager.from_ticket(self.ticket_data["_id"])
        if not ticket:
            await interaction.followup.send("Ticket data not found.", ephemeral=True)
            return

        ticket.data["closing"] = self.new_closing.value

        transcript = await manager.transcript.get(ticket.id)
        exported = await manager.exporter.export(ticket.data, transcript)

        html_str = await manager.exporter.to_html(exported)
        html_archive = await manager.archive.upload_html(ticket.id, html_str)
        if html_archive:
            ticket.data["html_url"] = html_archive["url"]

        await manager.save(ticket)

        embed = interaction.message.embeds[0]
        embed.set_field_at(6, name="closing", value=self.new_closing.value, inline=False)

        new_view = TranscriptView(ticket.data)
        await interaction.message.edit(embed=embed, view=new_view)

        await interaction.followup.send("Closing updated successfully!", ephemeral=True)

transcript = TranscriptManager(kafu, archive=ArchiveUploader(bot, JSON_CHANNEL, ATTACHMENT_CHANNEL))

@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()


bot.run(TOKEN)